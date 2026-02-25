"""Interpretability utility functions — parsing, extraction, and category mappings."""

from __future__ import annotations

import json
import re

# ---------------------------------------------------------------------------
# Injection-related patterns (shared with analyzers)
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
INJECTION_CATEGORIES = frozenset({
    "prompt_injection",
    "instruction_hierarchy",
    "schema_injection",
    "prompt_extraction",
})

# Hallucination-family categories
HALLUCINATION_CATEGORIES = frozenset({
    "hallucination",
    "confidence_hallucination",
})

# PII-family categories
PII_CATEGORIES = frozenset({
    "pii_leak",
    "financial_pii",
})


# ---------------------------------------------------------------------------
# JSON / content extraction
# ---------------------------------------------------------------------------


def safe_parse_json(text: str | None) -> dict | None:
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, TypeError):
        return None


def extract_user_content(body: dict | None) -> str | None:
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


def extract_response_text(body: dict | None) -> str | None:
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


def check_compliance(response_text: str, user_input: str) -> str:
    """Simple heuristic: check if response echoes suspicious user phrases."""
    lower_resp = response_text.lower()
    for pat in INJECTION_PATTERNS:
        match = pat.search(user_input)
        if match:
            phrase = match.group(0).lower()
            if phrase in lower_resp:
                return phrase
    return ""


# ---------------------------------------------------------------------------
# Category mappings
# ---------------------------------------------------------------------------


def category_to_root_cause(category: str) -> str:
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


def category_to_pattern(category: str) -> str:
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


def category_recommendations(category: str) -> list[str]:
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


def empty_investigation(reason: str) -> dict:
    """Return an empty investigation result with a reason."""
    return {
        "root_cause": reason,
        "contributing_factors": [],
        "attack_chain": [],
        "recommendations": [],
        "similar_incidents": [],
        "confidence": 0.0,
    }
