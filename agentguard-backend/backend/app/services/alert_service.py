"""Alert destination and alert management service."""

# pyright: reportCallIssue=false

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.alert import Alert, AlertDestination


async def create_destination(
    db: AsyncSession,
    org_id: UUID,
    name: str,
    destination_type: str,
    config: dict[str, Any] | None = None,
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
    count_result = await db.execute(
        select(func.count(AlertDestination.id)).where(
            AlertDestination.org_id == org_id
        )
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(AlertDestination)
        .where(AlertDestination.org_id == org_id)
        .order_by(AlertDestination.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def get_destination(
    db: AsyncSession, org_id: UUID, dest_id: UUID
) -> AlertDestination:
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
) -> AlertDestination:
    """Update alert destination fields."""
    dest = await get_destination(db, org_id, dest_id)
    if name is not None:
        dest.name = name  # type: ignore[assignment]
    if is_active is not None:
        dest.is_active = is_active  # type: ignore[assignment]
    if config is not None:
        dest.config = config  # type: ignore[assignment]
    await db.commit()
    await db.refresh(dest)
    return dest


async def delete_destination(
    db: AsyncSession, org_id: UUID, dest_id: UUID
) -> None:
    """Hard-delete an alert destination."""
    dest = await get_destination(db, org_id, dest_id)
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

    result = await db.execute(
        base.order_by(Alert.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total
