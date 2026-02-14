"""Cross-framework compliance reporting service.

Maps AgentGuard detectors to: EU AI Act, NIST AI 600-1, SR 11-7, DORA,
SOC 2, ISO 42001, OWASP LLM Top 10, MITRE ATLAS, PCI-DSS, FFIEC.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident

# ---------------------------------------------------------------------------
# Cross-framework regulatory mapping
# ---------------------------------------------------------------------------

FRAMEWORK_MAPPING: dict[str, list[dict[str, str]]] = {
    "hallucination": [
        {"framework": "EU AI Act", "article": "Art. 9 Risk Mgmt, Art. 15 Accuracy", "requirement": "Ensure AI system accuracy and minimize errors"},
        {"framework": "NIST AI 600-1", "risk": "GAI-2 Confabulation", "requirement": "Monitor for fabricated content in generative outputs"},
        {"framework": "SR 11-7", "section": "Ongoing Monitoring", "requirement": "Outcomes analysis and ongoing model performance monitoring"},
        {"framework": "DORA", "pillar": "Pillar 1 - ICT Risk Mgmt", "requirement": "Detect anomalous AI behavior and output degradation"},
        {"framework": "SOC 2", "criteria": "PI1.1 Processing Integrity", "requirement": "AI outputs are complete, valid, and accurate"},
        {"framework": "ISO 42001", "control": "A.7.4 AI System Monitoring", "requirement": "Monitor AI outputs for accuracy and reliability"},
        {"framework": "OWASP LLM", "risk": "LLM09 Misinformation", "requirement": "Detect and prevent false content generation"},
        {"framework": "MITRE ATLAS", "technique": "AML.T0048 Evade ML Model", "requirement": "Detect outputs that deviate from expected behavior"},
    ],
    "pii_leak": [
        {"framework": "EU AI Act", "article": "Art. 10 Data Governance", "requirement": "Prevent unauthorized personal data in AI outputs"},
        {"framework": "NIST AI 600-1", "risk": "GAI-4 Data Privacy", "requirement": "Prevent PII leakage in generative AI outputs"},
        {"framework": "DORA", "pillar": "Pillar 2 - ICT Incident Mgmt", "requirement": "Report and manage data exposure incidents"},
        {"framework": "SOC 2", "criteria": "P1.1 Privacy", "requirement": "Personal information is collected and used appropriately"},
        {"framework": "ISO 42001", "control": "A.8.5 Data for AI Systems", "requirement": "Protect personal data throughout AI lifecycle"},
        {"framework": "OWASP LLM", "risk": "LLM06 Sensitive Info Disclosure", "requirement": "Prevent exposure of sensitive data in outputs"},
        {"framework": "FFIEC", "section": "Info Security Handbook", "requirement": "Protect customer nonpublic personal information"},
    ],
    "compliance": [
        {"framework": "EU AI Act", "article": "Art. 9 Risk Mgmt System", "requirement": "Implement risk management for compliance violations"},
        {"framework": "NIST AI 600-1", "risk": "GAI-6 AI System Safety", "requirement": "Ensure AI systems comply with applicable regulations"},
        {"framework": "SR 11-7", "section": "Model Validation", "requirement": "Independent validation of model compliance controls"},
        {"framework": "DORA", "pillar": "Pillar 5 - Info Sharing", "requirement": "Share compliance incident intelligence across org"},
        {"framework": "SOC 2", "criteria": "CC2.1 Monitoring Activities", "requirement": "Monitor compliance obligations continuously"},
        {"framework": "ISO 42001", "control": "A.5.4 AI Risk Assessment", "requirement": "Assess regulatory compliance risks for AI systems"},
        {"framework": "OWASP LLM", "risk": "LLM05 Improper Output Handling", "requirement": "Validate outputs against regulatory requirements"},
    ],
    "cost_anomaly": [
        {"framework": "EU AI Act", "article": "Art. 72 Monitoring by Providers", "requirement": "Monitor AI resource consumption for anomalies"},
        {"framework": "NIST AI 600-1", "risk": "GAI-5 Environmental Impact", "requirement": "Track and manage excessive resource consumption"},
        {"framework": "DORA", "pillar": "Pillar 1 - ICT Risk Mgmt", "requirement": "Detect and respond to anomalous ICT spending"},
        {"framework": "SOC 2", "criteria": "A1.1 Availability", "requirement": "Monitor capacity and detect resource abuse"},
        {"framework": "ISO 42001", "control": "A.6.2.6 AI System Operation", "requirement": "Monitor operational costs and resource efficiency"},
        {"framework": "OWASP LLM", "risk": "LLM10 Unbounded Consumption", "requirement": "Detect denial-of-wallet and resource abuse attacks"},
    ],
    "loop": [
        {"framework": "EU AI Act", "article": "Art. 14 Human Oversight", "requirement": "Ensure AI systems can be interrupted and controlled"},
        {"framework": "NIST AI 600-1", "risk": "GAI-7 Human-AI Config", "requirement": "Maintain human ability to intervene in AI operations"},
        {"framework": "DORA", "pillar": "Pillar 3 - Digital Resilience Testing", "requirement": "Test for and detect degraded AI operation modes"},
        {"framework": "SOC 2", "criteria": "A1.2 Availability", "requirement": "Detect and recover from system operational failures"},
        {"framework": "ISO 42001", "control": "A.7.3 AI System Performance", "requirement": "Detect degraded or looping AI behavior"},
        {"framework": "OWASP LLM", "risk": "LLM10 Unbounded Consumption", "requirement": "Prevent infinite loops consuming resources"},
    ],
    "prompt_injection": [
        {"framework": "EU AI Act", "article": "Art. 15 Accuracy/Robustness", "requirement": "Protect AI systems against adversarial manipulation"},
        {"framework": "NIST AI 600-1", "risk": "GAI-9 Prompt Injection", "requirement": "Detect direct and indirect prompt injection attacks"},
        {"framework": "DORA", "pillar": "Pillar 2 - ICT Incident Mgmt", "requirement": "Detect and report AI security incidents"},
        {"framework": "SOC 2", "criteria": "CC6.1 Logical Access Security", "requirement": "Protect against unauthorized AI system manipulation"},
        {"framework": "ISO 42001", "control": "A.9.4 AI System Security", "requirement": "Protect AI systems from adversarial inputs"},
        {"framework": "OWASP LLM", "risk": "LLM01 Prompt Injection", "requirement": "Detect and block prompt injection attempts"},
        {"framework": "MITRE ATLAS", "technique": "AML.T0051 Prompt Injection", "requirement": "Identify prompt manipulation techniques"},
    ],
    "prompt_extraction": [
        {"framework": "EU AI Act", "article": "Art. 15 Robustness", "requirement": "Protect AI system instructions from extraction"},
        {"framework": "NIST AI 600-1", "risk": "GAI-9 Prompt Injection", "requirement": "Prevent system prompt disclosure via extraction"},
        {"framework": "SOC 2", "criteria": "CC6.1 Logical Access Security", "requirement": "Protect confidential system configurations"},
        {"framework": "OWASP LLM", "risk": "LLM07 System Prompt Leakage", "requirement": "Prevent disclosure of system instructions"},
        {"framework": "MITRE ATLAS", "technique": "AML.T0051.001 Direct Injection", "requirement": "Detect system prompt extraction attempts"},
    ],
    "toxicity": [
        {"framework": "EU AI Act", "article": "Art. 9 Risk Mgmt System", "requirement": "Prevent generation of harmful or toxic content"},
        {"framework": "NIST AI 600-1", "risk": "GAI-1 CBRN / GAI-3 Toxic Content", "requirement": "Monitor for toxic, hateful, or harmful outputs"},
        {"framework": "SOC 2", "criteria": "CC1.1 COSO Principles", "requirement": "Maintain ethical standards in AI operations"},
        {"framework": "ISO 42001", "control": "A.5.3 AI Policy", "requirement": "Enforce responsible AI use policies"},
        {"framework": "OWASP LLM", "risk": "LLM09 Misinformation", "requirement": "Detect harmful or misleading content generation"},
    ],
    "tool_call": [
        {"framework": "EU AI Act", "article": "Art. 14 Human Oversight", "requirement": "Monitor and control AI tool invocations"},
        {"framework": "NIST AI 600-1", "risk": "GAI-7 Human-AI Config", "requirement": "Validate AI agent tool usage and authorization"},
        {"framework": "DORA", "pillar": "Pillar 1 - ICT Risk Mgmt", "requirement": "Monitor third-party API and tool interactions"},
        {"framework": "SOC 2", "criteria": "CC6.3 Authorized Access", "requirement": "Control and monitor external system interactions"},
        {"framework": "OWASP LLM", "risk": "LLM08 Excessive Agency", "requirement": "Limit and monitor AI tool execution scope"},
        {"framework": "MITRE ATLAS", "technique": "AML.T0054 Plugin Compromise", "requirement": "Detect unauthorized tool invocation patterns"},
    ],
    "mcp_security": [
        {"framework": "EU AI Act", "article": "Art. 15 Accuracy/Robustness", "requirement": "Secure AI communication protocols against tampering"},
        {"framework": "NIST AI 600-1", "risk": "GAI-9 Prompt Injection", "requirement": "Protect model context protocol from injection"},
        {"framework": "DORA", "pillar": "Pillar 2 - ICT Incident Mgmt", "requirement": "Detect and report protocol-level security incidents"},
        {"framework": "SOC 2", "criteria": "CC6.6 System Boundaries", "requirement": "Secure communication channels and protocols"},
        {"framework": "OWASP LLM", "risk": "LLM01 Prompt Injection", "requirement": "Detect injection via MCP tool descriptions"},
    ],
    "schema_injection": [
        {"framework": "EU AI Act", "article": "Art. 15 Robustness", "requirement": "Protect structured outputs from schema manipulation"},
        {"framework": "NIST AI 600-1", "risk": "GAI-9 Prompt Injection", "requirement": "Detect injection via structured data schemas"},
        {"framework": "SOC 2", "criteria": "CC6.1 Logical Access Security", "requirement": "Validate data schema integrity"},
        {"framework": "OWASP LLM", "risk": "LLM01 Prompt Injection", "requirement": "Detect injection through schema-level manipulation"},
        {"framework": "MITRE ATLAS", "technique": "AML.T0051 Prompt Injection", "requirement": "Identify schema-based injection techniques"},
    ],
    "sequential_action": [
        {"framework": "EU AI Act", "article": "Art. 14 Human Oversight", "requirement": "Monitor multi-step AI agent action sequences"},
        {"framework": "NIST AI 600-1", "risk": "GAI-7 Human-AI Config", "requirement": "Track and validate sequential agent actions"},
        {"framework": "DORA", "pillar": "Pillar 3 - Digital Resilience Testing", "requirement": "Test multi-step AI workflows for safety"},
        {"framework": "SOC 2", "criteria": "CC7.2 Incident Response", "requirement": "Detect and respond to unauthorized action chains"},
        {"framework": "OWASP LLM", "risk": "LLM08 Excessive Agency", "requirement": "Detect dangerous multi-step action patterns"},
    ],
    "scope_enforcement": [
        {"framework": "EU AI Act", "article": "Art. 14 Human Oversight", "requirement": "Enforce boundaries on AI system capabilities"},
        {"framework": "NIST AI 600-1", "risk": "GAI-7 Human-AI Config", "requirement": "Maintain defined scope of AI operations"},
        {"framework": "SOC 2", "criteria": "CC6.3 Authorized Access", "requirement": "Enforce least-privilege for AI operations"},
        {"framework": "ISO 42001", "control": "A.7.2 AI System Lifecycle", "requirement": "Define and enforce AI operational boundaries"},
        {"framework": "OWASP LLM", "risk": "LLM08 Excessive Agency", "requirement": "Prevent AI from exceeding defined scope"},
    ],
    "sycophancy": [
        {"framework": "EU AI Act", "article": "Art. 9 Risk Mgmt, Art. 15 Accuracy", "requirement": "Detect AI outputs biased by user agreement-seeking"},
        {"framework": "NIST AI 600-1", "risk": "GAI-2 Confabulation", "requirement": "Detect sycophantic responses that sacrifice accuracy"},
        {"framework": "SR 11-7", "section": "Outcomes Analysis", "requirement": "Identify model bias toward user-pleasing outputs"},
        {"framework": "ISO 42001", "control": "A.7.4 AI System Monitoring", "requirement": "Monitor for sycophantic behavior patterns"},
        {"framework": "OWASP LLM", "risk": "LLM09 Misinformation", "requirement": "Detect agreement-biased inaccurate responses"},
    ],
    "memory_exfiltration": [
        {"framework": "EU AI Act", "article": "Art. 10 Data Governance", "requirement": "Protect AI system memory from unauthorized access"},
        {"framework": "NIST AI 600-1", "risk": "GAI-4 Data Privacy", "requirement": "Prevent extraction of data from AI memory stores"},
        {"framework": "DORA", "pillar": "Pillar 2 - ICT Incident Mgmt", "requirement": "Detect and report data exfiltration incidents"},
        {"framework": "SOC 2", "criteria": "CC6.1 Logical Access Security", "requirement": "Protect stored data from unauthorized extraction"},
        {"framework": "OWASP LLM", "risk": "LLM06 Sensitive Info Disclosure", "requirement": "Prevent memory-based data exfiltration"},
        {"framework": "MITRE ATLAS", "technique": "AML.T0024 Exfiltration", "requirement": "Detect attempts to extract training or session data"},
        {"framework": "PCI-DSS", "requirement": "Req 3 Protect Stored Data", "detail": "Prevent exfiltration of stored cardholder data via AI"},
    ],
    "confidence_hallucination": [
        {"framework": "EU AI Act", "article": "Art. 13 Transparency", "requirement": "Ensure AI confidence levels are calibrated and honest"},
        {"framework": "NIST AI 600-1", "risk": "GAI-2 Confabulation", "requirement": "Detect overconfident or miscalibrated AI outputs"},
        {"framework": "SR 11-7", "section": "Outcomes Analysis", "requirement": "Validate model confidence calibration accuracy"},
        {"framework": "ISO 42001", "control": "A.7.4 AI System Monitoring", "requirement": "Monitor AI confidence score reliability"},
        {"framework": "OWASP LLM", "risk": "LLM09 Misinformation", "requirement": "Detect false confidence in generated content"},
    ],
}

# ---------------------------------------------------------------------------
# Enforcement timeline
# ---------------------------------------------------------------------------

ENFORCEMENT_TIMELINE: list[dict[str, str]] = [
    {"framework": "DORA", "date": "2025-01-17", "status": "enforced", "detail": "Digital Operational Resilience Act fully applicable"},
    {"framework": "PCI DSS 4.0", "date": "2025-03-31", "status": "enforced", "detail": "PCI DSS v4.0 future-dated requirements now mandatory"},
    {"framework": "SR 11-7", "date": "continuous", "status": "enforced", "detail": "Fed supervisory guidance on model risk management"},
    {"framework": "FINRA Rule 3110", "date": "continuous", "status": "enforced", "detail": "Supervisory obligations for AI in broker-dealers"},
    {"framework": "SEC AI Examinations", "date": "2026-01-01", "status": "active", "detail": "SEC Division of Examinations AI-focused reviews"},
    {"framework": "Illinois HB 3773", "date": "2026-01-01", "status": "upcoming", "detail": "Illinois AI regulation for employment decisions"},
    {"framework": "Texas TRAIGA", "date": "2026-01-01", "status": "upcoming", "detail": "Texas Responsible AI Governance Act"},
    {"framework": "Colorado SB 205", "date": "2026-06-30", "status": "upcoming", "detail": "Colorado AI Act for high-risk AI systems"},
    {"framework": "EU AI Act (high-risk)", "date": "2026-08-02", "status": "upcoming", "detail": "Obligations for high-risk AI systems applicable"},
]


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------


async def get_compliance_matrix(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> list[dict[str, object]]:
    """Return the full compliance matrix with per-category incident counts."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    counts_result = await db.execute(
        select(Incident.category, func.count(Incident.id))
        .where(Incident.org_id == org_id, Incident.created_at >= cutoff)
        .group_by(Incident.category)
    )
    counts: dict[str, int] = {
        str(cat): int(cnt) for cat, cnt in counts_result.all()
    }

    matrix: list[dict[str, object]] = []
    for category, frameworks in FRAMEWORK_MAPPING.items():
        matrix.append({
            "category": category,
            "incident_count": counts.get(category, 0),
            "frameworks": frameworks,
        })
    return matrix


async def get_framework_summary(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> list[dict[str, object]]:
    """Return per-framework summary: total violations and covered categories."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    counts_result = await db.execute(
        select(Incident.category, func.count(Incident.id))
        .where(Incident.org_id == org_id, Incident.created_at >= cutoff)
        .group_by(Incident.category)
    )
    counts: dict[str, int] = {
        str(cat): int(cnt) for cat, cnt in counts_result.all()
    }

    # Invert the mapping: framework -> list of categories
    fw_categories: dict[str, list[str]] = {}
    for category, frameworks in FRAMEWORK_MAPPING.items():
        for entry in frameworks:
            fw_name = entry["framework"]
            fw_categories.setdefault(fw_name, []).append(category)

    summary: list[dict[str, object]] = []
    for fw_name, categories in sorted(fw_categories.items()):
        violations = sum(counts.get(cat, 0) for cat in categories)
        summary.append({
            "framework": fw_name,
            "covered_categories": sorted(set(categories)),
            "total_violations": violations,
            "categories_with_incidents": sorted(
                {cat for cat in categories if counts.get(cat, 0) > 0}
            ),
        })
    return summary


def get_enforcement_timeline() -> list[dict[str, str]]:
    """Return static list of upcoming and active enforcement dates."""
    return ENFORCEMENT_TIMELINE
