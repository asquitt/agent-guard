"""Compliance detector — rule-based keyword matching + LLM verification.

Maps keywords to specific regulatory requirements across 6 frameworks:
SOX, PCI-DSS, FFIEC, NYDFS-500, DORA, EU-AI-ACT.
"""

from __future__ import annotations

import logging
import re

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult
from app.services.llm_service import call_llm, parse_json_response

logger = logging.getLogger(__name__)

# Requirement-level keyword mapping: framework → requirement → keywords
_FRAMEWORK_REQUIREMENTS: dict[str, dict[str, list[str]]] = {
    "SOX": {
        "Section 302 - CEO/CFO Certifications": [
            "financial statement",
            "management assessment",
        ],
        "Section 404 - Internal Controls": [
            "internal controls",
            "material weakness",
        ],
        "Section 409 - Real-Time Disclosure": [
            "disclosure controls",
            "restatement",
            "audit opinion",
        ],
    },
    "PCI-DSS": {
        "Req 3.2 - Do not store sensitive auth data": [
            "cvv",
            "card verification",
            "magnetic stripe",
        ],
        "Req 3.4 - Render PAN unreadable": [
            "primary account number",
            "pan data",
        ],
        "Req 4.1 - Encrypt cardholder data": [
            "cardholder",
            "payment card",
        ],
    },
    "FFIEC": {
        "Fair Lending - Equal Credit": [
            "fair lending",
            "redlining",
            "disparate impact",
        ],
        "BSA/AML - Anti-Money Laundering": [
            "bank secrecy",
            "anti-money laundering",
        ],
        "CRA - Community Reinvestment": [
            "community reinvestment",
            "risk disclosure",
        ],
    },
    "NYDFS-500": {
        "Section 500.2 - Cybersecurity Program": [
            "cybersecurity program",
            "cybersecurity policy",
        ],
        "Section 500.7 - Access Privileges": [
            "access privilege",
            "least privilege",
            "access control",
        ],
        "Section 500.14 - Training & Monitoring": [
            "security training",
            "security awareness",
        ],
    },
    "DORA": {
        "Article 5-6 - ICT Risk Management": [
            "ict risk",
            "operational resilience",
        ],
        "Article 9 - Protection & Prevention": [
            "data protection",
            "encryption standard",
        ],
        "Article 15 - ICT Testing": [
            "penetration test",
            "vulnerability assessment",
        ],
    },
    "EU-AI-ACT": {
        "Article 9 - Risk Management": [
            "ai risk assessment",
            "risk management system",
        ],
        "Article 13 - Transparency": [
            "ai transparency",
            "explainability",
            "interpretability",
        ],
        "Article 14 - Human Oversight": [
            "human oversight",
            "human-in-the-loop",
            "human review",
        ],
    },
}

# Pre-compiled patterns: framework → requirement → compiled patterns
_REQUIREMENT_PATTERNS: dict[str, dict[str, list[re.Pattern[str]]]] = {
    fw: {
        req: [re.compile(re.escape(kw), re.IGNORECASE) for kw in keywords]
        for req, keywords in reqs.items()
    }
    for fw, reqs in _FRAMEWORK_REQUIREMENTS.items()
}

_ALL_FRAMEWORKS = list(_FRAMEWORK_REQUIREMENTS.keys())

_LLM_SYSTEM_PROMPT = """\
You are a financial regulatory compliance analyst. Analyze the given text for
potential regulatory violations.

Respond with ONLY valid JSON (no markdown fences):
{
  "violation": <true|false>,
  "framework": "<which regulation>",
  "explanation": "<brief explanation of the violation or why it's compliant>"
}
"""


def _get_enabled_frameworks(detector_config: dict[str, object]) -> list[str]:
    """Get list of enabled regulatory frameworks from config."""
    raw = detector_config.get("frameworks")
    if isinstance(raw, list):
        valid = [str(f) for f in raw if str(f) in _FRAMEWORK_REQUIREMENTS]
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

        # Pass 1: requirement-level keyword matching
        keyword_hits: dict[str, list[str]] = {}
        violated_requirements: list[str] = []

        for framework in frameworks:
            req_patterns = _REQUIREMENT_PATTERNS.get(framework, {})
            fw_keywords: list[str] = []
            for req_name, patterns in req_patterns.items():
                matched = [
                    p.pattern.replace("\\", "")
                    for p in patterns
                    if p.search(response_lower)
                ]
                if matched:
                    fw_keywords.extend(matched)
                    violated_requirements.append(f"{framework} {req_name}")
            if fw_keywords:
                keyword_hits[framework] = fw_keywords

        if not keyword_hits:
            return self._pass("No regulatory keywords detected")

        # Pass 2: LLM verification (best-effort)
        llm_verified = self._llm_verify(response_body, keyword_hits)

        # Build title from requirements
        req_summary = ", ".join(violated_requirements[:4])
        if len(violated_requirements) > 4:
            req_summary += f" (+{len(violated_requirements) - 4} more)"
        title = f"Compliance: {req_summary}"

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
            title=title,
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
                "violated_requirements": violated_requirements,
                "llm_verification": llm_verified,
                "frameworks_checked": frameworks,
                "model": model or "unknown",
            },
        )

    @staticmethod
    def _llm_verify(
        response_body: str, keyword_hits: dict[str, list[str]]
    ) -> dict[str, object]:
        """Send flagged content to LLM for compliance verification."""
        frameworks_str = ", ".join(keyword_hits.keys())
        keywords_str = "; ".join(
            f"{fw}: {', '.join(kws)}" for fw, kws in keyword_hits.items()
        )

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
