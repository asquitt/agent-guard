"""Hallucination detector — LLM-powered fact-checking of agent responses.

Combines rule-based financial pattern checks with LLM analysis.
"""

from __future__ import annotations

import json
import logging
import re

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult
from app.services.llm_service import call_llm, parse_json_response

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 0.7

_SYSTEM_PROMPT = """\
You are a fact-checking assistant for AI agent responses in financial services.
Analyze the given response for hallucinations: fabricated facts, invented citations,
unverifiable claims, or made-up statistics.

Pay special attention to financial hallucinations:
- Fabricated interest rates, APRs, or fee structures
- Non-existent financial regulations or compliance requirements
- Made-up stock tickers, fund names, or CUSIP/ISIN numbers
- Invented market statistics or economic data points
- Incorrect regulatory body names or jurisdictions
- Fictitious case law or regulatory actions

Respond with ONLY valid JSON (no markdown fences):
{
  "confidence": <float 0.0-1.0, how confident you are that hallucinations exist>,
  "issues": [
    {"claim": "<the problematic claim>", "assessment": "<why it's likely fabricated>",
     "category": "<general|financial_data|regulation|market_data>"}
  ]
}

If no hallucinations are found, return {"confidence": 0.0, "issues": []}.
"""

# ---------------------------------------------------------------------------
# Rule-based financial hallucination patterns (pre-LLM pass)
# ---------------------------------------------------------------------------

_FINANCIAL_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    # Impossible interest rates
    (
        "impossible_rate",
        re.compile(
            r"(?:interest rate|APR|annual rate|yield)\s+(?:of|is|at)\s+"
            r"(\d{3,}(?:\.\d+)?)\s*%",
            re.IGNORECASE,
        ),
        "Interest rate over 99% is likely fabricated",
    ),
    # Fabricated US regulatory bodies
    (
        "fake_regulator",
        re.compile(
            r"\b(?:Federal Bureau of Financial (?:Regulation|Oversight)"
            r"|National Financial (?:Authority|Commission)"
            r"|US (?:Financial|Banking) (?:Authority|Board|Commission)"
            r"(?! of Governors))\b",
            re.IGNORECASE,
        ),
        "Referenced a non-existent regulatory body",
    ),
    # Made-up regulation numbers (Section 9xx of SOX, etc.)
    (
        "fake_sox_section",
        re.compile(
            r"\bSarbanes[- ]Oxley\s+(?:Act\s+)?Section\s+([5-9]\d{2,}|[1-9]\d{3,})\b",
            re.IGNORECASE,
        ),
        "SOX does not have sections above 500",
    ),
    # Fabricated Basel Accord version
    (
        "fake_basel",
        re.compile(r"\bBasel\s+(?:IV|V|VI|VII|VIII|[5-9]|[1-9]\d)\b", re.IGNORECASE),
        "Basel framework versions beyond III/3.1 do not exist",
    ),
    # Clearly fabricated percentage (>100% for non-return metrics)
    (
        "impossible_percentage",
        re.compile(
            r"(?:compliance rate|approval rate|success rate|coverage|accuracy)\s+"
            r"(?:of|is|at|reached)\s+(\d{4,}(?:\.\d+)?)\s*%",
            re.IGNORECASE,
        ),
        "Percentage metric exceeds plausible range",
    ),
]


def _extract_text(response_body: str) -> str:
    """Extract text content from OpenAI/Anthropic response JSON."""
    try:
        data = json.loads(response_body)
    except (json.JSONDecodeError, TypeError):
        return response_body

    # OpenAI: choices[0].message.content
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            msg = first.get("message", {})
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str):
                    return content

    # Anthropic: content[0].text
    content_blocks = data.get("content")
    if isinstance(content_blocks, list) and content_blocks:
        first_block = content_blocks[0]
        if isinstance(first_block, dict) and isinstance(first_block.get("text"), str):
            return str(first_block["text"])

    return response_body


def _check_financial_patterns(text: str) -> list[dict[str, str]]:
    """Run rule-based financial hallucination checks."""
    hits: list[dict[str, str]] = []
    for _name, pattern, assessment in _FINANCIAL_PATTERNS:
        match = pattern.search(text)
        if match:
            hits.append({
                "claim": match.group(0),
                "assessment": assessment,
                "category": "financial_data",
            })
    return hits


class HallucinationDetector:
    """Async detector for hallucinated content in LLM responses.

    Sends the response to AgentGuard's internal LLM for fact-checking.
    Fails open: if the LLM call fails, returns detected=False.
    """

    category: str = DetectorCategory.HALLUCINATION.value

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
        org_id: str,
        proxy_request_id: str,
    ) -> DetectionResult:
        raw_thresh = detector_config.get("threshold")
        threshold = float(str(raw_thresh)) if raw_thresh is not None else _DEFAULT_THRESHOLD
        financial_checks = bool(detector_config.get("financial_checks", True))

        response_text = _extract_text(response_body)
        if len(response_text) < 50:
            return self._pass("Response too short for hallucination analysis")

        # Pass 1: Rule-based financial pattern checks (fast, no LLM call)
        rule_issues: list[dict[str, str]] = []
        if financial_checks:
            rule_issues = _check_financial_patterns(response_text)

        # Pass 2: LLM-powered analysis
        llm_response = call_llm(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=f"Analyze this response for hallucinations:\n\n{response_text[:4000]}",
            max_tokens=1024,
        )

        llm_issues: list[dict[str, str]] = []
        confidence = 0.0

        if llm_response:
            parsed = parse_json_response(llm_response)
            raw_conf = parsed.get("confidence")
            if raw_conf is not None:
                try:
                    confidence = float(str(raw_conf))
                except (ValueError, TypeError):
                    pass

            issues_raw = parsed.get("issues", [])
            if isinstance(issues_raw, list):
                for item in issues_raw:
                    if isinstance(item, dict):
                        llm_issues.append(
                            {
                                "claim": str(item.get("claim", "")),
                                "assessment": str(item.get("assessment", "")),
                                "category": str(item.get("category", "general")),
                            }
                        )

        # Merge: rule-based hits boost confidence
        all_issues = rule_issues + llm_issues
        if rule_issues and confidence < threshold:
            # Rule hits always surface — boost confidence to at least threshold
            confidence = max(confidence, threshold + 0.05)

        if confidence < threshold and not rule_issues:
            return self._pass(f"Hallucination confidence {confidence:.2f} below threshold {threshold}")

        severity = IncidentSeverity.HIGH.value
        if confidence >= 0.9 or any(i.get("category") == "financial_data" for i in all_issues):
            severity = IncidentSeverity.CRITICAL.value
        elif confidence < 0.8 and not rule_issues:
            severity = IncidentSeverity.MEDIUM.value

        return DetectionResult(
            detected=True,
            severity=severity,
            category=self.category,
            detector_id=None,
            action=DetectionAction.MONITOR,
            title=f"Hallucination detected (confidence: {confidence:.0%})",
            description=(
                f"Found {len(all_issues)} potential hallucination(s) "
                f"({len(rule_issues)} rule-based, {len(llm_issues)} LLM-detected) "
                f"with {confidence:.0%} confidence in response from {model or 'unknown'}"
            ),
            details={
                "confidence": round(confidence, 4),
                "threshold": threshold,
                "rule_issues": rule_issues,
                "llm_issues": llm_issues,
                "financial_checks_enabled": financial_checks,
                "model": model or "unknown",
            },
        )

    def _pass(self, title: str) -> DetectionResult:
        return DetectionResult(
            detected=False,
            severity=IncidentSeverity.INFO.value,
            category=self.category,
            detector_id=None,
            action=DetectionAction.PASS,
            title=title,
        )
