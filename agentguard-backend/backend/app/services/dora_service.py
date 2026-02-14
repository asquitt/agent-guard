# pyright: reportGeneralTypeIssues=false, reportArgumentType=false
"""DORA incident reporting automation service.

Classifies ICT incidents per DORA (Digital Operational Resilience Act)
severity tiers and generates reports within regulatory timelines.
Enforceable since Jan 17, 2025 for EU financial entities.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import IncidentSeverity
from app.models.incident import Incident

logger = logging.getLogger(__name__)

# Categories that affect critical functions (trading, payments, customer data)
CRITICAL_FUNCTION_CATEGORIES: frozenset[str] = frozenset({
    "pii_leak",
    "financial_pii",
    "compliance",
    "prompt_injection",
    "memory_exfiltration",
})

# Categories that trigger Major classification at high severity
HIGH_SEVERITY_MAJOR_CATEGORIES: frozenset[str] = frozenset({
    "pii_leak",
    "compliance",
    "financial_pii",
})

# DORA reporting timeline windows
TIMELINE_INITIAL_HOURS = 24
TIMELINE_INTERMEDIATE_HOURS = 72
TIMELINE_FINAL_DAYS = 30


def _classify_single(
    incident_severity: str,
    incident_category: str,
    cluster_count: int,
) -> tuple[bool, list[str]]:
    """Classify one incident as Major or Non-Major with reasoning.

    Returns (is_major, list_of_reasons).
    """
    reasons: list[str] = []

    # Rule 1: Critical severity -> Major
    if incident_severity == IncidentSeverity.CRITICAL.value:
        reasons.append("Critical severity incident affecting ICT services")

    # Rule 2: High severity in sensitive categories -> Major
    if (
        incident_severity == IncidentSeverity.HIGH.value
        and incident_category in HIGH_SEVERITY_MAJOR_CATEGORIES
    ):
        reasons.append(
            f"High severity incident in critical category: {incident_category}"
        )

    # Rule 3: Cluster of same category within 2h window -> escalation
    if cluster_count >= 3:
        reasons.append(
            f"Cluster of {cluster_count} incidents in same category within 2h window"
        )

    is_major = len(reasons) > 0
    if not is_major:
        reasons.append("Does not meet DORA Major incident criteria")

    return is_major, reasons


async def _count_cluster(
    db: AsyncSession,
    org_id: UUID,
    category: str,
    created_at: datetime,
) -> int:
    """Count incidents of the same category within a 2-hour window."""
    window_start = created_at - timedelta(hours=1)
    window_end = created_at + timedelta(hours=1)

    result = await db.execute(
        select(func.count(Incident.id)).where(
            Incident.org_id == org_id,
            Incident.category == category,
            Incident.created_at >= window_start,
            Incident.created_at <= window_end,
        )
    )
    return result.scalar_one()


def _timeline_status(
    created_at: datetime,
) -> dict[str, str]:
    """Determine which DORA report phases are due for an incident.

    Returns status for each phase: 'due', 'overdue', or 'not_yet'.
    """
    now = datetime.now(timezone.utc)
    age = now - created_at

    initial_deadline = timedelta(hours=TIMELINE_INITIAL_HOURS)
    intermediate_deadline = timedelta(hours=TIMELINE_INTERMEDIATE_HOURS)
    final_deadline = timedelta(days=TIMELINE_FINAL_DAYS)

    def _phase_status(deadline: timedelta) -> str:
        if age > deadline:
            return "overdue"
        if age > deadline - timedelta(hours=4):
            return "due"
        return "not_yet"

    return {
        "initial_24h": _phase_status(initial_deadline),
        "intermediate_72h": _phase_status(intermediate_deadline),
        "final_1m": _phase_status(final_deadline),
    }


async def classify_incident(
    db: AsyncSession,
    org_id: UUID,
    incident_id: UUID,
) -> dict:
    """Classify an incident as DORA Major or Non-Major.

    Returns classification result with reasoning.
    """
    result = await db.execute(
        select(Incident).where(
            Incident.id == incident_id,
            Incident.org_id == org_id,
        )
    )
    incident = result.scalar_one_or_none()
    if incident is None:
        raise ValueError(f"Incident {incident_id} not found")

    cluster_count = await _count_cluster(
        db, org_id, str(incident.category), incident.created_at
    )

    is_major, reasons = _classify_single(
        str(incident.severity),
        str(incident.category),
        cluster_count,
    )

    timeline = _timeline_status(incident.created_at) if is_major else None

    return {
        "incident_id": str(incident.id),
        "title": str(incident.title),
        "severity": str(incident.severity),
        "category": str(incident.category),
        "classification": "major" if is_major else "non_major",
        "reasons": reasons,
        "timeline": timeline,
        "created_at": incident.created_at.isoformat(),
    }


async def get_dora_report(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> dict:
    """Generate DORA incident summary report for a given period."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Fetch all incidents in the period
    result = await db.execute(
        select(Incident)
        .where(
            Incident.org_id == org_id,
            Incident.created_at >= cutoff,
        )
        .order_by(Incident.created_at.desc())
    )
    incidents = result.scalars().all()

    # Pre-compute cluster counts per category for efficiency
    cluster_cache: dict[str, int] = {}
    for inc in incidents:
        cat = str(inc.category)
        if cat not in cluster_cache:
            cluster_cache[cat] = await _count_cluster(
                db, org_id, cat, inc.created_at
            )

    major_list: list[dict] = []
    non_major_count = 0

    # Timeline bucket counters
    now = datetime.now(timezone.utc)
    timeline_buckets = {"initial_24h": 0, "intermediate_72h": 0, "final_1m": 0}

    for inc in incidents:
        is_major, reasons = _classify_single(
            str(inc.severity),
            str(inc.category),
            cluster_cache.get(str(inc.category), 1),
        )

        if is_major:
            age = now - inc.created_at
            if age <= timedelta(hours=TIMELINE_INITIAL_HOURS):
                timeline_buckets["initial_24h"] += 1
            elif age <= timedelta(hours=TIMELINE_INTERMEDIATE_HOURS):
                timeline_buckets["intermediate_72h"] += 1
            else:
                timeline_buckets["final_1m"] += 1

            major_list.append({
                "incident_id": str(inc.id),
                "title": str(inc.title),
                "severity": str(inc.severity),
                "category": str(inc.category),
                "status": str(inc.status),
                "classification": "major",
                "reasons": reasons,
                "timeline": _timeline_status(inc.created_at),
                "created_at": inc.created_at.isoformat(),
            })
        else:
            non_major_count += 1

    return {
        "total_incidents": len(incidents),
        "major_incidents": len(major_list),
        "non_major_incidents": non_major_count,
        "by_timeline": timeline_buckets,
        "major_incidents_list": major_list,
        "period_days": days,
    }


async def get_incident_timeline(
    db: AsyncSession,
    org_id: UUID,
    incident_id: UUID,
) -> dict:
    """Get DORA reporting timeline status for a single incident."""
    classification = await classify_incident(db, org_id, incident_id)

    if classification["classification"] != "major":
        return {
            "incident_id": classification["incident_id"],
            "classification": "non_major",
            "message": "Non-major incidents do not require DORA timeline reporting",
            "timeline": None,
        }

    return {
        "incident_id": classification["incident_id"],
        "title": classification["title"],
        "classification": "major",
        "timeline": classification["timeline"],
        "reasons": classification["reasons"],
        "created_at": classification["created_at"],
    }
