"""Compliance detector — rule-based keyword matching + LLM verification."""

from __future__ import annotations

import logging
import re

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult
from app.services.llm_service import call_llm, parse_json_response

logger = logging.getLogger(__name__)

# Regulatory keyword sets (case-insensitive matching)
_FRAMEWORK_KEYWORDS: dict[str, list[str]] = {
    "SOX": [
        "financial statement",
        "material weakness",
        "internal controls",
        "audit opinion",
        "restatement",
        "disclosure controls",
        "management assessment",
    ],
    "PCI-DSS": [
        "cardholder",
        "cvv",
        "magnetic stripe",
        "card verification",
        "payment card",
        "primary account number",
        "pan data",
    ],
    "FFIEC": [
        "fair lending",
        "redlining",
        "disparate impact",
        "risk disclosure",
        "community reinvestment",
        "bank secrecy",
        "anti-money laundering",
    ],
}

# Pre-compiled patterns per framework
_FRAMEWORK_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    framework: [re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords]
    for framework, keywords in _FRAMEWORK_KEYWORDS.items()
}

_ALL_FRAMEWORKS = list(_FRAMEWORK_KEYWORDS.keys())

_LLM_SYSTEM_PROMPT = """\
You are a financial regulatory compliance analyst. Analyze the given text for
potential regulatory violations.

Respond with ONLY valid JSON (no markdown fences):
{
  "violation": <true|false>,
  "framework": "<which regulation: SOX, PCI-DSS, or FFIEC>",
  "explanation": "<brief explanation of the violation or why it's compliant>"
}
"""


def _get_enabled_frameworks(detector_config: dict[str, object]) -> list[str]:
    """Get list of enabled regulatory frameworks from config."""
    raw = detector_config.get("frameworks")
    if isinstance(raw, list):
        valid = [str(f) for f in raw if str(f) in _FRAMEWORK_KEYWORDS]
        if valid:
            return valid
    return _ALL_FRAMEWORKS


class ComplianceDetector:
    """Sync detector for regulatory compliance violations.

    Two-pass detection:
    1. Rule-based keyword matching against configured frameworks
    2. LLM verification of flagged content (if LLM available)

    If LLM is unavailable, keyword matches alone are reported.
    """

    category: str = DetectorCategory.COMPLIANCE.value

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
    ) -> DetectionResult:
        frameworks = _get_enabled_frameworks(detector_config)
        response_lower = response_body.lower()

        # Pass 1: keyword matching
        keyword_hits: dict[str, list[str]] = {}
        for framework in frameworks:
            patterns = _FRAMEWORK_PATTERNS.get(framework, [])
            matched = [p.pattern.replace("\\", "") for p in patterns if p.search(response_lower)]
            if matched:
                keyword_hits[framework] = matched

        if not keyword_hits:
            return self._pass("No regulatory keywords detected")

        # Pass 2: LLM verification (best-effort)
        llm_verified = self._llm_verify(response_body, keyword_hits)

        # Build result
        hit_summary = ", ".join(f"{fw} ({len(kws)})" for fw, kws in keyword_hits.items())

        severity = IncidentSeverity.MEDIUM.value
        if any(fw in ("SOX", "PCI-DSS") for fw in keyword_hits):
            severity = IncidentSeverity.HIGH.value
        if llm_verified.get("violation") is True:
            severity = IncidentSeverity.CRITICAL.value

        return DetectionResult(
            detected=True,
            severity=severity,
            category=self.category,
            detector_id=None,
            action=DetectionAction.MONITOR,
            title=f"Compliance keywords: {hit_summary}",
            description=(
                f"Detected regulatory keywords across {len(keyword_hits)} framework(s). "
                + (
                    f"LLM confirmed violation: {llm_verified.get('explanation', 'N/A')}"
                    if llm_verified.get("violation") is True
                    else (
                        "LLM did not confirm violation (keyword match only)."
                        if llm_verified
                        else "LLM verification unavailable."
                    )
                )
            ),
            details={
                "keyword_hits": keyword_hits,
                "llm_verification": llm_verified,
                "frameworks_checked": frameworks,
                "model": model or "unknown",
            },
        )

    @staticmethod
    def _llm_verify(response_body: str, keyword_hits: dict[str, list[str]]) -> dict[str, object]:
        """Send flagged content to LLM for compliance verification."""
        frameworks_str = ", ".join(keyword_hits.keys())
        keywords_str = "; ".join(f"{fw}: {', '.join(kws)}" for fw, kws in keyword_hits.items())

        prompt = (
            f"Check if this text violates {frameworks_str} regulations.\n"
            f"Flagged keywords: {keywords_str}\n\n"
            f"Text:\n{response_body[:3000]}"
        )

        raw = call_llm(
            system_prompt=_LLM_SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=512,
        )

        if not raw:
            return {}

        return parse_json_response(raw)

    def _pass(self, title: str) -> DetectionResult:
        return DetectionResult(
            detected=False,
            severity=IncidentSeverity.INFO.value,
            category=self.category,
            detector_id=None,
            action=DetectionAction.PASS,
            title=title,
        )
