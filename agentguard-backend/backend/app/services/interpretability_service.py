"""Interpretability-powered incident investigation service (Feature 20).

Provides root-cause analysis for incidents — answering "why did the agent
hallucinate / get injected / leak PII" rather than just "what happened".
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.models.proxy import ProxyRequest

from .interpretability_analyzers import (
    analyze_cost_anomaly,
    analyze_generic,
    analyze_hallucination,
    analyze_injection,
    analyze_loop,
    analyze_memory_exfiltration,
    analyze_pii_leak,
    analyze_sycophancy,
    analyze_toxicity,
)
from .interpretability_utils import (
    HALLUCINATION_CATEGORIES,
    INJECTION_CATEGORIES,
    PII_CATEGORIES,
    category_recommendations,
    category_to_pattern,
    category_to_root_cause,
    empty_investigation,
    safe_parse_json,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def investigate_incident(
    db: AsyncSession,
    org_id: UUID,
    incident_id: UUID,
) -> dict:
    """Generate a structured root-cause investigation for a single incident.

    Returns dict with keys: root_cause, contributing_factors, attack_chain,
    recommendations, similar_incidents, confidence.
    """
    # Fetch incident (tenant-isolated)
    result = await db.execute(
        select(Incident).where(
            Incident.id == incident_id,
            Incident.org_id == org_id,
        )
    )
    incident = result.scalar_one_or_none()
    if incident is None:
        return empty_investigation("Incident not found")

    category = str(incident.category)
    severity = str(incident.severity)
    raw_meta = incident.metadata_
    metadata: dict = raw_meta if isinstance(raw_meta, dict) else {}

    # Fetch associated proxy request if present
    proxy_req = None
    if incident.proxy_request_id is not None:
        pr_result = await db.execute(
            select(ProxyRequest).where(
                ProxyRequest.id == incident.proxy_request_id,
                ProxyRequest.org_id == org_id,
            )
        )
        proxy_req = pr_result.scalar_one_or_none()

    request_body = safe_parse_json(str(proxy_req.request_body)) if proxy_req and proxy_req.request_body is not None else None
    response_body = safe_parse_json(str(proxy_req.response_body)) if proxy_req and proxy_req.response_body is not None else None

    # Dispatch analysis by category
    if category in INJECTION_CATEGORIES:
        analysis = analyze_injection(category, metadata, request_body, response_body)
    elif category in HALLUCINATION_CATEGORIES:
        analysis = analyze_hallucination(
            category, metadata, proxy_req, response_body
        )
    elif category in PII_CATEGORIES:
        analysis = analyze_pii_leak(category, metadata, response_body)
    elif category == "cost_anomaly":
        analysis = analyze_cost_anomaly(metadata, proxy_req)
    elif category == "sycophancy":
        analysis = analyze_sycophancy(metadata, request_body)
    elif category == "memory_exfiltration":
        analysis = analyze_memory_exfiltration(metadata, request_body, response_body)
    elif category == "toxicity":
        analysis = analyze_toxicity(metadata, response_body)
    elif category == "loop":
        analysis = analyze_loop(metadata, proxy_req)
    else:
        analysis = analyze_generic(category, severity, metadata)

    # Find similar incidents (same category, last 30 days)
    similar = await _find_similar_incidents(
        db, org_id, incident_id, category, days=30
    )

    return {
        "root_cause": analysis["root_cause"],
        "contributing_factors": analysis["contributing_factors"],
        "attack_chain": analysis.get("attack_chain", []),
        "recommendations": analysis["recommendations"],
        "similar_incidents": similar,
        "confidence": analysis["confidence"],
    }


async def get_investigation_summary(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> dict:
    """Aggregate investigation stats over a time window.

    Returns dict with: top_root_causes, recurring_patterns,
    recommended_actions.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Count incidents by category
    result = await db.execute(
        select(
            Incident.category,
            func.count(Incident.id).label("cnt"),
        )
        .where(Incident.org_id == org_id, Incident.created_at >= cutoff)
        .group_by(Incident.category)
        .order_by(func.count(Incident.id).desc())
    )
    category_counts = [(str(row.category), int(row.cnt)) for row in result.all()]

    top_root_causes = [
        {"cause": category_to_root_cause(cat), "count": cnt}
        for cat, cnt in category_counts
    ]

    # Recurring patterns: categories with 3+ incidents
    recurring_patterns = [
        {"pattern": category_to_pattern(cat), "frequency": cnt}
        for cat, cnt in category_counts
        if cnt >= 3
    ]

    # Aggregate recommendations from top categories
    recommended_actions: list[str] = []
    seen: set[str] = set()
    for cat, _ in category_counts[:5]:
        for rec in category_recommendations(cat):
            if rec not in seen:
                recommended_actions.append(rec)
                seen.add(rec)

    return {
        "top_root_causes": top_root_causes,
        "recurring_patterns": recurring_patterns,
        "recommended_actions": recommended_actions,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _find_similar_incidents(
    db: AsyncSession,
    org_id: UUID,
    exclude_id: UUID,
    category: str,
    days: int = 30,
) -> list[str]:
    """Find recent incidents with the same category (up to 10)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(Incident.id)
        .where(
            Incident.org_id == org_id,
            Incident.category == category,
            Incident.id != exclude_id,
            Incident.created_at >= cutoff,
        )
        .order_by(Incident.created_at.desc())
        .limit(10)
    )
    return [str(row[0]) for row in result.all()]
