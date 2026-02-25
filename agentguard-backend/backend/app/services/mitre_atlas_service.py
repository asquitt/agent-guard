"""MITRE ATLAS threat mapping service for AI-specific attack techniques."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident

# ---------------------------------------------------------------------------
# MITRE ATLAS technique catalogue mapped to AgentGuard detection categories.
# Reference: https://atlas.mitre.org  (Oct 2025 update incl. agent techniques)
# ---------------------------------------------------------------------------

ATLAS_TECHNIQUES: list[dict[str, object]] = [
    # --- Initial Access ---
    {
        "id": "AML.T0051",
        "name": "LLM Prompt Injection - Direct",
        "tactic": "Initial Access",
        "mapped_categories": ["prompt_injection"],
        "description": "Attacker crafts input to override system instructions",
    },
    {
        "id": "AML.T0051.001",
        "name": "LLM Prompt Injection - Indirect",
        "tactic": "Initial Access",
        "mapped_categories": ["prompt_injection", "schema_injection"],
        "description": "Malicious instructions embedded in external data sources",
    },
    {
        "id": "AML.T0051.002",
        "name": "Context Poisoning",
        "tactic": "Initial Access",
        "mapped_categories": ["prompt_injection", "mcp_security"],
        "description": "Poisoned context injected via RAG or tool outputs",
    },
    {
        "id": "AML.T0051.003",
        "name": "Thread Injection",
        "tactic": "Initial Access",
        "mapped_categories": ["prompt_injection", "sequential_action"],
        "description": "Injecting instructions into multi-turn conversation threads",
    },
    # --- Reconnaissance ---
    {
        "id": "AML.T0014",
        "name": "ML Model Reconnaissance",
        "tactic": "Reconnaissance",
        "mapped_categories": ["prompt_extraction", "prompt_injection"],
        "description": "Probing to discover model capabilities and boundaries",
    },
    {
        "id": "AML.T0056",
        "name": "LLM Meta Prompt Extraction",
        "tactic": "Reconnaissance",
        "mapped_categories": ["prompt_extraction"],
        "description": "Techniques to extract system prompts from the model",
    },
    # --- Defense Evasion ---
    {
        "id": "AML.T0054",
        "name": "LLM Jailbreak",
        "tactic": "Defense Evasion",
        "mapped_categories": ["prompt_injection"],
        "description": "Techniques to bypass safety training and guardrails",
    },
    {
        "id": "AML.T0054.001",
        "name": "Sycophancy Exploitation",
        "tactic": "Defense Evasion",
        "mapped_categories": ["sycophancy"],
        "description": "Exploiting model tendency to agree to override safety",
    },
    {
        "id": "AML.T0054.002",
        "name": "Instruction Hierarchy Bypass",
        "tactic": "Defense Evasion",
        "mapped_categories": ["prompt_injection", "scope_enforcement"],
        "description": "Circumventing instruction priority to elevate attacker input",
    },
    # --- Exfiltration ---
    {
        "id": "AML.T0057",
        "name": "LLM Data Leakage",
        "tactic": "Exfiltration",
        "mapped_categories": ["pii_leak"],
        "description": "Model reveals training data or sensitive context",
    },
    {
        "id": "AML.T0057.001",
        "name": "Exfiltration via Tool Invocation",
        "tactic": "Exfiltration",
        "mapped_categories": ["pii_leak", "tool_call", "mcp_security"],
        "description": "Using tool calls to send sensitive data to external endpoints",
    },
    {
        "id": "AML.T0057.002",
        "name": "RAG Credential Harvesting",
        "tactic": "Exfiltration",
        "mapped_categories": ["pii_leak", "mcp_security"],
        "description": "Extracting credentials from retrieved documents via RAG",
    },
    # --- Collection ---
    {
        "id": "AML.T0025",
        "name": "Exfiltration of ML Artifacts",
        "tactic": "Collection",
        "mapped_categories": ["prompt_extraction", "pii_leak"],
        "description": "Extracting model weights, prompts, or training data",
    },
    {
        "id": "AML.T0025.001",
        "name": "Memory Manipulation",
        "tactic": "Collection",
        "mapped_categories": ["sequential_action", "prompt_injection"],
        "description": "Manipulating agent persistent memory to alter future behavior",
    },
    # --- Impact ---
    {
        "id": "AML.T0029",
        "name": "Denial of ML Service",
        "tactic": "Impact",
        "mapped_categories": ["cost_anomaly", "loop"],
        "description": "Causing model unavailability through resource exhaustion",
    },
    {
        "id": "AML.T0034",
        "name": "Cost Harvesting",
        "tactic": "Impact",
        "mapped_categories": ["cost_anomaly"],
        "description": "Driving up API costs through excessive token consumption",
    },
    {
        "id": "AML.T0048",
        "name": "Resource Hijacking",
        "tactic": "Impact",
        "mapped_categories": ["cost_anomaly", "tool_call"],
        "description": "Hijacking compute for attacker-controlled workloads",
    },
    # --- Execution ---
    {
        "id": "AML.T0040",
        "name": "ML Model Poisoning",
        "tactic": "Execution",
        "mapped_categories": ["hallucination", "compliance"],
        "description": "Manipulating model outputs to produce incorrect results",
    },
    {
        "id": "AML.T0040.001",
        "name": "Config Modification via Agent",
        "tactic": "Execution",
        "mapped_categories": ["tool_call", "scope_enforcement"],
        "description": "Agent modifying its own config or permissions via tools",
    },
    {
        "id": "AML.T0040.002",
        "name": "Schema Injection",
        "tactic": "Execution",
        "mapped_categories": ["schema_injection", "mcp_security"],
        "description": "Injecting malicious schemas to alter tool call behavior",
    },
    # --- Persistence ---
    {
        "id": "AML.T0020",
        "name": "Poisoning of Training Data",
        "tactic": "Persistence",
        "mapped_categories": ["hallucination"],
        "description": "Corrupting data pipelines to introduce persistent biases",
    },
    # --- ML Attack Staging ---
    {
        "id": "AML.T0043",
        "name": "Adversarial Input",
        "tactic": "ML Attack Staging",
        "mapped_categories": ["toxicity", "prompt_injection"],
        "description": "Crafted inputs to trigger harmful or toxic model outputs",
    },
    {
        "id": "AML.T0043.001",
        "name": "Loop Induction",
        "tactic": "ML Attack Staging",
        "mapped_categories": ["loop", "sequential_action"],
        "description": "Forcing agent into infinite loops via crafted tool responses",
    },
    # --- Compliance-specific ---
    {
        "id": "AML.T0060",
        "name": "Regulatory Violation Induction",
        "tactic": "Impact",
        "mapped_categories": ["compliance"],
        "description": "Tricking agents into producing outputs that violate regulations",
    },
]

# Pre-build a reverse index: category -> list of technique ids
_CATEGORY_TO_TECHNIQUES: dict[str, list[str]] = {}
for _tech in ATLAS_TECHNIQUES:
    for _cat in _tech["mapped_categories"]:  # type: ignore[union-attr]
        _CATEGORY_TO_TECHNIQUES.setdefault(str(_cat), []).append(str(_tech["id"]))


async def get_threat_mapping(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> list[dict[str, Any]]:
    """Return ATLAS techniques enriched with incident counts for the org."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(Incident.category, func.count(Incident.id))
        .where(Incident.org_id == org_id, Incident.created_at >= cutoff)
        .group_by(Incident.category)
    )
    counts_by_category: dict[str, int] = {
        str(cat): int(cnt) for cat, cnt in result.all()
    }

    techniques: list[dict[str, object]] = []
    for tech in ATLAS_TECHNIQUES:
        mapped: list[str] = tech["mapped_categories"]  # type: ignore[assignment]
        incident_count = sum(counts_by_category.get(c, 0) for c in mapped)
        techniques.append({
            **tech,
            "incident_count": incident_count,
            "observed": incident_count > 0,
        })
    return techniques


async def get_attack_surface_summary(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> list[dict[str, object]]:
    """Summarize observed techniques grouped by MITRE ATLAS tactic."""
    techniques = await get_threat_mapping(db, org_id, days)

    tactic_map: dict[str, dict[str, object]] = {}
    for tech in techniques:
        tactic = str(tech["tactic"])
        if tactic not in tactic_map:
            tactic_map[tactic] = {
                "tactic": tactic,
                "total_techniques": 0,
                "observed_techniques": 0,
                "total_incidents": 0,
            }
        entry = tactic_map[tactic]
        entry["total_techniques"] = int(entry["total_techniques"]) + 1  # type: ignore[arg-type]
        if tech["observed"]:
            entry["observed_techniques"] = int(entry["observed_techniques"]) + 1  # type: ignore[arg-type]
        entry["total_incidents"] = int(entry["total_incidents"]) + int(tech["incident_count"])  # type: ignore[arg-type]

    return sorted(
        tactic_map.values(),
        key=lambda t: int(t["total_incidents"]),  # type: ignore[arg-type]
        reverse=True,
    )
