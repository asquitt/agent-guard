"""LLM proxy forwarding and logging service."""

# pyright: reportCallIssue=false

from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError, ProxyError
from app.models.proxy import ProxyEndpoint, ProxyRequest

# Cost per 1M tokens: (input, output)
OPENAI_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4": (30.00, 60.00),
    "gpt-3.5-turbo": (0.50, 1.50),
    "text-embedding-3-small": (0.02, 0.0),
    "text-embedding-3-large": (0.13, 0.0),
    "text-embedding-ada-002": (0.10, 0.0),
}

ANTHROPIC_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-6": (15.00, 75.00),
    "claude-sonnet-4-5": (3.00, 15.00),
    "claude-haiku-4-5": (0.80, 4.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku": (0.80, 4.00),
    "claude-3-opus": (15.00, 75.00),
    "claude-3-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
}

MAX_BODY_SIZE = 512 * 1024  # 512 KB


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


def _lookup_pricing(model: str, table: dict[str, tuple[float, float]]) -> tuple[float, float] | None:
    """Find pricing by exact match, then longest prefix match."""
    if model in table:
        return table[model]
    for known in sorted(table, key=len, reverse=True):
        if model.startswith(known):
            return table[known]
    return None


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD. Returns 0.0 for unknown models."""
    pricing = _lookup_pricing(model, OPENAI_PRICING) or _lookup_pricing(model, ANTHROPIC_PRICING)
    if pricing is None:
        return 0.0

    input_price, output_price = pricing
    cost = (input_tokens * input_price / 1_000_000) + (output_tokens * output_price / 1_000_000)
    return round(cost, 6)


def extract_model_from_body(body: dict[str, Any]) -> str | None:
    """Extract model name from request body."""
    return body.get("model")


def extract_tokens_from_response(
    body: dict[str, Any],
) -> tuple[int | None, int | None]:
    """Extract input/output token counts from OpenAI response usage."""
    usage = body.get("usage")
    if not usage or not isinstance(usage, dict):
        return None, None
    return usage.get("prompt_tokens"), usage.get("completion_tokens")


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
    if provider == "anthropic":
        if settings.ANTHROPIC_API_KEY:
            return settings.ANTHROPIC_API_KEY
        raise ProxyError("No Anthropic API key configured")

    if settings.OPENAI_API_KEY:
        return settings.OPENAI_API_KEY
    raise ProxyError("No OpenAI API key configured")


def build_target_url(endpoint: ProxyEndpoint, path: str) -> str:
    """Build the full upstream URL from endpoint target_url + path."""
    base = str(endpoint.target_url).rstrip("/")  # type: ignore[union-attr]
    return f"{base}{path}"


def extract_anthropic_tokens(
    body: dict[str, Any],
) -> tuple[int | None, int | None]:
    """Extract input/output token counts from Anthropic response usage."""
    usage = body.get("usage")
    if not usage or not isinstance(usage, dict):
        return None, None
    return usage.get("input_tokens"), usage.get("output_tokens")


async def forward_request(
    client: httpx.AsyncClient,
    target_url: str,
    body: dict[str, Any],
    api_key: str,
) -> httpx.Response:
    """Forward a non-streaming request to the upstream LLM (OpenAI)."""
    return await client.post(
        target_url,
        json=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=120.0,
    )


async def forward_anthropic_request(
    client: httpx.AsyncClient,
    target_url: str,
    body: dict[str, Any],
    api_key: str,
) -> httpx.Response:
    """Forward a non-streaming request to Anthropic."""
    return await client.post(
        target_url,
        json=body,
        headers={
            "x-api-key": api_key,
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        },
        timeout=120.0,
    )
