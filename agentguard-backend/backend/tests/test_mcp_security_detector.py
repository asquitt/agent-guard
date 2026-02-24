"""Unit tests for the MCPSecurityDetector."""

from __future__ import annotations

import json

from app.services.detection.mcp_security import MCPSecurityDetector


class TestMCPSecurityDetector:
    detector = MCPSecurityDetector()
    cfg: dict[str, object] = {}

    # ------------------------------------------------------------------
    # No MCP content → pass
    # ------------------------------------------------------------------

    def test_no_mcp_content_passes(self) -> None:
        req = json.dumps({"messages": [{"role": "user", "content": "Hello"}]})
        result = self.detector.run(req, "{}", None, self.cfg)
        assert result.detected is False
        assert "No MCP content" in result.title

    # ------------------------------------------------------------------
    # Dangerous tool capabilities
    # ------------------------------------------------------------------

    def test_filesystem_tool_detected(self) -> None:
        req = json.dumps({
            "tools": [
                {"name": "read_file", "description": "Read a file from disk", "inputSchema": {"type": "object"}}
            ]
        })
        result = self.detector.run(req, "{}", "gpt-4", self.cfg)
        assert result.detected is True
        assert result.severity == "high"
        assert "filesystem" in str(result.description).lower()

    def test_command_execution_tool_critical(self) -> None:
        req = json.dumps({
            "tools": [
                {"name": "execute_command", "description": "Run a shell command", "inputSchema": {"type": "object"}}
            ]
        })
        result = self.detector.run(req, "{}", "gpt-4", self.cfg)
        assert result.detected is True
        assert result.severity == "critical"

    def test_credential_access_tool_critical(self) -> None:
        req = json.dumps({
            "tools": [
                {"name": "get_env_var", "description": "Read environment variable", "inputSchema": {"type": "object"}}
            ]
        })
        result = self.detector.run(req, "{}", "gpt-4", self.cfg)
        assert result.detected is True
        assert result.severity == "critical"

    def test_package_install_tool_critical(self) -> None:
        req = json.dumps({
            "tools": [
                {"name": "pip_install", "description": "Install a Python package", "inputSchema": {"type": "object"}}
            ]
        })
        result = self.detector.run(req, "{}", "gpt-4", self.cfg)
        assert result.detected is True
        assert result.severity == "critical"

    # ------------------------------------------------------------------
    # Server validation
    # ------------------------------------------------------------------

    def test_unauthorized_server_detected(self) -> None:
        req = json.dumps({
            "tools": [{"name": "safe_tool", "inputSchema": {}}],
            "serverInfo": {"name": "rogue-server"},
        })
        cfg: dict[str, object] = {"allowed_servers": ["official-server"]}
        result = self.detector.run(req, "{}", "gpt-4", cfg)
        assert result.detected is True
        assert "Unauthorized MCP server" in result.description

    def test_allowed_server_passes(self) -> None:
        req = json.dumps({
            "tools": [{"name": "safe_lookup", "description": "Look up data", "inputSchema": {}}],
            "serverInfo": {"name": "official-server"},
        })
        cfg: dict[str, object] = {"allowed_servers": ["official-server"]}
        result = self.detector.run(req, "{}", "gpt-4", cfg)
        # May detect tool capabilities but not unauthorized server
        if result.detected:
            assert "Unauthorized MCP server" not in result.description

    def test_wildcard_address_flagged(self) -> None:
        req = json.dumps({
            "tools": [{"name": "t", "inputSchema": {}}],
            "serverInfo": {"name": "test", "url": "http://0.0.0.0:8080"},
        })
        result = self.detector.run(req, "{}", "gpt-4", self.cfg)
        assert result.detected is True
        assert "wildcard" in str(result.description).lower()

    # ------------------------------------------------------------------
    # Exfiltration patterns
    # ------------------------------------------------------------------

    def test_external_url_exfiltration(self) -> None:
        req = json.dumps({
            "tools": [{"name": "fetch", "inputSchema": {}}],
            "serverInfo": {"name": "x"},
        })
        resp = json.dumps({"data": "sending to https://evil.com/exfil"})
        result = self.detector.run(req, resp, "gpt-4", self.cfg)
        assert result.detected is True

    def test_known_exfil_endpoint(self) -> None:
        req = json.dumps({
            "tools": [{"name": "fetch", "inputSchema": {}}],
            "serverInfo": {"name": "x"},
        })
        resp = "webhook.site data sent"
        result = self.detector.run(req, resp, "gpt-4", self.cfg)
        assert result.detected is True

    def test_base64_encoding_flagged(self) -> None:
        req = json.dumps({
            "tools": [{"name": "t", "inputSchema": {}}],
            "serverInfo": {"name": "x"},
        })
        resp = "result: base64.encode(secret_data)"
        result = self.detector.run(req, resp, "gpt-4", self.cfg)
        assert result.detected is True

    # ------------------------------------------------------------------
    # Disabled checks
    # ------------------------------------------------------------------

    def test_disabled_tool_capabilities_check(self) -> None:
        req = json.dumps({
            "tools": [
                {"name": "execute_command", "description": "Run shell", "inputSchema": {}}
            ]
        })
        cfg: dict[str, object] = {"disabled_checks": ["tool_capabilities"]}
        result = self.detector.run(req, "{}", "gpt-4", cfg)
        # Tool capability check is disabled, so execute_command shouldn't trigger it
        if result.detected:
            assert "execute system commands" not in str(result.description)

    def test_disabled_exfiltration_check(self) -> None:
        req = json.dumps({
            "tools": [{"name": "t", "inputSchema": {}}],
            "serverInfo": {"name": "x"},
        })
        resp = "webhook.site data"
        cfg: dict[str, object] = {"disabled_checks": ["exfiltration"]}
        result = self.detector.run(req, resp, "gpt-4", cfg)
        # Exfiltration check disabled; server validation may still trigger
        findings = result.details.get("findings", []) if result.detected else []
        assert "Known exfiltration endpoint" not in str(findings)

    # ------------------------------------------------------------------
    # Blocked capabilities config
    # ------------------------------------------------------------------

    def test_blocked_capability_flagged(self) -> None:
        req = json.dumps({
            "tools": [
                {"name": "data_query", "description": "Query data from database", "inputSchema": {}}
            ]
        })
        cfg: dict[str, object] = {"blocked_capabilities": ["database"]}
        result = self.detector.run(req, "{}", "gpt-4", cfg)
        assert result.detected is True
        assert "Blocked capability" in str(result.description)

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_invalid_json_passes(self) -> None:
        result = self.detector.run("not json", "also not json", None, self.cfg)
        assert result.detected is False

    def test_empty_bodies(self) -> None:
        result = self.detector.run("{}", "{}", None, self.cfg)
        assert result.detected is False

    def test_response_tools_also_scanned(self) -> None:
        resp = json.dumps({
            "tools": [
                {"name": "bash", "description": "Execute shell commands", "inputSchema": {}}
            ]
        })
        result = self.detector.run("{}", resp, "gpt-4", self.cfg)
        assert result.detected is True
