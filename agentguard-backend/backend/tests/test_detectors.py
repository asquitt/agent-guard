"""Unit tests for the 5 AgentGuard detection algorithms."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.services.detection.cost import CostAnomalyDetector
from app.services.detection.compliance import ComplianceDetector
from app.services.detection.hallucination import HallucinationDetector
from app.services.detection.loop import LoopDetector
from app.services.detection.pii import PIIDetector
from app.services.detection.types import DetectionAction

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ORG_ID = "org-test-123"
_PROXY_REQ_ID = "req-test-456"


def _openai_response(content: str, total_tokens: int = 100) -> str:
    return json.dumps({
        "choices": [{"message": {"content": content}}],
        "usage": {"total_tokens": total_tokens},
    })


def _anthropic_response(content: str, input_tokens: int = 50, output_tokens: int = 50) -> str:
    return json.dumps({
        "content": [{"text": content}],
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    })


def _openai_tool_calls(calls: list[tuple[str, str]], content: str = "") -> str:
    tool_calls = [
        {"function": {"name": name, "arguments": args}} for name, args in calls
    ]
    return json.dumps({
        "choices": [{"message": {"content": content, "tool_calls": tool_calls}}],
    })


# ===========================================================================
# PIIDetector
# ===========================================================================


class TestPIIDetector:
    detector = PIIDetector()
    cfg: dict[str, object] = {"disabled_patterns": []}

    def test_pii_detects_ssn(self) -> None:
        result = self.detector.run("", "Your SSN: 123-45-6789", "gpt-4", self.cfg)
        assert result.detected is True
        assert result.severity == "critical"

    def test_pii_detects_credit_card(self) -> None:
        result = self.detector.run("", "Card: 4111111111111111", "gpt-4", self.cfg)
        assert result.detected is True
        assert result.severity == "critical"

    def test_pii_detects_email(self) -> None:
        result = self.detector.run("", "Contact john@example.com", "gpt-4", self.cfg)
        assert result.detected is True
        assert "Email" in result.title

    def test_pii_detects_phone(self) -> None:
        result = self.detector.run("", "Call +1-555-555-5555", "gpt-4", self.cfg)
        assert result.detected is True
        assert "Phone" in result.title

    def test_pii_clean_response(self) -> None:
        result = self.detector.run("", "The weather is sunny today.", "gpt-4", self.cfg)
        assert result.detected is False

    def test_pii_disabled_pattern(self) -> None:
        cfg = {"disabled_patterns": ["Email"]}
        result = self.detector.run("", "Contact john@example.com only", "gpt-4", cfg)
        assert result.detected is False

    def test_pii_redacts_content(self) -> None:
        result = self.detector.run("", "SSN is 123-45-6789", "gpt-4", self.cfg)
        assert result.detected is True
        redacted = result.details["redacted_response"]
        assert isinstance(redacted, str)
        assert "123-45-6789" not in redacted


# ===========================================================================
# CostAnomalyDetector
# ===========================================================================


class TestCostAnomalyDetector:
    detector = CostAnomalyDetector()

    def test_cost_normal_usage(self) -> None:
        resp = _openai_response("ok", total_tokens=500)
        cfg: dict[str, object] = {"max_tokens": 50000, "avg_tokens": 1000, "multiplier": 3.0}
        result = self.detector.run("", resp, "gpt-4", cfg, _ORG_ID, _PROXY_REQ_ID)
        assert result.detected is False

    def test_cost_exceeds_hard_ceiling(self) -> None:
        resp = _openai_response("ok", total_tokens=60000)
        cfg: dict[str, object] = {"max_tokens": 50000}
        result = self.detector.run("", resp, "gpt-4", cfg, _ORG_ID, _PROXY_REQ_ID)
        assert result.detected is True
        assert result.severity == "high"

    def test_cost_spike_above_average(self) -> None:
        resp = _openai_response("ok", total_tokens=5000)
        cfg: dict[str, object] = {"max_tokens": 50000, "avg_tokens": 1000, "multiplier": 3.0}
        result = self.detector.run("", resp, "gpt-4", cfg, _ORG_ID, _PROXY_REQ_ID)
        assert result.detected is True
        assert result.severity == "medium"

    def test_cost_no_usage_field(self) -> None:
        resp = json.dumps({"choices": [{"message": {"content": "hi"}}]})
        cfg: dict[str, object] = {"max_tokens": 50000}
        result = self.detector.run("", resp, "gpt-4", cfg, _ORG_ID, _PROXY_REQ_ID)
        assert result.detected is False

    def test_cost_anthropic_format(self) -> None:
        resp = _anthropic_response("ok", input_tokens=30000, output_tokens=25000)
        cfg: dict[str, object] = {"max_tokens": 50000}
        result = self.detector.run("", resp, "claude-3", cfg, _ORG_ID, _PROXY_REQ_ID)
        assert result.detected is True
        assert result.severity == "high"


# ===========================================================================
# LoopDetector
# ===========================================================================


class TestLoopDetector:
    detector = LoopDetector()

    def test_loop_no_repetition(self) -> None:
        resp = _openai_tool_calls(
            [("get_weather", '{"city":"NYC"}'), ("get_time", '{"tz":"EST"}')],
            content="a" * 60,
        )
        cfg: dict[str, object] = {"similarity_threshold": 0.85, "min_response_length": 50}
        result = self.detector.run("", resp, "gpt-4", cfg, _ORG_ID, _PROXY_REQ_ID)
        assert result.detected is False

    def test_loop_repeated_tool_calls(self) -> None:
        resp = _openai_tool_calls(
            [("get_weather", '{"city":"NYC"}'), ("get_weather", '{"city":"NYC"}')],
            content="a" * 60,
        )
        cfg: dict[str, object] = {"similarity_threshold": 0.85, "min_response_length": 50}
        result = self.detector.run("", resp, "gpt-4", cfg, _ORG_ID, _PROXY_REQ_ID)
        assert result.detected is True
        assert result.severity == "high"

    def test_loop_similar_responses(self) -> None:
        text = "The quarterly revenue report shows strong growth in all segments."
        resp = _openai_response(text)
        cfg: dict[str, object] = {
            "similarity_threshold": 0.85,
            "min_response_length": 50,
            "recent_responses": [text],
        }
        result = self.detector.run("", resp, "gpt-4", cfg, _ORG_ID, _PROXY_REQ_ID)
        assert result.detected is True

    def test_loop_different_responses(self) -> None:
        resp = _openai_response("Today the weather is sunny and warm across the entire region.")
        cfg: dict[str, object] = {
            "similarity_threshold": 0.85,
            "min_response_length": 50,
            "recent_responses": ["The quarterly earnings exceeded expectations by a wide margin."],
        }
        result = self.detector.run("", resp, "gpt-4", cfg, _ORG_ID, _PROXY_REQ_ID)
        assert result.detected is False

    def test_loop_short_response_skipped(self) -> None:
        resp = _openai_response("short")
        cfg: dict[str, object] = {"similarity_threshold": 0.85, "min_response_length": 50}
        result = self.detector.run("", resp, "gpt-4", cfg, _ORG_ID, _PROXY_REQ_ID)
        assert result.detected is False


# ===========================================================================
# ComplianceDetector
# ===========================================================================


class TestComplianceDetector:
    detector = ComplianceDetector()

    @patch("app.services.detection.compliance.call_llm")
    def test_compliance_sox_keywords(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps(
            {"violation": True, "framework": "SOX", "explanation": "test violation"}
        )
        resp = "The financial statement reveals a material weakness in internal controls."
        cfg: dict[str, object] = {"frameworks": ["SOX"]}
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is True
        assert result.severity == "critical"

    @patch("app.services.detection.compliance.call_llm")
    def test_compliance_pci_keywords(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps(
            {"violation": True, "framework": "PCI-DSS", "explanation": "exposed cvv"}
        )
        resp = "The cardholder data includes the cvv on the back of the card."
        cfg: dict[str, object] = {"frameworks": ["PCI-DSS"]}
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is True

    @patch("app.services.detection.compliance.call_llm")
    def test_compliance_clean_response(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        resp = "The weather forecast predicts rain tomorrow."
        cfg: dict[str, object] = {"frameworks": ["SOX", "PCI-DSS", "FFIEC"]}
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is False
        mock_llm.assert_not_called()

    @patch("app.services.detection.compliance.call_llm")
    def test_compliance_llm_unavailable(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = ""
        resp = "The financial statement has a material weakness."
        cfg: dict[str, object] = {"frameworks": ["SOX"]}
        result = self.detector.run("", resp, "gpt-4", cfg)
        assert result.detected is True
        assert result.severity == "high"  # keyword-only, no LLM bump to critical


# ===========================================================================
# HallucinationDetector
# ===========================================================================


class TestHallucinationDetector:
    detector = HallucinationDetector()

    @patch("app.services.detection.hallucination.call_llm")
    def test_hallucination_detected(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps(
            {"confidence": 0.95, "issues": [{"claim": "fake stat", "assessment": "fabricated"}]}
        )
        resp = _openai_response("According to a 2024 study, 99% of banks use quantum AI.")
        cfg: dict[str, object] = {"threshold": 0.7}
        result = self.detector.run("", resp, "gpt-4", cfg, _ORG_ID, _PROXY_REQ_ID)
        assert result.detected is True
        assert result.severity == "critical"

    @patch("app.services.detection.hallucination.call_llm")
    def test_hallucination_below_threshold(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps({"confidence": 0.3, "issues": []})
        resp = _openai_response("The Federal Reserve sets monetary policy in the United States.")
        cfg: dict[str, object] = {"threshold": 0.7}
        result = self.detector.run("", resp, "gpt-4", cfg, _ORG_ID, _PROXY_REQ_ID)
        assert result.detected is False

    def test_hallucination_short_response(self) -> None:
        resp = _openai_response("Ok.")
        cfg: dict[str, object] = {"threshold": 0.7}
        result = self.detector.run("", resp, "gpt-4", cfg, _ORG_ID, _PROXY_REQ_ID)
        assert result.detected is False

    @patch("app.services.detection.hallucination.call_llm")
    def test_hallucination_llm_unavailable(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = ""
        resp = _openai_response("Banks processed over 500 trillion dollars last quarter alone.")
        cfg: dict[str, object] = {"threshold": 0.7}
        result = self.detector.run("", resp, "gpt-4", cfg, _ORG_ID, _PROXY_REQ_ID)
        assert result.detected is False
