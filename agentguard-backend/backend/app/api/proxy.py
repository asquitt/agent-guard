"""LLM proxy router — forwards requests to upstream providers."""

import json
import time
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org_from_api_key, get_db
from app.core.exceptions import NotFoundError, ProxyError
from app.models.user import Organization
from app.services import proxy_service

router = APIRouter()

# Lazy singleton httpx client
_http_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    """Get or create the shared httpx client."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(
                max_connections=100, max_keepalive_connections=20
            ),
            follow_redirects=True,
        )
    return _http_client


async def _parse_and_resolve(
    request: Request,
    db: AsyncSession,
    org: Organization,
    endpoint_header: str | None,
) -> tuple[dict[str, Any], str, Any, str, Any]:
    """Shared setup: parse body, resolve endpoint, log request, get API key.

    Returns: (body, path, endpoint, api_key, proxy_req)
    """
    # Parse body
    raw_body = await request.body()
    try:
        body: dict[str, Any] = json.loads(raw_body)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request body: {exc}",
        )

    # Resolve endpoint
    endpoint_id = UUID(endpoint_header) if endpoint_header else None
    try:
        endpoint = await proxy_service.resolve_endpoint(
            db, UUID(str(org.id)), endpoint_id
        )
    except (NotFoundError, ProxyError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )

    # Build path from the request URL
    path = request.url.path.replace("/api/v1/proxy", "")
    model = proxy_service.extract_model_from_body(body)

    # Log request
    proxy_req = await proxy_service.create_request_log(
        db,
        UUID(str(org.id)),
        UUID(str(endpoint.id)),
        "POST",
        path,
        raw_body.decode("utf-8", errors="replace"),
        model,
    )

    # Get upstream API key
    try:
        api_key = proxy_service.get_upstream_api_key(endpoint)
    except ProxyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )

    return body, path, endpoint, api_key, proxy_req


async def _handle_non_streaming(
    client: httpx.AsyncClient,
    target_url: str,
    body: dict[str, Any],
    api_key: str,
    proxy_req: Any,
    db: AsyncSession,
    start_time: float,
) -> JSONResponse:
    """Forward a non-streaming request and log the response."""
    try:
        response = await proxy_service.forward_request(
            client, target_url, body, api_key
        )
    except httpx.TimeoutException:
        latency_ms = int((time.time() - start_time) * 1000)
        await proxy_service.update_request_log(
            db, proxy_req, 504, '{"error":"upstream timeout"}',
            latency_ms, None, None, None,
        )
        return JSONResponse(
            status_code=504,
            content={"error": {"message": "Upstream LLM request timed out", "type": "timeout_error"}},
        )
    except httpx.HTTPError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        await proxy_service.update_request_log(
            db, proxy_req, 502, json.dumps({"error": str(e)}),
            latency_ms, None, None, None,
        )
        return JSONResponse(
            status_code=502,
            content={"error": {"message": f"Upstream LLM error: {e}", "type": "proxy_error"}},
        )

    latency_ms = int((time.time() - start_time) * 1000)
    response_text = response.text

    # Parse response for token usage
    response_data: dict[str, Any] = {}
    if response.status_code == 200:
        try:
            response_data = response.json()
        except (json.JSONDecodeError, ValueError):
            pass

    input_tokens, output_tokens = proxy_service.extract_tokens_from_response(
        response_data
    )
    response_model = response_data.get("model") or proxy_service.extract_model_from_body(body)

    await proxy_service.update_request_log(
        db, proxy_req, response.status_code,
        proxy_service.truncate_body(response_text),
        latency_ms, input_tokens, output_tokens, response_model,
    )

    # Pass upstream response through as-is
    return JSONResponse(
        status_code=response.status_code,
        content=response_data if response_data else json.loads(response_text),
    )


async def _handle_streaming(
    client: httpx.AsyncClient,
    target_url: str,
    body: dict[str, Any],
    api_key: str,
    proxy_req: Any,
    db: AsyncSession,
    start_time: float,
) -> StreamingResponse:
    """Forward a streaming request, passthrough SSE, log after completion."""
    # Inject stream_options to get usage in final chunk
    body.setdefault("stream_options", {})["include_usage"] = True

    async def stream_generator():
        accumulated_content = ""
        input_tokens: int | None = None
        output_tokens: int | None = None
        model_name: str | None = None
        resp_status = 200

        try:
            async with client.stream(
                "POST",
                target_url,
                json=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            ) as response:
                resp_status = response.status_code

                if response.status_code != 200:
                    # Error — yield full error body
                    error_body = b""
                    async for chunk in response.aiter_bytes():
                        error_body += chunk
                        yield chunk
                    latency_ms = int((time.time() - start_time) * 1000)
                    await proxy_service.update_request_log(
                        db, proxy_req, resp_status,
                        error_body.decode("utf-8", errors="replace"),
                        latency_ms, None, None, None,
                    )
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    yield f"{line}\n\n"

                    # Parse SSE data for logging
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            chunk_data = json.loads(line[6:])
                            if model_name is None:
                                model_name = chunk_data.get("model")
                            for choice in chunk_data.get("choices", []):
                                delta = choice.get("delta", {})
                                content = delta.get("content")
                                if content:
                                    accumulated_content += content
                            # Usage in final chunk
                            usage = chunk_data.get("usage")
                            if usage:
                                input_tokens = usage.get("prompt_tokens")
                                output_tokens = usage.get("completion_tokens")
                        except (json.JSONDecodeError, KeyError, TypeError):
                            pass

        except httpx.TimeoutException:
            yield 'data: {"error":"upstream timeout"}\n\n'
            resp_status = 504
        except httpx.HTTPError as e:
            yield f'data: {{"error":"{e}"}}\n\n'
            resp_status = 502

        # Log after stream completes
        latency_ms = int((time.time() - start_time) * 1000)
        response_summary = json.dumps({
            "streamed": True,
            "content_preview": accumulated_content[:500],
            "model": model_name,
        })
        await proxy_service.update_request_log(
            db, proxy_req, resp_status,
            proxy_service.truncate_body(response_summary),
            latency_ms, input_tokens, output_tokens, model_name,
        )

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --- Endpoints ---


@router.post("/v1/chat/completions", response_model=None)
async def proxy_chat_completions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org_from_api_key),
    x_agentguard_endpoint_id: str | None = Header(default=None),
) -> JSONResponse | StreamingResponse:
    """Proxy OpenAI chat completions (streaming + non-streaming)."""
    start_time = time.time()
    body, path, endpoint, api_key, proxy_req = await _parse_and_resolve(
        request, db, org, x_agentguard_endpoint_id
    )

    client = await get_http_client()
    target_url = proxy_service.build_target_url(endpoint, path)

    if body.get("stream"):
        return await _handle_streaming(
            client, target_url, body, api_key, proxy_req, db, start_time
        )
    return await _handle_non_streaming(
        client, target_url, body, api_key, proxy_req, db, start_time
    )


@router.post("/v1/completions", response_model=None)
async def proxy_completions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org_from_api_key),
    x_agentguard_endpoint_id: str | None = Header(default=None),
) -> JSONResponse | StreamingResponse:
    """Proxy OpenAI legacy completions (streaming + non-streaming)."""
    start_time = time.time()
    body, path, endpoint, api_key, proxy_req = await _parse_and_resolve(
        request, db, org, x_agentguard_endpoint_id
    )

    client = await get_http_client()
    target_url = proxy_service.build_target_url(endpoint, path)

    if body.get("stream"):
        return await _handle_streaming(
            client, target_url, body, api_key, proxy_req, db, start_time
        )
    return await _handle_non_streaming(
        client, target_url, body, api_key, proxy_req, db, start_time
    )


@router.post("/v1/embeddings", response_model=None)
async def proxy_embeddings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org_from_api_key),
    x_agentguard_endpoint_id: str | None = Header(default=None),
) -> JSONResponse:
    """Proxy OpenAI embeddings (never streaming)."""
    start_time = time.time()
    body, path, endpoint, api_key, proxy_req = await _parse_and_resolve(
        request, db, org, x_agentguard_endpoint_id
    )

    client = await get_http_client()
    target_url = proxy_service.build_target_url(endpoint, path)

    return await _handle_non_streaming(
        client, target_url, body, api_key, proxy_req, db, start_time
    )
