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


# Severity weights for risk scoring
_SEVERITY_WEIGHT: dict[str, int] = {
    "critical": 10,
    "high": 5,
    "medium": 2,
    "low": 1,
    "info": 0,
}


async def get_risk_score(
    db: AsyncSession, org_id: UUID, days: int = 30
) -> dict[str, Any]:
    """Compute composite risk score (0-100, lower is better).

    Factors:
    1. Severity-weighted incident density (40%)
    2. Unresolved ratio (30%)
    3. Category breadth (15%)
    4. Trend direction (15%)
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Per-category, per-severity, per-status counts
    stats = await db.execute(
        select(
            Incident.category,
            Incident.severity,
            Incident.status,
            func.count(Incident.id),
        )
        .where(Incident.org_id == org_id, Incident.created_at >= cutoff)
        .group_by(Incident.category, Incident.severity, Incident.status)
    )

    cat_data: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"total": 0, "critical": 0, "high": 0, "open": 0, "weighted": 0}
    )
    total_incidents = 0
    open_incidents = 0
    critical_open = 0
    weighted_sum = 0

    for cat, severity, status, cnt in stats.all():
        cat_str = str(cat)
        sev_str = str(severity)
        status_str = str(status)
        count = int(cnt)
        weight = _SEVERITY_WEIGHT.get(sev_str, 0)

        cat_data[cat_str]["total"] += count
        cat_data[cat_str]["weighted"] += count * weight
        total_incidents += count
        weighted_sum += count * weight

        if sev_str == "critical":
            cat_data[cat_str]["critical"] += count
        if sev_str == "high":
            cat_data[cat_str]["high"] += count
        if status_str in ("open", "acknowledged"):
            cat_data[cat_str]["open"] += count
            open_incidents += count
            if sev_str == "critical":
                critical_open += count

    # Factor 1: Severity-weighted density (0-100)
    density_score = min(weighted_sum / max(days, 1), 100)

    # Factor 2: Unresolved ratio (0-100)
    unresolved_score = (open_incidents / total_incidents * 100) if total_incidents > 0 else 0

    # Factor 3: Category breadth (0-100)
    active_categories = len(cat_data)
    breadth_score = min(active_categories * 10, 100)

    # Factor 4: Trend — compare recent half vs older half
    midpoint = cutoff + timedelta(days=days / 2)
    older_result = await db.execute(
        select(func.count(Incident.id)).where(
            Incident.org_id == org_id,
            Incident.created_at >= cutoff,
            Incident.created_at < midpoint,
        )
    )
    recent_result_q = await db.execute(
        select(func.count(Incident.id)).where(
            Incident.org_id == org_id,
            Incident.created_at >= midpoint,
        )
    )
    older_count = int(older_result.scalar_one() or 0)
    recent_count = int(recent_result_q.scalar_one() or 0)

    if older_count + recent_count == 0:
        trend_score = 0.0
        trend_direction = "stable"
    elif older_count == 0:
        trend_score = min(recent_count * 5.0, 100.0)
        trend_direction = "degrading"
    else:
        ratio = recent_count / older_count
        if ratio > 1.2:
            trend_score = min((ratio - 1) * 100, 100)
            trend_direction = "degrading"
        elif ratio < 0.8:
            trend_score = 0.0
            trend_direction = "improving"
        else:
            trend_score = 30.0
            trend_direction = "stable"

    # Composite
    overall = (
        density_score * 0.40
        + unresolved_score * 0.30
        + breadth_score * 0.15
        + trend_score * 0.15
    )
    overall = round(min(max(overall, 0), 100), 1)

    if overall <= 15:
        grade = "A"
    elif overall <= 35:
        grade = "B"
    elif overall <= 55:
        grade = "C"
    elif overall <= 75:
        grade = "D"
    else:
        grade = "F"

    # Per-category scores
    category_risks: list[dict[str, Any]] = []
    for cat in sorted(cat_data.keys()):
        d = cat_data[cat]
        cat_score = min(d["weighted"] / max(days, 1) * 10, 100)
        category_risks.append({
            "category": cat,
            "score": round(cat_score, 1),
            "incident_count": d["total"],
            "critical_count": d["critical"],
            "high_count": d["high"],
            "open_count": d["open"],
        })
    category_risks.sort(key=lambda x: x["score"], reverse=True)

    # Daily risk trend
    daily_sev = await db.execute(
        select(
            cast(Incident.created_at, DATE).label("day"),
            Incident.severity,
            func.count(Incident.id),
        )
        .where(Incident.org_id == org_id, Incident.created_at >= cutoff)
        .group_by("day", Incident.severity)
        .order_by("day")
    )
    day_weights: dict[str, float] = defaultdict(float)
    for day, sev, cnt in daily_sev.all():
        day_weights[str(day)] += int(cnt) * _SEVERITY_WEIGHT.get(str(sev), 0)

    trend_points: list[dict[str, Any]] = [
        {"date": day, "score": round(min(val / 10, 100), 1)}
        for day, val in sorted(day_weights.items())
    ]

    return {
        "overall_score": overall,
        "grade": grade,
        "trend_direction": trend_direction,
        "categories": category_risks,
        "trend": trend_points,
        "total_incidents": total_incidents,
        "open_incidents": open_incidents,
        "critical_open": critical_open,
        "period_days": days,
    }
