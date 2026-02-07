"""Daily data retention task — archive old records and delete from PostgreSQL."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.user import Organization
from app.services import retention_service
from app.services.audit_service import write_audit_sync
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.retention.run_retention",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
)
def run_retention(self: Any) -> dict[str, object]:
    """Archive and delete old records for all organizations."""
    logger.info("Starting retention task")

    with SessionLocal() as db:
        orgs = list(db.execute(select(Organization)).scalars().all())

    results: dict[str, object] = {"orgs_processed": 0, "total_archived": 0, "total_deleted": 0, "errors": []}
    errors: list[dict[str, str]] = []

    for org in orgs:
        org_id = UUID(str(org.id))
        try:
            with SessionLocal() as db:
                policy = retention_service.get_or_create_policy(db, org_id)
                tables = {
                    "proxy_requests": int(policy.proxy_requests_days),  # type: ignore[arg-type]
                    "incidents": int(policy.incidents_days),  # type: ignore[arg-type]
                    "audit_logs": int(policy.audit_logs_days),  # type: ignore[arg-type]
                }

            for table_name, retention_days in tables.items():
                try:
                    with SessionLocal() as db:
                        result = retention_service.archive_table(db, org_id, table_name, retention_days)

                    archived = result.get("archived", 0)
                    deleted = result.get("deleted", 0)

                    if archived > 0:
                        results["total_archived"] = int(str(results["total_archived"])) + archived  # type: ignore[assignment]
                        results["total_deleted"] = int(str(results["total_deleted"])) + deleted  # type: ignore[assignment]
                        write_audit_sync(
                            org_id=org_id,
                            user_id=None,
                            action="data.retention",
                            resource_type="retention",
                            details={"table": table_name, "archived": archived, "deleted": deleted},
                            ip_address="system",
                        )

                except Exception:
                    logger.exception("Error archiving %s for org %s", table_name, org_id)
                    errors.append({"org_id": str(org_id), "table": table_name})

            results["orgs_processed"] = int(str(results["orgs_processed"])) + 1  # type: ignore[assignment]

        except Exception:
            logger.exception("Error processing retention for org %s", org_id)
            errors.append({"org_id": str(org_id), "table": "all"})

    results["errors"] = errors
    logger.info("Retention task complete: %s", results)
    return results
