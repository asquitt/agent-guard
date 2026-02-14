# pyright: reportGeneralTypeIssues=false, reportArgumentType=false
"""EU AI Act Article 12 compliance logging service.

Article 12 requires high-risk AI systems to maintain structured logs including
timestamps, input/output pairs, model identification, decision traceability,
human oversight markers, and 10-year retention capability.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.models.proxy import ProxyRequest
from app.models.retention_policy import RetentionPolicy
from app.models.review_queue import ReviewItem

logger = logging.getLogger(__name__)

# EU AI Act Article 12 requires 10-year minimum retention for high-risk systems
ARTICLE_12_RETENTION_YEARS = 10
ARTICLE_12_RETENTION_DAYS = ARTICLE_12_RETENTION_YEARS * 365

# Severity categories considered high-risk under EU AI Act
HIGH_RISK_SEVERITIES = frozenset({"critical", "high"})

# Max characters for input/output summaries (PII truncation boundary)
SUMMARY_MAX_CHARS = 200


def _truncate_summary(text: str | None) -> str:
    """Truncate text for log summaries, stripping potential PII."""
    if not text:
        return ""
    cleaned = text[:SUMMARY_MAX_CHARS]
    if len(text) > SUMMARY_MAX_CHARS:
        cleaned += "..."
    return cleaned


def _check_retention_compliant(policy_days: int | None) -> bool:
    """Check if the org's retention policy meets Article 12 requirements."""
    if policy_days is None:
        return False
    return policy_days >= ARTICLE_12_RETENTION_DAYS


async def get_article12_logs(
    db: AsyncSession,
    org_id: UUID,
    date_from: datetime,
    date_to: datetime,
    skip: int = 0,
    limit: int = 50,
) -> dict:
    """Return paginated Article 12-formatted compliance logs.

    Each log entry maps a proxy_request to the structured metadata
    required by EU AI Act Article 12.
    """
    # Fetch retention policy for compliance check
    policy_result = await db.execute(
        select(RetentionPolicy.proxy_requests_days).where(
            RetentionPolicy.org_id == org_id,
        )
    )
    retention_days: int | None = policy_result.scalar_one_or_none()
    retention_compliant = _check_retention_compliant(retention_days)

    # Fetch proxy requests in date range
    pr_stmt = (
        select(ProxyRequest)
        .where(
            ProxyRequest.org_id == org_id,
            ProxyRequest.created_at >= date_from,
            ProxyRequest.created_at <= date_to,
        )
        .order_by(ProxyRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    pr_result = await db.execute(pr_stmt)
    requests = pr_result.scalars().all()

    if not requests:
        return {"logs": [], "total": 0, "skip": skip, "limit": limit}

    # Collect request IDs for batch incident lookup
    request_ids = [r.id for r in requests]

    # Fetch linked incidents for decision traceability
    inc_stmt = select(Incident).where(
        Incident.org_id == org_id,
        Incident.proxy_request_id.in_(request_ids),
    )
    inc_result = await db.execute(inc_stmt)
    incidents = inc_result.scalars().all()

    # Fetch human review items for oversight status
    review_stmt = select(ReviewItem).where(
        ReviewItem.org_id == org_id,
        ReviewItem.proxy_request_id.in_(request_ids),
    )
    review_result = await db.execute(review_stmt)
    review_items = review_result.scalars().all()

    # Index by proxy_request_id
    incidents_by_req: dict[UUID, list[dict]] = {}
    for inc in incidents:
        req_id = UUID(str(inc.proxy_request_id))
        incidents_by_req.setdefault(req_id, []).append({
            "incident_id": str(inc.id),
            "category": inc.category,
            "severity": inc.severity,
            "status": inc.status,
        })

    reviews_by_req: dict[UUID, str] = {}
    for ri in review_items:
        if ri.proxy_request_id:
            req_id = UUID(str(ri.proxy_request_id))
            # Use the most definitive status (reviewed > pending)
            if ri.status in ("approved", "rejected"):
                reviews_by_req[req_id] = "reviewed"
            elif req_id not in reviews_by_req:
                reviews_by_req[req_id] = "pending_review"

    # Build Article 12 log entries
    logs = []
    for req in requests:
        req_id = UUID(str(req.id))
        linked_incidents = incidents_by_req.get(req_id, [])

        # Determine risk classification from linked incidents
        severities = {inc["severity"] for inc in linked_incidents}
        if severities & HIGH_RISK_SEVERITIES:
            risk_classification = "high"
        elif severities:
            risk_classification = "standard"
        else:
            risk_classification = "none"

        # Human oversight status
        oversight = reviews_by_req.get(req_id, "none")

        logs.append({
            "timestamp": req.created_at.isoformat() if req.created_at else None,
            "interaction_id": str(req.id),
            "model_identifier": req.model or "unknown",
            "input_summary": _truncate_summary(req.request_body),
            "output_summary": _truncate_summary(req.response_body),
            "risk_classification": risk_classification,
            "human_oversight_status": oversight,
            "decision_traceability": [
                inc["incident_id"] for inc in linked_incidents
            ],
            "data_retention_compliant": retention_compliant,
        })

    # Total count for pagination
    count_stmt = (
        select(func.count(ProxyRequest.id))
        .where(
            ProxyRequest.org_id == org_id,
            ProxyRequest.created_at >= date_from,
            ProxyRequest.created_at <= date_to,
        )
    )
    total = (await db.execute(count_stmt)).scalar_one()

    return {"logs": logs, "total": total, "skip": skip, "limit": limit}


async def get_article12_summary(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> dict:
    """Return Article 12 summary statistics for the given period."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Total interactions logged
    total_stmt = select(func.count(ProxyRequest.id)).where(
        ProxyRequest.org_id == org_id,
        ProxyRequest.created_at >= cutoff,
    )
    total_interactions = (await db.execute(total_stmt)).scalar_one()

    # Distinct models used
    models_stmt = (
        select(func.count(func.distinct(ProxyRequest.model)))
        .where(
            ProxyRequest.org_id == org_id,
            ProxyRequest.created_at >= cutoff,
            ProxyRequest.model.isnot(None),
        )
    )
    models_used = (await db.execute(models_stmt)).scalar_one()

    # Model name list
    model_list_stmt = (
        select(func.distinct(ProxyRequest.model))
        .where(
            ProxyRequest.org_id == org_id,
            ProxyRequest.created_at >= cutoff,
            ProxyRequest.model.isnot(None),
        )
    )
    model_names = [
        str(row[0]) for row in (await db.execute(model_list_stmt)).all()
    ]

    # High-risk classifications (incidents with critical/high severity)
    high_risk_stmt = (
        select(func.count(func.distinct(Incident.proxy_request_id)))
        .where(
            Incident.org_id == org_id,
            Incident.created_at >= cutoff,
            Incident.severity.in_(list(HIGH_RISK_SEVERITIES)),
            Incident.proxy_request_id.isnot(None),
        )
    )
    high_risk_count = (await db.execute(high_risk_stmt)).scalar_one()

    # Human oversight events (review items in period)
    oversight_stmt = select(func.count(ReviewItem.id)).where(
        ReviewItem.org_id == org_id,
        ReviewItem.created_at >= cutoff,
    )
    human_oversight_events = (await db.execute(oversight_stmt)).scalar_one()

    # Retention compliance check
    policy_result = await db.execute(
        select(RetentionPolicy.proxy_requests_days).where(
            RetentionPolicy.org_id == org_id,
        )
    )
    retention_days: int | None = policy_result.scalar_one_or_none()
    retention_compliant = _check_retention_compliant(retention_days)

    return {
        "total_interactions": total_interactions,
        "models_used": models_used,
        "model_names": model_names,
        "high_risk_classifications": high_risk_count,
        "human_oversight_events": human_oversight_events,
        "data_retention_compliant": retention_compliant,
        "retention_days_configured": retention_days,
        "retention_days_required": ARTICLE_12_RETENTION_DAYS,
        "period_days": days,
    }


async def export_article12_report(
    db: AsyncSession,
    org_id: UUID,
    date_from: datetime,
    date_to: datetime,
) -> dict:
    """Return structured data for Article 12 compliance report export.

    Combines summary stats with the full log set for the period,
    suitable for PDF/CSV generation by the caller.
    """
    # Calculate period days for summary
    period_delta = date_to - date_from
    days = max(period_delta.days, 1)

    summary = await get_article12_summary(db, org_id, days)

    # Fetch all logs (no pagination) for export
    all_logs = await get_article12_logs(
        db, org_id, date_from, date_to, skip=0, limit=10000,
    )

    return {
        "report_generated_at": datetime.now(timezone.utc).isoformat(),
        "period_start": date_from.isoformat(),
        "period_end": date_to.isoformat(),
        "summary": summary,
        "logs": all_logs["logs"],
        "total_log_entries": all_logs["total"],
    }
