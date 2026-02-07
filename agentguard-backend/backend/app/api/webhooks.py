"""Webhook management router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db, require_admin
from app.core.exceptions import NotFoundError
from app.models.user import Organization, User
from app.schemas.webhooks import WebhookCreateRequest, WebhookListResponse, WebhookResponse, WebhookUpdateRequest
from app.services import webhook_service

router = APIRouter()


@router.post("/", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    body: WebhookCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> WebhookResponse:
    """Register a webhook endpoint."""
    dest = await webhook_service.create_webhook(
        db,
        UUID(str(org.id)),
        name=body.name,
        url=body.url,
        secret=body.secret,
        event_types=body.event_types,
        min_severity=body.min_severity,
    )
    return WebhookResponse(**webhook_service.to_webhook_response(dest))


@router.get("/", response_model=WebhookListResponse)
async def list_webhooks(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> WebhookListResponse:
    """List webhooks for the current org."""
    items, total = await webhook_service.list_webhooks(db, UUID(str(org.id)), skip, limit)
    return WebhookListResponse(
        items=[WebhookResponse(**webhook_service.to_webhook_response(d)) for d in items],
        total=total,
    )


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> WebhookResponse:
    """Get a single webhook."""
    try:
        dest = await webhook_service.get_webhook(db, UUID(str(org.id)), webhook_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    return WebhookResponse(**webhook_service.to_webhook_response(dest))


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: UUID,
    body: WebhookUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> WebhookResponse:
    """Update a webhook."""
    try:
        dest = await webhook_service.update_webhook(
            db,
            UUID(str(org.id)),
            webhook_id,
            name=body.name,
            url=body.url,
            secret=body.secret,
            event_types=body.event_types,
            min_severity=body.min_severity,
            is_active=body.is_active,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    return WebhookResponse(**webhook_service.to_webhook_response(dest))


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> None:
    """Delete a webhook."""
    try:
        await webhook_service.delete_webhook(db, UUID(str(org.id)), webhook_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
