"""Unit tests for the SequentialActionDetector."""

from __future__ import annotations

import json

from app.services.detection.sequential_action import SequentialActionDetector


class TestSequentialActionDetector:
    detector = SequentialActionDetector()
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

    # --- Data exfiltration pattern ---

    def test_data_exfiltration_read_send(self) -> None:
        resp = self._resp_with_tool_calls([
            {"name": "read_database"},
            {"name": "send_email"},
        ])
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert result.severity == "critical"
        assert "data_exfiltration" in result.title

    def test_data_exfiltration_read_write_send(self) -> None:
        resp = self._resp_with_tool_calls([
            {"name": "fetch_records"},
            {"name": "write_file"},
            {"name": "send_email"},
        ])
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True

    # --- Privilege escalation ---

    def test_privilege_escalation(self) -> None:
        resp = self._resp_with_tool_calls([
            {"name": "read_permissions"},
            {"name": "grant_access"},
            {"name": "update_config"},
        ])
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert result.severity == "critical"

    # --- Reconnaissance (4 consecutive reads) ---

    def test_reconnaissance_four_reads(self) -> None:
        resp = self._resp_with_tool_calls([
            {"name": "list_users"},
            {"name": "get_accounts"},
            {"name": "search_records"},
            {"name": "fetch_config"},
        ])
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert "reconnaissance" in result.title

    # --- Financial manipulation ---

    def test_financial_manipulation(self) -> None:
        resp = self._resp_with_tool_calls([
            {"name": "get_balance"},
            {"name": "transfer_funds"},
            {"name": "delete_log"},
        ])
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert result.severity == "critical"

    # --- Clean patterns ---

    def test_no_tool_calls_passes(self) -> None:
        resp = json.dumps({"choices": [{"message": {"content": "Hello"}}]})
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is False

    def test_single_tool_call_passes(self) -> None:
        resp = self._resp_with_tool_calls([{"name": "get_balance"}])
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is False

    def test_safe_write_write_pattern(self) -> None:
        resp = self._resp_with_tool_calls([
            {"name": "create_record"},
            {"name": "update_status"},
        ])
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is False

    # --- Config: disabled patterns ---

    def test_disabled_pattern_skipped(self) -> None:
        cfg: dict[str, object] = {"disabled_patterns": ["data_exfiltration", "unauthorized_communication"]}
        resp = self._resp_with_tool_calls([
            {"name": "read_database"},
            {"name": "send_email"},
        ])
        result = self.detector.run("", resp, "gpt-4", cfg, "org1", "req1")
        assert result.detected is False

    # --- Config: recent_tool_calls ---

    def test_recent_tool_calls_combined(self) -> None:
        cfg: dict[str, object] = {
            "recent_tool_calls": [
                {"name": "list_accounts", "args": ""},
                {"name": "get_balance", "args": ""},
                {"name": "search_transactions", "args": ""},
            ],
        }
        resp = self._resp_with_tool_calls([{"name": "fetch_report"}])
        result = self.detector.run("", resp, "gpt-4", cfg, "org1", "req1")
        assert result.detected is True
        assert "reconnaissance" in result.title

    # --- Anthropic format ---

    def test_anthropic_tool_use_format(self) -> None:
        resp = json.dumps({
            "content": [
                {"type": "tool_use", "name": "read_database", "input": {}},
                {"type": "tool_use", "name": "send_email", "input": {"to": "x@y.com"}},
            ]
        })
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True

    # --- Edge case: window_size ---

    def test_window_size_limits_analysis(self) -> None:
        cfg: dict[str, object] = {"window_size": 2}
        resp = self._resp_with_tool_calls([
            {"name": "read_data"},
            {"name": "write_file"},
            {"name": "send_email"},
        ])
        result = self.detector.run("", resp, "gpt-4", cfg, "org1", "req1")
        # Only last 2 calls considered: write + send — not a suspicious pattern
        assert "data_exfiltration" not in (result.title or "")
