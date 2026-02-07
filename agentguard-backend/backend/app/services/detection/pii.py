"""PII leak detector — regex-based detection of personal data in LLM responses."""

from __future__ import annotations

import re

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult

# Pattern name → (compiled regex, severity, description)
_PII_PATTERNS: list[tuple[str, re.Pattern[str], str, str]] = [
    (
        "SSN",
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        IncidentSeverity.CRITICAL.value,
        "Social Security Number detected",
    ),
    (
        "Credit Card",
        re.compile(r"\b(?:4\d{3}|5[1-5]\d{2}|3[47]\d{2}|6(?:011|5\d{2}))[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
        IncidentSeverity.CRITICAL.value,
        "Credit card number detected",
    ),
    (
        "Bank Account",
        re.compile(r"\b\d{8,17}\b(?=.*(?:account|routing|aba|iban))", re.IGNORECASE),
        IncidentSeverity.HIGH.value,
        "Bank account number detected",
    ),
    (
        "Phone",
        re.compile(r"\b(?:\+1[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b"),
        IncidentSeverity.MEDIUM.value,
        "Phone number detected",
    ),
    (
        "Email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        IncidentSeverity.MEDIUM.value,
        "Email address detected",
    ),
    (
        "DOB",
        re.compile(
            r"\b(?:(?:0[1-9]|1[0-2])[/\-](?:0[1-9]|[12]\d|3[01])[/\-](?:19|20)\d{2})\b"
        ),
        IncidentSeverity.HIGH.value,
        "Date of birth detected",
    ),
]

# Masking character
_MASK = "█"


def _mask_match(match: re.Match[str]) -> str:
    """Replace matched text with mask characters of same length."""
    return _MASK * len(match.group())


class PIIDetector:
    """Sync detector for PII leaks in LLM responses.

    Scans response body for common PII patterns (SSN, credit card, etc.).
    Supports redaction by returning a masked version of the response.
    """

    category: str = DetectorCategory.PII_LEAK.value

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
        severity_rank = {
            IncidentSeverity.INFO.value: 0,
            IncidentSeverity.LOW.value: 1,
            IncidentSeverity.MEDIUM.value: 2,
            IncidentSeverity.HIGH.value: 3,
            IncidentSeverity.CRITICAL.value: 4,
        }

        redacted = response_body

        for name, pattern, severity, description in _PII_PATTERNS:
            if name in disabled_patterns:
                continue

            matches = pattern.findall(response_body)
            if not matches:
                continue

            findings.append({
                "pattern": name,
                "count": str(len(matches)),
                "severity": severity,
                "description": description,
            })

            if severity_rank.get(severity, 0) > severity_rank.get(
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
                title="No PII detected",
            )

        return DetectionResult(
            detected=True,
            severity=highest_severity,
            category=self.category,
            detector_id=None,
            action=DetectionAction.MONITOR,
            title=f"PII detected: {', '.join(f['pattern'] for f in findings)}",
            description=f"Found {len(findings)} PII pattern type(s) in response",
            details={
                "findings": findings,
                "redacted_response": redacted,
            },
        )
