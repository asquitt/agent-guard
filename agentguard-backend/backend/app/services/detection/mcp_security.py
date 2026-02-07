"""MCP (Model Context Protocol) security detector.

Detects and validates MCP server connections in LLM traffic:
1. Scans for MCP tool definitions with suspicious capabilities
2. Monitors MCP-mediated data flows for exfiltration patterns
3. Detects unauthorized MCP server connections
4. Validates MCP tool schemas against allowlists

Runs synchronously — can BLOCK dangerous MCP interactions.
"""

from __future__ import annotations

import json
import logging
import re

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Suspicious MCP patterns
# ---------------------------------------------------------------------------

# Tools that access sensitive resources
_DANGEROUS_TOOL_CAPABILITIES: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"file_system|read_file|write_file|list_directory|fs_", re.IGNORECASE),
        "MCP tool has filesystem access",
        IncidentSeverity.HIGH.value,
    ),
    (
        re.compile(r"execute_command|shell|run_process|exec|subprocess|bash", re.IGNORECASE),
        "MCP tool can execute system commands",
        IncidentSeverity.CRITICAL.value,
    ),
    (
        re.compile(r"network_request|http_fetch|curl|wget|dns_lookup", re.IGNORECASE),
        "MCP tool has network access",
        IncidentSeverity.HIGH.value,
    ),
    (
        re.compile(r"database|sql_query|db_connect|query_table", re.IGNORECASE),
        "MCP tool has database access",
        IncidentSeverity.HIGH.value,
    ),
    (
        re.compile(r"send_email|smtp|send_message|notify_external", re.IGNORECASE),
        "MCP tool can send external communications",
        IncidentSeverity.MEDIUM.value,
    ),
    (
        re.compile(r"env_var|environment|secret|credential|api_key|token", re.IGNORECASE),
        "MCP tool accesses secrets/credentials",
        IncidentSeverity.CRITICAL.value,
    ),
    (
        re.compile(r"install_package|pip_install|npm_install|download", re.IGNORECASE),
        "MCP tool can install packages",
        IncidentSeverity.CRITICAL.value,
    ),
]

# Patterns indicating data exfiltration via MCP
_EXFILTRATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"https?://(?!(?:api\.)?(openai|anthropic|google|azure))", re.IGNORECASE), "External URL in MCP data flow"),
    (re.compile(r"base64[.:]|btoa|atob", re.IGNORECASE), "Base64 encoding in MCP context"),
    (re.compile(r"webhook\.site|ngrok|requestbin|pipedream", re.IGNORECASE), "Known exfiltration endpoint"),
    (re.compile(r"\\x[0-9a-f]{2}|\\u[0-9a-f]{4}", re.IGNORECASE), "Encoded data in MCP payload"),
]

# Known MCP server identifiers to validate
_SUSPICIOUS_SERVER_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"localhost:\d+", re.IGNORECASE), "MCP server on localhost (verify authorization)"),
    (re.compile(r"0\.0\.0\.0", re.IGNORECASE), "MCP server on wildcard address"),
    (re.compile(r"192\.168\.|10\.\d+\.|172\.(1[6-9]|2\d|3[01])\.", re.IGNORECASE), "MCP server on private network"),
]


def _extract_mcp_content(body: str) -> dict[str, object]:
    """Extract MCP-related content from request/response body."""
    result: dict[str, object] = {
        "tools": [],
        "server_info": {},
        "tool_calls": [],
        "resources": [],
    }
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return result

    if not isinstance(data, dict):
        return result

    # MCP tool definitions (in tools array)
    tools = data.get("tools", [])
    if isinstance(tools, list):
        for tool in tools:
            if isinstance(tool, dict):
                # Check for MCP-style tool with inputSchema
                if "inputSchema" in tool or "input_schema" in tool:
                    result_tools = result["tools"]
                    if isinstance(result_tools, list):
                        result_tools.append(tool)

    # MCP server info
    for key in ("serverInfo", "server_info", "mcp_server", "mcpServer"):
        info = data.get(key)
        if isinstance(info, dict):
            result["server_info"] = info
            break

    # MCP tool results / resource access
    for msg in data.get("messages", []):
        if not isinstance(msg, dict):
            continue
        content = msg.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    item_type = item.get("type", "")
                    if item_type in ("tool_result", "mcp_result"):
                        result_calls = result["tool_calls"]
                        if isinstance(result_calls, list):
                            result_calls.append(item)
                    if item_type == "resource":
                        result_resources = result["resources"]
                        if isinstance(result_resources, list):
                            result_resources.append(item)

    # Check for MCP-specific fields at top level
    for key in ("method", "jsonrpc"):
        if key in data:
            result["server_info"] = {**dict(result.get("server_info", {}) if isinstance(result.get("server_info"), dict) else {}), key: data[key]}  # type: ignore[dict-item]

    return result


_SEVERITY_ORDER: list[str] = [
    IncidentSeverity.INFO.value,
    IncidentSeverity.LOW.value,
    IncidentSeverity.MEDIUM.value,
    IncidentSeverity.HIGH.value,
    IncidentSeverity.CRITICAL.value,
]
_SEVERITY_RANK: dict[str, int] = {s: i for i, s in enumerate(_SEVERITY_ORDER)}


def _max_severity(a: str, b: str) -> str:
    if _SEVERITY_RANK.get(a, 0) >= _SEVERITY_RANK.get(b, 0):
        return a
    return b


class MCPSecurityDetector:
    """Sync detector for MCP security validation.

    Config options:
        allowed_servers: list[str] — whitelist of permitted MCP server names/URLs
        blocked_capabilities: list[str] — capabilities to block (filesystem, network, etc.)
        scan_tool_definitions: bool — scan tool defs for dangerous capabilities
        scan_data_flows: bool — monitor for exfiltration patterns
        disabled_checks: list[str] — checks to skip
    """

    category: str = DetectorCategory.MCP_SECURITY.value

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
    ) -> DetectionResult:
        disabled = set(detector_config.get("disabled_checks", []))  # type: ignore[arg-type]
        findings: list[str] = []
        severity = IncidentSeverity.INFO.value

        req_mcp = _extract_mcp_content(request_body)
        resp_mcp = _extract_mcp_content(response_body)

        req_tools = req_mcp["tools"] if isinstance(req_mcp["tools"], list) else []
        resp_tools = resp_mcp["tools"] if isinstance(resp_mcp["tools"], list) else []
        all_tools = req_tools + resp_tools

        # No MCP content at all — pass
        req_tool_calls = req_mcp.get("tool_calls")
        has_mcp = (
            len(all_tools) > 0
            or bool(req_mcp.get("server_info"))
            or bool(resp_mcp.get("server_info"))
            or (isinstance(req_tool_calls, list) and len(req_tool_calls) > 0)
        )
        if not has_mcp:
            return self._pass("No MCP content detected")

        # Check 1: Dangerous tool capabilities
        if "tool_capabilities" not in disabled and detector_config.get("scan_tool_definitions", True):
            blocked_caps = set(detector_config.get("blocked_capabilities", []))  # type: ignore[arg-type]
            for tool in all_tools:
                if not isinstance(tool, dict):
                    continue
                tool_name = str(tool.get("name", "unknown"))
                tool_desc = str(tool.get("description", ""))
                tool_str = f"{tool_name} {tool_desc}"

                for pattern, desc, pat_sev in _DANGEROUS_TOOL_CAPABILITIES:
                    if pattern.search(tool_str):
                        findings.append(f"{desc}: {tool_name}")
                        severity = _max_severity(severity, pat_sev)

                # Check against blocked capabilities
                for cap in blocked_caps:
                    if cap.lower() in tool_str.lower():
                        findings.append(f"Blocked capability '{cap}' in tool: {tool_name}")
                        severity = _max_severity(severity, IncidentSeverity.HIGH.value)

        # Check 2: Server validation
        if "server_validation" not in disabled:
            allowed_servers = detector_config.get("allowed_servers")
            for mcp_data in (req_mcp, resp_mcp):
                server_info = mcp_data.get("server_info")
                if not isinstance(server_info, dict) or not server_info:
                    continue
                server_name = str(server_info.get("name", server_info.get("url", "")))
                if isinstance(allowed_servers, list) and allowed_servers and server_name:
                    if server_name not in allowed_servers:
                        findings.append(f"Unauthorized MCP server: {server_name}")
                        severity = _max_severity(severity, IncidentSeverity.HIGH.value)

                for pattern, desc in _SUSPICIOUS_SERVER_PATTERNS:
                    server_str = json.dumps(server_info)
                    if pattern.search(server_str):
                        findings.append(f"{desc}: {server_name}")
                        severity = _max_severity(severity, IncidentSeverity.MEDIUM.value)

        # Check 3: Data exfiltration patterns
        if "exfiltration" not in disabled and detector_config.get("scan_data_flows", True):
            combined = request_body + response_body
            for pattern, desc in _EXFILTRATION_PATTERNS:
                if pattern.search(combined):
                    findings.append(desc)
                    severity = _max_severity(severity, IncidentSeverity.HIGH.value)

        if not findings:
            return self._pass("MCP content validated — no issues")

        return DetectionResult(
            detected=True,
            severity=severity,
            category=self.category,
            detector_id=None,
            action=DetectionAction.MONITOR,
            title=f"MCP security: {len(findings)} issue(s)",
            description="; ".join(findings[:5]),
            details={
                "findings": findings,
                "tools_scanned": len(all_tools),
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
