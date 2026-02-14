# pyright: reportGeneralTypeIssues=false, reportArgumentType=false
"""Interpretability-powered incident investigation service (Feature 20).

Provides root-cause analysis for incidents — answering "why did the agent
hallucinate / get injected / leak PII" rather than just "what happened".
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.models.proxy import ProxyRequest

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Injection-related patterns
# ---------------------------------------------------------------------------
INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(previous|above|all)\s+(instructions?|prompts?)", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"system\s*:\s*", re.I),
    re.compile(r"<\|im_start\|>", re.I),
    re.compile(r"\[INST\]", re.I),
    re.compile(r"do\s+not\s+follow\s+(your|the)\s+(rules|guidelines)", re.I),
    re.compile(r"reveal\s+(your|the)\s+(system|hidden)\s+prompt", re.I),
]

PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
}

# Categories that indicate prompt-injection-family attacks
_INJECTION_CATEGORIES = frozenset({
    "prompt_injection",
    "instruction_hierarchy",
    "schema_injection",
    "prompt_extraction",
})

# Hallucination-family categories
_HALLUCINATION_CATEGORIES = frozenset({
    "hallucination",
    "confidence_hallucination",
})

# PII-family categories
_PII_CATEGORIES = frozenset({
    "pii_leak",
    "financial_pii",
})


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
        return _empty_investigation("Incident not found")

    category = str(incident.category)
    severity = str(incident.severity)
    metadata = incident.metadata_ or {}

    # Fetch associated proxy request if present
    proxy_req = None
    if incident.proxy_request_id:
        pr_result = await db.execute(
            select(ProxyRequest).where(
                ProxyRequest.id == incident.proxy_request_id,
                ProxyRequest.org_id == org_id,
            )
        )
        proxy_req = pr_result.scalar_one_or_none()

    request_body = _safe_parse_json(proxy_req.request_body) if proxy_req else None
    response_body = _safe_parse_json(proxy_req.response_body) if proxy_req else None

    # Dispatch analysis by category
    if category in _INJECTION_CATEGORIES:
        analysis = _analyze_injection(category, metadata, request_body, response_body)
    elif category in _HALLUCINATION_CATEGORIES:
        analysis = _analyze_hallucination(
            category, metadata, proxy_req, response_body
        )
    elif category in _PII_CATEGORIES:
        analysis = _analyze_pii_leak(category, metadata, response_body)
    elif category == "cost_anomaly":
        analysis = _analyze_cost_anomaly(metadata, proxy_req)
    elif category == "sycophancy":
        analysis = _analyze_sycophancy(metadata, request_body)
    elif category == "memory_exfiltration":
        analysis = _analyze_memory_exfiltration(metadata, request_body, response_body)
    elif category == "toxicity":
        analysis = _analyze_toxicity(metadata, response_body)
    elif category == "loop":
        analysis = _analyze_loop(metadata, proxy_req)
    else:
        analysis = _analyze_generic(category, severity, metadata)

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
        {"cause": _category_to_root_cause(cat), "count": cnt}
        for cat, cnt in category_counts
    ]

    # Recurring patterns: categories with 3+ incidents
    recurring_patterns = [
        {"pattern": _category_to_pattern(cat), "frequency": cnt}
        for cat, cnt in category_counts
        if cnt >= 3
    ]

    # Aggregate recommendations from top categories
    recommended_actions: list[str] = []
    seen: set[str] = set()
    for cat, _ in category_counts[:5]:
        for rec in _category_recommendations(cat):
            if rec not in seen:
                recommended_actions.append(rec)
                seen.add(rec)

    return {
        "top_root_causes": top_root_causes,
        "recurring_patterns": recurring_patterns,
        "recommended_actions": recommended_actions,
    }


# ---------------------------------------------------------------------------
# Per-category analysis helpers
# ---------------------------------------------------------------------------


def _analyze_injection(
    category: str,
    metadata: dict,
    request_body: dict | None,
    response_body: dict | None,
) -> dict:
    """Analyze prompt-injection-family incidents."""
    root_cause = "Prompt injection payload in user input bypassed safeguards"
    factors: list[str] = []
    chain: list[dict] = []
    confidence = 0.7

    # Try to extract injection payload from request
    user_input = _extract_user_content(request_body)
    matched_patterns: list[str] = []
    if user_input:
        for pat in INJECTION_PATTERNS:
            match = pat.search(user_input)
            if match:
                matched_patterns.append(match.group(0))

    if matched_patterns:
        confidence = 0.9
        root_cause = (
            f"Detected injection pattern in user input: "
            f"'{matched_patterns[0][:60]}'"
        )
        chain.append({
            "step": "injection_point",
            "description": "Malicious payload found in user message",
            "evidence": matched_patterns[0][:80],
        })

    if category == "instruction_hierarchy":
        factors.append("User input attempted to override system-level instructions")
        root_cause = "User message contained instructions that conflict with system prompt hierarchy"
    elif category == "schema_injection":
        factors.append("Structured input (JSON/XML) contained embedded instructions")
        root_cause = "Injection payload embedded within structured data schema"
    elif category == "prompt_extraction":
        factors.append("User attempted to extract system prompt content")
        root_cause = "Request designed to reveal system prompt or hidden instructions"

    # Check if model complied
    resp_text = _extract_response_text(response_body)
    if resp_text and user_input:
        compliance_indicators = _check_compliance(resp_text, user_input)
        if compliance_indicators:
            factors.append("Model response shows signs of complying with injected instructions")
            chain.append({
                "step": "compliance",
                "description": "Model partially followed injected instructions",
                "evidence": compliance_indicators[:80],
            })
            confidence = min(confidence + 0.1, 1.0)

    if not factors:
        factors.append("Input contained adversarial patterns targeting LLM behavior")

    return {
        "root_cause": root_cause,
        "contributing_factors": factors,
        "attack_chain": chain,
        "recommendations": _category_recommendations(category),
        "confidence": confidence,
    }


def _analyze_hallucination(
    category: str,
    metadata: dict,
    proxy_req: ProxyRequest | None,
    response_body: dict | None,
) -> dict:
    """Analyze hallucination and confidence-hallucination incidents."""
    factors: list[str] = []
    confidence = 0.6

    model_name = str(proxy_req.model) if proxy_req and proxy_req.model else "unknown"
    output_tokens = proxy_req.output_tokens if proxy_req else None
    resp_text = _extract_response_text(response_body)
    resp_len = len(resp_text) if resp_text else 0

    root_cause = "Model generated factually unsupported content"

    if output_tokens and output_tokens > 2000:
        factors.append(
            f"Long response ({output_tokens} tokens) increases hallucination risk"
        )
        confidence += 0.1

    if resp_len > 4000:
        factors.append("Extended response length correlates with reduced factual accuracy")

    if category == "confidence_hallucination":
        root_cause = "Model expressed high confidence in unverifiable or incorrect claims"
        factors.append("Overconfident language detected without supporting evidence")
        confidence += 0.1

    score = metadata.get("score") or metadata.get("hallucination_score")
    if score is not None:
        factors.append(f"Detection score: {score}")
        confidence = min(0.5 + float(score) * 0.4, 1.0)

    factors.append(f"Model used: {model_name}")

    return {
        "root_cause": root_cause,
        "contributing_factors": factors,
        "recommendations": _category_recommendations(category),
        "confidence": round(confidence, 2),
    }


def _analyze_pii_leak(
    category: str,
    metadata: dict,
    response_body: dict | None,
) -> dict:
    """Analyze PII and financial PII leak incidents."""
    factors: list[str] = []
    confidence = 0.75

    resp_text = _extract_response_text(response_body)
    detected_types: list[str] = []

    if resp_text:
        for pii_type, pattern in PII_PATTERNS.items():
            if pattern.search(resp_text):
                detected_types.append(pii_type)

    if detected_types:
        factors.append(f"PII types found in response: {', '.join(detected_types)}")
        confidence = 0.9
    else:
        factors.append("PII detected by pattern matching in detection pipeline")

    root_cause = "Model included personally identifiable information in its response"
    if category == "financial_pii":
        root_cause = "Model exposed financial PII (account numbers, SSNs, or card data)"
        factors.append("Financial data requires heightened protection under PCI-DSS / SOX")

    pii_meta = metadata.get("pii_types") or metadata.get("detected_entities")
    if pii_meta:
        factors.append(f"Detection metadata: {pii_meta}")

    return {
        "root_cause": root_cause,
        "contributing_factors": factors,
        "recommendations": _category_recommendations(category),
        "confidence": round(confidence, 2),
    }


def _analyze_cost_anomaly(metadata: dict, proxy_req: ProxyRequest | None) -> dict:
    """Analyze cost anomaly incidents."""
    factors: list[str] = []
    confidence = 0.7

    if proxy_req:
        total_tokens = (proxy_req.input_tokens or 0) + (proxy_req.output_tokens or 0)
        cost = proxy_req.cost_usd or 0.0
        factors.append(f"Request used {total_tokens} tokens (${cost:.4f})")
        if total_tokens > 10000:
            confidence = 0.85
            factors.append("Token count significantly above typical request baseline")

    threshold = metadata.get("threshold")
    if threshold:
        factors.append(f"Cost threshold exceeded: {threshold}")

    return {
        "root_cause": "Request token consumption exceeded organization baseline thresholds",
        "contributing_factors": factors,
        "recommendations": _category_recommendations("cost_anomaly"),
        "confidence": round(confidence, 2),
    }


def _analyze_sycophancy(metadata: dict, request_body: dict | None) -> dict:
    """Analyze sycophancy incidents."""
    factors: list[str] = []
    user_input = _extract_user_content(request_body)

    if user_input:
        leading_indicators = [
            "don't you think",
            "wouldn't you agree",
            "obviously",
            "clearly",
            "everyone knows",
            "isn't it true",
        ]
        found = [ind for ind in leading_indicators if ind in user_input.lower()]
        if found:
            factors.append(f"Leading language detected: {', '.join(found[:3])}")

    if not factors:
        factors.append("User input contained leading or opinion-seeking phrasing")

    return {
        "root_cause": "Model agreed with user's premise without critical evaluation",
        "contributing_factors": factors,
        "recommendations": _category_recommendations("sycophancy"),
        "confidence": 0.65,
    }


def _analyze_memory_exfiltration(
    metadata: dict, request_body: dict | None, response_body: dict | None
) -> dict:
    """Analyze memory exfiltration incidents."""
    factors: list[str] = []
    user_input = _extract_user_content(request_body)

    if user_input:
        extraction_phrases = [
            "what do you remember",
            "tell me everything",
            "previous conversation",
            "earlier session",
            "past interactions",
        ]
        found = [p for p in extraction_phrases if p in user_input.lower()]
        if found:
            factors.append(f"Extraction phrases detected: {', '.join(found[:3])}")

    if not factors:
        factors.append("Request attempted to extract information from model context/memory")

    return {
        "root_cause": "User attempted to extract stored context or conversation history",
        "contributing_factors": factors,
        "recommendations": _category_recommendations("memory_exfiltration"),
        "confidence": 0.7,
    }


def _analyze_toxicity(metadata: dict, response_body: dict | None) -> dict:
    """Analyze toxicity incidents."""
    factors: list[str] = []
    score = metadata.get("toxicity_score") or metadata.get("score")
    if score is not None:
        factors.append(f"Toxicity score: {score}")

    categories = metadata.get("categories") or metadata.get("toxic_categories")
    if categories:
        factors.append(f"Toxic content categories: {categories}")

    if not factors:
        factors.append("Response contained harmful, offensive, or inappropriate content")

    return {
        "root_cause": "Model generated content flagged as toxic or harmful",
        "contributing_factors": factors,
        "recommendations": _category_recommendations("toxicity"),
        "confidence": 0.75,
    }


def _analyze_loop(metadata: dict, proxy_req: ProxyRequest | None) -> dict:
    """Analyze loop detection incidents."""
    factors: list[str] = []

    repetition = metadata.get("repetition_count") or metadata.get("loop_count")
    if repetition:
        factors.append(f"Repeated output detected {repetition} times")

    if proxy_req and proxy_req.output_tokens and proxy_req.output_tokens > 3000:
        factors.append("High token output suggests agent stuck in generation loop")

    if not factors:
        factors.append("Agent produced repetitive or cyclical output patterns")

    return {
        "root_cause": "Agent entered a repetitive output loop, wasting resources",
        "contributing_factors": factors,
        "recommendations": _category_recommendations("loop"),
        "confidence": 0.8,
    }


def _analyze_generic(category: str, severity: str, metadata: dict) -> dict:
    """Fallback analysis for categories without specialized logic."""
    return {
        "root_cause": f"Detection triggered for category '{category}' at {severity} severity",
        "contributing_factors": [
            f"Category: {category}",
            f"Severity: {severity}",
        ],
        "recommendations": _category_recommendations(category),
        "confidence": 0.5,
    }


# ---------------------------------------------------------------------------
# Helpers
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


def _safe_parse_json(text: str | None) -> dict | None:
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def _extract_user_content(body: dict | None) -> str | None:
    """Extract the last user message content from a chat-completion request body."""
    if not body:
        return None
    messages = body.get("messages")
    if not isinstance(messages, list):
        return body.get("prompt")
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return " ".join(
                    p.get("text", "") for p in content if isinstance(p, dict)
                )
    return None


def _extract_response_text(body: dict | None) -> str | None:
    """Extract assistant response text from a chat-completion response body."""
    if not body:
        return None
    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message", {})
        if isinstance(msg, dict):
            return msg.get("content")
    # Fallback for non-chat completions
    return body.get("text") or body.get("output")


def _check_compliance(response_text: str, user_input: str) -> str:
    """Simple heuristic: check if response echoes suspicious user phrases."""
    lower_resp = response_text.lower()
    for pat in INJECTION_PATTERNS:
        match = pat.search(user_input)
        if match:
            phrase = match.group(0).lower()
            if phrase in lower_resp:
                return phrase
    return ""


def _category_to_root_cause(category: str) -> str:
    """Map a detection category to a human-readable root cause label."""
    mapping: dict[str, str] = {
        "prompt_injection": "Prompt injection attacks",
        "instruction_hierarchy": "Instruction hierarchy violations",
        "schema_injection": "Schema-based injection payloads",
        "prompt_extraction": "System prompt extraction attempts",
        "hallucination": "Model hallucinations",
        "confidence_hallucination": "Overconfident hallucinations",
        "pii_leak": "PII data leakage",
        "financial_pii": "Financial PII exposure",
        "cost_anomaly": "Abnormal token consumption",
        "sycophancy": "Sycophantic model responses",
        "memory_exfiltration": "Memory/context exfiltration",
        "toxicity": "Toxic content generation",
        "loop": "Agent output loops",
        "compliance": "Regulatory compliance violations",
        "scope_enforcement": "Agent scope violations",
        "capability_monitor": "Unauthorized capability usage",
        "sequential_action": "Suspicious action sequences",
    }
    return mapping.get(category, f"Detection: {category}")


def _category_to_pattern(category: str) -> str:
    """Map a detection category to a recurring pattern description."""
    mapping: dict[str, str] = {
        "prompt_injection": "Repeated injection attempts targeting LLM input",
        "instruction_hierarchy": "Persistent instruction override attempts",
        "schema_injection": "Recurring schema-based injection payloads",
        "hallucination": "Frequent factual accuracy failures",
        "confidence_hallucination": "Repeated overconfident false claims",
        "pii_leak": "Recurring PII exposure in model outputs",
        "financial_pii": "Repeated financial data leakage",
        "cost_anomaly": "Recurring cost spikes in LLM usage",
        "sycophancy": "Pattern of uncritical agreement by model",
        "toxicity": "Recurring toxic content in responses",
        "loop": "Repeated agent output loops",
    }
    return mapping.get(category, f"Recurring {category} detections")


def _category_recommendations(category: str) -> list[str]:
    """Return actionable recommendations for a detection category."""
    recs: dict[str, list[str]] = {
        "prompt_injection": [
            "Enable instruction_hierarchy detector in BLOCK mode",
            "Add input sanitization rules to strip known injection patterns",
            "Review system prompt for delimiter-based isolation",
        ],
        "instruction_hierarchy": [
            "Strengthen system prompt with explicit hierarchy boundaries",
            "Enable schema_injection detector for structured input validation",
        ],
        "schema_injection": [
            "Validate all structured inputs against strict schemas before LLM processing",
            "Enable prompt_injection detector as a complementary defense layer",
        ],
        "prompt_extraction": [
            "Add output filtering to detect system prompt leakage",
            "Use canary tokens in system prompts to detect extraction",
        ],
        "hallucination": [
            "Consider enabling confidence_hallucination detector for richer analysis",
            "Reduce max_tokens to limit response length where appropriate",
            "Add retrieval-augmented generation (RAG) to ground model responses",
        ],
        "confidence_hallucination": [
            "Enable hallucination detector alongside confidence checks",
            "Instruct model to cite sources and express uncertainty",
        ],
        "pii_leak": [
            "Set PII detector to REDACT mode to automatically mask sensitive data",
            "Review input prompts to ensure PII is not injected into context",
        ],
        "financial_pii": [
            "Set financial_pii detector to BLOCK mode for PCI-DSS compliance",
            "Audit prompt templates for accidental inclusion of financial data",
        ],
        "cost_anomaly": [
            "Set per-request token limits via proxy endpoint configuration",
            "Review cost thresholds and adjust baselines for the organization",
        ],
        "sycophancy": [
            "Add system prompt instructions for critical evaluation of user claims",
            "Enable reasoning_trace detector to monitor chain-of-thought quality",
        ],
        "memory_exfiltration": [
            "Limit conversation context window size",
            "Enable prompt_injection detector to catch extraction-style prompts",
        ],
        "toxicity": [
            "Set toxicity detector to BLOCK mode for production endpoints",
            "Review system prompt safety guidelines",
        ],
        "loop": [
            "Set max_tokens limits on proxy endpoints",
            "Enable cost_anomaly detector to catch loops that waste tokens",
        ],
    }
    return recs.get(category, [f"Review {category} detector configuration and thresholds"])


def _empty_investigation(reason: str) -> dict:
    """Return an empty investigation result with a reason."""
    return {
        "root_cause": reason,
        "contributing_factors": [],
        "attack_chain": [],
        "recommendations": [],
        "similar_incidents": [],
        "confidence": 0.0,
    }
