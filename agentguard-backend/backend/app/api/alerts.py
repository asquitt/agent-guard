"""Alert destination and alert management router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db, require_admin
from app.core.exceptions import NotFoundError
from app.models.user import Organization, User
from app.schemas.alerts import (
    AlertDestinationCreateRequest,
    AlertDestinationListResponse,
    AlertDestinationResponse,
    AlertDestinationUpdateRequest,
    AlertListResponse,
    AlertResponse,
)
from app.services import alert_service

router = APIRouter()


# --- Alert Destinations ---


@router.post(
    "/destinations",
    response_model=AlertDestinationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_destination(
    body: AlertDestinationCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> AlertDestinationResponse:
    """Create an alert destination (Slack, PagerDuty, etc.)."""
    dest = await alert_service.create_destination(
        db=db,
        org_id=UUID(str(org.id)),
        name=body.name,
        destination_type=body.destination_type,
        config=body.config,
    )
    return AlertDestinationResponse.model_validate(dest)


@router.get("/destinations", response_model=AlertDestinationListResponse)
async def list_destinations(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> AlertDestinationListResponse:
    """List alert destinations for the current org."""
    items, total = await alert_service.list_destinations(
        db, UUID(str(org.id)), skip, limit
    )
    return AlertDestinationListResponse(
        items=[AlertDestinationResponse.model_validate(d) for d in items],
        total=total,
    )


@router.patch(
    "/destinations/{dest_id}", response_model=AlertDestinationResponse
)
async def update_destination(
    dest_id: UUID,
    body: AlertDestinationUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> AlertDestinationResponse:
    """Update an alert destination."""
    try:
        dest = await alert_service.update_destination(
            db,
            UUID(str(org.id)),
            dest_id,
            name=body.name,
            is_active=body.is_active,
            config=body.config,
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
    return AlertDestinationResponse.model_validate(dest)


@router.delete(
    "/destinations/{dest_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_destination(
    dest_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> None:
    """Delete an alert destination."""
    try:
        await alert_service.delete_destination(
            db, UUID(str(org.id)), dest_id
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )


@router.post("/destinations/{dest_id}/test")
async def test_destination(
    dest_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> dict[str, str]:
    """Send a test alert to a destination."""
    try:
        error = await alert_service.test_destination(
            db, UUID(str(org.id)), dest_id
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
    if error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=error
        )
    return {"status": "ok", "message": "Test alert sent successfully"}


# --- Alerts ---


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    skip: int = 0,
    limit: int = 50,
    incident_id: UUID | None = None,
    destination_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> AlertListResponse:
    """List alerts with optional filters."""
    items, total = await alert_service.list_alerts(
        db,
        UUID(str(org.id)),
        skip,
        limit,
        incident_id=incident_id,
        destination_id=destination_id,
    )
    return AlertListResponse(
        items=[AlertResponse.model_validate(a) for a in items],
        total=total,
    )
