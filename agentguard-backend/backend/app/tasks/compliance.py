"""Compliance report generation Celery task."""

from __future__ import annotations

import csv
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

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

            # Dispatch to the right generator
            generators = {
                "access_audit": _generate_access_audit,
                "incident_summary": _generate_incident_summary,
                "detection_efficacy": _generate_detection_efficacy,
                "configuration_changes": _generate_configuration_changes,
                "sox_governance": _generate_framework_report,
                "pci_dss_security": _generate_framework_report,
                "ffiec_risk": _generate_framework_report,
                "nydfs_500_cyber": _generate_framework_report,
                "dora_ict": _generate_framework_report,
                "eu_ai_act": _generate_framework_report,
            }
            gen = generators.get(report_type)
            if gen is None:
                raise ValueError(f"Unknown report type: {report_type}")
            if gen is _generate_framework_report:
                gen(db, org_id, date_from, date_to, file_path, report_type)
            else:
                gen(db, org_id, date_from, date_to, file_path)

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


# ---------------------------------------------------------------------------
# Framework-specific compliance reports
# ---------------------------------------------------------------------------

# Maps report_type → (display name, framework prefix used in incident metadata,
#   list of (requirement key, description) tuples)
_FRAMEWORK_DEFS: dict[str, tuple[str, str, list[tuple[str, str]]]] = {
    "sox_governance": (
        "SOX AI Governance Report",
        "SOX",
        [
            ("Section 302", "CEO/CFO certification of financial reporting accuracy"),
            ("Section 404", "Internal controls over financial reporting"),
            ("Section 409", "Real-time disclosure of material events"),
        ],
    ),
    "pci_dss_security": (
        "PCI-DSS AI Security Assessment",
        "PCI-DSS",
        [
            ("Req 3", "Protect stored cardholder data"),
            ("Req 4", "Encrypt transmission of cardholder data"),
            ("Req 6", "Develop and maintain secure systems"),
            ("Req 7", "Restrict access by business need to know"),
            ("Req 10", "Track and monitor all access"),
            ("Req 11", "Regularly test security systems"),
        ],
    ),
    "ffiec_risk": (
        "FFIEC AI Risk Assessment",
        "FFIEC",
        [
            ("Management", "Board and management oversight of AI systems"),
            ("Development", "AI system development and acquisition"),
            ("Operations", "AI operational controls and monitoring"),
            ("Support", "AI support and maintenance procedures"),
        ],
    ),
    "nydfs_500_cyber": (
        "NYDFS Part 500 Cybersecurity Report",
        "NYDFS-500",
        [
            ("500.02", "Cybersecurity program requirements"),
            ("500.03", "Cybersecurity policy documentation"),
            ("500.06", "Audit trail maintenance"),
            ("500.07", "Access privilege limitations"),
            ("500.09", "Risk assessment requirements"),
            ("500.14", "Training and monitoring"),
        ],
    ),
    "dora_ict": (
        "DORA ICT Risk Management Report",
        "DORA",
        [
            ("Art 5-6", "ICT risk management framework"),
            ("Art 7", "ICT systems identification and classification"),
            ("Art 8-9", "Protection and prevention measures"),
            ("Art 10-11", "Detection and response capabilities"),
            ("Art 12-14", "Recovery, communication, and learning"),
        ],
    ),
    "eu_ai_act": (
        "EU AI Act High-Risk AI Documentation",
        "EU-AI-ACT",
        [
            ("Art 9", "Risk management system"),
            ("Art 10", "Data and data governance"),
            ("Art 13", "Transparency and information provision"),
            ("Art 14", "Human oversight measures"),
            ("Art 15", "Accuracy, robustness, and cybersecurity"),
        ],
    ),
}


def _generate_framework_report(
    db: Session,  # type: ignore[type-arg]
    org_id: UUID,
    date_from: Any,
    date_to: Any,
    file_path: str,
    report_type: str,
) -> None:
    """Generate a structured compliance report for a specific regulatory framework."""
    title, fw_prefix, requirements = _FRAMEWORK_DEFS[report_type]

    # 1. Fetch all incidents in period
    all_incidents = db.execute(
        select(Incident)
        .where(Incident.org_id == org_id, Incident.created_at >= date_from, Incident.created_at <= date_to)
        .order_by(Incident.created_at.desc())
    ).scalars().all()

    # 2. Filter compliance incidents for this framework
    fw_violations: list[Any] = []
    req_counts: dict[str, int] = defaultdict(int)
    for inc in all_incidents:
        meta = inc.metadata_ if isinstance(inc.metadata_, dict) else {}
        violated = meta.get("violated_requirements", [])
        if not isinstance(violated, list):
            continue
        for entry in violated:
            if not isinstance(entry, str):
                continue
            if entry.startswith(f"{fw_prefix} "):
                fw_violations.append(inc)
                req_name = entry.split(" ", 1)[1] if " " in entry else entry
                req_counts[req_name] += 1
                break

    # 3. Incident summary by category
    category_counts: dict[str, int] = defaultdict(int)
    severity_counts: dict[str, int] = defaultdict(int)
    for inc in all_incidents:
        category_counts[str(inc.category)] += 1
        severity_counts[str(inc.severity)] += 1

    # 4. Active detectors
    detectors = db.execute(
        select(Detector.name, Detector.category, Detector.is_active)
        .where(Detector.org_id == org_id)
    ).all()

    # 5. Audit trail summary
    audit_count = db.execute(
        select(func.count(AuditLog.id))
        .where(AuditLog.org_id == org_id, AuditLog.created_at >= date_from, AuditLog.created_at <= date_to)
    ).scalar_one()

    # 6. Write structured CSV
    with open(file_path, "w", newline="") as f:
        w = csv.writer(f)

        # Executive Summary
        w.writerow(["=== EXECUTIVE SUMMARY ==="])
        w.writerow(["Report", title])
        w.writerow(["Framework", fw_prefix])
        w.writerow(["Period", f"{date_from} to {date_to}"])
        w.writerow(["Generated", datetime.now(timezone.utc).isoformat()])
        w.writerow(["Total Incidents", len(all_incidents)])
        w.writerow(["Framework Violations", len(fw_violations)])
        w.writerow(["Audit Log Entries", audit_count])
        w.writerow([])

        # Requirement Coverage
        w.writerow(["=== REQUIREMENT COVERAGE ==="])
        w.writerow(["Requirement", "Description", "Violations", "Status"])
        for req_key, req_desc in requirements:
            count = req_counts.get(req_key, 0)
            status = "PASS" if count == 0 else "FAIL"
            w.writerow([req_key, req_desc, count, status])
        w.writerow([])

        # Incident Summary by Category
        w.writerow(["=== INCIDENT SUMMARY BY CATEGORY ==="])
        w.writerow(["Category", "Count"])
        for cat, cnt in sorted(category_counts.items(), key=lambda x: -x[1]):
            w.writerow([cat, cnt])
        w.writerow([])

        # Incident Summary by Severity
        w.writerow(["=== INCIDENT SUMMARY BY SEVERITY ==="])
        w.writerow(["Severity", "Count"])
        for sev, cnt in sorted(severity_counts.items(), key=lambda x: -x[1]):
            w.writerow([sev, cnt])
        w.writerow([])

        # Detector Coverage
        w.writerow(["=== DETECTOR COVERAGE ==="])
        w.writerow(["Detector", "Category", "Enabled"])
        for det in detectors:
            w.writerow([str(det[0]), str(det[1]), "Yes" if det[2] else "No"])
        w.writerow([])

        # Framework Violation Details
        w.writerow(["=== FRAMEWORK VIOLATION DETAILS ==="])
        w.writerow(["Incident ID", "Title", "Severity", "Status", "Violated Requirements", "Created"])
        for inc in fw_violations:
            meta = inc.metadata_ if isinstance(inc.metadata_, dict) else {}
            reqs = [r for r in meta.get("violated_requirements", []) if isinstance(r, str) and r.startswith(f"{fw_prefix} ")]
            w.writerow([
                str(inc.id), str(inc.title), str(inc.severity), str(inc.status),
                "; ".join(reqs), str(inc.created_at),
            ])
