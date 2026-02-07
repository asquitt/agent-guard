"""LLM proxy router — forwards requests to upstream providers."""

# pyright: reportGeneralTypeIssues=false

import json
import time
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_client_ip, get_current_org_from_api_key, get_db
from app.core.exceptions import NotFoundError, ProxyError
from app.models.user import Organization
from app.services import proxy_service
from app.services.billing_service import get_request_limit
from app.services.detection import pipeline as detection_pipeline
from app.services.detection.types import DetectionAction

router = APIRouter()

# Lazy singleton httpx client
_http_client: httpx.AsyncClient | None = None


async def get_http_client() -> httpx.AsyncClient:
    """Get or create the shared httpx client."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            follow_redirects=True,
        )
    return _http_client


async def _parse_and_resolve(
    request: Request,
    db: AsyncSession,
    org: Organization,
    endpoint_header: str | None,
    provider: str = "openai",
) -> tuple[dict[str, Any], str, Any, str, Any]:
    """Shared setup: parse body, resolve endpoint, log request, get API key.

    Returns: (body, path, endpoint, api_key, proxy_req)
    """
    # IP allowlist check (if configured in org settings)
    org_settings: dict[str, Any] = org.settings or {}  # type: ignore[assignment]
    ip_allowlist: list[str] = org_settings.get("ip_allowlist", [])
    if ip_allowlist:
        client_ip = get_client_ip(request)
        if client_ip not in ip_allowlist:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"IP {client_ip} is not in the organization's allowlist",
            )

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
        endpoint = await proxy_service.resolve_endpoint(db, UUID(str(org.id)), endpoint_id, provider=provider)
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

    # Usage limit enforcement
    limit = get_request_limit(org.plan_tier)  # type: ignore[arg-type]
    current_count = org.monthly_request_count or 0
    if limit is not None and current_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Monthly request limit exceeded",
                "limit": limit,
                "current": current_count,
                "upgrade_url": "/dashboard/billing",
            },
        )

    # Increment usage counter
    org.monthly_request_count = current_count + 1  # type: ignore[assignment]
    await db.flush()

    return body, path, endpoint, api_key, proxy_req


async def _handle_non_streaming(
    client: httpx.AsyncClient,
    target_url: str,
    body: dict[str, Any],
    api_key: str,
    proxy_req: Any,
    db: AsyncSession,
    start_time: float,
    org_id: UUID,
) -> JSONResponse:
    """Forward a non-streaming request and log the response."""
    try:
        response = await proxy_service.forward_request(client, target_url, body, api_key)
    except httpx.TimeoutException:
        latency_ms = int((time.time() - start_time) * 1000)
        await proxy_service.update_request_log(
            db,
            proxy_req,
            504,
            '{"error":"upstream timeout"}',
            latency_ms,
            None,
            None,
            None,
        )
        return JSONResponse(
            status_code=504,
            content={"error": {"message": "Upstream LLM request timed out", "type": "timeout_error"}},
        )
    except httpx.HTTPError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        await proxy_service.update_request_log(
            db,
            proxy_req,
            502,
            json.dumps({"error": str(e)}),
            latency_ms,
            None,
            None,
            None,
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

    input_tokens, output_tokens = proxy_service.extract_tokens_from_response(response_data)
    response_model = response_data.get("model") or proxy_service.extract_model_from_body(body)

    await proxy_service.update_request_log(
        db,
        proxy_req,
        response.status_code,
        proxy_service.truncate_body(response_text),
        latency_ms,
        input_tokens,
        output_tokens,
        response_model,
    )

    # Run detection pipeline on successful responses
    if response.status_code == 200:
        decision = await detection_pipeline.run_sync_detectors(
            db,
            org_id,
            json.dumps(body),
            response_text,
            response_model,
            UUID(str(proxy_req.id)),
        )
        await db.commit()

        if decision.action == DetectionAction.BLOCK:
            return JSONResponse(
                status_code=403,
                content={"error": {"message": "Request blocked by security policy", "type": "detection_blocked"}},
            )
        if decision.action == DetectionAction.REDACT and decision.modified_response:
            response_data = json.loads(decision.modified_response)

        await detection_pipeline.queue_async_detectors(db, org_id, UUID(str(proxy_req.id)))

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
    org_id: UUID,
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
                        db,
                        proxy_req,
                        resp_status,
                        error_body.decode("utf-8", errors="replace"),
                        latency_ms,
                        None,
                        None,
                        None,
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
        response_summary = json.dumps(
            {
                "streamed": True,
                "content_preview": accumulated_content[:500],
                "model": model_name,
            }
        )
        await proxy_service.update_request_log(
            db,
            proxy_req,
            resp_status,
            proxy_service.truncate_body(response_summary),
            latency_ms,
            input_tokens,
            output_tokens,
            model_name,
        )

        # Queue async detection for streaming responses
        if resp_status == 200:
            await detection_pipeline.queue_async_detectors(db, org_id, UUID(str(proxy_req.id)))

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
    org_id = UUID(str(org.id))
    body, path, endpoint, api_key, proxy_req = await _parse_and_resolve(request, db, org, x_agentguard_endpoint_id)

    client = await get_http_client()
    target_url = proxy_service.build_target_url(endpoint, path)

    if body.get("stream"):
        return await _handle_streaming(client, target_url, body, api_key, proxy_req, db, start_time, org_id)
    return await _handle_non_streaming(client, target_url, body, api_key, proxy_req, db, start_time, org_id)


@router.post("/v1/completions", response_model=None)
async def proxy_completions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org_from_api_key),
    x_agentguard_endpoint_id: str | None = Header(default=None),
) -> JSONResponse | StreamingResponse:
    """Proxy OpenAI legacy completions (streaming + non-streaming)."""
    start_time = time.time()
    org_id = UUID(str(org.id))
    body, path, endpoint, api_key, proxy_req = await _parse_and_resolve(request, db, org, x_agentguard_endpoint_id)

    client = await get_http_client()
    target_url = proxy_service.build_target_url(endpoint, path)

    if body.get("stream"):
        return await _handle_streaming(client, target_url, body, api_key, proxy_req, db, start_time, org_id)
    return await _handle_non_streaming(client, target_url, body, api_key, proxy_req, db, start_time, org_id)


@router.post("/v1/embeddings", response_model=None)
async def proxy_embeddings(
    request: Request,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org_from_api_key),
    x_agentguard_endpoint_id: str | None = Header(default=None),
) -> JSONResponse:
    """Proxy OpenAI embeddings (never streaming)."""
    start_time = time.time()
    org_id = UUID(str(org.id))
    body, path, endpoint, api_key, proxy_req = await _parse_and_resolve(request, db, org, x_agentguard_endpoint_id)

    client = await get_http_client()
    target_url = proxy_service.build_target_url(endpoint, path)

    return await _handle_non_streaming(client, target_url, body, api_key, proxy_req, db, start_time, org_id)


# --- Anthropic ---


async def _handle_anthropic_non_streaming(
    client: httpx.AsyncClient,
    target_url: str,
    body: dict[str, Any],
    api_key: str,
    proxy_req: Any,
    db: AsyncSession,
    start_time: float,
    org_id: UUID,
) -> JSONResponse:
    """Forward a non-streaming Anthropic request and log the response."""
    try:
        response = await proxy_service.forward_anthropic_request(client, target_url, body, api_key)
    except httpx.TimeoutException:
        latency_ms = int((time.time() - start_time) * 1000)
        await proxy_service.update_request_log(
            db,
            proxy_req,
            504,
            '{"error":"upstream timeout"}',
            latency_ms,
            None,
            None,
            None,
        )
        return JSONResponse(
            status_code=504,
            content={"type": "error", "error": {"type": "timeout_error", "message": "Upstream LLM request timed out"}},
        )
    except httpx.HTTPError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        await proxy_service.update_request_log(
            db,
            proxy_req,
            502,
            json.dumps({"error": str(e)}),
            latency_ms,
            None,
            None,
            None,
        )
        return JSONResponse(
            status_code=502,
            content={"type": "error", "error": {"type": "proxy_error", "message": f"Upstream LLM error: {e}"}},
        )

    latency_ms = int((time.time() - start_time) * 1000)
    response_text = response.text

    response_data: dict[str, Any] = {}
    if response.status_code == 200:
        try:
            response_data = response.json()
        except (json.JSONDecodeError, ValueError):
            pass

    input_tokens, output_tokens = proxy_service.extract_anthropic_tokens(response_data)
    response_model = response_data.get("model") or proxy_service.extract_model_from_body(body)

    await proxy_service.update_request_log(
        db,
        proxy_req,
        response.status_code,
        proxy_service.truncate_body(response_text),
        latency_ms,
        input_tokens,
        output_tokens,
        response_model,
    )

    # Run detection pipeline on successful responses
    if response.status_code == 200:
        decision = await detection_pipeline.run_sync_detectors(
            db,
            org_id,
            json.dumps(body),
            response_text,
            response_model,
            UUID(str(proxy_req.id)),
        )
        await db.commit()

        if decision.action == DetectionAction.BLOCK:
            return JSONResponse(
                status_code=403,
                content={
                    "type": "error",
                    "error": {"type": "detection_blocked", "message": "Request blocked by security policy"},
                },
            )
        if decision.action == DetectionAction.REDACT and decision.modified_response:
            response_data = json.loads(decision.modified_response)

        await detection_pipeline.queue_async_detectors(db, org_id, UUID(str(proxy_req.id)))

    return JSONResponse(
        status_code=response.status_code,
        content=response_data if response_data else json.loads(response_text),
    )


async def _handle_anthropic_streaming(
    client: httpx.AsyncClient,
    target_url: str,
    body: dict[str, Any],
    api_key: str,
    proxy_req: Any,
    db: AsyncSession,
    start_time: float,
    org_id: UUID,
) -> StreamingResponse:
    """Forward an Anthropic streaming request, passthrough SSE, log after."""

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
                    "x-api-key": api_key,
                    "content-type": "application/json",
                    "anthropic-version": "2023-06-01",
                },
                timeout=120.0,
            ) as response:
                resp_status = response.status_code

                if response.status_code != 200:
                    error_body = b""
                    async for chunk in response.aiter_bytes():
                        error_body += chunk
                        yield chunk
                    latency_ms = int((time.time() - start_time) * 1000)
                    await proxy_service.update_request_log(
                        db,
                        proxy_req,
                        resp_status,
                        error_body.decode("utf-8", errors="replace"),
                        latency_ms,
                        None,
                        None,
                        None,
                    )
                    return

                # Anthropic SSE: "event: <type>\ndata: <json>\n\n"
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    yield f"{line}\n\n"

                    if not line.startswith("data: "):
                        continue

                    try:
                        chunk_data = json.loads(line[6:])
                    except (json.JSONDecodeError, ValueError):
                        continue

                    event_type = chunk_data.get("type", "")

                    if event_type == "message_start":
                        msg = chunk_data.get("message", {})
                        if model_name is None:
                            model_name = msg.get("model")
                        usage = msg.get("usage", {})
                        if usage.get("input_tokens"):
                            input_tokens = usage["input_tokens"]

                    elif event_type == "content_block_delta":
                        delta = chunk_data.get("delta", {})
                        if delta.get("type") == "text_delta":
                            text = delta.get("text", "")
                            if text:
                                accumulated_content += text

                    elif event_type == "message_delta":
                        usage = chunk_data.get("usage", {})
                        if usage.get("output_tokens"):
                            output_tokens = usage["output_tokens"]

        except httpx.TimeoutException:
            yield 'event: error\ndata: {"type":"error","error":{"type":"timeout_error","message":"upstream timeout"}}\n\n'
            resp_status = 504
        except httpx.HTTPError as e:
            yield f'event: error\ndata: {{"type":"error","error":{{"type":"proxy_error","message":"{e}"}}}}\n\n'
            resp_status = 502

        latency_ms = int((time.time() - start_time) * 1000)
        response_summary = json.dumps(
            {
                "streamed": True,
                "content_preview": accumulated_content[:500],
                "model": model_name,
            }
        )
        await proxy_service.update_request_log(
            db,
            proxy_req,
            resp_status,
            proxy_service.truncate_body(response_summary),
            latency_ms,
            input_tokens,
            output_tokens,
            model_name,
        )

        # Queue async detection for streaming responses
        if resp_status == 200:
            await detection_pipeline.queue_async_detectors(db, org_id, UUID(str(proxy_req.id)))

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/v1/messages", response_model=None)
async def proxy_anthropic_messages(
    request: Request,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org_from_api_key),
    x_agentguard_endpoint_id: str | None = Header(default=None),
) -> JSONResponse | StreamingResponse:
    """Proxy Anthropic Messages API (streaming + non-streaming)."""
    start_time = time.time()
    org_id = UUID(str(org.id))
    body, _path, endpoint, api_key, proxy_req = await _parse_and_resolve(
        request, db, org, x_agentguard_endpoint_id, provider="anthropic"
    )

    client = await get_http_client()
    target_url = proxy_service.build_target_url(endpoint, "/v1/messages")

    if body.get("stream"):
        return await _handle_anthropic_streaming(client, target_url, body, api_key, proxy_req, db, start_time, org_id)
    return await _handle_anthropic_non_streaming(client, target_url, body, api_key, proxy_req, db, start_time, org_id)
