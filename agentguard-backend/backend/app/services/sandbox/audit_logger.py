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


async def verify_chain(
    db: AsyncSession,
    org_id: UUID,
    sandbox_id: UUID,
) -> dict[str, object]:
    """Verify the hash chain integrity for a sandbox's audit logs.

    Returns {valid: bool, total_entries: int, broken_at: int | None, message: str}.
    """
    from app.models.sandbox_execution import SandboxExecution

    # Get execution IDs for this sandbox
    exec_result = await db.execute(
        select(SandboxExecution.id).where(SandboxExecution.sandbox_id == sandbox_id)
    )
    exec_ids = [row[0] for row in exec_result.fetchall()]
    if not exec_ids:
        return {"valid": True, "total_entries": 0, "broken_at": None, "message": "No entries"}

    # Fetch all audit logs in chronological order
    result = await db.execute(
        select(SandboxAuditLog)
        .where(
            SandboxAuditLog.org_id == org_id,
            SandboxAuditLog.execution_id.in_(exec_ids),
        )
        .order_by(SandboxAuditLog.created_at.asc())
    )
    entries = list(result.scalars().all())
    if not entries:
        return {"valid": True, "total_entries": 0, "broken_at": None, "message": "No entries"}

    prev_hash = ""
    for i, entry in enumerate(entries):
        entry_data = {
            "org_id": str(entry.org_id),
            "execution_id": str(entry.execution_id),
            "action_type": entry.action_type,
            "action_detail": entry.action_detail,
            "allowed": entry.allowed,
            "capability_matched": entry.capability_matched,
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else "",
        }
        expected_hash = _compute_entry_hash(prev_hash, entry_data)
        if entry.entry_hash != expected_hash:
            return {
                "valid": False,
                "total_entries": len(entries),
                "broken_at": i,
                "message": f"Hash mismatch at entry {i}",
            }
        prev_hash = entry.entry_hash

    return {
        "valid": True,
        "total_entries": len(entries),
        "broken_at": None,
        "message": f"All {len(entries)} entries verified",
    }
