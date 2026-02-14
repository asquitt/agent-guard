"""Agent Capability Monitoring detector.

Tracks whether agents exhibit new or unexpected capabilities and alerts
when behavior crosses predefined thresholds. Detects unauthorized tool
usage patterns, persuasive language, autonomous planning, and financial
actions that fall outside the agent's allowed capability set.

Runs asynchronously via Celery after response delivery.
"""

from __future__ import annotations

import json
import logging
import re

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Capability categories and their detection patterns
# ---------------------------------------------------------------------------

_I = re.IGNORECASE

_CAPABILITY_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "code_execution": [
        re.compile(r'"type"\s*:\s*"(?:function_call|tool_use)"', _I),
        re.compile(r"```(?:python|javascript|bash|sh|shell|ruby|go)\b", _I),
        re.compile(r"\b(?:exec|eval)\s*\(|\bsubprocess\.", _I),
    ],
    "web_browsing": [
        re.compile(r"https?://[^\s\"',]+", _I),
        re.compile(r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+(?:/|https?://)", _I),
        re.compile(r"\b(?:fetch|requests\.get|urllib|curl|wget)\b", _I),
        re.compile(r"\b(?:browse|navigate|open_url|visit_page)\b", _I),
    ],
    "file_system": [
        re.compile(r"\b(?:read_file|write_file|open_file|save_file|create_file)\b", _I),
        re.compile(r"\b(?:os\.path|pathlib|shutil|glob)\b", _I),
        re.compile(r"\bwith\s+open\s*\(", _I),
        re.compile(r"\b(?:mkdir|rmdir|unlink|rename)\b", _I),
    ],
    "email_sending": [
        re.compile(r"\b(?:send_email|send_message|compose_email|mail_to)\b", _I),
        re.compile(r"\b(?:smtp|sendgrid|mailgun|ses\.send)\b", _I),
        re.compile(r"\bTo:\s*\S+@\S+", _I),
        re.compile(r"\b(?:reply_all|forward_email|draft_email)\b", _I),
    ],
    "financial_transaction": [
        re.compile(r"\b(?:transfer|wire|payment|payout|withdraw|deposit)\b", _I),
        re.compile(r"\b(?:buy|sell|trade|purchase|refund|charge|invoice)\b", _I),
        re.compile(r"\b(?:approve_transaction|submit_order|place_order)\b", _I),
    ],
    "data_modification": [
        re.compile(r"\b(?:INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM)\b", _I),
        re.compile(r"\b(?:CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE)\b", _I),
        re.compile(r"\b(?:db\.(?:insert|update|delete)|\.save\(\))\b", _I),
    ],
    "external_api": [
        re.compile(r"\bapi[_.](?:call|request|post|get|invoke)\b", _I),
        re.compile(r'"url"\s*:\s*"https?://', _I),
        re.compile(r"\b(?:webhook|callback|third_party|external_service)\b", _I),
    ],
    "persuasion": [
        re.compile(
            r"\b(?:you\s+should\s+definitely|I\s+strongly\s+recommend"
            r"|don'?t\s+miss\s+this\s+opportunity|act\s+now|limited\s+time"
            r"|guaranteed\s+returns|you\s+must\s+act|don'?t\s+hesitate"
            r"|trust\s+me\s+on\s+this|you\s+can'?t\s+afford\s+to"
            r"|this\s+is\s+a\s+once\s+in\s+a\s+lifetime)\b", _I,
        ),
    ],
    "autonomous_planning": [
        re.compile(r"\b(?:step\s+\d+|phase\s+\d+|first.*then.*finally)\b", _I),
        re.compile(
            r"\b(?:my\s+plan\s+is|I\s+will\s+proceed\s+to"
            r"|I'?ll\s+now\s+execute|executing\s+plan"
            r"|autonomous(?:ly)?|self[_-]directed"
            r"|without\s+(?:your\s+)?approval)\b", _I,
        ),
    ],
}

_UNAUTHORIZED_SEVERITY: dict[str, str] = {
    "financial_transaction": IncidentSeverity.CRITICAL.value,
    "data_modification": IncidentSeverity.HIGH.value,
    "file_system": IncidentSeverity.HIGH.value,
    "external_api": IncidentSeverity.HIGH.value,
    "email_sending": IncidentSeverity.HIGH.value,
    "code_execution": IncidentSeverity.MEDIUM.value,
    "web_browsing": IncidentSeverity.MEDIUM.value,
    "persuasion": IncidentSeverity.MEDIUM.value,
    "autonomous_planning": IncidentSeverity.MEDIUM.value,
}

_FINANCIAL_CONTEXT_RE = re.compile(
    r"\b(?:invest|portfolio|stock|bond|fund|loan|mortgage"
    r"|credit|debit|account|balance|rate|return|yield)\b", _I,
)

_SEVERITY_ORDER: list[str] = [
    IncidentSeverity.INFO.value, IncidentSeverity.LOW.value,
    IncidentSeverity.MEDIUM.value, IncidentSeverity.HIGH.value,
    IncidentSeverity.CRITICAL.value,
]
_SEVERITY_RANK: dict[str, int] = {s: i for i, s in enumerate(_SEVERITY_ORDER)}


def _max_severity(a: str, b: str) -> str:
    return b if _SEVERITY_RANK.get(b, 0) > _SEVERITY_RANK.get(a, 0) else a


def _detect_capabilities(text: str) -> dict[str, int]:
    """Scan text and return capability -> match count."""
    found: dict[str, int] = {}
    for capability, patterns in _CAPABILITY_PATTERNS.items():
        count = sum(len(p.findall(text)) for p in patterns)
        if count > 0:
            found[capability] = count
    return found


def _has_financial_context(text: str) -> bool:
    return bool(_FINANCIAL_CONTEXT_RE.search(text))


def _has_explicit_user_request(request_body: str) -> bool:
    """Check if user explicitly asked for planning in the request."""
    try:
        data = json.loads(request_body)
    except (json.JSONDecodeError, TypeError):
        return False
    if not isinstance(data, dict):
        return False
    for msg in data.get("messages", []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str) and re.search(
                r"\b(?:plan|steps|outline|strategy|how\s+would\s+you)\b",
                content, _I,
            ):
                return True
    return False


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


class CapabilityMonitorDetector:
    """Async detector for agent capability monitoring.

    Config options:
        allowed_capabilities: list[str] -- capabilities the agent may use
        capability_limits: dict[str, int] -- capability -> max count per request
        strict_mode: bool -- if True, any unrecognized capability triggers alert
    """

    category: str = DetectorCategory.CAPABILITY_MONITOR.value

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
        org_id: str,
        proxy_request_id: str,
    ) -> DetectionResult:
        allowed_raw = detector_config.get("allowed_capabilities")
        allowed: set[str] = (
            set(allowed_raw) if isinstance(allowed_raw, list) else set()
        )
        limits_raw = detector_config.get("capability_limits")
        limits: dict[str, int] = (
            {k: int(v) for k, v in limits_raw.items() if isinstance(v, (int, float))}
            if isinstance(limits_raw, dict)
            else {}
        )
        strict_mode = bool(detector_config.get("strict_mode", False))

        detected_caps = _detect_capabilities(response_body)
        if not detected_caps:
            return self._pass("No capabilities detected in response")

        findings: list[dict[str, object]] = []
        severity = IncidentSeverity.INFO.value
        financial_context = _has_financial_context(response_body)
        user_requested_plan = _has_explicit_user_request(request_body)

        for cap, count in detected_caps.items():
            # Unauthorized capability check
            if allowed and cap not in allowed:
                cap_sev = _UNAUTHORIZED_SEVERITY.get(cap, IncidentSeverity.MEDIUM.value)
                findings.append({
                    "capability": cap, "violation": "unauthorized",
                    "count": count, "severity": cap_sev,
                })
                severity = _max_severity(severity, cap_sev)
            elif strict_mode and not allowed:
                cap_sev = _UNAUTHORIZED_SEVERITY.get(cap, IncidentSeverity.MEDIUM.value)
                findings.append({
                    "capability": cap, "violation": "strict_mode_no_allowlist",
                    "count": count, "severity": cap_sev,
                })
                severity = _max_severity(severity, cap_sev)

            # Capability limit check
            if cap in limits and count > limits[cap]:
                findings.append({
                    "capability": cap, "violation": "limit_exceeded",
                    "count": count, "limit": limits[cap],
                    "severity": IncidentSeverity.MEDIUM.value,
                })
                severity = _max_severity(severity, IncidentSeverity.MEDIUM.value)

            # Persuasion in financial context -> escalate to HIGH
            if cap == "persuasion" and financial_context:
                findings.append({
                    "capability": cap, "violation": "persuasion_financial_context",
                    "count": count, "severity": IncidentSeverity.HIGH.value,
                })
                severity = _max_severity(severity, IncidentSeverity.HIGH.value)

            # Autonomous planning without explicit user request
            if cap == "autonomous_planning" and not user_requested_plan:
                if not (allowed and cap in allowed):
                    findings.append({
                        "capability": cap, "violation": "autonomous_without_request",
                        "count": count, "severity": IncidentSeverity.MEDIUM.value,
                    })
                    severity = _max_severity(severity, IncidentSeverity.MEDIUM.value)

        if not findings:
            return self._pass("All capabilities within allowed scope")

        cap_names = list({str(f["capability"]) for f in findings})
        return DetectionResult(
            detected=True,
            severity=severity,
            category=self.category,
            detector_id=None,
            action=DetectionAction.MONITOR,
            title=f"Capability violation: {', '.join(cap_names[:3])}",
            description=f"{len(findings)} capability issue(s) detected",
            details={
                "findings": findings,
                "detected_capabilities": detected_caps,
                "allowed_capabilities": sorted(allowed),
                "model": model or "unknown",
                "org_id": org_id,
                "proxy_request_id": proxy_request_id,
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
