"""LLM proxy router — forwards requests to upstream providers."""

# pyright: reportGeneralTypeIssues=false

import asyncio
import ipaddress
import json
import logging
import time
from typing import Any
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_client_ip, get_current_org_from_api_key, get_db
from app.core.exceptions import NotFoundError, ProxyError
from app.models.user import Organization
from app.services import proxy_service
from app.services.billing_service import get_request_limit
from app.services.detection import pipeline as detection_pipeline
from app.services.rate_limiter import RateLimitExceeded, check_rate_limit, record_request
from app.services.detection.types import DetectionAction
from app.services.providers import get_adapter
from app.services.providers.base import ProviderAdapter

logger = logging.getLogger(__name__)

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


def _ip_in_allowlist(client_ip: str, allowlist: list[str]) -> bool:
    """Check if client IP matches any entry in allowlist (supports CIDR)."""
    try:
        addr = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    for entry in allowlist:
        try:
            if "/" in entry:
                if addr in ipaddress.ip_network(entry, strict=False):
                    return True
            elif client_ip == entry:
                return True
        except ValueError:
            continue
    return False


async def _resolve_sandbox_execution(
    db: AsyncSession, org_id: UUID, header_value: str | None,
) -> UUID | None:
    """Validate and resolve X-Sandbox-Execution-Id header."""
    if not header_value:
        return None
    from sqlalchemy import select
    from app.models.sandbox_execution import SandboxExecution

    exec_id = UUID(header_value)
    result = await db.execute(
        select(SandboxExecution.id).where(
            SandboxExecution.id == exec_id,
            SandboxExecution.org_id == org_id,
            SandboxExecution.status == "running",
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Sandbox execution {header_value} not found or not running",
        )
    return exec_id


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
        if not _ip_in_allowlist(client_ip, ip_allowlist):
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

    # Resolve sandbox execution (optional header)
    sandbox_exec_header = request.headers.get("x-sandbox-execution-id")
    sandbox_execution_id = await _resolve_sandbox_execution(
        db, UUID(str(org.id)), sandbox_exec_header,
    )

    # Log request
    proxy_req = await proxy_service.create_request_log(
        db,
        UUID(str(org.id)),
        UUID(str(endpoint.id)),
        "POST",
        path,
        raw_body.decode("utf-8", errors="replace"),
        model,
        sandbox_execution_id=sandbox_execution_id,
    )

    # Get upstream API key
    try:
        api_key = proxy_service.get_upstream_api_key(endpoint)
    except ProxyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )

    # Sliding-window rate limit (Redis)
    org_id_str = str(org.id)
    org_rate_settings: dict[str, Any] = org_settings.get("rate_limits", {})
    try:
        await check_rate_limit(
            org_id_str,
            requests_per_minute=org_rate_settings.get("rpm") or settings.RATE_LIMIT_RPM or None,
            requests_per_hour=org_rate_settings.get("rph") or settings.RATE_LIMIT_RPH or None,
            requests_per_day=org_rate_settings.get("rpd") or settings.RATE_LIMIT_RPD or None,
        )
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": f"Rate limit exceeded: {exc.current}/{exc.limit} per {exc.window}",
                "limit": exc.limit,
                "window": exc.window,
                "current": exc.current,
                "retry_after": exc.retry_after,
            },
            headers={"Retry-After": str(exc.retry_after)},
        )

    # Usage limit enforcement (monthly billing cap)
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

    # Increment usage counter + record for rate limiting
    org.monthly_request_count = current_count + 1  # type: ignore[assignment]
    await db.flush()
    await record_request(org_id_str)

    return body, path, endpoint, api_key, proxy_req


async def _handle_non_streaming(
    client: httpx.AsyncClient,
    target_url: str,
    body: dict[str, Any],
    api_key: str,
    adapter: ProviderAdapter,
    proxy_req: Any,
    db: AsyncSession,
    start_time: float,
    org_id: UUID,
) -> JSONResponse:
    """Forward a non-streaming request using the provider adapter."""
    headers = adapter.build_headers(api_key)

    try:
        response = await client.post(target_url, json=body, headers=headers, timeout=120.0)
    except httpx.TimeoutException:
        latency_ms = int((time.time() - start_time) * 1000)
        await proxy_service.update_request_log(
            db, proxy_req, 504, '{"error":"upstream timeout"}', latency_ms, None, None, None,
        )
        return JSONResponse(
            status_code=504,
            content={"error": {"message": "Upstream LLM request timed out", "type": "timeout_error"}},
        )
    except httpx.HTTPError as e:
        latency_ms = int((time.time() - start_time) * 1000)
        await proxy_service.update_request_log(
            db, proxy_req, 502, json.dumps({"error": str(e)}), latency_ms, None, None, None,
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

    input_tokens, output_tokens = adapter.extract_tokens(response_data)
    response_model = response_data.get("model") or proxy_service.extract_model_from_body(body)

    await proxy_service.update_request_log(
        db, proxy_req, response.status_code, proxy_service.truncate_body(response_text),
        latency_ms, input_tokens, output_tokens, response_model,
    )

    # Run detection pipeline on successful responses
    if response.status_code == 200:
        # Track sandbox token usage if sandboxed
        sandbox_exec_id = str(proxy_req.sandbox_execution_id) if proxy_req.sandbox_execution_id else None
        if sandbox_exec_id and (input_tokens or output_tokens):
            try:
                await _track_sandbox_tokens(db, org_id, sandbox_exec_id, (input_tokens or 0) + (output_tokens or 0))
            except Exception:
                logger.warning("Failed to track sandbox tokens for %s", sandbox_exec_id)

        timeout_s = settings.SYNC_DETECTION_TIMEOUT_MS / 1000.0

        sandbox_exec_uuid = UUID(sandbox_exec_id) if sandbox_exec_id else None

        if settings.DEGRADED_MODE_ENABLED and timeout_s > 0:
            try:
                decision = await asyncio.wait_for(
                    detection_pipeline.run_sync_detectors(
                        db, org_id, json.dumps(body), response_text, response_model,
                        UUID(str(proxy_req.id)), sandbox_execution_id=sandbox_exec_uuid,
                    ),
                    timeout=timeout_s,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Sync detection timed out after %dms for org %s — degraded mode, queuing all async",
                    settings.SYNC_DETECTION_TIMEOUT_MS, org_id,
                )
                decision = None
        else:
            decision = await detection_pipeline.run_sync_detectors(
                db, org_id, json.dumps(body), response_text, response_model,
                UUID(str(proxy_req.id)), sandbox_execution_id=sandbox_exec_uuid,
            )

        if decision is not None:
            await db.commit()
            if decision.action == DetectionAction.BLOCK:
                return JSONResponse(
                    status_code=403,
                    content={"error": {"message": "Request blocked by security policy", "type": "detection_blocked"}},
                )
            if decision.action == DetectionAction.REDACT and decision.modified_response:
                response_data = json.loads(decision.modified_response)

        # Always queue async detectors (handles both normal + degraded mode)
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
    adapter: ProviderAdapter,
    proxy_req: Any,
    db: AsyncSession,
    start_time: float,
    org_id: UUID,
) -> StreamingResponse:
    """Forward a streaming request using the provider adapter."""
    body = adapter.inject_stream_options(body)
    headers = adapter.build_stream_headers(api_key)

    async def stream_generator():
        accumulated_content = ""
        input_tokens: int | None = None
        output_tokens: int | None = None
        model_name: str | None = None
        resp_status = 200

        try:
            async with client.stream(
                "POST", target_url, json=body, headers=headers, timeout=120.0,
            ) as response:
                resp_status = response.status_code

                if response.status_code != 200:
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

                    # Parse via adapter
                    chunk_result = adapter.parse_stream_chunk(line)
                    if chunk_result.model and model_name is None:
                        model_name = chunk_result.model
                    if chunk_result.content:
                        accumulated_content += chunk_result.content
                    if chunk_result.input_tokens is not None:
                        input_tokens = chunk_result.input_tokens
                    if chunk_result.output_tokens is not None:
                        output_tokens = chunk_result.output_tokens

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
            db, proxy_req, resp_status, proxy_service.truncate_body(response_summary),
            latency_ms, input_tokens, output_tokens, model_name,
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


# --- Helper to route through adapter ---


async def _proxy_request(
    request: Request,
    db: AsyncSession,
    org: Organization,
    endpoint_header: str | None,
    provider: str,
    path_override: str | None = None,
) -> JSONResponse | StreamingResponse:
    """Unified proxy handler: resolve endpoint, pick adapter, forward."""
    start_time = time.time()
    org_id = UUID(str(org.id))
    body, path, endpoint, api_key, proxy_req = await _parse_and_resolve(
        request, db, org, endpoint_header, provider=provider,
    )

    # Use the endpoint's actual provider for adapter selection
    actual_provider = str(endpoint.provider) if hasattr(endpoint, "provider") else provider
    adapter = get_adapter(actual_provider)

    client = await get_http_client()
    target_url = proxy_service.build_target_url(endpoint, path_override or path)

    if body.get("stream"):
        return await _handle_streaming(client, target_url, body, api_key, adapter, proxy_req, db, start_time, org_id)
    return await _handle_non_streaming(client, target_url, body, api_key, adapter, proxy_req, db, start_time, org_id)


# --- Endpoints (backward-compatible) ---


@router.post("/v1/chat/completions", response_model=None)
async def proxy_chat_completions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org_from_api_key),
    x_agentguard_endpoint_id: str | None = Header(default=None),
) -> JSONResponse | StreamingResponse:
    """Proxy OpenAI chat completions (streaming + non-streaming)."""
    return await _proxy_request(request, db, org, x_agentguard_endpoint_id, "openai")


@router.post("/v1/completions", response_model=None)
async def proxy_completions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org_from_api_key),
    x_agentguard_endpoint_id: str | None = Header(default=None),
) -> JSONResponse | StreamingResponse:
    """Proxy OpenAI legacy completions (streaming + non-streaming)."""
    return await _proxy_request(request, db, org, x_agentguard_endpoint_id, "openai")


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
    body, path, endpoint, api_key, proxy_req = await _parse_and_resolve(
        request, db, org, x_agentguard_endpoint_id,
    )

    adapter = get_adapter(str(endpoint.provider) if hasattr(endpoint, "provider") else "openai")
    client = await get_http_client()
    target_url = proxy_service.build_target_url(endpoint, path)

    return await _handle_non_streaming(client, target_url, body, api_key, adapter, proxy_req, db, start_time, org_id)


@router.post("/v1/messages", response_model=None)
async def proxy_anthropic_messages(
    request: Request,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org_from_api_key),
    x_agentguard_endpoint_id: str | None = Header(default=None),
) -> JSONResponse | StreamingResponse:
    """Proxy Anthropic Messages API (streaming + non-streaming)."""
    return await _proxy_request(
        request, db, org, x_agentguard_endpoint_id, "anthropic", path_override="/v1/messages",
    )


async def _track_sandbox_tokens(
    db: AsyncSession, org_id: UUID, sandbox_exec_id: str, tokens: int
) -> None:
    """Track token usage against a sandbox execution's resource budget."""
    from sqlalchemy import select
    from app.models.sandbox_execution import SandboxExecution
    from app.models.sandbox import Sandbox

    exec_uuid = UUID(sandbox_exec_id)
    result = await db.execute(
        select(SandboxExecution).where(
            SandboxExecution.id == exec_uuid,
            SandboxExecution.org_id == org_id,
        )
    )
    execution = result.scalar_one_or_none()
    if not execution:
        return

    # Update token usage
    usage = execution.resource_usage or {}
    usage["tokens_used"] = usage.get("tokens_used", 0) + tokens
    execution.resource_usage = usage
    await db.flush()

    # Check if token budget exceeded
    sandbox_result = await db.execute(
        select(Sandbox).where(Sandbox.id == execution.sandbox_id)
    )
    sandbox = sandbox_result.scalar_one_or_none()
    if sandbox:
        limits = sandbox.resource_limits or {}
        max_tokens = limits.get("max_tokens", 10000)
        if usage["tokens_used"] > max_tokens:
            from app.services.sandbox.sandbox_service import terminate_execution
            await terminate_execution(
                db, org_id, exec_uuid, reason="token_budget_exceeded"
            )
