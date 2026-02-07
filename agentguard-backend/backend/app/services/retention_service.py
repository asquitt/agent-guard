"""Data retention service — archive old records, batch delete from PostgreSQL."""

# pyright: reportCallIssue=false

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit import AuditLog
from app.models.data_archive import DataArchive
from app.models.incident import Incident
from app.models.proxy import ProxyRequest
from app.models.retention_policy import RetentionPolicy
from app.services.archive_storage import ArchiveStorage, LocalArchiveStorage

logger = logging.getLogger(__name__)

TABLE_MAP: dict[str, type] = {
    "proxy_requests": ProxyRequest,
    "incidents": Incident,
    "audit_logs": AuditLog,
}

BATCH_SIZE = settings.RETENTION_BATCH_SIZE


def get_or_create_policy(db: Session, org_id: UUID) -> RetentionPolicy:
    """Get org's retention policy, creating default if none exists."""
    result = db.execute(select(RetentionPolicy).where(RetentionPolicy.org_id == org_id))
    policy = result.scalar_one_or_none()
    if policy is not None:
        return policy

    policy = RetentionPolicy(org_id=org_id)
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def update_policy(
    db: Session,
    org_id: UUID,
    proxy_requests_days: int | None = None,
    incidents_days: int | None = None,
    audit_logs_days: int | None = None,
) -> RetentionPolicy:
    """Update retention policy fields."""
    policy = get_or_create_policy(db, org_id)
    if proxy_requests_days is not None:
        policy.proxy_requests_days = proxy_requests_days  # type: ignore[assignment]
    if incidents_days is not None:
        policy.incidents_days = incidents_days  # type: ignore[assignment]
    if audit_logs_days is not None:
        policy.audit_logs_days = audit_logs_days  # type: ignore[assignment]
    db.commit()
    db.refresh(policy)
    return policy


def archive_table(
    db: Session,
    org_id: UUID,
    table_name: str,
    retention_days: int,
    storage: ArchiveStorage | None = None,
) -> dict[str, Any]:
    """Archive records older than retention_days, then batch-delete from PostgreSQL."""
    if retention_days <= 0:
        return {"skipped": True, "reason": "retention_disabled"}

    model = TABLE_MAP.get(table_name)
    if model is None:
        raise ValueError(f"Unknown table: {table_name}")

    if storage is None:
        storage = LocalArchiveStorage(settings.ARCHIVE_STORAGE_PATH)

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    # Count records to archive
    count_q = (
        select(func.count(model.id))  # type: ignore[attr-defined]
        .where(model.org_id == org_id, model.created_at < cutoff)  # type: ignore[attr-defined]
    )
    total = db.execute(count_q).scalar_one()
    if total == 0:
        return {"archived": 0, "deleted": 0}

    logger.info("Archiving %d records from %s for org %s (cutoff: %s)", total, table_name, org_id, cutoff)

    # Export all qualifying records
    export_q = (
        select(model)
        .where(model.org_id == org_id, model.created_at < cutoff)  # type: ignore[attr-defined]
        .order_by(model.created_at)  # type: ignore[attr-defined]
    )
    rows = db.execute(export_q).scalars().all()
    records = [_model_to_dict(r) for r in rows]

    start_date = min(r["created_at"] for r in records)
    end_date = max(r["created_at"] for r in records)

    metadata = {
        "org_id": str(org_id),
        "table_name": table_name,
        "retention_days": retention_days,
        "record_count": len(records),
        "archived_at": datetime.now(timezone.utc).isoformat(),
    }

    file_path, file_size = storage.write(str(org_id), table_name, records, metadata)

    # Create archive metadata
    archive = DataArchive(
        org_id=org_id,
        table_name=table_name,
        start_date=start_date,
        end_date=end_date,
        file_path=file_path,
        row_count=len(records),
        file_size_bytes=file_size,
        status="completed",
    )
    db.add(archive)
    db.commit()

    # Batch delete
    deleted = 0
    if not settings.RETENTION_DRY_RUN:
        deleted = _batch_delete(db, model, org_id, cutoff)

    logger.info("Retention complete for %s org %s: archived=%d deleted=%d", table_name, org_id, len(records), deleted)
    return {"archived": len(records), "deleted": deleted, "file_path": file_path}


def _batch_delete(db: Session, model: type, org_id: UUID, cutoff: datetime) -> int:
    """Delete records in batches to avoid long table locks."""
    deleted_total = 0
    while True:
        # Subquery to select a batch of IDs
        subq = (
            select(model.id)  # type: ignore[attr-defined]
            .where(model.org_id == org_id, model.created_at < cutoff)  # type: ignore[attr-defined]
            .limit(BATCH_SIZE)
            .scalar_subquery()
        )
        stmt = delete(model).where(model.id.in_(subq))  # type: ignore[attr-defined]
        result = db.execute(stmt)
        batch_count = result.rowcount  # type: ignore[union-attr]
        db.commit()

        if batch_count == 0:
            break
        deleted_total += batch_count
        logger.info("Deleted batch of %d from %s (total: %d)", batch_count, model.__tablename__, deleted_total)

    return deleted_total


def list_archives(
    db: Session,
    org_id: UUID,
    table_name: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[DataArchive], int]:
    """List archives for org with optional table filter."""
    base = select(DataArchive).where(DataArchive.org_id == org_id)
    count_q = select(func.count(DataArchive.id)).where(DataArchive.org_id == org_id)

    if table_name:
        base = base.where(DataArchive.table_name == table_name)
        count_q = count_q.where(DataArchive.table_name == table_name)

    total = db.execute(count_q).scalar_one()
    result = db.execute(base.order_by(DataArchive.created_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all()), total


def get_archive(db: Session, org_id: UUID, archive_id: UUID) -> DataArchive | None:
    """Get single archive, scoped to org."""
    result = db.execute(
        select(DataArchive).where(DataArchive.id == archive_id, DataArchive.org_id == org_id)
    )
    return result.scalar_one_or_none()


def _model_to_dict(record: Any) -> dict[str, Any]:
    """Serialize SQLAlchemy model instance to dict for archival."""
    result: dict[str, Any] = {}
    for col in record.__table__.columns:
        val = getattr(record, col.name)
        if isinstance(val, UUID):
            result[col.name] = str(val)
        elif isinstance(val, datetime):
            result[col.name] = val.isoformat()
        else:
            result[col.name] = val
    return result
