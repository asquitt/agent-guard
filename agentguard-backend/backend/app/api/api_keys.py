"""API key management router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db, require_admin
from app.core.exceptions import NotFoundError
from app.models.user import Organization, User
from app.schemas.api_keys import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
    ApiKeyResponse,
    ApiKeyUpdateRequest,
)
from app.services import api_key_service

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def create_api_key(
    request: Request,
    body: ApiKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> ApiKeyCreateResponse:
    """Generate a new API key. Full key returned ONCE."""
    api_key, full_key = await api_key_service.create_api_key(
        db=db,
        org_id=UUID(str(org.id)),
        name=body.name,
        scopes=body.scopes,
        expires_at=body.expires_at,
    )
    response = ApiKeyCreateResponse.model_validate(api_key)
    response.key = full_key
    return response


@router.get("/", response_model=ApiKeyListResponse)
async def list_api_keys(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> ApiKeyListResponse:
    """List API keys for the current org. Never returns full keys."""
    items, total = await api_key_service.list_api_keys(db, UUID(str(org.id)), skip, limit)
    return ApiKeyListResponse(
        items=[ApiKeyResponse.model_validate(k) for k in items],
        total=total,
    )


@router.delete("/{key_id}", response_model=ApiKeyResponse)
async def revoke_api_key(
    key_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> ApiKeyResponse:
    """Revoke (soft-delete) an API key."""
    try:
        api_key = await api_key_service.revoke_api_key(db, UUID(str(org.id)), key_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    return ApiKeyResponse.model_validate(api_key)


@router.patch("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: UUID,
    body: ApiKeyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> ApiKeyResponse:
    """Update API key name and/or scopes."""
    try:
        api_key = await api_key_service.update_api_key(
            db, UUID(str(org.id)), key_id, name=body.name, scopes=body.scopes
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    return ApiKeyResponse.model_validate(api_key)
