"""Compliance audit logs and report generation routes."""

import os
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_client_ip, get_current_org, get_current_user, get_db
from app.models.compliance_report import ComplianceReport
from app.models.user import Organization, User
from app.schemas.compliance import (
    AuditLogListResponse,
    AuditLogResponse,
    ChainVerificationResponse,
    ComplianceReportListResponse,
    ComplianceReportRequest,
    ComplianceReportResponse,
    ComplianceScoreResponse,
    FrameworkScore,
    RequirementScore,
)
from app.services import audit_service
from app.services.compliance_scoring_service import get_framework_scores

router = APIRouter()


@router.get("/frameworks/scores", response_model=ComplianceScoreResponse)
async def get_scores(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ComplianceScoreResponse:
    """Get compliance framework violation scores."""
    raw = await get_framework_scores(db, UUID(str(org.id)), days)
    frameworks = [
        FrameworkScore(
            name=fw["name"],
            total_violations=fw["total_violations"],
            requirements=[
                RequirementScore(name=r["name"], violation_count=r["violation_count"])
                for r in fw["requirements"]
            ],
        )
        for fw in raw["frameworks"]
    ]
    return ComplianceScoreResponse(frameworks=frameworks, period_days=raw["period_days"])


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    action: str | None = None,
    resource_type: str | None = Query(None, alias="resourceType"),
    user_id: UUID | None = Query(None, alias="userId"),
    date_from: datetime | None = Query(None, alias="dateFrom"),
    date_to: datetime | None = Query(None, alias="dateTo"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> AuditLogListResponse:
    """List audit log entries with optional filters."""
    items, total = await audit_service.list_audit_logs(
        db, UUID(str(org.id)), skip, limit, action, resource_type, user_id, date_from, date_to
    )
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(i) for i in items],
        total=total,
    )


@router.get("/audit-logs/verify", response_model=ChainVerificationResponse)
async def verify_audit_chain(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ChainVerificationResponse:
    """Verify the hash chain integrity of audit logs."""
    result = await audit_service.verify_chain_integrity(db, UUID(str(org.id)))
    return ChainVerificationResponse(**result)


@router.get("/audit-logs/{audit_log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    audit_log_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> AuditLogResponse:
    """Get a single audit log entry."""
    entry = await audit_service.get_audit_log(db, UUID(str(org.id)), audit_log_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log entry not found")
    return AuditLogResponse.model_validate(entry)


@router.post("/reports", response_model=ComplianceReportResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_report(
    body: ComplianceReportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org: Organization = Depends(get_current_org),
    client_ip: str = Depends(get_client_ip),
) -> ComplianceReportResponse:
    """Queue a compliance report for generation."""
    report = ComplianceReport(
        org_id=org.id,
        report_type=body.report_type,
        status="pending",
        date_from=body.date_from,
        date_to=body.date_to,
    )
    db.add(report)
    await db.flush()

    await audit_service.write_audit(
        db, UUID(str(org.id)), UUID(str(current_user.id)),
        "report.requested", "compliance_report", UUID(str(report.id)),
        {"report_type": body.report_type}, client_ip,
    )
    await db.commit()
    await db.refresh(report)

    # Queue Celery task
    from app.tasks.compliance import generate_compliance_report
    generate_compliance_report.delay(str(report.id), str(org.id))

    return ComplianceReportResponse.model_validate(report)


@router.get("/reports", response_model=ComplianceReportListResponse)
async def list_reports(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ComplianceReportListResponse:
    """List compliance reports for org."""
    from sqlalchemy import func, select

    count_q = select(func.count(ComplianceReport.id)).where(ComplianceReport.org_id == org.id)
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        select(ComplianceReport)
        .where(ComplianceReport.org_id == org.id)
        .order_by(ComplianceReport.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = list(result.scalars().all())
    return ComplianceReportListResponse(
        items=[ComplianceReportResponse.model_validate(r) for r in items],
        total=total,
    )


@router.get("/reports/{report_id}/download")
async def download_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> FileResponse:
    """Download a completed compliance report CSV."""
    from sqlalchemy import select

    result = await db.execute(
        select(ComplianceReport).where(ComplianceReport.id == report_id, ComplianceReport.org_id == org.id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if str(report.status) != "completed" or not str(report.file_path or ""):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Report not ready for download")

    # Path traversal defense: resolve and verify the file is within the reports directory
    reports_dir = Path("/app/reports").resolve()
    file_path = Path(str(report.file_path)).resolve()
    if not str(file_path).startswith(str(reports_dir)) or not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid report file path")

    return FileResponse(
        path=str(file_path),
        filename=f"{report.report_type}_{report_id}.csv",
        media_type="text/csv",
    )


@router.get("/audit-logs/export/cef")
async def export_audit_logs_cef(
    date_from: datetime | None = Query(None, alias="dateFrom"),
    date_to: datetime | None = Query(None, alias="dateTo"),
    limit: int = Query(default=10000, le=50000),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> Response:
    """Export audit logs in Common Event Format (CEF) for SIEM integration.

    CEF format: CEF:0|AgentGuard|AuditLog|1.0|<action>|<action>|<severity>|<ext>
    """
    items, _ = await audit_service.list_audit_logs(
        db, UUID(str(org.id)), 0, limit, date_from=date_from, date_to=date_to,
    )

    lines: list[str] = []
    for entry in items:
        # CEF severity: 0-3 low, 4-6 medium, 7-8 high, 9-10 critical
        action = str(entry.action)
        sev = "3"
        if "delete" in action or "revoke" in action:
            sev = "7"
        elif "failed" in action:
            sev = "5"

        ext_parts = [
            f"rt={entry.created_at.isoformat() if entry.created_at is not None else ''}",
            f"suser={entry.user_id or ''}",
            f"cs1={entry.resource_type or ''}",
            f"cs1Label=resourceType",
            f"cs2={entry.resource_id or ''}",
            f"cs2Label=resourceId",
            f"src={entry.ip_address or ''}",
        ]
        ext = " ".join(ext_parts)

        line = f"CEF:0|AgentGuard|AuditLog|1.0|{action}|{action}|{sev}|{ext}"
        lines.append(line)

    content = "\n".join(lines)
    return Response(
        content=content,
        media_type="text/plain",
        headers={
            "Content-Disposition": "attachment; filename=audit_logs.cef",
        },
    )
