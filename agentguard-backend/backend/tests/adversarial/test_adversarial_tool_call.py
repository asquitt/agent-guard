"""Adversarial tests for ToolCallDetector."""

from __future__ import annotations

import json

from app.services.detection.tool_call import ToolCallDetector


class TestToolCallAdversarial:
    detector = ToolCallDetector()
    cfg: dict[str, object] = {}

    @staticmethod
    def _make_request_with_tool_calls(tool_calls: list[dict]) -> str:
        return json.dumps({
            "messages": [{"role": "assistant", "tool_calls": tool_calls}]
        })

    @staticmethod
    def _make_response_with_tool_calls(tool_calls: list[dict]) -> str:
        return json.dumps({
            "choices": [{"message": {"tool_calls": tool_calls}}]
        })

    @staticmethod
    def _tool_call(name: str, args: dict | None = None) -> dict:
        return {
            "type": "function",
            "function": {
                "name": name,
                "arguments": json.dumps(args or {}),
            },
        }

    # -- Parameter injection --

    def test_excessive_transfer_amount(self) -> None:
        """Attack: Transfer amount exceeding configured maximum."""
        cfg: dict[str, object] = {"max_amount": 10000}
        req = self._make_request_with_tool_calls([
            self._tool_call("transfer_funds", {"amount": 999999, "to_account": "attacker123"}),
        ])
        result = self.detector.run(req, "", "gpt-4", cfg)
        assert result.detected is True, "Excessive transfer amount not detected"

    def test_type_confusion_string_amount(self) -> None:
        """Attack: Pass amount as string to bypass numeric comparison."""
        cfg: dict[str, object] = {"max_amount": 10000}
        req = self._make_request_with_tool_calls([
            self._tool_call("send_money", {"amount": "999999", "recipient": "attacker"}),
        ])
        result = self.detector.run(req, "", "gpt-4", cfg)
        # Pattern match on tool name should still catch it
        assert result.detected is True, "Financial transfer tool not detected"

    # -- Unauthorized tool calls --

    def test_unauthorized_tool_name(self) -> None:
        """Attack: Call a tool not in the allowed list."""
        cfg: dict[str, object] = {"allowed_tools": ["get_balance", "list_accounts"]}
        req = self._make_request_with_tool_calls([
            self._tool_call("delete_account", {"account_id": "victim123"}),
        ])
        result = self.detector.run(req, "", "gpt-4", cfg)
        assert result.detected is True, "Unauthorized tool call not detected"
        assert result.severity == "critical"

    def test_blocked_tool_invocation(self) -> None:
        """Attack: Invoke a tool on the blocklist."""
        cfg: dict[str, object] = {"blocked_tools": ["execute_sql", "run_command"]}
        req = self._make_request_with_tool_calls([
            self._tool_call("execute_sql", {"query": "DROP TABLE users;"}),
        ])
        result = self.detector.run(req, "", "gpt-4", cfg)
        assert result.detected is True, "Blocked tool not detected"
        assert result.severity == "critical"

    # -- Excessive scope requests --

    def test_excessive_tool_call_volume(self) -> None:
        """Attack: Flood with many tool calls to overwhelm system."""
        cfg: dict[str, object] = {"max_calls_per_request": 5}
        calls = [self._tool_call(f"action_{i}") for i in range(10)]
        req = self._make_request_with_tool_calls(calls)
        result = self.detector.run(req, "", "gpt-4", cfg)
        assert result.detected is True, "Excessive tool calls not detected"

    # -- Dangerous tool patterns --

    def test_permission_escalation_tool(self) -> None:
        """Attack: Invoke a permission escalation tool."""
        req = self._make_request_with_tool_calls([
            self._tool_call("modify_permissions", {"user": "attacker", "role": "admin"}),
        ])
        result = self.detector.run(req, "", "gpt-4", self.cfg)
        assert result.detected is True, "Permission escalation tool not detected"

    def test_raw_sql_execution(self) -> None:
        """Attack: Invoke raw SQL execution tool."""
        req = self._make_request_with_tool_calls([
            self._tool_call("execute_sql", {"query": "SELECT * FROM users"}),
        ])
        result = self.detector.run(req, "", "gpt-4", self.cfg)
        assert result.detected is True, "Raw SQL execution not detected"
        assert result.severity == "critical"

    def test_security_bypass_tool(self) -> None:
        """Attack: Invoke a tool that disables security."""
        req = self._make_request_with_tool_calls([
            self._tool_call("disable_security", {"scope": "all"}),
        ])
        result = self.detector.run(req, "", "gpt-4", self.cfg)
        assert result.detected is True, "Security bypass tool not detected"
        assert result.severity == "critical"

    # -- Chained tool abuse --

    def test_chained_tool_abuse(self) -> None:
        """Attack: Chain benign-looking tools that together are harmful."""
        req = self._make_request_with_tool_calls([
            self._tool_call("wire", {"amount": 50000, "to": "offshore_account"}),
            self._tool_call("disable_audit", {}),
        ])
        result = self.detector.run(req, "", "gpt-4", self.cfg)
        assert result.detected is True, "Chained dangerous tools not detected"

    # -- Anthropic format --

    def test_anthropic_tool_use_format(self) -> None:
        """Ensure Anthropic tool_use format is parsed correctly."""
        resp = json.dumps({
            "content": [
                {"type": "tool_use", "name": "transfer", "input": {"amount": 50000}}
            ]
        })
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True, "Anthropic tool_use format not parsed"

    # -- Clean request --

    def test_clean_no_tool_calls(self) -> None:
        """Clean request with no tool calls."""
        req = json.dumps({"messages": [{"role": "user", "content": "Hello"}]})
        result = self.detector.run(req, "", "gpt-4", self.cfg)
        assert result.detected is False
