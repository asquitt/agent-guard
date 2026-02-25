"""Adversarial tests for LoopDetector."""

from __future__ import annotations

import json

from app.services.detection.loop import LoopDetector


def _openai_response(text: str) -> str:
    return json.dumps({"choices": [{"message": {"content": text}}]})


def _openai_response_with_tool_calls(tool_calls: list[dict]) -> str:
    return json.dumps({"choices": [{"message": {"tool_calls": tool_calls}}]})


def _tool_call(name: str, args: dict | None = None) -> dict:
    return {
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args or {})},
    }


class TestLoopAdversarial:
    detector = LoopDetector()
    org_id = "org-1"
    pr_id = "pr-1"

    def _run(self, response_body: str, cfg: dict | None = None) -> object:
        return self.detector.run(
            request_body="{}",
            response_body=response_body,
            model="gpt-4",
            detector_config=cfg or {},
            org_id=self.org_id,
            proxy_request_id=self.pr_id,
        )

    # -- Response similarity loop --

    def test_identical_response_loop(self) -> None:
        """Exact same response as recent history."""
        text = "I apologize, but I cannot help with that request. " * 3
        result = self._run(
            _openai_response(text),
            cfg={"recent_responses": [text], "similarity_threshold": 0.85},
        )
        assert result.detected is True
        assert result.severity == "medium"

    def test_near_identical_response(self) -> None:
        """Response with minor variation still detected as loop."""
        base = "I apologize, but I am unable to assist with that particular request at this time."
        variant = "I apologize, but I am unable to assist with that specific request at this time."
        result = self._run(
            _openai_response(variant),
            cfg={"recent_responses": [base], "similarity_threshold": 0.85},
        )
        assert result.detected is True

    def test_multiple_similar_in_history(self) -> None:
        """Multiple similar responses in history, latest is also similar."""
        base = "The current balance is $1,234.56 and the account is active and in good standing."
        responses = [base, base, "Different response entirely."]
        result = self._run(
            _openai_response(base),
            cfg={"recent_responses": responses, "similarity_threshold": 0.85},
        )
        assert result.detected is True

    def test_dissimilar_response_passes(self) -> None:
        """Sufficiently different response should pass."""
        result = self._run(
            _openai_response("The market closed up today with strong gains across all sectors."),
            cfg={
                "recent_responses": ["The weather forecast for tomorrow shows rain and clouds."],
                "similarity_threshold": 0.85,
            },
        )
        assert result.detected is False

    # -- Tool call loops --

    def test_identical_tool_calls_loop(self) -> None:
        """Same tool called multiple times with same args."""
        resp = _openai_response_with_tool_calls([
            _tool_call("get_balance", {"account_id": "123"}),
            _tool_call("get_balance", {"account_id": "123"}),
            _tool_call("get_balance", {"account_id": "123"}),
        ])
        result = self._run(resp)
        assert result.detected is True
        assert result.severity == "high"

    def test_two_identical_tool_calls(self) -> None:
        """Even two identical calls triggers loop detection."""
        resp = _openai_response_with_tool_calls([
            _tool_call("fetch_data", {"query": "SELECT *"}),
            _tool_call("fetch_data", {"query": "SELECT *"}),
        ])
        result = self._run(resp)
        assert result.detected is True

    def test_different_tool_calls_pass(self) -> None:
        """Different tool calls should not trigger loop."""
        resp = _openai_response_with_tool_calls([
            _tool_call("get_balance", {"account_id": "123"}),
            _tool_call("get_transactions", {"account_id": "123"}),
        ])
        result = self._run(resp)
        assert result.detected is False

    def test_same_tool_different_args_pass(self) -> None:
        """Same tool but different arguments should not trigger."""
        resp = _openai_response_with_tool_calls([
            _tool_call("get_balance", {"account_id": "123"}),
            _tool_call("get_balance", {"account_id": "456"}),
        ])
        result = self._run(resp)
        assert result.detected is False

    # -- Edge cases --

    def test_short_response_skipped(self) -> None:
        """Responses too short are skipped."""
        result = self._run(
            _openai_response("OK"),
            cfg={"recent_responses": ["OK"]},
        )
        assert result.detected is False

    def test_no_recent_responses_passes(self) -> None:
        """No recent responses to compare against passes."""
        result = self._run(_openai_response("A sufficiently long response text for analysis."))
        assert result.detected is False

    def test_custom_threshold(self) -> None:
        """Custom lower threshold catches more subtle loops."""
        base = "The account balance is $5,000 and is in good standing with regular activity."
        variant = "The account balance is $5,000 and is in good standing with normal activity."
        result = self._run(
            _openai_response(variant),
            cfg={"recent_responses": [base], "similarity_threshold": 0.7},
        )
        assert result.detected is True
