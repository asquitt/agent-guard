"""Incident management router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_current_user, get_db
from app.core.exceptions import NotFoundError
from app.models.user import Organization, User
from app.schemas.incidents import (
    IncidentActionCreateRequest,
    IncidentActionResponse,
    IncidentDetailResponse,
    IncidentListResponse,
    IncidentResponse,
    IncidentUpdateRequest,
)
from app.services import incident_service

router = APIRouter()


@router.get("/", response_model=IncidentListResponse)
async def list_incidents(
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
    severity: str | None = None,
    category: str | None = None,
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
        incident = await incident_service.get_incident(
            db, UUID(str(org.id)), incident_id
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
    return IncidentDetailResponse.model_validate(incident)


@router.patch("/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: UUID,
    body: IncidentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> IncidentResponse:
    """Update incident status."""
    try:
        incident = await incident_service.update_incident_status(
            db, UUID(str(org.id)), incident_id, body.status
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
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
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        )
    return IncidentActionResponse.model_validate(action)
