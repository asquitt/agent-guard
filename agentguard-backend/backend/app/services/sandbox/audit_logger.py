"""Immutable audit logging for sandbox actions with hash chain tamper detection.

Follows the same hash-chain pattern as app/services/audit_service.py.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal
from app.models.sandbox_audit_log import SandboxAuditLog

logger = logging.getLogger(__name__)


def _compute_entry_hash(prev_hash: str, entry_data: dict[str, Any]) -> str:
    """SHA-256(prev_hash + canonical JSON of entry data)."""
    canonical = json.dumps(entry_data, sort_keys=True, default=str)
    return hashlib.sha256(f"{prev_hash}{canonical}".encode()).hexdigest()


async def _get_prev_hash(db: AsyncSession, org_id: UUID) -> str:
    """Get the most recent entry_hash for this org's sandbox audit logs."""
    result = await db.execute(
        select(SandboxAuditLog.entry_hash)
        .where(SandboxAuditLog.org_id == org_id, SandboxAuditLog.entry_hash.isnot(None))
        .order_by(SandboxAuditLog.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return str(row) if row else ""


async def log_sandbox_action(
    db: AsyncSession,
    org_id: UUID,
    execution_id: UUID,
    action_type: str,
    action_detail: dict[str, Any],
    allowed: bool,
    capability_matched: str | None = None,
) -> SandboxAuditLog:
    """Write an immutable, hash-chained audit log entry for a sandbox action."""
    prev_hash = await _get_prev_hash(db, org_id)

    entry_data = {
        "org_id": str(org_id),
        "execution_id": str(execution_id),
        "action_type": action_type,
        "action_detail": action_detail,
        "allowed": allowed,
        "capability_matched": capability_matched,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    entry_hash = _compute_entry_hash(prev_hash, entry_data)

    log_entry = SandboxAuditLog(
        org_id=org_id,
        execution_id=execution_id,
        action_type=action_type,
        action_detail=action_detail,
        allowed=allowed,
        capability_matched=capability_matched,
        entry_hash=entry_hash,
    )
    db.add(log_entry)
    await db.flush()
    return log_entry


def log_sandbox_action_sync(
    org_id: UUID,
    execution_id: UUID,
    action_type: str,
    action_detail: dict[str, Any],
    allowed: bool,
    capability_matched: str | None = None,
) -> None:
    """Sync version of log_sandbox_action for Celery tasks."""
    with SessionLocal() as db:
        result = db.execute(
            select(SandboxAuditLog.entry_hash)
            .where(SandboxAuditLog.org_id == org_id, SandboxAuditLog.entry_hash.isnot(None))
            .order_by(SandboxAuditLog.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        prev_hash = str(row) if row else ""

        entry_data = {
            "org_id": str(org_id),
            "execution_id": str(execution_id),
            "action_type": action_type,
            "action_detail": action_detail,
            "allowed": allowed,
            "capability_matched": capability_matched,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        entry_hash = _compute_entry_hash(prev_hash, entry_data)

        log_entry = SandboxAuditLog(
            org_id=org_id,
            execution_id=execution_id,
            action_type=action_type,
            action_detail=action_detail,
            allowed=allowed,
            capability_matched=capability_matched,
            entry_hash=entry_hash,
        )
        db.add(log_entry)
        db.commit()
