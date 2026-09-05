"""LLM proxy router — forwards requests to upstream providers."""

import asyncio
import ipaddress
import json
import logging
import time
from collections.abc import AsyncIterable, AsyncIterator, Awaitable, Callable
from typing import Any
from uuid import UUID

import anyio
import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.types import Receive, Scope, Send

from app.core.circuit_breaker import get_breaker
from app.core.config import settings
from app.core.deps import get_client_ip, get_current_org_from_api_key, get_db
from app.core.exceptions import NotFoundError, ProxyError
from app.core.metrics import PROXY_LATENCY, PROXY_REQUESTS_TOTAL
from app.models.user import Organization
from app.services import proxy_service
from app.services.billing_service import get_request_limit
from app.services.detection import pipeline as detection_pipeline
from app.services.detection.types import DetectionAction
from app.services.providers import get_adapter
from app.services.providers.base import ProviderAdapter
from app.services.rate_limiter import RateLimitExceeded, check_rate_limit, record_request

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
            follow_redirects=False,
        )
    return _http_client


class _ManagedStreamingResponse(StreamingResponse):
    """Finalize resources even when downstream delivery stops before iteration."""

    def __init__(
        self,
        content: AsyncIterable[str | bytes],
        *,
        finalize: Callable[[], Awaitable[None]],
        status_code: int,
        media_type: str,
        headers: dict[str, str],
    ) -> None:
        super().__init__(content, status_code=status_code, media_type=media_type, headers=headers)
        self._finalize = finalize

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        response_error: BaseException | None = None
        try:
            await super().__call__(scope, receive, send)
        except BaseException as exc:
            response_error = exc
            raise
        finally:
            try:
                await self._finalize()
            except Exception:
                if response_error is None:
                    raise
                logger.exception("Failed to finalize upstream streaming response")


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
    db: AsyncSession,
    org_id: UUID,
    header_value: str | None,
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
        proxy_service.validate_provider_target(str(endpoint.provider), str(endpoint.target_url))
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
        db,
        UUID(str(org.id)),
        sandbox_exec_header,
    )

    # Resolve credentials before persisting payload data or attempting egress.
    try:
        api_key = proxy_service.get_upstream_api_key(endpoint)
    except ProxyError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.message,
        )

    # Log request only after the endpoint and credential gates pass.
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
    _raw_count = org.monthly_request_count
    current_count: int = _raw_count if isinstance(_raw_count, int) else 0
    if limit is not None and current_count >= limit:  # type: ignore[reportGeneralTypeIssues]
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
        response = await client.post(
            target_url,
            json=body,
            headers=headers,
            timeout=120.0,
            follow_redirects=False,
        )
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

    if response.is_redirect:
        await proxy_service.update_request_log(
            db,
            proxy_req,
            502,
            '{"error":"upstream redirect rejected"}',
            latency_ms,
            None,
            None,
            None,
        )
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "message": "Upstream provider redirect rejected",
                    "type": "proxy_redirect_rejected",
                }
            },
        )

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
                        db,
                        org_id,
                        json.dumps(body),
                        response_text,
                        response_model,
                        UUID(str(proxy_req.id)),
                        sandbox_execution_id=sandbox_exec_uuid,
                    ),
                    timeout=timeout_s,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Sync detection timed out after %dms for org %s — degraded mode, queuing all async",
                    settings.SYNC_DETECTION_TIMEOUT_MS,
                    org_id,
                )
                decision = None
        else:
            decision = await detection_pipeline.run_sync_detectors(
                db,
                org_id,
                json.dumps(body),
                response_text,
                response_model,
                UUID(str(proxy_req.id)),
                sandbox_execution_id=sandbox_exec_uuid,
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
) -> JSONResponse | StreamingResponse:
    """Forward a streaming request using the provider adapter."""
    body = adapter.inject_stream_options(body)
    headers = adapter.build_stream_headers(api_key)

    try:
        stream_context = client.stream(
            "POST",
            target_url,
            json=body,
            headers=headers,
            timeout=120.0,
            follow_redirects=False,
        )
        response = await stream_context.__aenter__()
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
    except httpx.HTTPError:
        latency_ms = int((time.time() - start_time) * 1000)
        await proxy_service.update_request_log(
            db,
            proxy_req,
            502,
            '{"error":"upstream transport failure"}',
            latency_ms,
            None,
            None,
            None,
        )
        return JSONResponse(
            status_code=502,
            content={"error": {"message": "Upstream LLM request failed", "type": "proxy_error"}},
        )

    async def close_upstream() -> None:
        try:
            await stream_context.__aexit__(None, None, None)
        except Exception:
            logger.warning("Failed to close upstream streaming response")

    if response.is_redirect:
        latency_ms = int((time.time() - start_time) * 1000)
        try:
            await proxy_service.update_request_log(
                db,
                proxy_req,
                502,
                '{"error":"upstream redirect rejected"}',
                latency_ms,
                None,
                None,
                None,
            )
        finally:
            await close_upstream()
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "message": "Upstream provider redirect rejected",
                    "type": "proxy_redirect_rejected",
                }
            },
        )

    accumulated_content = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    model_name: str | None = None
    resp_status = response.status_code
    response_summary = ""
    stream_completed = False
    finalized = False
    finalize_lock = asyncio.Lock()

    async def finalize_stream() -> None:
        nonlocal finalized, resp_status, response_summary

        with anyio.CancelScope(shield=True):
            async with finalize_lock:
                if finalized:
                    return
                finalized = True

                if not stream_completed and resp_status == 200:
                    resp_status = 499
                    response_summary = '{"error":"downstream stream closed"}'

                await close_upstream()
                latency_ms = int((time.time() - start_time) * 1000)
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

                if resp_status == 200 and stream_completed:
                    await detection_pipeline.queue_async_detectors(db, org_id, UUID(str(proxy_req.id)))

    async def stream_generator() -> AsyncIterator[str | bytes]:
        nonlocal accumulated_content, input_tokens, model_name, output_tokens
        nonlocal resp_status, response_summary, stream_completed

        try:
            if response.status_code != 200:
                error_preview = bytearray()
                async for chunk in response.aiter_bytes():
                    remaining = proxy_service.MAX_BODY_SIZE - len(error_preview)
                    if remaining > 0:
                        error_preview.extend(chunk[:remaining])
                    yield chunk
                response_summary = error_preview.decode("utf-8", errors="replace")
                stream_completed = True
            else:
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
                stream_completed = True
                response_summary = json.dumps(
                    {
                        "streamed": True,
                        "content_preview": accumulated_content[:500],
                        "model": model_name,
                    }
                )

        except httpx.TimeoutException:
            yield 'data: {"error":"upstream timeout"}\n\n'
            resp_status = 504
            response_summary = '{"error":"upstream timeout"}'
        except httpx.HTTPError:
            yield 'data: {"error":"upstream transport failure"}\n\n'
            resp_status = 502
            response_summary = '{"error":"upstream transport failure"}'

    return _ManagedStreamingResponse(
        stream_generator(),
        finalize=finalize_stream,
        status_code=response.status_code,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --- Helper to route through adapter ---


def _build_target_or_422(endpoint: Any, path: str) -> str:
    """Translate an egress allowlist rejection into an API validation error."""
    try:
        return proxy_service.build_target_url(endpoint, path)
    except ProxyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.message,
        )


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
        request,
        db,
        org,
        endpoint_header,
        provider=provider,
    )

    # Use the endpoint's actual provider for adapter selection
    actual_provider = str(endpoint.provider) if hasattr(endpoint, "provider") else provider
    adapter = get_adapter(actual_provider)

    # Circuit breaker check — fail fast if provider is down
    breaker = get_breaker(actual_provider)
    if not breaker.allow_request():
        PROXY_REQUESTS_TOTAL.labels(provider=actual_provider, model="", status="circuit_open").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": f"Provider '{actual_provider}' is temporarily unavailable (circuit open)",
                "type": "circuit_breaker",
                "retry_after": int(breaker.recovery_timeout),
            },
            headers={"Retry-After": str(int(breaker.recovery_timeout))},
        )

    target_url = _build_target_or_422(endpoint, path_override or path)
    client = await get_http_client()

    model = proxy_service.extract_model_from_body(body)

    try:
        if body.get("stream"):
            result = await _handle_streaming(
                client, target_url, body, api_key, adapter, proxy_req, db, start_time, org_id
            )
        else:
            result = await _handle_non_streaming(
                client, target_url, body, api_key, adapter, proxy_req, db, start_time, org_id
            )

        breaker.record_success()
        PROXY_REQUESTS_TOTAL.labels(provider=actual_provider, model=model or "", status="success").inc()
        PROXY_LATENCY.labels(provider=actual_provider).observe(time.time() - start_time)
        return result
    except httpx.HTTPError:
        breaker.record_failure()
        PROXY_REQUESTS_TOTAL.labels(provider=actual_provider, model=model or "", status="error").inc()
        PROXY_LATENCY.labels(provider=actual_provider).observe(time.time() - start_time)
        raise


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
        request,
        db,
        org,
        x_agentguard_endpoint_id,
    )

    adapter = get_adapter(str(endpoint.provider) if hasattr(endpoint, "provider") else "openai")
    target_url = _build_target_or_422(endpoint, path)
    client = await get_http_client()

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
        request,
        db,
        org,
        x_agentguard_endpoint_id,
        "anthropic",
        path_override="/v1/messages",
    )


async def _track_sandbox_tokens(db: AsyncSession, org_id: UUID, sandbox_exec_id: str, tokens: int) -> None:
    """Track token usage against a sandbox execution's resource budget."""
    from sqlalchemy import select

    from app.models.sandbox import Sandbox
    from app.models.sandbox_execution import SandboxExecution

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

    # Update token usage (clamp to non-negative to prevent budget bypass)
    raw_usage = execution.resource_usage
    usage: dict[str, Any] = dict(raw_usage) if isinstance(raw_usage, dict) else {}
    usage["tokens_used"] = usage.get("tokens_used", 0) + max(0, tokens)
    execution.resource_usage = usage  # type: ignore[assignment]
    await db.flush()

    # Check if token budget exceeded
    sandbox_result = await db.execute(select(Sandbox).where(Sandbox.id == execution.sandbox_id))
    sandbox = sandbox_result.scalar_one_or_none()
    if sandbox:
        limits = sandbox.resource_limits or {}
        max_tokens = limits.get("max_tokens", 10000)
        if usage["tokens_used"] > max_tokens:
            from app.services.sandbox.sandbox_service import terminate_execution

            await terminate_execution(db, org_id, exec_uuid, reason="token_budget_exceeded")
