"""Per-category incident analysis functions for the interpretability service."""

from __future__ import annotations

from app.models.proxy import ProxyRequest

from .interpretability_utils import (
    INJECTION_PATTERNS,
    PII_PATTERNS,
    category_recommendations,
    check_compliance,
    extract_response_text,
    extract_user_content,
)


def analyze_injection(
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
    user_input = extract_user_content(request_body)
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
    resp_text = extract_response_text(response_body)
    if resp_text and user_input:
        compliance_indicators = check_compliance(resp_text, user_input)
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
        "recommendations": category_recommendations(category),
        "confidence": confidence,
    }


def analyze_hallucination(
    category: str,
    metadata: dict,
    proxy_req: ProxyRequest | None,
    response_body: dict | None,
) -> dict:
    """Analyze hallucination and confidence-hallucination incidents."""
    factors: list[str] = []
    confidence = 0.6

    model_name = str(proxy_req.model) if proxy_req and proxy_req.model is not None else "unknown"
    output_tokens: int | None = int(proxy_req.output_tokens) if proxy_req and proxy_req.output_tokens is not None else None  # type: ignore[arg-type]
    resp_text = extract_response_text(response_body)
    resp_len = len(resp_text) if resp_text else 0

    root_cause = "Model generated factually unsupported content"

    if output_tokens is not None and output_tokens > 2000:
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
        "recommendations": category_recommendations(category),
        "confidence": round(confidence, 2),
    }


def analyze_pii_leak(
    category: str,
    metadata: dict,
    response_body: dict | None,
) -> dict:
    """Analyze PII and financial PII leak incidents."""
    factors: list[str] = []
    confidence = 0.75

    resp_text = extract_response_text(response_body)
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
        "recommendations": category_recommendations(category),
        "confidence": round(confidence, 2),
    }


def analyze_cost_anomaly(metadata: dict, proxy_req: ProxyRequest | None) -> dict:
    """Analyze cost anomaly incidents."""
    factors: list[str] = []
    confidence = 0.7

    if proxy_req is not None:
        total_tokens = int(proxy_req.input_tokens or 0) + int(proxy_req.output_tokens or 0)  # type: ignore[arg-type]
        cost = float(proxy_req.cost_usd or 0.0)  # type: ignore[arg-type]
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
        "recommendations": category_recommendations("cost_anomaly"),
        "confidence": round(confidence, 2),
    }


def analyze_sycophancy(metadata: dict, request_body: dict | None) -> dict:
    """Analyze sycophancy incidents."""
    factors: list[str] = []
    user_input = extract_user_content(request_body)

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
        "recommendations": category_recommendations("sycophancy"),
        "confidence": 0.65,
    }


def analyze_memory_exfiltration(
    metadata: dict, request_body: dict | None, response_body: dict | None
) -> dict:
    """Analyze memory exfiltration incidents."""
    factors: list[str] = []
    user_input = extract_user_content(request_body)

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
        "recommendations": category_recommendations("memory_exfiltration"),
        "confidence": 0.7,
    }


def analyze_toxicity(metadata: dict, response_body: dict | None) -> dict:
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
        "recommendations": category_recommendations("toxicity"),
        "confidence": 0.75,
    }


def analyze_loop(metadata: dict, proxy_req: ProxyRequest | None) -> dict:
    """Analyze loop detection incidents."""
    factors: list[str] = []

    repetition = metadata.get("repetition_count") or metadata.get("loop_count")
    if repetition:
        factors.append(f"Repeated output detected {repetition} times")

    if proxy_req is not None and proxy_req.output_tokens is not None and int(proxy_req.output_tokens) > 3000:  # type: ignore[arg-type]
        factors.append("High token output suggests agent stuck in generation loop")

    if not factors:
        factors.append("Agent produced repetitive or cyclical output patterns")

    return {
        "root_cause": "Agent entered a repetitive output loop, wasting resources",
        "contributing_factors": factors,
        "recommendations": category_recommendations("loop"),
        "confidence": 0.8,
    }


def analyze_generic(category: str, severity: str, metadata: dict) -> dict:
    """Fallback analysis for categories without specialized logic."""
    return {
        "root_cause": f"Detection triggered for category '{category}' at {severity} severity",
        "contributing_factors": [
            f"Category: {category}",
            f"Severity: {severity}",
        ],
        "recommendations": category_recommendations(category),
        "confidence": 0.5,
    }
