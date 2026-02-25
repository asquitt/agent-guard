"""Financial-services PII detector — extends generic PII with finance-specific patterns.

Catches routing numbers, SWIFT/BIC, IBAN, CVV, trade confirmations, wire transfer
details, security identifiers (CUSIP/SEDOL/ISIN), and MNPI indicators that generic
PII detectors miss.
"""

from __future__ import annotations

import re

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult

# Masking character
_MASK = "\u2588"


def _mask_match(match: re.Match[str]) -> str:
    """Replace matched text with mask characters of same length."""
    return _MASK * len(match.group())


# Context-aware patterns: (name, pattern, context_pattern | None, severity, description)
# When context_pattern is set, the main pattern only fires if context appears nearby.
_FINANCIAL_PATTERNS: list[
    tuple[str, re.Pattern[str], re.Pattern[str] | None, str, str]
] = [
    (
        "Credit Card",
        re.compile(
            r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6(?:011|5\d{2}))"
            r"[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"
        ),
        None,
        IncidentSeverity.CRITICAL.value,
        "Credit card number detected",
    ),
    (
        "Routing Number",
        re.compile(r"\b[0-9]{9}\b"),
        re.compile(r"routing|aba|transit", re.IGNORECASE),
        IncidentSeverity.HIGH.value,
        "ABA routing number detected",
    ),
    (
        "SWIFT/BIC",
        re.compile(r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b"),
        None,
        IncidentSeverity.HIGH.value,
        "SWIFT/BIC code detected",
    ),
    (
        "IBAN",
        re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{4,30}\b"),
        None,
        IncidentSeverity.HIGH.value,
        "IBAN detected",
    ),
    (
        "CVV/CVC",
        re.compile(r"\b\d{3,4}\b"),
        re.compile(r"cvv|cvc|security\s+code|card\s+verification", re.IGNORECASE),
        IncidentSeverity.CRITICAL.value,
        "CVV/CVC security code detected",
    ),
    (
        "Account Number",
        re.compile(r"\b\d{8,17}\b"),
        re.compile(r"account\s*(number|no|#|num)?", re.IGNORECASE),
        IncidentSeverity.HIGH.value,
        "Financial account number detected",
    ),
    (
        "Trade Confirmation",
        re.compile(
            r"\b(?:BOUGHT|SOLD|BUY|SELL)\s+\d[\d,]*\s+shares?\s+(?:of\s+)?\w+\s+at\s+\$[\d,.]+",
            re.IGNORECASE,
        ),
        None,
        IncidentSeverity.MEDIUM.value,
        "Trade confirmation details detected",
    ),
    (
        "Portfolio Position",
        re.compile(
            r"\b(?:holds?|holding|position)\s+\d[\d,]*\s+(?:shares?|units?)\s+(?:of\s+)?\w+",
            re.IGNORECASE,
        ),
        None,
        IncidentSeverity.MEDIUM.value,
        "Portfolio position data detected",
    ),
    (
        "Wire Transfer",
        re.compile(
            r"\b(?:wire\s+(?:ref(?:erence)?|transfer)|beneficiary\s+(?:name|account|bank))\s*[:#]?\s*\S+",
            re.IGNORECASE,
        ),
        None,
        IncidentSeverity.CRITICAL.value,
        "Wire transfer details detected",
    ),
    (
        "Tax ID / EIN",
        re.compile(r"\b\d{2}-\d{7}\b"),
        None,
        IncidentSeverity.HIGH.value,
        "Employer Identification Number (EIN) detected",
    ),
    (
        "CUSIP",
        re.compile(r"\b[A-Z0-9]{9}\b"),
        re.compile(r"cusip", re.IGNORECASE),
        IncidentSeverity.MEDIUM.value,
        "CUSIP identifier detected",
    ),
    (
        "SEDOL",
        re.compile(r"\b[A-Z0-9]{7}\b"),
        re.compile(r"sedol", re.IGNORECASE),
        IncidentSeverity.MEDIUM.value,
        "SEDOL identifier detected",
    ),
    (
        "ISIN",
        re.compile(r"\b[A-Z]{2}[A-Z0-9]{10}\b"),
        None,
        IncidentSeverity.MEDIUM.value,
        "ISIN identifier detected",
    ),
    (
        "Loan Number",
        re.compile(r"\b\d{10,20}\b"),
        re.compile(r"loan\s*(number|no|#|num|id)?", re.IGNORECASE),
        IncidentSeverity.MEDIUM.value,
        "Loan number detected",
    ),
    (
        "Policy Number",
        re.compile(r"\b[A-Z]{2,4}\d{6,12}\b"),
        re.compile(r"policy\s*(number|no|#|num)?", re.IGNORECASE),
        IncidentSeverity.MEDIUM.value,
        "Insurance policy number detected",
    ),
    (
        "MNPI Indicator",
        re.compile(
            r"(?:not\s+yet\s+announced|before\s+the\s+public\s+release|"
            r"confidential\s+earnings|material\s+non[- ]public|"
            r"insider\s+information|pre[- ]announcement|embargoed)",
            re.IGNORECASE,
        ),
        None,
        IncidentSeverity.CRITICAL.value,
        "Material Non-Public Information (MNPI) indicator detected",
    ),
]

_SEVERITY_RANK: dict[str, int] = {
    IncidentSeverity.INFO.value: 0,
    IncidentSeverity.LOW.value: 1,
    IncidentSeverity.MEDIUM.value: 2,
    IncidentSeverity.HIGH.value: 3,
    IncidentSeverity.CRITICAL.value: 4,
}


class FinancialPIIDetector:
    """Sync detector for financial-services PII in LLM responses.

    Extends generic PII detection with finance-specific patterns: routing
    numbers, SWIFT/BIC, IBAN, CVV, trade data, wire transfers, security
    identifiers, and MNPI indicators. Supports redaction.
    """

    category: str = "financial_pii"

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
    ) -> DetectionResult:
        disabled_patterns: list[str] = []
        raw = detector_config.get("disabled_patterns")
        if isinstance(raw, list):
            disabled_patterns = [str(p) for p in raw]

        findings: list[dict[str, str]] = []
        highest_severity = IncidentSeverity.INFO.value
        redacted = response_body

        for name, pattern, context_pattern, severity, description in _FINANCIAL_PATTERNS:
            if name in disabled_patterns:
                continue

            # Context-gated patterns require a context keyword in the response
            if context_pattern is not None and not context_pattern.search(response_body):
                continue

            matches = pattern.findall(response_body)
            if not matches:
                continue

            findings.append(
                {
                    "pattern": name,
                    "count": str(len(matches)),
                    "severity": severity,
                    "description": description,
                }
            )

            if _SEVERITY_RANK.get(severity, 0) > _SEVERITY_RANK.get(
                highest_severity, 0
            ):
                highest_severity = severity

            redacted = pattern.sub(_mask_match, redacted)

        if not findings:
            return DetectionResult(
                detected=False,
                severity=IncidentSeverity.INFO.value,
                category=self.category,
                detector_id=None,
                action=DetectionAction.PASS,
                title="No financial PII detected",
            )

        return DetectionResult(
            detected=True,
            severity=highest_severity,
            category=self.category,
            detector_id=None,
            action=DetectionAction.MONITOR,
            title=f"Financial PII detected: {', '.join(f['pattern'] for f in findings)}",
            description=f"Found {len(findings)} financial PII pattern type(s) in response",
            details={
                "findings": findings,
                "redacted_response": redacted,
            },
        )
