"""Shared audit logging service with hash chain for tamper detection."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


def _compute_entry_hash(prev_hash: str, entry_data: dict[str, Any]) -> str:
    """SHA-256(prev_hash + canonical JSON of entry data)."""
    canonical = json.dumps(entry_data, sort_keys=True, default=str)
    return hashlib.sha256(f"{prev_hash}{canonical}".encode()).hexdigest()


async def _get_prev_hash(db: AsyncSession, org_id: UUID) -> str:
    """Get the most recent entry_hash for this org, or empty string for genesis."""
    result = await db.execute(
        select(AuditLog.entry_hash)
        .where(AuditLog.org_id == org_id, AuditLog.entry_hash.isnot(None))
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return str(row) if row else ""


def _get_prev_hash_sync(org_id: UUID) -> str:
    """Sync version of _get_prev_hash for Celery tasks."""
    with SessionLocal() as db:
        result = db.execute(
            select(AuditLog.entry_hash)
            .where(AuditLog.org_id == org_id, AuditLog.entry_hash.isnot(None))
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return str(row) if row else ""


async def write_audit(
    db: AsyncSession,
    org_id: UUID,
    user_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Write an append-only audit log entry with hash chain."""
    now = datetime.now(timezone.utc)
    prev_hash = await _get_prev_hash(db, org_id)

    entry_data = {
        "org_id": str(org_id),
        "user_id": str(user_id) if user_id else None,
        "action": action,
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id else None,
        "details": details or {},
        "ip_address": ip_address,
        "created_at": now.isoformat(),
    }
    entry_hash = _compute_entry_hash(prev_hash, entry_data)

    entry = AuditLog(
        org_id=org_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        prev_hash=prev_hash or None,
        entry_hash=entry_hash,
        created_at=now,
    )
    db.add(entry)
    await db.flush()


def write_audit_sync(
    org_id: UUID,
    user_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Sync version for Celery tasks."""
    now = datetime.now(timezone.utc)
    prev_hash = _get_prev_hash_sync(org_id)

    entry_data = {
        "org_id": str(org_id),
        "user_id": str(user_id) if user_id else None,
        "action": action,
        "resource_type": resource_type,
        "resource_id": str(resource_id) if resource_id else None,
        "details": details or {},
        "ip_address": ip_address,
        "created_at": now.isoformat(),
    }
    entry_hash = _compute_entry_hash(prev_hash, entry_data)

    with SessionLocal() as db:
        entry = AuditLog(
            org_id=org_id,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            prev_hash=prev_hash or None,
            entry_hash=entry_hash,
            created_at=now,
        )
        db.add(entry)
        db.commit()


async def list_audit_logs(
    db: AsyncSession,
    org_id: UUID,
    skip: int = 0,
    limit: int = 50,
    action: str | None = None,
    resource_type: str | None = None,
    user_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[AuditLog], int]:
    """List audit logs for org with optional filters."""
    base = select(AuditLog).where(AuditLog.org_id == org_id)
    count_q = select(func.count(AuditLog.id)).where(AuditLog.org_id == org_id)

    if action:
        base = base.where(AuditLog.action == action)
        count_q = count_q.where(AuditLog.action == action)
    if resource_type:
        base = base.where(AuditLog.resource_type == resource_type)
        count_q = count_q.where(AuditLog.resource_type == resource_type)
    if user_id:
        base = base.where(AuditLog.user_id == user_id)
        count_q = count_q.where(AuditLog.user_id == user_id)
    if date_from:
        base = base.where(AuditLog.created_at >= date_from)
        count_q = count_q.where(AuditLog.created_at >= date_from)
    if date_to:
        base = base.where(AuditLog.created_at <= date_to)
        count_q = count_q.where(AuditLog.created_at <= date_to)

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(base.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all()), total


async def get_audit_log(db: AsyncSession, org_id: UUID, log_id: UUID) -> AuditLog | None:
    """Get a single audit log entry by ID, scoped to org."""
    result = await db.execute(
        select(AuditLog).where(AuditLog.id == log_id, AuditLog.org_id == org_id)
    )
    return result.scalar_one_or_none()


async def verify_chain_integrity(
    db: AsyncSession, org_id: UUID
) -> dict[str, Any]:
    """Walk the hash chain for an org and verify each entry."""
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.org_id == org_id, AuditLog.entry_hash.isnot(None))
        .order_by(AuditLog.created_at.asc())
    )
    entries = list(result.scalars().all())

    if not entries:
        return {"valid": True, "checked": 0, "broken_at": None}

    for entry in entries:
        expected_prev = ""
        # Find what the prev_hash should be
        if entry.prev_hash:
            expected_prev = str(entry.prev_hash)

        entry_data = {
            "org_id": str(entry.org_id),
            "user_id": str(entry.user_id) if entry.user_id else None,
            "action": str(entry.action),
            "resource_type": str(entry.resource_type),
            "resource_id": str(entry.resource_id) if entry.resource_id else None,
            "details": entry.details if isinstance(entry.details, dict) else {},
            "ip_address": str(entry.ip_address) if entry.ip_address else None,
            "created_at": entry.created_at.isoformat() if entry.created_at else "",
        }
        expected_hash = _compute_entry_hash(expected_prev, entry_data)
        if str(entry.entry_hash) != expected_hash:
            return {"valid": False, "checked": len(entries), "broken_at": str(entry.id)}

    return {"valid": True, "checked": len(entries), "broken_at": None}
