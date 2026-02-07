"""Incident management service."""

# pyright: reportCallIssue=false

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.incident import Incident, IncidentAction


async def list_incidents(
    db: AsyncSession,
    org_id: UUID,
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
    severity: str | None = None,
    category: str | None = None,
) -> tuple[list[Incident], int]:
    """List incidents for org with optional filters."""
    base = select(Incident).where(Incident.org_id == org_id)
    count_base = select(func.count(Incident.id)).where(Incident.org_id == org_id)

    if status:
        base = base.where(Incident.status == status)
        count_base = count_base.where(Incident.status == status)
    if severity:
        base = base.where(Incident.severity == severity)
        count_base = count_base.where(Incident.severity == severity)
    if category:
        base = base.where(Incident.category == category)
        count_base = count_base.where(Incident.category == category)

    count_result = await db.execute(count_base)
    total = count_result.scalar_one()

    result = await db.execute(
        base.order_by(Incident.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total


async def get_incident(
    db: AsyncSession, org_id: UUID, incident_id: UUID
) -> Incident:
    """Get single incident with actions, scoped to org."""
    result = await db.execute(
        select(Incident)
        .options(selectinload(Incident.actions))
        .where(Incident.id == incident_id, Incident.org_id == org_id)
    )
    incident = result.scalar_one_or_none()
    if incident is None:
        raise NotFoundError(f"Incident {incident_id} not found")
    return incident


async def update_incident_status(
    db: AsyncSession,
    org_id: UUID,
    incident_id: UUID,
    new_status: str,
) -> Incident:
    """Update incident status."""
    incident = await get_incident(db, org_id, incident_id)
    incident.status = new_status  # type: ignore[assignment]

    # Set resolved_at if transitioning to resolved
    if new_status == "resolved":
        incident.resolved_at = func.now()  # type: ignore[assignment]

    await db.commit()
    await db.refresh(incident)
    return incident


async def add_action(
    db: AsyncSession,
    org_id: UUID,
    incident_id: UUID,
    action_type: str,
    user_id: UUID | None = None,
    details: dict[str, Any] | None = None,
) -> IncidentAction:
    """Add an action to an incident."""
    # Verify incident exists and belongs to org
    await get_incident(db, org_id, incident_id)

    action = IncidentAction(
        incident_id=incident_id,
        user_id=user_id,
        action_type=action_type,
        details=details or {},
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action
