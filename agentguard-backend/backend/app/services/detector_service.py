"""Detector and detector rule management service."""

# pyright: reportCallIssue=false

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.detector import Detector, DetectorRule


async def create_detector(
    db: AsyncSession,
    org_id: UUID,
    name: str,
    category: str,
    action_mode: str,
    config: dict[str, Any] | None = None,
    rules: list[dict[str, Any]] | None = None,
) -> Detector:
    """Create a detector with optional inline rules."""
    detector = Detector(
        org_id=org_id,
        name=name,
        category=category,
        action_mode=action_mode,
        config=config or {},
        is_active=True,
    )
    db.add(detector)
    await db.flush()

    if rules:
        for rule_data in rules:
            rule = DetectorRule(
                detector_id=detector.id,
                name=rule_data["name"],
                rule_type=rule_data["rule_type"],
                parameters=rule_data.get("parameters") or {},
                is_active=rule_data.get("is_active", True),
            )
            db.add(rule)

    await db.commit()

    # Reload with rules
    result = await db.execute(
        select(Detector)
        .options(selectinload(Detector.rules))
        .where(Detector.id == detector.id)
    )
    return result.scalar_one()


async def list_detectors(
    db: AsyncSession,
    org_id: UUID,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Detector], int]:
    """List detectors for org with pagination."""
    count_result = await db.execute(
        select(func.count(Detector.id)).where(Detector.org_id == org_id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(Detector)
        .options(selectinload(Detector.rules))
        .where(Detector.org_id == org_id)
        .order_by(Detector.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def get_detector(
    db: AsyncSession, org_id: UUID, detector_id: UUID
) -> Detector:
    """Get single detector with rules, scoped to org."""
    result = await db.execute(
        select(Detector)
        .options(selectinload(Detector.rules))
        .where(Detector.id == detector_id, Detector.org_id == org_id)
    )
    detector = result.scalar_one_or_none()
    if detector is None:
        raise NotFoundError(f"Detector {detector_id} not found")
    return detector


async def update_detector(
    db: AsyncSession,
    org_id: UUID,
    detector_id: UUID,
    name: str | None = None,
    is_active: bool | None = None,
    action_mode: str | None = None,
    config: dict[str, Any] | None = None,
) -> Detector:
    """Update detector fields."""
    detector = await get_detector(db, org_id, detector_id)
    if name is not None:
        detector.name = name  # type: ignore[assignment]
    if is_active is not None:
        detector.is_active = is_active  # type: ignore[assignment]
    if action_mode is not None:
        detector.action_mode = action_mode  # type: ignore[assignment]
    if config is not None:
        detector.config = config  # type: ignore[assignment]
    await db.commit()
    await db.refresh(detector)
    return detector


async def delete_detector(
    db: AsyncSession, org_id: UUID, detector_id: UUID
) -> None:
    """Hard-delete a detector (cascades to rules)."""
    detector = await get_detector(db, org_id, detector_id)
    await db.delete(detector)
    await db.commit()


async def add_rule(
    db: AsyncSession,
    org_id: UUID,
    detector_id: UUID,
    name: str,
    rule_type: str,
    parameters: dict[str, Any] | None = None,
    is_active: bool = True,
) -> DetectorRule:
    """Add a rule to a detector."""
    # Verify detector exists and belongs to org
    await get_detector(db, org_id, detector_id)

    rule = DetectorRule(
        detector_id=detector_id,
        name=name,
        rule_type=rule_type,
        parameters=parameters or {},
        is_active=is_active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def delete_rule(
    db: AsyncSession, org_id: UUID, detector_id: UUID, rule_id: UUID
) -> None:
    """Delete a rule from a detector."""
    # Verify detector belongs to org
    await get_detector(db, org_id, detector_id)

    result = await db.execute(
        select(DetectorRule).where(
            DetectorRule.id == rule_id,
            DetectorRule.detector_id == detector_id,
        )
    )
    rule = result.scalar_one_or_none()
    if rule is None:
        raise NotFoundError(f"Rule {rule_id} not found")
    await db.delete(rule)
    await db.commit()
