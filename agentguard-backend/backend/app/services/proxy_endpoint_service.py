"""Proxy endpoint configuration service."""

# pyright: reportCallIssue=false

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.proxy import ProxyEndpoint
from app.services.proxy_endpoint_security import validate_endpoint_config, validate_provider_target


async def create_proxy_endpoint(
    db: AsyncSession,
    org_id: UUID,
    name: str,
    provider: str,
    target_url: str,
    config: dict[str, Any] | None = None,
) -> ProxyEndpoint:
    """Create a new proxy endpoint configuration."""
    canonical_config = validate_endpoint_config(config)
    normalized_target = validate_provider_target(provider, target_url)
    endpoint = ProxyEndpoint(
        org_id=org_id,
        name=name,
        provider=provider,
        target_url=normalized_target,
        config=canonical_config,
        is_active=True,
    )
    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)
    return endpoint


async def list_proxy_endpoints(
    db: AsyncSession,
    org_id: UUID,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[ProxyEndpoint], int]:
    """List proxy endpoints for org with pagination."""
    count_result = await db.execute(select(func.count(ProxyEndpoint.id)).where(ProxyEndpoint.org_id == org_id))
    total = count_result.scalar_one()

    result = await db.execute(
        select(ProxyEndpoint)
        .where(ProxyEndpoint.org_id == org_id)
        .order_by(ProxyEndpoint.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def get_proxy_endpoint(db: AsyncSession, org_id: UUID, endpoint_id: UUID) -> ProxyEndpoint:
    """Get single proxy endpoint scoped to org."""
    result = await db.execute(
        select(ProxyEndpoint).where(
            ProxyEndpoint.id == endpoint_id,
            ProxyEndpoint.org_id == org_id,
        )
    )
    endpoint = result.scalar_one_or_none()
    if endpoint is None:
        raise NotFoundError(f"Proxy endpoint {endpoint_id} not found")
    return endpoint


async def update_proxy_endpoint(
    db: AsyncSession,
    org_id: UUID,
    endpoint_id: UUID,
    name: str | None = None,
    target_url: str | None = None,
    is_active: bool | None = None,
    config: dict[str, Any] | None = None,
) -> ProxyEndpoint:
    """Update proxy endpoint fields."""
    endpoint = await get_proxy_endpoint(db, org_id, endpoint_id)
    normalized_target = None
    if target_url is not None:
        normalized_target = validate_provider_target(str(endpoint.provider), target_url)
    canonical_config = None
    if config is not None:
        canonical_config = validate_endpoint_config(config)

    if name is not None:
        endpoint.name = name  # type: ignore[assignment]
    if normalized_target is not None:
        endpoint.target_url = normalized_target  # type: ignore[assignment]
    if is_active is not None:
        endpoint.is_active = is_active  # type: ignore[assignment]
    if canonical_config is not None:
        endpoint.config = canonical_config  # type: ignore[assignment]
    await db.commit()
    await db.refresh(endpoint)
    return endpoint


async def delete_proxy_endpoint(db: AsyncSession, org_id: UUID, endpoint_id: UUID) -> None:
    """Hard-delete a proxy endpoint."""
    endpoint = await get_proxy_endpoint(db, org_id, endpoint_id)
    await db.delete(endpoint)
    await db.commit()
