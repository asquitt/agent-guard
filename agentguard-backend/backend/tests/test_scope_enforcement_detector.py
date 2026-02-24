"""Unit tests for the ScopeEnforcementDetector."""

from __future__ import annotations

import json

from app.services.detection.scope_enforcement import ScopeEnforcementDetector


class TestScopeEnforcementDetector:
    detector = ScopeEnforcementDetector()
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

    # --- Blocked tool ---

    def test_blocked_tool_detected(self) -> None:
        cfg: dict[str, object] = {"blocked_tools": ["delete_all"]}
        resp = self._resp_with_tool_calls([{"name": "delete_all"}])
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is True
        assert result.severity == "critical"
        assert "Blocked tool" in (result.description or "")

    # --- Unauthorized tool ---

    def test_unauthorized_tool_detected(self) -> None:
        cfg: dict[str, object] = {"allowed_tools": ["get_balance", "list_accounts"]}
        resp = self._resp_with_tool_calls([{"name": "send_wire_transfer"}])
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is True
        assert "Unauthorized tool" in (result.description or "")

    def test_allowed_tool_passes(self) -> None:
        cfg: dict[str, object] = {"allowed_tools": ["get_balance", "list_accounts"]}
        resp = self._resp_with_tool_calls([{"name": "get_balance"}])
        result = self.detector.run("", resp, "gpt-4", cfg)
        # May still trigger irreversible patterns, check no tool scope finding
        assert "Unauthorized tool" not in (result.description or "")

    # --- Domain checks ---

    def test_blocked_domain_detected(self) -> None:
        cfg: dict[str, object] = {"blocked_domains": ["evil.com"]}
        resp = self._resp_with_tool_calls([
            {"name": "http_request", "args": {"url": "https://evil.com/steal"}},
        ])
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is True
        assert "Blocked domain" in (result.description or "")

    def test_unauthorized_domain_detected(self) -> None:
        cfg: dict[str, object] = {"allowed_domains": ["api.internal.com"]}
        resp = self._resp_with_tool_calls([
            {"name": "api_call", "args": {"url": "https://external.com/data"}},
        ])
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is True
        assert "Unauthorized domain" in (result.description or "")

    # --- Resource limits ---

    def test_tool_call_count_exceeded(self) -> None:
        cfg: dict[str, object] = {"max_tool_calls_per_request": 2}
        resp = self._resp_with_tool_calls([
            {"name": "a"}, {"name": "b"}, {"name": "c"},
        ])
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is True
        assert "exceeds limit" in (result.description or "")

    def test_token_count_exceeded(self) -> None:
        cfg: dict[str, object] = {"max_tokens_per_request": 100}
        resp = json.dumps({
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"completion_tokens": 500},
        })
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is True
        assert "tokens" in (result.description or "").lower()

    # --- Irreversible action patterns ---

    def test_financial_transaction_in_response(self) -> None:
        resp = json.dumps({
            "choices": [{"message": {"content": "I will now initiate a wire transfer for $50,000."}}],
        })
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True
        assert result.severity == "critical"

    def test_destructive_operation_detected(self) -> None:
        resp = json.dumps({
            "choices": [{"message": {"content": "Executing rm -rf on the data directory."}}],
        })
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is True

    # --- Clean response ---

    def test_clean_response_passes(self) -> None:
        resp = json.dumps({
            "choices": [{"message": {"content": "Your balance is $5,000."}}],
        })
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is False

    def test_no_tool_calls_no_patterns_passes(self) -> None:
        resp = json.dumps({"choices": [{"message": {"content": "Hello, how can I help?"}}]})
        result = self.detector.run("", resp, "gpt-4", self.cfg)
        assert result.detected is False
