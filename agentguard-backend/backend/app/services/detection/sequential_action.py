"""Sequential Action Analyzer — detects suspicious multi-step tool call patterns.

Runs asynchronously via Celery after response delivery.
"""

from __future__ import annotations

import json
import logging
import re

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult

logger = logging.getLogger(__name__)

_DEFAULT_WINDOW_SIZE = 10

# Tool call category classification patterns
_CATEGORY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("READ", re.compile(
        r"read|get|fetch|list|query|search|lookup|describe|show|view|retrieve|load|select",
        re.IGNORECASE,
    )),
    ("WRITE", re.compile(
        r"write|create|insert|add|put|set|update|modify|change|patch|alter",
        re.IGNORECASE,
    )),
    ("DELETE", re.compile(
        r"delete|remove|drop|clear|purge|truncate|destroy|wipe|erase",
        re.IGNORECASE,
    )),
    ("SEND", re.compile(
        r"send|email|post|publish|forward|transmit|notify|broadcast|dispatch|http_request",
        re.IGNORECASE,
    )),
    ("MODIFY_ACCESS", re.compile(
        r"permission|role|access|grant|revoke|elevate|escalate|privilege|authorize|admin",
        re.IGNORECASE,
    )),
    ("FINANCIAL", re.compile(
        r"transfer|payment|transaction|withdraw|deposit|wire|payout|refund|charge|invoice",
        re.IGNORECASE,
    )),
]

# Suspicious sequence definitions: (name, category_sequences, severity, description)
_PATTERNS: list[tuple[str, list[list[str]], str, str]] = [
    (
        "data_exfiltration",
        [["READ", "SEND"], ["READ", "WRITE", "SEND"], ["READ", "READ", "SEND"]],
        IncidentSeverity.CRITICAL.value,
        "Data read then sent externally — potential exfiltration",
    ),
    (
        "privilege_escalation",
        [["READ", "MODIFY_ACCESS", "WRITE"], ["READ", "MODIFY_ACCESS", "DELETE"]],
        IncidentSeverity.CRITICAL.value,
        "Permissions queried then modified before privileged action",
    ),
    (
        "reconnaissance",
        [["READ", "READ", "READ", "READ"]],
        IncidentSeverity.HIGH.value,
        "Multiple sequential data reads without user-facing output",
    ),
    (
        "financial_manipulation",
        [["READ", "FINANCIAL", "DELETE"], ["FINANCIAL", "DELETE"],
         ["READ", "FINANCIAL", "WRITE", "DELETE"]],
        IncidentSeverity.CRITICAL.value,
        "Financial action followed by audit trail deletion",
    ),
    (
        "unauthorized_communication",
        [["READ", "WRITE", "SEND"], ["READ", "SEND"]],
        IncidentSeverity.HIGH.value,
        "Sensitive data read then communicated externally",
    ),
]


def _classify_tool(name: str) -> str:
    """Classify a tool name into an action category."""
    for category, pattern in _CATEGORY_PATTERNS:
        if pattern.search(name):
            return category
    return "OTHER"


def _extract_tool_calls(body: str) -> list[tuple[str, str]]:
    """Extract (tool_name, args_summary) pairs from request/response JSON."""
    calls: list[tuple[str, str]] = []
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return calls
    if not isinstance(data, dict):
        return calls

    # OpenAI format: messages[].tool_calls, choices[].message.tool_calls
    for msg in data.get("messages", []):
        if isinstance(msg, dict):
            for tc in msg.get("tool_calls", []):
                if isinstance(tc, dict):
                    calls.append(_parse_tool_call(tc))
    for choice in data.get("choices", []):
        msg = choice.get("message", {}) if isinstance(choice, dict) else {}
        for tc in (msg.get("tool_calls", []) if isinstance(msg, dict) else []):
            if isinstance(tc, dict):
                calls.append(_parse_tool_call(tc))

    # Anthropic format: content[].type == "tool_use"
    for item in data.get("content", []):
        if isinstance(item, dict) and item.get("type") == "tool_use":
            calls.append((str(item.get("name", "")), _summarize_args(item.get("input", {}))))
    return calls


def _parse_tool_call(tc: dict[str, object]) -> tuple[str, str]:
    """Parse a single OpenAI-format tool call into (name, args_summary)."""
    fn = tc.get("function")
    if isinstance(fn, dict):
        name = str(fn.get("name", ""))
        raw_args = fn.get("arguments", "{}")
        if isinstance(raw_args, str):
            try:
                return (name, _summarize_args(json.loads(raw_args)))
            except (json.JSONDecodeError, TypeError):
                return (name, raw_args[:80])
        return (name, _summarize_args(raw_args))
    return (str(tc.get("name", "")), _summarize_args(tc.get("input", {})))


def _summarize_args(args: object) -> str:
    """Create a short summary of tool arguments."""
    if isinstance(args, dict):
        keys = list(args.keys())[:5]
        return ",".join(keys) if keys else ""
    return str(args)[:80] if args else ""


def _find_pattern_match(categories: list[str], pattern_seq: list[str]) -> int | None:
    """Sliding window check: does pattern_seq appear as a contiguous subsequence?"""
    if len(pattern_seq) > len(categories):
        return None
    for i in range(len(categories) - len(pattern_seq) + 1):
        if categories[i : i + len(pattern_seq)] == pattern_seq:
            return i
    return None


_SEVERITY_ORDER: list[str] = [
    IncidentSeverity.INFO.value, IncidentSeverity.LOW.value,
    IncidentSeverity.MEDIUM.value, IncidentSeverity.HIGH.value,
    IncidentSeverity.CRITICAL.value,
]
_SEVERITY_RANK: dict[str, int] = {s: i for i, s in enumerate(_SEVERITY_ORDER)}


def _max_severity(a: str, b: str) -> str:
    """Return the more severe of two severity values."""
    return b if _SEVERITY_RANK.get(b, 0) > _SEVERITY_RANK.get(a, 0) else a


class SequentialActionDetector:
    """Async detector for suspicious multi-step tool call sequences.

    Config options:
        window_size: int — number of recent tool calls to analyze (default 10)
        disabled_patterns: list[str] — pattern names to skip
        recent_tool_calls: list[dict] — previous calls: {"name": str, "args": str}
    """

    category: str = DetectorCategory.SEQUENTIAL_ACTION.value

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
        org_id: str,
        proxy_request_id: str,
    ) -> DetectionResult:
        raw_window = detector_config.get("window_size")
        window_size = int(str(raw_window)) if raw_window is not None else _DEFAULT_WINDOW_SIZE

        disabled_raw = detector_config.get("disabled_patterns")
        disabled: set[str] = set(disabled_raw) if isinstance(disabled_raw, list) else set()

        # Build tool call list: previous calls + current request/response
        tool_calls: list[tuple[str, str]] = []
        recent_raw = detector_config.get("recent_tool_calls")
        if isinstance(recent_raw, list):
            for entry in recent_raw:
                if isinstance(entry, dict):
                    name = str(entry.get("name", ""))
                    args = str(entry.get("args", ""))
                    if name:
                        tool_calls.append((name, args))

        tool_calls.extend(_extract_tool_calls(request_body))
        tool_calls.extend(_extract_tool_calls(response_body))
        tool_calls = tool_calls[-window_size:]

        if len(tool_calls) < 2:
            return self._pass("Insufficient tool calls for sequence analysis")

        # Classify each tool call and check patterns
        categories = [_classify_tool(name) for name, _ in tool_calls]
        findings: list[dict[str, object]] = []
        max_sev = IncidentSeverity.INFO.value

        for pattern_name, sequences, severity, description in _PATTERNS:
            if pattern_name in disabled:
                continue
            for seq in sequences:
                match_idx = _find_pattern_match(categories, seq)
                if match_idx is not None:
                    matched_tools = tool_calls[match_idx : match_idx + len(seq)]
                    findings.append({
                        "pattern": pattern_name,
                        "severity": severity,
                        "description": description,
                        "sequence": [
                            {"tool": name, "category": cat}
                            for (name, _), cat in zip(matched_tools, seq)
                        ],
                    })
                    max_sev = _max_severity(max_sev, severity)
                    break  # one match per pattern is enough

        if not findings:
            return self._pass("No suspicious sequences detected")

        titles = [str(f["pattern"]) for f in findings]
        return DetectionResult(
            detected=True,
            severity=max_sev,
            category=self.category,
            detector_id=None,
            action=DetectionAction.MONITOR,
            title=f"Suspicious action sequence: {', '.join(titles)}",
            description=str(findings[0]["description"]),
            details={
                "findings": findings,
                "total_tool_calls": len(tool_calls),
                "categories": categories,
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
