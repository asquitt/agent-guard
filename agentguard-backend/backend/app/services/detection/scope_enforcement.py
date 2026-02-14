"""Scope enforcement detector.

Tracks when agents perform actions outside their allowed scope:
- Unauthorized tool usage (not in allowed list, or in blocked list)
- HTTP requests to unauthorized/blocked domains
- Irreversible actions (deletes, financial transfers, permission changes)
- Resource limit violations (token count, tool call count)

Runs synchronously -- can BLOCK unauthorized actions before execution.
"""

from __future__ import annotations

import json
import logging
import re

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult

logger = logging.getLogger(__name__)

# Severity ranking helpers
_SEVERITY_ORDER: list[str] = [
    IncidentSeverity.INFO.value,
    IncidentSeverity.LOW.value,
    IncidentSeverity.MEDIUM.value,
    IncidentSeverity.HIGH.value,
    IncidentSeverity.CRITICAL.value,
]
_SEVERITY_RANK: dict[str, int] = {s: i for i, s in enumerate(_SEVERITY_ORDER)}


def _max_severity(a: str, b: str) -> str:
    return a if _SEVERITY_RANK.get(a, 0) >= _SEVERITY_RANK.get(b, 0) else b


# Irreversible action patterns matched against response body
_IRREVERSIBLE_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"\bDELETE\b.*\b(?:account|user|record|database|table)\b", re.IGNORECASE),
        "DELETE on critical resource",
        IncidentSeverity.HIGH.value,
    ),
    (
        re.compile(r"\b(?:transfer|wire|payment|payout|withdraw)\b", re.IGNORECASE),
        "Financial transaction detected",
        IncidentSeverity.CRITICAL.value,
    ),
    (
        re.compile(
            r"\b(?:change_password|reset_password|modify_permissions|grant_access|revoke_access)\b",
            re.IGNORECASE,
        ),
        "Account/permission modification",
        IncidentSeverity.HIGH.value,
    ),
    (
        re.compile(r"\b(?:send_email|send_message|send_sms|post_message)\b", re.IGNORECASE),
        "Outbound message sending",
        IncidentSeverity.MEDIUM.value,
    ),
    (
        re.compile(r"\b(?:rm\s+-rf|unlink|overwrite|truncate)\b", re.IGNORECASE),
        "File system destructive operation",
        IncidentSeverity.MEDIUM.value,
    ),
]

_URL_DOMAIN_RE = re.compile(r"https?://([^/:?\s]+)", re.IGNORECASE)


def _extract_domains_from_args(args: dict[str, object]) -> list[str]:
    """Pull domain names from URL-like values in tool call arguments."""
    domains: list[str] = []
    for val in args.values():
        if isinstance(val, str):
            for m in _URL_DOMAIN_RE.finditer(val):
                domains.append(m.group(1).lower())
    return domains


def _extract_tool_calls(body: str) -> list[dict[str, object]]:
    """Extract tool/function calls from request or response JSON."""
    calls: list[dict[str, object]] = []
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return calls
    if not isinstance(data, dict):
        return calls

    # OpenAI response choices
    for choice in data.get("choices", []):
        msg = choice.get("message", {}) if isinstance(choice, dict) else {}
        for tc in msg.get("tool_calls", []) if isinstance(msg, dict) else []:
            if isinstance(tc, dict):
                calls.append(tc)

    # OpenAI request messages
    for msg in data.get("messages", []):
        if isinstance(msg, dict):
            for tc in msg.get("tool_calls", []):
                if isinstance(tc, dict):
                    calls.append(tc)

    # Top-level tool_calls
    for tc in data.get("tool_calls", []):
        if isinstance(tc, dict):
            calls.append(tc)

    # Anthropic content blocks
    for item in data.get("content", []):
        if isinstance(item, dict) and item.get("type") == "tool_use":
            calls.append({
                "type": "function",
                "function": {
                    "name": item.get("name", ""),
                    "arguments": json.dumps(item.get("input", {})),
                },
            })
    return calls


def _get_function_name(tc: dict[str, object]) -> str:
    fn = tc.get("function")
    if isinstance(fn, dict):
        name = fn.get("name")
        return str(name) if name else ""
    return str(tc.get("name", ""))


def _get_function_args(tc: dict[str, object]) -> dict[str, object]:
    fn = tc.get("function")
    if isinstance(fn, dict):
        raw = fn.get("arguments", "{}")
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
            except (json.JSONDecodeError, TypeError):
                return {}
        if isinstance(raw, dict):
            return raw
    inp = tc.get("input")
    return inp if isinstance(inp, dict) else {}


def _extract_token_count(body: str) -> int | None:
    """Extract completion token count from response body."""
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    usage = data.get("usage")
    if isinstance(usage, dict):
        ct = usage.get("completion_tokens")
        if isinstance(ct, int):
            return ct
    return None


class ScopeEnforcementDetector:
    """Sync detector for agent scope enforcement.

    Config: allowed_tools, blocked_tools, allowed_domains, blocked_domains,
    max_tokens_per_request, max_tool_calls_per_request (all optional).
    """

    category: str = DetectorCategory.SCOPE_ENFORCEMENT.value

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
    ) -> DetectionResult:
        req_calls = _extract_tool_calls(request_body)
        resp_calls = _extract_tool_calls(response_body)
        all_calls = req_calls + resp_calls

        findings: list[str] = []
        severity = IncidentSeverity.INFO.value

        allowed_tools = detector_config.get("allowed_tools")
        blocked_tools = detector_config.get("blocked_tools")
        allowed_domains = detector_config.get("allowed_domains")
        blocked_domains = detector_config.get("blocked_domains")

        # Tool scope checks
        for tc in all_calls:
            name = _get_function_name(tc)
            args = _get_function_args(tc)

            if name and isinstance(blocked_tools, list) and name in blocked_tools:
                findings.append(f"Blocked tool invoked: {name}")
                severity = _max_severity(severity, IncidentSeverity.CRITICAL.value)
            elif name and isinstance(allowed_tools, list) and allowed_tools:
                if name not in allowed_tools:
                    findings.append(f"Unauthorized tool: {name}")
                    severity = _max_severity(severity, IncidentSeverity.HIGH.value)

            # Domain checks on tool arguments
            domains = _extract_domains_from_args(args)
            for domain in domains:
                if isinstance(blocked_domains, list) and domain in blocked_domains:
                    findings.append(f"Blocked domain: {domain}")
                    severity = _max_severity(severity, IncidentSeverity.CRITICAL.value)
                elif isinstance(allowed_domains, list) and allowed_domains:
                    if domain not in allowed_domains:
                        findings.append(f"Unauthorized domain: {domain}")
                        severity = _max_severity(severity, IncidentSeverity.HIGH.value)

        # Resource limit: tool call count
        max_calls = detector_config.get("max_tool_calls_per_request")
        if isinstance(max_calls, int) and len(all_calls) > max_calls:
            findings.append(f"{len(all_calls)} tool calls exceeds limit of {max_calls}")
            severity = _max_severity(severity, IncidentSeverity.MEDIUM.value)

        # Resource limit: token count
        max_tokens = detector_config.get("max_tokens_per_request")
        token_count = _extract_token_count(response_body)
        if isinstance(max_tokens, int) and isinstance(token_count, int):
            if token_count > max_tokens:
                findings.append(
                    f"Completion tokens {token_count} exceeds limit of {max_tokens}"
                )
                severity = _max_severity(severity, IncidentSeverity.MEDIUM.value)

        # Irreversible action patterns in response
        for pattern, desc, pat_sev in _IRREVERSIBLE_PATTERNS:
            if pattern.search(response_body):
                findings.append(desc)
                severity = _max_severity(severity, pat_sev)

        if not findings:
            return DetectionResult(
                detected=False,
                severity=IncidentSeverity.INFO.value,
                category=self.category,
                detector_id=None,
                action=DetectionAction.PASS,
                title="Agent actions within allowed scope",
            )

        return DetectionResult(
            detected=True,
            severity=severity,
            category=self.category,
            detector_id=None,
            action=DetectionAction.MONITOR,
            title=f"Scope violation: {len(findings)} issue(s)",
            description="; ".join(findings[:5]),
            details={
                "findings": findings,
                "total_tool_calls": len(all_calls),
                "model": model or "unknown",
            },
        )
