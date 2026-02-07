"""Compliance report generation Celery task."""

import csv
import logging
import os
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.audit import AuditLog
from app.models.compliance_report import ComplianceReport
from app.models.detector import Detector
from app.models.incident import Incident
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

REPORTS_DIR = "/app/reports"


@celery_app.task(
    name="app.tasks.compliance.generate_compliance_report",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def generate_compliance_report(self, report_id_str: str, org_id_str: str) -> dict[str, str]:  # type: ignore[override]
    """Generate a compliance report CSV."""
    report_id = UUID(report_id_str)
    org_id = UUID(org_id_str)

    with SessionLocal() as db:
        report = db.execute(select(ComplianceReport).where(ComplianceReport.id == report_id)).scalar_one_or_none()
        if report is None:
            logger.error("Report %s not found", report_id)
            return {"status": "error", "message": "Report not found"}

        report.status = "generating"  # type: ignore[assignment]
        db.commit()

        try:
            report_type = str(report.report_type)
            date_from = report.date_from
            date_to = report.date_to

            # Ensure output directory exists
            out_dir = os.path.join(REPORTS_DIR, str(org_id))
            os.makedirs(out_dir, exist_ok=True)
            file_path = os.path.join(out_dir, f"{report_id}.csv")

            if report_type == "access_audit":
                _generate_access_audit(db, org_id, date_from, date_to, file_path)
            elif report_type == "incident_summary":
                _generate_incident_summary(db, org_id, date_from, date_to, file_path)
            elif report_type == "detection_efficacy":
                _generate_detection_efficacy(db, org_id, date_from, date_to, file_path)
            elif report_type == "configuration_changes":
                _generate_configuration_changes(db, org_id, date_from, date_to, file_path)
            else:
                raise ValueError(f"Unknown report type: {report_type}")

            file_size = os.path.getsize(file_path)
            report.status = "completed"  # type: ignore[assignment]
            report.file_path = file_path  # type: ignore[assignment]
            report.file_size_bytes = file_size  # type: ignore[assignment]
            report.completed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
            db.commit()

            logger.info("Report %s completed: %s bytes", report_id, file_size)
            return {"status": "completed", "file_path": file_path}

        except Exception as e:
            logger.error("Report %s failed: %s", report_id, e)
            report.status = "failed"  # type: ignore[assignment]
            report.error_message = str(e)[:500]  # type: ignore[assignment]
            db.commit()
            return {"status": "failed", "message": str(e)}


def _generate_access_audit(db, org_id: UUID, date_from, date_to, file_path: str) -> None:  # type: ignore[no-untyped-def]
    """All audit log entries in date range."""
    rows = db.execute(
        select(AuditLog)
        .where(AuditLog.org_id == org_id, AuditLog.created_at >= date_from, AuditLog.created_at <= date_to)
        .order_by(AuditLog.created_at.asc())
    ).scalars().all()

    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "User ID", "Action", "Resource Type", "Resource ID", "IP Address", "Details"])
        for row in rows:
            writer.writerow([
                str(row.created_at), str(row.user_id or ""), str(row.action),
                str(row.resource_type), str(row.resource_id or ""), str(row.ip_address or ""),
                str(row.details or {}),
            ])


def _generate_incident_summary(db, org_id: UUID, date_from, date_to, file_path: str) -> None:  # type: ignore[no-untyped-def]
    """Incidents grouped by severity and status."""
    rows = db.execute(
        select(Incident.severity, Incident.status, func.count(Incident.id))
        .where(Incident.org_id == org_id, Incident.created_at >= date_from, Incident.created_at <= date_to)
        .group_by(Incident.severity, Incident.status)
    ).all()

    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Severity", "Status", "Count"])
        for row in rows:
            writer.writerow([str(row[0]), str(row[1]), int(row[2])])


def _generate_detection_efficacy(db, org_id: UUID, date_from, date_to, file_path: str) -> None:  # type: ignore[no-untyped-def]
    """Incidents grouped by detector."""
    rows = db.execute(
        select(Detector.name, Detector.category, func.count(Incident.id))
        .join(Incident, Incident.detector_id == Detector.id)
        .where(Incident.org_id == org_id, Incident.created_at >= date_from, Incident.created_at <= date_to)
        .group_by(Detector.name, Detector.category)
    ).all()

    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Detector Name", "Category", "Incidents Detected"])
        for row in rows:
            writer.writerow([str(row[0]), str(row[1]), int(row[2])])


def _generate_configuration_changes(db, org_id: UUID, date_from, date_to, file_path: str) -> None:  # type: ignore[no-untyped-def]
    """Audit logs filtered to config-change actions."""
    config_patterns = [
        "detector.%", "alert_destination.%", "sso_config.%", "webhook.%", "api_key.%", "sso.%",
    ]
    base = (
        select(AuditLog)
        .where(AuditLog.org_id == org_id, AuditLog.created_at >= date_from, AuditLog.created_at <= date_to)
    )
    # Filter to config-change actions using OR of LIKE patterns
    from sqlalchemy import or_
    base = base.where(or_(*[AuditLog.action.like(p) for p in config_patterns]))
    rows = db.execute(base.order_by(AuditLog.created_at.asc())).scalars().all()

    with open(file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "User ID", "Action", "Resource Type", "Resource ID", "Details"])
        for row in rows:
            writer.writerow([
                str(row.created_at), str(row.user_id or ""), str(row.action),
                str(row.resource_type), str(row.resource_id or ""), str(row.details or {}),
            ])
