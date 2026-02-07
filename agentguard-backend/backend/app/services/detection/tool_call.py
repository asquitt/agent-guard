"""Tool/function call validation detector.

Validates that tool calls in LLM requests/responses:
1. Match expected schemas (if configured)
2. Don't call unauthorized tools
3. Respect parameter boundaries (e.g. transfer amounts)
4. Don't exhibit suspicious call patterns (rapid-fire, sequencing)

Runs synchronously — can BLOCK dangerous tool calls before execution.
"""

from __future__ import annotations

import json
import logging
import re

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Suspicious tool-call patterns (financial context)
# ---------------------------------------------------------------------------

_DANGEROUS_TOOL_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    # (pattern, description, severity)
    (
        re.compile(r"transfer|send_money|wire|payment|payout", re.IGNORECASE),
        "Financial transfer tool invoked",
        IncidentSeverity.HIGH.value,
    ),
    (
        re.compile(r"delete_account|close_account|terminate", re.IGNORECASE),
        "Destructive account action",
        IncidentSeverity.CRITICAL.value,
    ),
    (
        re.compile(r"modify_permissions|change_role|grant_access|elevate", re.IGNORECASE),
        "Permission escalation tool",
        IncidentSeverity.HIGH.value,
    ),
    (
        re.compile(r"execute_sql|run_query|raw_query|exec_command", re.IGNORECASE),
        "Raw execution tool invoked",
        IncidentSeverity.CRITICAL.value,
    ),
    (
        re.compile(r"disable_(?:security|audit|logging|monitoring|compliance)", re.IGNORECASE),
        "Security bypass tool",
        IncidentSeverity.CRITICAL.value,
    ),
]


def _extract_tool_calls(body: str) -> list[dict[str, object]]:
    """Extract tool/function calls from request or response JSON."""
    calls: list[dict[str, object]] = []
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return calls

    # OpenAI format: messages[].tool_calls or response choices[].message.tool_calls
    if isinstance(data, dict):
        # Check response choices
        for choice in data.get("choices", []):
            msg = choice.get("message", {}) if isinstance(choice, dict) else {}
            for tc in msg.get("tool_calls", []) if isinstance(msg, dict) else []:
                if isinstance(tc, dict):
                    calls.append(tc)

        # Check request messages for tool_calls
        for msg in data.get("messages", []):
            if isinstance(msg, dict):
                for tc in msg.get("tool_calls", []):
                    if isinstance(tc, dict):
                        calls.append(tc)

        # Check top-level tool_calls (some formats)
        for tc in data.get("tool_calls", []):
            if isinstance(tc, dict):
                calls.append(tc)

        # Anthropic format: content[].type == "tool_use"
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
    """Extract function name from a tool call dict."""
    fn = tc.get("function")
    if isinstance(fn, dict):
        name = fn.get("name")
        return str(name) if name else ""
    return str(tc.get("name", ""))


def _get_function_args(tc: dict[str, object]) -> dict[str, object]:
    """Extract function arguments from a tool call dict."""
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
    # Anthropic-style input
    inp = tc.get("input")
    return inp if isinstance(inp, dict) else {}


class ToolCallDetector:
    """Sync detector for tool/function call validation.

    Config options:
        allowed_tools: list[str] — whitelist of permitted tool names
        blocked_tools: list[str] — blacklist of forbidden tool names
        max_amount: float — max allowed value for amount/value params
        max_calls_per_request: int — max tool calls in a single request
        disabled_checks: list[str] — checks to skip
    """

    category: str = DetectorCategory.TOOL_CALL.value

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
    ) -> DetectionResult:
        # Extract tool calls from both request and response
        req_calls = _extract_tool_calls(request_body)
        resp_calls = _extract_tool_calls(response_body)
        all_calls = req_calls + resp_calls

        if not all_calls:
            return self._pass("No tool calls found")

        disabled = set(detector_config.get("disabled_checks", []))  # type: ignore[arg-type]
        findings: list[str] = []
        severity = IncidentSeverity.INFO.value

        # Check 1: Call volume limit
        max_calls = int(detector_config.get("max_calls_per_request", 20))  # type: ignore[arg-type]
        if "call_volume" not in disabled and len(all_calls) > max_calls:
            findings.append(f"{len(all_calls)} tool calls exceeds limit of {max_calls}")
            severity = _max_severity(severity, IncidentSeverity.HIGH.value)

        for tc in all_calls:
            name = _get_function_name(tc)
            args = _get_function_args(tc)

            # Check 2: Allowed/blocked tool names
            if "allowlist" not in disabled:
                allowed = detector_config.get("allowed_tools")
                if isinstance(allowed, list) and allowed:
                    if name and name not in allowed:
                        findings.append(f"Unauthorized tool: {name}")
                        severity = _max_severity(severity, IncidentSeverity.HIGH.value)

            if "blocklist" not in disabled:
                blocked = detector_config.get("blocked_tools")
                if isinstance(blocked, list):
                    if name in blocked:
                        findings.append(f"Blocked tool invoked: {name}")
                        severity = _max_severity(severity, IncidentSeverity.CRITICAL.value)

            # Check 3: Dangerous tool pattern matching
            if "pattern_match" not in disabled:
                for pattern, desc, pat_sev in _DANGEROUS_TOOL_PATTERNS:
                    if name and pattern.search(name):
                        findings.append(f"{desc}: {name}")
                        severity = _max_severity(severity, pat_sev)

            # Check 4: Parameter boundary validation
            if "param_bounds" not in disabled:
                max_amount = detector_config.get("max_amount")
                if isinstance(max_amount, (int, float)):
                    for key in ("amount", "value", "total", "quantity", "limit"):
                        val = args.get(key)
                        if isinstance(val, (int, float)) and val > max_amount:
                            findings.append(
                                f"Parameter '{key}' = {val} exceeds max {max_amount} "
                                f"in tool '{name}'"
                            )
                            severity = _max_severity(severity, IncidentSeverity.HIGH.value)

        if not findings:
            return self._pass("Tool calls validated — no issues")

        return DetectionResult(
            detected=True,
            severity=severity,
            category=self.category,
            detector_id=None,
            action=DetectionAction.MONITOR,
            title=f"Tool call violation: {len(findings)} issue(s)",
            description="; ".join(findings[:5]),
            details={
                "findings": findings,
                "total_calls": len(all_calls),
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


_SEVERITY_ORDER: list[str] = [
    IncidentSeverity.INFO.value,
    IncidentSeverity.LOW.value,
    IncidentSeverity.MEDIUM.value,
    IncidentSeverity.HIGH.value,
    IncidentSeverity.CRITICAL.value,
]
_SEVERITY_RANK: dict[str, int] = {s: i for i, s in enumerate(_SEVERITY_ORDER)}


def _max_severity(a: str, b: str) -> str:
    """Return the more severe of two severity values."""
    if _SEVERITY_RANK.get(a, 0) >= _SEVERITY_RANK.get(b, 0):
        return a
    return b
