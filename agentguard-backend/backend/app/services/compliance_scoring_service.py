"""Compliance scoring service — aggregates framework violations from incidents."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident


async def get_framework_scores(
    db: AsyncSession, org_id: UUID, days: int = 30
) -> dict[str, Any]:
    """Query compliance incidents and aggregate by framework/requirement.

    Returns a dict suitable for ComplianceScoreResponse serialization:
    {
        "frameworks": [
            {
                "name": "PCI-DSS",
                "total_violations": 5,
                "requirements": [
                    {"name": "Req 3.2 - Do not store ...", "violation_count": 3},
                    ...
                ]
            },
            ...
        ],
        "period_days": 30,
    }
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(Incident.metadata_)
        .where(
            Incident.org_id == org_id,
            Incident.category == "compliance",
            Incident.created_at >= cutoff,
        )
    )
    rows = result.scalars().all()

    # Aggregate: framework → requirement → count
    fw_req_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for metadata in rows:
        if not isinstance(metadata, dict):
            continue
        violated = metadata.get("violated_requirements")
        if not isinstance(violated, list):
            continue
        for entry in violated:
            if not isinstance(entry, str):
                continue
            # Format: "FRAMEWORK Requirement Name"
            parts = entry.split(" ", 1)
            if len(parts) == 2:
                fw_name, req_name = parts
                fw_req_counts[fw_name][req_name] += 1

    frameworks = []
    for fw_name, reqs in sorted(fw_req_counts.items()):
        requirements = [
            {"name": req, "violation_count": count}
            for req, count in sorted(reqs.items(), key=lambda x: -x[1])
        ]
        frameworks.append({
            "name": fw_name,
            "total_violations": sum(r["violation_count"] for r in requirements),
            "requirements": requirements,
        })

    # Sort by most violations first
    frameworks.sort(key=lambda f: -f["total_violations"])

    return {"frameworks": frameworks, "period_days": days}
