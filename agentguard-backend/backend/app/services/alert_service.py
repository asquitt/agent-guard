"""Alert destination and alert management service."""

# pyright: reportCallIssue=false

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.alert import Alert, AlertDestination
from app.services.alert_delivery import deliver
from app.services.audit_service import write_audit

logger = logging.getLogger(__name__)


async def create_destination(
    db: AsyncSession,
    org_id: UUID,
    name: str,
    destination_type: str,
    config: dict[str, Any] | None = None,
    user_id: UUID | None = None,
    ip_address: str | None = None,
) -> AlertDestination:
    """Create an alert destination."""
    dest = AlertDestination(
        org_id=org_id,
        name=name,
        destination_type=destination_type,
        config=config or {},
        is_active=True,
    )
    db.add(dest)
    await db.flush()
    await write_audit(db, org_id, user_id, "alert_destination.created", "alert_destination", dest.id, {"name": name, "type": destination_type}, ip_address)
    await db.commit()
    await db.refresh(dest)
    return dest


async def list_destinations(
    db: AsyncSession,
    org_id: UUID,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[AlertDestination], int]:
    """List alert destinations for org."""
    count_result = await db.execute(select(func.count(AlertDestination.id)).where(AlertDestination.org_id == org_id))
    total = count_result.scalar_one()

    result = await db.execute(
        select(AlertDestination)
        .where(AlertDestination.org_id == org_id)
        .order_by(AlertDestination.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def get_destination(db: AsyncSession, org_id: UUID, dest_id: UUID) -> AlertDestination:
    """Get single alert destination, scoped to org."""
    result = await db.execute(
        select(AlertDestination).where(
            AlertDestination.id == dest_id,
            AlertDestination.org_id == org_id,
        )
    )
    dest = result.scalar_one_or_none()
    if dest is None:
        raise NotFoundError(f"Alert destination {dest_id} not found")
    return dest


async def update_destination(
    db: AsyncSession,
    org_id: UUID,
    dest_id: UUID,
    name: str | None = None,
    is_active: bool | None = None,
    config: dict[str, Any] | None = None,
    user_id: UUID | None = None,
    ip_address: str | None = None,
) -> AlertDestination:
    """Update alert destination fields."""
    dest = await get_destination(db, org_id, dest_id)
    if name is not None:
        dest.name = name  # type: ignore[assignment]
    if is_active is not None:
        dest.is_active = is_active  # type: ignore[assignment]
    if config is not None:
        dest.config = config  # type: ignore[assignment]
    await write_audit(db, org_id, user_id, "alert_destination.updated", "alert_destination", dest_id, {"name": name}, ip_address)
    await db.commit()
    await db.refresh(dest)
    return dest


async def delete_destination(
    db: AsyncSession, org_id: UUID, dest_id: UUID, user_id: UUID | None = None, ip_address: str | None = None
) -> None:
    """Hard-delete an alert destination."""
    dest = await get_destination(db, org_id, dest_id)
    await write_audit(db, org_id, user_id, "alert_destination.deleted", "alert_destination", dest_id, {"name": str(dest.name)}, ip_address)
    await db.delete(dest)
    await db.commit()


async def list_alerts(
    db: AsyncSession,
    org_id: UUID,
    skip: int = 0,
    limit: int = 50,
    incident_id: UUID | None = None,
    destination_id: UUID | None = None,
) -> tuple[list[Alert], int]:
    """List alerts for org with optional filters."""
    base = select(Alert).where(Alert.org_id == org_id)
    count_base = select(func.count(Alert.id)).where(Alert.org_id == org_id)

    if incident_id:
        base = base.where(Alert.incident_id == incident_id)
        count_base = count_base.where(Alert.incident_id == incident_id)
    if destination_id:
        base = base.where(Alert.destination_id == destination_id)
        count_base = count_base.where(Alert.destination_id == destination_id)

    count_result = await db.execute(count_base)
    total = count_result.scalar_one()

    result = await db.execute(base.order_by(Alert.created_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all()), total


async def trigger_alerts(org_id: UUID, incident_id: UUID) -> str | None:
    """Queue Celery task to send alerts for a new incident. Returns task ID."""
    from app.tasks.alerting import send_alerts_for_incident

    task = send_alerts_for_incident.delay(str(incident_id), str(org_id))
    logger.info("Queued alert task %s for incident %s", task.id, incident_id)
    return str(task.id)


async def test_destination(
    db: AsyncSession,
    org_id: UUID,
    dest_id: UUID,
) -> str | None:
    """Send a test alert to a destination. Returns error message or None."""
    dest = await get_destination(db, org_id, dest_id)
    config = dest.config if isinstance(dest.config, dict) else {}
    dest_type = str(dest.destination_type)

    test_payload: dict[str, Any] = {
        "incident_id": "00000000-0000-0000-0000-000000000000",
        "severity": "info",
        "category": "test",
        "title": "AgentGuard Test Alert",
        "description": "This is a test alert from AgentGuard.",
        "status": "test",
        "action_taken": "",
        "created_at": "",
    }

    return deliver(dest_type, config, test_payload)
