"""OWASP LLM Top 10 compliance scoring service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import IncidentStatus
from app.models.incident import Incident

# OWASP LLM Top 10 (2025) mapped to AgentGuard detection categories
OWASP_LLM_TOP_10: list[dict[str, object]] = [
    {
        "id": "LLM01",
        "name": "Prompt Injection",
        "description": "User prompts alter LLM behavior in unintended ways",
        "mapped_categories": ["prompt_injection", "instruction_hierarchy", "schema_injection"],
        "coverage": "full",
    },
    {
        "id": "LLM02",
        "name": "Sensitive Information Disclosure",
        "description": "Unintended exposure of PII, credentials, API keys",
        "mapped_categories": ["pii_leak", "financial_pii", "memory_exfiltration"],
        "coverage": "full",
    },
    {
        "id": "LLM03",
        "name": "Supply Chain",
        "description": "Compromised training data, models, or plugins",
        "mapped_categories": [],
        "coverage": "none",
    },
    {
        "id": "LLM04",
        "name": "Data and Model Poisoning",
        "description": "Manipulated training data affecting model behavior",
        "mapped_categories": [],
        "coverage": "none",
    },
    {
        "id": "LLM05",
        "name": "Improper Output Handling",
        "description": "LLM output used without validation in downstream systems",
        "mapped_categories": ["compliance", "sycophancy"],
        "coverage": "partial",
    },
    {
        "id": "LLM06",
        "name": "Excessive Agency",
        "description": "LLMs granted more autonomy than necessary",
        "mapped_categories": ["scope_enforcement", "capability_monitor", "sequential_action"],
        "coverage": "full",
    },
    {
        "id": "LLM07",
        "name": "System Prompt Leakage",
        "description": "System prompts exposed to users",
        "mapped_categories": ["prompt_extraction", "prompt_injection"],
        "coverage": "full",
    },
    {
        "id": "LLM08",
        "name": "Vector and Embedding Weaknesses",
        "description": "RAG pipelines vulnerable to data poisoning",
        "mapped_categories": [],
        "coverage": "none",
    },
    {
        "id": "LLM09",
        "name": "Misinformation",
        "description": "LLMs generating false but convincing content",
        "mapped_categories": ["hallucination", "confidence_hallucination", "sycophancy"],
        "coverage": "full",
    },
    {
        "id": "LLM10",
        "name": "Unbounded Consumption",
        "description": "Resource abuse causing DoS or cost explosion",
        "mapped_categories": ["cost_anomaly", "loop"],
        "coverage": "full",
    },
]


async def get_owasp_compliance(db: AsyncSession, org_id: UUID, days: int = 30) -> dict:
    """Get OWASP LLM Top 10 compliance status with incident counts."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Get incident counts by category with resolved breakdown
    result = await db.execute(
        select(
            Incident.category,
            func.count(Incident.id).label("total"),
            func.count(
                case(
                    (Incident.status == IncidentStatus.RESOLVED.value, Incident.id),
                )
            ).label("resolved"),
        )
        .where(
            Incident.org_id == org_id,
            Incident.created_at >= cutoff,
        )
        .group_by(Incident.category)
    )
    category_counts: dict[str, dict[str, int]] = {
        str(row.category): {"total": row.total, "resolved": row.resolved}
        for row in result.all()
    }

    # Build OWASP compliance report
    risks = []
    covered_count = 0
    for risk in OWASP_LLM_TOP_10:
        mapped: list[str] = risk["mapped_categories"]  # type: ignore[assignment]
        incident_count = sum(category_counts.get(cat, {}).get("total", 0) for cat in mapped)
        resolved_count = sum(category_counts.get(cat, {}).get("resolved", 0) for cat in mapped)

        coverage = risk["coverage"]
        if coverage in ("full", "partial"):
            covered_count += 1

        risks.append({
            "id": risk["id"],
            "name": risk["name"],
            "description": risk["description"],
            "coverage": coverage,
            "mapped_categories": mapped,
            "incidents_detected": incident_count,
            "incidents_resolved": resolved_count,
            "active_incidents": incident_count - resolved_count,
        })

    coverage_pct = round(covered_count / len(OWASP_LLM_TOP_10) * 100, 1)

    return {
        "risks": risks,
        "coverage_percentage": coverage_pct,
        "covered_risks": covered_count,
        "total_risks": len(OWASP_LLM_TOP_10),
        "period_days": days,
    }
