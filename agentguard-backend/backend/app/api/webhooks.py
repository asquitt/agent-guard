"""Webhook management router."""

# pyright: reportGeneralTypeIssues=false, reportArgumentType=false

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_client_ip, get_current_org, get_db, require_admin, require_permission
from app.core.exceptions import NotFoundError
from app.models.alert import Alert, AlertDestination
from app.models.enums import AlertStatus
from app.models.user import Organization, User
from app.schemas.webhooks import (
    WebhookCreateRequest,
    WebhookListResponse,
    WebhookResponse,
    WebhookUpdateRequest,
)
from app.services import webhook_service

router = APIRouter()


# ---------------------------------------------------------------------------
# CRUD endpoints
# ---------------------------------------------------------------------------


@router.post("/", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    body: WebhookCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
    client_ip: str = Depends(get_client_ip),
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
        user_id=UUID(str(admin_user.id)),
        ip_address=client_ip,
    )
    return WebhookResponse(**webhook_service.to_webhook_response(dest))


@router.get("/", response_model=WebhookListResponse)
async def list_webhooks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("alerts:read")),
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
    _user: User = Depends(require_permission("alerts:read")),
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
    client_ip: str = Depends(get_client_ip),
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
            user_id=UUID(str(admin_user.id)),
            ip_address=client_ip,
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
    client_ip: str = Depends(get_client_ip),
) -> None:
    """Delete a webhook."""
    try:
        await webhook_service.delete_webhook(
            db,
            UUID(str(org.id)),
            webhook_id,
            user_id=UUID(str(admin_user.id)),
            ip_address=client_ip,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


# ---------------------------------------------------------------------------
# Delivery dashboard endpoints
# ---------------------------------------------------------------------------


class DeliveryStatsResponse(BaseModel):
    """Aggregate delivery stats for a webhook."""

    model_config = ConfigDict(populate_by_name=True)

    total: int
    sent: int
    failed: int
    pending: int
    success_rate: float = Field(serialization_alias="successRate")


class DeliveryItem(BaseModel):
    """Single delivery record."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    incident_id: UUID = Field(serialization_alias="incidentId")
    status: str
    error_message: str | None = Field(serialization_alias="errorMessage")
    sent_at: str | None = Field(serialization_alias="sentAt")
    created_at: str = Field(serialization_alias="createdAt")


class DeliveryListResponse(BaseModel):
    items: list[DeliveryItem]
    total: int


@router.get("/{webhook_id}/deliveries/stats", response_model=DeliveryStatsResponse)
async def get_delivery_stats(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("alerts:read")),
    org: Organization = Depends(get_current_org),
) -> DeliveryStatsResponse:
    """Get delivery statistics for a webhook."""
    # Verify webhook belongs to org
    await _get_webhook_or_404(db, org, webhook_id)

    result = await db.execute(
        select(
            func.count(Alert.id).label("total"),
            func.count(case((Alert.status == AlertStatus.SENT.value, 1))).label("sent"),
            func.count(case((Alert.status == AlertStatus.FAILED.value, 1))).label("failed"),
            func.count(case((Alert.status == AlertStatus.PENDING.value, 1))).label("pending"),
        ).where(
            Alert.destination_id == webhook_id,
            Alert.org_id == org.id,
        )
    )
    row = result.one()
    total = row.total or 0
    return DeliveryStatsResponse(
        total=total,
        sent=row.sent or 0,
        failed=row.failed or 0,
        pending=row.pending or 0,
        success_rate=(row.sent / total * 100) if total > 0 else 0.0,
    )


@router.get("/{webhook_id}/deliveries", response_model=DeliveryListResponse)
async def list_deliveries(
    webhook_id: UUID,
    alert_status: str | None = Query(default=None, alias="status", pattern="^(pending|sent|failed)$"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("alerts:read")),
    org: Organization = Depends(get_current_org),
) -> DeliveryListResponse:
    """List delivery attempts for a webhook with optional status filter."""
    await _get_webhook_or_404(db, org, webhook_id)

    base = select(Alert).where(
        Alert.destination_id == webhook_id,
        Alert.org_id == org.id,
    )
    if alert_status:
        base = base.where(Alert.status == alert_status)

    count_q = select(func.count()).select_from(base.subquery())
    count_result = await db.execute(count_q)
    total = count_result.scalar_one()

    result = await db.execute(
        base.order_by(Alert.created_at.desc()).offset(skip).limit(limit)
    )
    alerts = result.scalars().all()

    items = [
        DeliveryItem(
            id=a.id,
            incident_id=a.incident_id,
            status=a.status,
            error_message=a.error_message,
            sent_at=a.sent_at.isoformat() if a.sent_at is not None else None,
            created_at=a.created_at.isoformat() if a.created_at is not None else "",
        )
        for a in alerts
    ]
    return DeliveryListResponse(items=items, total=total)


class ReplayResponse(BaseModel):
    replayed: int
    message: str


@router.post("/{webhook_id}/deliveries/replay", response_model=ReplayResponse)
async def replay_failed_deliveries(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> ReplayResponse:
    """Re-queue all failed deliveries for a webhook via Celery."""
    await _get_webhook_or_404(db, org, webhook_id)

    # Find failed alerts for this webhook (lock rows to prevent duplicate replays)
    result = await db.execute(
        select(Alert).where(
            Alert.destination_id == webhook_id,
            Alert.org_id == org.id,
            Alert.status == AlertStatus.FAILED.value,
        ).with_for_update(skip_locked=True)
    )
    failed_alerts = result.scalars().all()

    if not failed_alerts:
        return ReplayResponse(replayed=0, message="No failed deliveries to replay")

    # Reset to pending so Celery can re-process
    for alert in failed_alerts:
        alert.status = AlertStatus.PENDING.value  # type: ignore[assignment]
        alert.error_message = None  # type: ignore[assignment]
    await db.commit()

    # Queue Celery tasks for each unique incident
    from app.tasks.alerting import send_alerts_for_incident

    incident_ids = {str(a.incident_id) for a in failed_alerts}
    for inc_id in incident_ids:
        send_alerts_for_incident.delay(inc_id, str(org.id))

    return ReplayResponse(
        replayed=len(failed_alerts),
        message=f"Replaying {len(failed_alerts)} deliveries across {len(incident_ids)} incidents",
    )


async def _get_webhook_or_404(
    db: AsyncSession, org: Organization, webhook_id: UUID
) -> AlertDestination:
    """Verify webhook exists and belongs to org, or raise 404."""
    result = await db.execute(
        select(AlertDestination).where(
            AlertDestination.id == webhook_id,
            AlertDestination.org_id == org.id,
            AlertDestination.destination_type == "webhook",
        )
    )
    dest = result.scalar_one_or_none()
    if not dest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )
    return dest
