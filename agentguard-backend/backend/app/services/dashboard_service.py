"""Dashboard metrics service."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import DATE
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident


async def get_metrics(
    db: AsyncSession,
    org_id: UUID,
    recent_limit: int = 10,
) -> dict:
    """Aggregate dashboard metrics for an org."""
    # Total incidents
    total_result = await db.execute(select(func.count(Incident.id)).where(Incident.org_id == org_id))
    total_incidents: int = total_result.scalar_one()

    # Open incidents
    open_result = await db.execute(
        select(func.count(Incident.id)).where(
            Incident.org_id == org_id,
            Incident.status == "open",
        )
    )
    open_incidents: int = open_result.scalar_one()

    # Incidents by status
    status_result = await db.execute(
        select(Incident.status, func.count(Incident.id)).where(Incident.org_id == org_id).group_by(Incident.status)
    )
    incidents_by_status = [{"status": row[0], "count": row[1]} for row in status_result.all()]

    # Incidents by severity
    severity_result = await db.execute(
        select(Incident.severity, func.count(Incident.id)).where(Incident.org_id == org_id).group_by(Incident.severity)
    )
    incidents_by_severity = [{"severity": row[0], "count": row[1]} for row in severity_result.all()]

    # Recent incidents
    recent_result = await db.execute(
        select(Incident).where(Incident.org_id == org_id).order_by(Incident.created_at.desc()).limit(recent_limit)
    )
    recent_incidents = list(recent_result.scalars().all())

    return {
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "incidents_by_status": incidents_by_status,
        "incidents_by_severity": incidents_by_severity,
        "recent_incidents": recent_incidents,
    }


async def get_detection_efficacy(
    db: AsyncSession, org_id: UUID, days: int = 30
) -> dict[str, Any]:
    """Compute detection efficacy analytics per category."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Fetch per-category stats in one query
    stats = await db.execute(
        select(
            Incident.category,
            Incident.status,
            func.count(Incident.id),
        )
        .where(Incident.org_id == org_id, Incident.created_at >= cutoff)
        .group_by(Incident.category, Incident.status)
    )

    # Aggregate
    cat_data: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for cat, status_val, cnt in stats.all():
        cat_data[str(cat)][str(status_val)] = int(cnt)

    # Mean time to resolve per category (resolved incidents only)
    mttr_result = await db.execute(
        select(
            Incident.category,
            func.avg(
                func.extract("epoch", Incident.resolved_at) - func.extract("epoch", Incident.created_at)
            ),
        )
        .where(
            Incident.org_id == org_id,
            Incident.created_at >= cutoff,
            Incident.resolved_at.isnot(None),
        )
        .group_by(Incident.category)
    )
    mttr_by_cat: dict[str, float] = {}
    for cat, avg_seconds in mttr_result.all():
        if avg_seconds is not None:
            mttr_by_cat[str(cat)] = round(float(avg_seconds) / 3600, 2)

    # Build category efficacy list
    categories: list[dict[str, Any]] = []
    total_all = 0
    dismissed_all = 0

    for cat in sorted(cat_data.keys()):
        statuses = cat_data[cat]
        total = sum(statuses.values())
        resolved = statuses.get("resolved", 0)
        dismissed = statuses.get("dismissed", 0)
        open_count = statuses.get("open", 0) + statuses.get("acknowledged", 0)
        fp_rate = round(dismissed / total, 4) if total > 0 else 0.0

        total_all += total
        dismissed_all += dismissed

        categories.append({
            "category": cat,
            "total": total,
            "resolved": resolved,
            "dismissed": dismissed,
            "open": open_count,
            "false_positive_rate": fp_rate,
            "mean_time_to_resolve_hours": mttr_by_cat.get(cat),
        })

    # Daily detection trend
    daily_result = await db.execute(
        select(
            cast(Incident.created_at, DATE).label("day"),
            func.count(Incident.id),
        )
        .where(Incident.org_id == org_id, Incident.created_at >= cutoff)
        .group_by("day")
        .order_by("day")
    )
    daily_trend = [
        {"date": str(row[0]), "count": int(row[1])} for row in daily_result.all()
    ]

    overall_fp = round(dismissed_all / total_all, 4) if total_all > 0 else 0.0

    return {
        "categories": categories,
        "daily_trend": daily_trend,
        "overall_false_positive_rate": overall_fp,
        "period_days": days,
    }
