"""Incident management service."""

# pyright: reportCallIssue=false

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.audit import AuditLog
from app.models.incident import Incident, IncidentAction


async def list_incidents(
    db: AsyncSession,
    org_id: UUID,
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
    severity: str | None = None,
    category: str | None = None,
    detector_id: str | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
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
    if detector_id:
        base = base.where(Incident.detector_id == UUID(detector_id))
        count_base = count_base.where(Incident.detector_id == UUID(detector_id))
    if search:
        pattern = f"%{search}%"
        base = base.where(
            Incident.title.ilike(pattern) | Incident.description.ilike(pattern)
        )
        count_base = count_base.where(
            Incident.title.ilike(pattern) | Incident.description.ilike(pattern)
        )
    if date_from:
        base = base.where(Incident.created_at >= date_from)
        count_base = count_base.where(Incident.created_at >= date_from)
    if date_to:
        base = base.where(Incident.created_at <= date_to)
        count_base = count_base.where(Incident.created_at <= date_to)

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
    user_id: UUID | None = None,
) -> Incident:
    """Update incident status and log audit trail."""
    incident = await get_incident(db, org_id, incident_id)
    old_status = str(incident.status)
    incident.status = new_status  # type: ignore[assignment]

    if new_status == "resolved":
        incident.resolved_at = func.now()  # type: ignore[assignment]

    await _write_audit(
        db,
        org_id=org_id,
        user_id=user_id,
        action="incident.status_changed",
        resource_type="incident",
        resource_id=incident_id,
        details={"old_status": old_status, "new_status": new_status},
    )

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
    """Add an action to an incident and log audit trail."""
    await get_incident(db, org_id, incident_id)

    action = IncidentAction(
        incident_id=incident_id,
        user_id=user_id,
        action_type=action_type,
        details=details or {},
    )
    db.add(action)

    await _write_audit(
        db,
        org_id=org_id,
        user_id=user_id,
        action=f"incident.action.{action_type}",
        resource_type="incident",
        resource_id=incident_id,
        details={"action_type": action_type, **(details or {})},
    )

    await db.commit()
    await db.refresh(action)
    return action


async def get_stats(
    db: AsyncSession,
    org_id: UUID,
) -> dict[str, Any]:
    """Get aggregate incident counts by severity, category, and status."""
    sev_q = (
        select(Incident.severity, func.count(Incident.id))
        .where(Incident.org_id == org_id)
        .group_by(Incident.severity)
    )
    cat_q = (
        select(Incident.category, func.count(Incident.id))
        .where(Incident.org_id == org_id)
        .group_by(Incident.category)
    )
    stat_q = (
        select(Incident.status, func.count(Incident.id))
        .where(Incident.org_id == org_id)
        .group_by(Incident.status)
    )
    total_q = select(func.count(Incident.id)).where(Incident.org_id == org_id)

    sev_result = await db.execute(sev_q)
    cat_result = await db.execute(cat_q)
    stat_result = await db.execute(stat_q)
    total_result = await db.execute(total_q)

    return {
        "by_severity": {str(r[0]): int(r[1]) for r in sev_result.all()},
        "by_category": {str(r[0]): int(r[1]) for r in cat_result.all()},
        "by_status": {str(r[0]): int(r[1]) for r in stat_result.all()},
        "total": total_result.scalar_one(),
    }


async def bulk_update_status(
    db: AsyncSession,
    org_id: UUID,
    incident_ids: list[UUID],
    new_status: str,
    user_id: UUID | None = None,
) -> int:
    """Bulk update incident statuses. Returns count of updated rows."""
    values: dict[str, Any] = {"status": new_status}
    if new_status == "resolved":
        values["resolved_at"] = func.now()

    stmt = (
        update(Incident)
        .where(Incident.org_id == org_id, Incident.id.in_(incident_ids))
        .values(**values)
    )

    result = await db.execute(stmt)
    updated: int = result.rowcount  # type: ignore[assignment]

    await _write_audit(
        db,
        org_id=org_id,
        user_id=user_id,
        action="incident.bulk_status_changed",
        resource_type="incident",
        resource_id=None,
        details={
            "incident_ids": [str(i) for i in incident_ids],
            "new_status": new_status,
            "updated_count": updated,
        },
    )

    await db.commit()
    return updated


# ------------------------------------------------------------------
# Audit helpers
# ------------------------------------------------------------------


async def _write_audit(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID | None,
    details: dict[str, Any] | None = None,
) -> None:
    """Write an append-only audit log entry."""
    entry = AuditLog(
        org_id=org_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
    )
    db.add(entry)
    await db.flush()
