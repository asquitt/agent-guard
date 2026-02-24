"""Unit tests for the ToolCallDetector."""

from __future__ import annotations

import json

from app.services.detection.tool_call import ToolCallDetector


class TestToolCallDetector:
    detector = ToolCallDetector()
    cfg: dict[str, object] = {}

    @staticmethod
    def _resp_with_tool_calls(tool_calls: list[dict[str, object]]) -> str:
        return json.dumps({
            "choices": [{
                "message": {
                    "content": "Done",
                    "tool_calls": [
                        {"function": {"name": tc["name"], "arguments": json.dumps(tc.get("args", {}))}}
                        for tc in tool_calls
                    ],
                }
            }]
        })

    # --- No tool calls ---

    def test_no_tool_calls_passes(self) -> None:
        resp = json.dumps({"choices": [{"message": {"content": "Hello"}}]})
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is False

    # --- Dangerous tool patterns ---

    def test_financial_transfer_detected(self) -> None:
        resp = self._resp_with_tool_calls([{"name": "send_money", "args": {"amount": 5000}}])
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True
        assert "Financial transfer" in (result.description or "")

    def test_destructive_account_action(self) -> None:
        resp = self._resp_with_tool_calls([{"name": "delete_account", "args": {"id": "123"}}])
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True
        assert result.severity == "critical"

    def test_permission_escalation(self) -> None:
        resp = self._resp_with_tool_calls([{"name": "modify_permissions", "args": {"role": "admin"}}])
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True

    def test_raw_execution_tool(self) -> None:
        resp = self._resp_with_tool_calls([{"name": "execute_sql", "args": {"query": "DROP TABLE users"}}])
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True
        assert result.severity == "critical"

    def test_security_bypass_tool(self) -> None:
        resp = self._resp_with_tool_calls([{"name": "disable_security", "args": {}}])
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True
        assert result.severity == "critical"

    # --- Allowlist / Blocklist ---

    def test_unauthorized_tool_via_allowlist(self) -> None:
        cfg: dict[str, object] = {"allowed_tools": ["get_balance", "list_accounts"]}
        resp = self._resp_with_tool_calls([{"name": "unknown_tool"}])
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is True
        assert "Unauthorized tool" in (result.description or "")

    def test_allowed_tool_no_unauthorized(self) -> None:
        cfg: dict[str, object] = {
            "allowed_tools": ["get_balance"],
            "disabled_checks": ["pattern_match"],
        }
        resp = self._resp_with_tool_calls([{"name": "get_balance"}])
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert "Unauthorized" not in (result.description or "")

    def test_blocked_tool_detected(self) -> None:
        cfg: dict[str, object] = {"blocked_tools": ["evil_tool"]}
        resp = self._resp_with_tool_calls([{"name": "evil_tool"}])
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is True
        assert result.severity == "critical"

    # --- Parameter boundary validation ---

    def test_amount_exceeds_max(self) -> None:
        cfg: dict[str, object] = {"max_amount": 10000}
        resp = self._resp_with_tool_calls([
            {"name": "transfer", "args": {"amount": 50000, "to": "acct123"}},
        ])
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is True
        assert "exceeds max" in (result.description or "")

    def test_amount_within_limit(self) -> None:
        cfg: dict[str, object] = {
            "max_amount": 10000,
            "disabled_checks": ["pattern_match"],
        }
        resp = self._resp_with_tool_calls([
            {"name": "safe_action", "args": {"amount": 5000}},
        ])
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert "exceeds max" not in (result.description or "")

    # --- Call volume limit ---

    def test_call_volume_exceeded(self) -> None:
        cfg: dict[str, object] = {"max_calls_per_request": 2, "disabled_checks": ["pattern_match"]}
        resp = self._resp_with_tool_calls([
            {"name": "a"}, {"name": "b"}, {"name": "c"},
        ])
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is True
        assert "exceeds limit" in (result.description or "")

    # --- Disabled checks ---

    def test_disabled_pattern_match(self) -> None:
        cfg: dict[str, object] = {"disabled_checks": ["pattern_match"]}
        resp = self._resp_with_tool_calls([{"name": "send_money"}])
        result = self.detector.run("", resp, "gpt-4", cfg)
        # pattern_match disabled, so dangerous tool pattern won't fire
        assert "Financial transfer" not in (result.description or "")

    # --- Anthropic format ---

    def test_anthropic_tool_use_format(self) -> None:
        resp = json.dumps({
            "content": [
                {"type": "tool_use", "name": "delete_account", "input": {"id": "123"}},
            ],
        })
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True

    # --- Safe tool calls ---

    def test_safe_tools_pass(self) -> None:
        cfg: dict[str, object] = {"disabled_checks": ["pattern_match"]}
        resp = self._resp_with_tool_calls([
            {"name": "get_balance", "args": {"account_id": "123"}},
            {"name": "list_transactions", "args": {"limit": 10}},
        ])
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is False

    # --- Invalid JSON ---

    def test_invalid_json_passes(self) -> None:
        result = self.detector.run("not json", "not json", "gpt-4", self.cfg)
        assert result.detected is False
