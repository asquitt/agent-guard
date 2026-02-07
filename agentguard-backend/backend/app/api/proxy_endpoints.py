"""Proxy endpoint configuration router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db, require_admin
from app.core.exceptions import NotFoundError
from app.models.user import Organization, User
from app.schemas.proxy_endpoints import (
    ProxyEndpointCreateRequest,
    ProxyEndpointListResponse,
    ProxyEndpointResponse,
    ProxyEndpointUpdateRequest,
)
from app.services import proxy_endpoint_service

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/",
    response_model=ProxyEndpointResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def create_proxy_endpoint(
    request: Request,
    body: ProxyEndpointCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> ProxyEndpointResponse:
    """Create a new proxy endpoint configuration. Admin only."""
    endpoint = await proxy_endpoint_service.create_proxy_endpoint(
        db=db,
        org_id=UUID(str(org.id)),
        name=body.name,
        provider=body.provider,
        target_url=body.target_url,
        config=body.config,
    )
    return ProxyEndpointResponse.model_validate(endpoint)


@router.get("/", response_model=ProxyEndpointListResponse)
async def list_proxy_endpoints(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ProxyEndpointListResponse:
    """List proxy endpoints for the current org."""
    items, total = await proxy_endpoint_service.list_proxy_endpoints(
        db, UUID(str(org.id)), skip, limit
    )
    return ProxyEndpointListResponse(
        items=[ProxyEndpointResponse.model_validate(e) for e in items],
        total=total,
    )


@router.get("/{endpoint_id}", response_model=ProxyEndpointResponse)
async def get_proxy_endpoint(
    endpoint_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ProxyEndpointResponse:
    """Get a single proxy endpoint."""
    try:
        endpoint = await proxy_endpoint_service.get_proxy_endpoint(
            db, UUID(str(org.id)), endpoint_id
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
    return ProxyEndpointResponse.model_validate(endpoint)


@router.patch("/{endpoint_id}", response_model=ProxyEndpointResponse)
async def update_proxy_endpoint(
    endpoint_id: UUID,
    body: ProxyEndpointUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> ProxyEndpointResponse:
    """Update a proxy endpoint. Admin only."""
    try:
        endpoint = await proxy_endpoint_service.update_proxy_endpoint(
            db,
            UUID(str(org.id)),
            endpoint_id,
            name=body.name,
            target_url=body.target_url,
            is_active=body.is_active,
            config=body.config,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
    return ProxyEndpointResponse.model_validate(endpoint)


@router.delete("/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proxy_endpoint(
    endpoint_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> None:
    """Delete a proxy endpoint. Admin only."""
    try:
        await proxy_endpoint_service.delete_proxy_endpoint(
            db, UUID(str(org.id)), endpoint_id
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
