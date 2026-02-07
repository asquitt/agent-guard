"""LLM proxy forwarding and logging service."""

# pyright: reportCallIssue=false

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, ProxyError
from app.models.proxy import ProxyEndpoint, ProxyRequest
from app.services.providers.pricing import calculate_cost

MAX_BODY_SIZE = 512 * 1024  # 512 KB

# Provider → global settings key mapping
_PROVIDER_KEY_MAP: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google_gemini": "GOOGLE_GEMINI_API_KEY",
    "azure_openai": "AZURE_OPENAI_API_KEY",
    "bedrock": "AWS_ACCESS_KEY_ID",
}


async def resolve_endpoint(
    db: AsyncSession,
    org_id: UUID,
    endpoint_id: UUID | None = None,
    provider: str = "openai",
) -> ProxyEndpoint:
    """Resolve which ProxyEndpoint to forward to.

    If endpoint_id provided, look it up scoped to org.
    Otherwise, get first active endpoint for the given provider.
    """
    if endpoint_id:
        result = await db.execute(
            select(ProxyEndpoint).where(
                ProxyEndpoint.id == endpoint_id,
                ProxyEndpoint.org_id == org_id,
                ProxyEndpoint.is_active.is_(True),
            )
        )
        endpoint = result.scalar_one_or_none()
        if endpoint is None:
            raise NotFoundError(f"Proxy endpoint {endpoint_id} not found or inactive")
        return endpoint

    # Default: first active endpoint for the given provider
    result = await db.execute(
        select(ProxyEndpoint)
        .where(
            ProxyEndpoint.org_id == org_id,
            ProxyEndpoint.provider == provider,
            ProxyEndpoint.is_active.is_(True),
        )
        .order_by(ProxyEndpoint.created_at.asc())
        .limit(1)
    )
    endpoint = result.scalar_one_or_none()
    if endpoint is None:
        raise ProxyError(f"No active {provider} proxy endpoint configured for this organization")
    return endpoint


async def create_request_log(
    db: AsyncSession,
    org_id: UUID,
    endpoint_id: UUID,
    method: str,
    path: str,
    request_body: str,
    model: str | None,
) -> ProxyRequest:
    """Create initial ProxyRequest record before forwarding."""
    proxy_req = ProxyRequest(
        org_id=org_id,
        endpoint_id=endpoint_id,
        method=method,
        path=path,
        request_body=truncate_body(request_body),
        model=model,
    )
    db.add(proxy_req)
    await db.commit()
    await db.refresh(proxy_req)
    return proxy_req


async def update_request_log(
    db: AsyncSession,
    proxy_request: ProxyRequest,
    status_code: int,
    response_body: str,
    latency_ms: int,
    input_tokens: int | None,
    output_tokens: int | None,
    model: str | None,
) -> None:
    """Update ProxyRequest with response data after forwarding."""
    proxy_request.status_code = status_code  # type: ignore[assignment]
    proxy_request.response_body = truncate_body(response_body)  # type: ignore[assignment]
    proxy_request.latency_ms = latency_ms  # type: ignore[assignment]
    proxy_request.input_tokens = input_tokens  # type: ignore[assignment]
    proxy_request.output_tokens = output_tokens  # type: ignore[assignment]
    if model:
        proxy_request.model = model  # type: ignore[assignment]

    # Calculate cost if we have tokens
    if input_tokens is not None and output_tokens is not None and model:
        proxy_request.cost_usd = calculate_cost(model, input_tokens, output_tokens)  # type: ignore[assignment]

    await db.commit()


def extract_model_from_body(body: dict[str, Any]) -> str | None:
    """Extract model name from request body."""
    return body.get("model")


def truncate_body(body: str) -> str:
    """Truncate body if over MAX_BODY_SIZE."""
    if len(body) > MAX_BODY_SIZE:
        return body[:MAX_BODY_SIZE] + "\n[truncated]"
    return body


def get_upstream_api_key(endpoint: ProxyEndpoint) -> str:
    """Get upstream API key from endpoint config, fall back to global.

    Priority:
    1. endpoint.config["api_key"] if set
    2. Global key for the endpoint's provider
    """
    config = endpoint.config  # type: ignore[union-attr]
    if isinstance(config, dict):
        key = config.get("api_key", "")
        if key:
            return str(key)

    provider = str(endpoint.provider)  # type: ignore[union-attr]
    settings_key = _PROVIDER_KEY_MAP.get(provider)
    if settings_key:
        val = getattr(settings, settings_key, "")
        if val:
            return str(val)
        raise ProxyError(f"No {provider} API key configured (set {settings_key})")

    # Fallback for unknown providers
    if settings.OPENAI_API_KEY:
        return settings.OPENAI_API_KEY
    raise ProxyError(f"No API key configured for provider '{provider}'")


def build_target_url(endpoint: ProxyEndpoint, path: str) -> str:
    """Build the full upstream URL from endpoint target_url + path."""
    base = str(endpoint.target_url).rstrip("/")  # type: ignore[union-attr]
    return f"{base}{path}"
