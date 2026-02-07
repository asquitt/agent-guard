"""Dashboard metrics service."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident


async def get_metrics(
    db: AsyncSession,
    org_id: UUID,
    recent_limit: int = 10,
) -> dict:
    """Aggregate dashboard metrics for an org."""
    # Total incidents
    total_result = await db.execute(select(func.count(Incident.id)).where(Incident.org_id == org_id))
    total_incidents: int = total_result.scalar_one()

    # Open incidents
    open_result = await db.execute(
        select(func.count(Incident.id)).where(
            Incident.org_id == org_id,
            Incident.status == "open",
        )
    )
    open_incidents: int = open_result.scalar_one()

    # Incidents by status
    status_result = await db.execute(
        select(Incident.status, func.count(Incident.id)).where(Incident.org_id == org_id).group_by(Incident.status)
    )
    incidents_by_status = [{"status": row[0], "count": row[1]} for row in status_result.all()]

    # Incidents by severity
    severity_result = await db.execute(
        select(Incident.severity, func.count(Incident.id)).where(Incident.org_id == org_id).group_by(Incident.severity)
    )
    incidents_by_severity = [{"severity": row[0], "count": row[1]} for row in severity_result.all()]

    # Recent incidents
    recent_result = await db.execute(
        select(Incident).where(Incident.org_id == org_id).order_by(Incident.created_at.desc()).limit(recent_limit)
    )
    recent_incidents = list(recent_result.scalars().all())

    return {
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "incidents_by_status": incidents_by_status,
        "incidents_by_severity": incidents_by_severity,
        "recent_incidents": recent_incidents,
    }
