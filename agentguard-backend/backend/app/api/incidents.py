"""Incident management router."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_client_ip, get_current_org, get_current_user, get_db
from app.core.exceptions import NotFoundError
from app.models.user import Organization, User
from app.schemas.incidents import (
    BulkStatusUpdateRequest,
    BulkStatusUpdateResponse,
    IncidentActionCreateRequest,
    IncidentActionResponse,
    IncidentDetailResponse,
    IncidentListResponse,
    IncidentResponse,
    IncidentStatsResponse,
    IncidentUpdateRequest,
)
from app.services import incident_service

router = APIRouter()


@router.get("/stats", response_model=IncidentStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> IncidentStatsResponse:
    """Get aggregate incident statistics."""
    stats = await incident_service.get_stats(db, UUID(str(org.id)))
    return IncidentStatsResponse(**stats)


@router.get("/", response_model=IncidentListResponse)
async def list_incidents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    severity: str | None = None,
    category: str | None = None,
    detector_id: str | None = Query(None, alias="detectorId"),
    search: str | None = Query(None, alias="q"),
    date_from: datetime | None = Query(None, alias="dateFrom"),
    date_to: datetime | None = Query(None, alias="dateTo"),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> IncidentListResponse:
    """List incidents with optional filters."""
    items, total = await incident_service.list_incidents(
        db,
        UUID(str(org.id)),
        skip,
        limit,
        status=status_filter,
        severity=severity,
        category=category,
        detector_id=detector_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    return IncidentListResponse(
        items=[IncidentResponse.model_validate(i) for i in items],
        total=total,
    )


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
async def get_incident(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> IncidentDetailResponse:
    """Get a single incident with its actions."""
    try:
        incident = await incident_service.get_incident(db, UUID(str(org.id)), incident_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    return IncidentDetailResponse.model_validate(incident)


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: UUID,
    body: IncidentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    client_ip: str = Depends(get_client_ip),
) -> IncidentResponse:
    """Update incident status."""
    try:
        incident = await incident_service.update_incident_status(
            db,
            UUID(str(org.id)),
            incident_id,
            body.status,
            user_id=UUID(str(current_user.id)),
            ip_address=client_ip,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    return IncidentResponse.model_validate(incident)


@router.post(
    "/{incident_id}/actions",
    response_model=IncidentActionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_action(
    incident_id: UUID,
    body: IncidentActionCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    client_ip: str = Depends(get_client_ip),
) -> IncidentActionResponse:
    """Add an action to an incident."""
    try:
        action = await incident_service.add_action(
            db,
            UUID(str(org.id)),
            incident_id,
            action_type=body.action_type,
            user_id=UUID(str(current_user.id)),
            details=body.details,
            ip_address=client_ip,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    return IncidentActionResponse.model_validate(action)


@router.post(
    "/bulk-update",
    response_model=BulkStatusUpdateResponse,
)
async def bulk_update_status(
    body: BulkStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    client_ip: str = Depends(get_client_ip),
) -> BulkStatusUpdateResponse:
    """Bulk update incident statuses."""
    updated = await incident_service.bulk_update_status(
        db,
        UUID(str(org.id)),
        body.incident_ids,
        body.status,
        user_id=UUID(str(current_user.id)),
        ip_address=client_ip,
    )
    return BulkStatusUpdateResponse(updated=updated)
