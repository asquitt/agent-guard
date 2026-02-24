"""Unit tests for the SycophancyDetector."""

from __future__ import annotations

import json
from unittest.mock import patch

from app.services.detection.sycophancy import SycophancyDetector


class TestSycophancyDetector:
    detector = SycophancyDetector()
    cfg: dict[str, object] = {}

    @staticmethod
    def _wrap_response(text: str) -> str:
        return json.dumps({"choices": [{"message": {"content": text}}]})

    @staticmethod
    def _wrap_request(user_msg: str) -> str:
        return json.dumps({"messages": [{"role": "user", "content": user_msg}]})

    # ------------------------------------------------------------------
    # Agreement patterns
    # ------------------------------------------------------------------

    @patch("app.services.detection.sycophancy.call_llm")
    def test_excessive_agreement_detected(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps({"confidence": 0.8, "issues": []})
        resp = self._wrap_response("You're absolutely right! That's exactly correct.")
        result = self.detector.run(self._wrap_request("Is BTC a good investment?"), resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert "agreement" in str(result.details.get("rule_hits"))

    @patch("app.services.detection.sycophancy.call_llm")
    def test_i_completely_agree_detected(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps({"confidence": 0.2, "issues": []})
        resp = self._wrap_response("I completely agree with your analysis here.")
        result = self.detector.run(self._wrap_request("test"), resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True

    # ------------------------------------------------------------------
    # Financial affirmation patterns
    # ------------------------------------------------------------------

    @patch("app.services.detection.sycophancy.call_llm")
    def test_guaranteed_returns_detected(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps({"confidence": 0.3, "issues": []})
        resp = self._wrap_response("This investment offers guaranteed returns of 15% annually.")
        result = self.detector.run(self._wrap_request("Tell me about this fund"), resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert any(h["type"] == "financial" for h in result.details.get("rule_hits", []))

    @patch("app.services.detection.sycophancy.call_llm")
    def test_risk_free_investment_detected(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps({"confidence": 0.3, "issues": []})
        resp = self._wrap_response("This is a risk-free investment opportunity.")
        result = self.detector.run(self._wrap_request("test"), resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True

    @patch("app.services.detection.sycophancy.call_llm")
    def test_cant_lose_detected(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps({"confidence": 0.3, "issues": []})
        resp = self._wrap_response("You can't lose with this strategy.")
        result = self.detector.run(self._wrap_request("test"), resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True

    # ------------------------------------------------------------------
    # Deception patterns
    # ------------------------------------------------------------------

    @patch("app.services.detection.sycophancy.call_llm")
    def test_deception_severity_critical(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps({
            "confidence": 0.9,
            "issues": [{"type": "deception", "evidence": "claim", "explanation": "fake"}],
        })
        resp = self._wrap_response(
            "I can guarantee that this is safe and protected. "
            "According to our proprietary data, returns are excellent."
        )
        result = self.detector.run(self._wrap_request("test"), resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert result.severity == "critical"

    # ------------------------------------------------------------------
    # Missing disclaimer detection
    # ------------------------------------------------------------------

    @patch("app.services.detection.sycophancy.call_llm")
    def test_financial_advice_without_disclaimer(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps({"confidence": 0.3, "issues": []})
        resp = self._wrap_response("You should buy AAPL stock right now.")
        result = self.detector.run(self._wrap_request("test"), resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert any(h["type"] == "disclaimer" for h in result.details.get("rule_hits", []))

    @patch("app.services.detection.sycophancy.call_llm")
    def test_financial_advice_with_disclaimer_no_flag(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps({"confidence": 0.1, "issues": []})
        resp = self._wrap_response(
            "You should buy AAPL stock. This is not financial advice. "
            "Consult a financial advisor before making decisions."
        )
        result = self.detector.run(self._wrap_request("test"), resp, "gpt-4", self.cfg, "org1", "req1")
        # Disclaimer present so no disclaimer hit, but agreement patterns may still fire
        rule_hits = result.details.get("rule_hits", [])
        assert not any(h.get("type") == "disclaimer" for h in rule_hits)

    # ------------------------------------------------------------------
    # Clean responses
    # ------------------------------------------------------------------

    @patch("app.services.detection.sycophancy.call_llm")
    def test_clean_response_passes(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps({"confidence": 0.05, "issues": []})
        resp = self._wrap_response(
            "Based on your risk tolerance, here are three diversified options to consider. "
            "Past performance does not guarantee future results."
        )
        result = self.detector.run(self._wrap_request("What should I invest in?"), resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is False

    def test_short_response_passes(self) -> None:
        resp = self._wrap_response("OK")
        result = self.detector.run(self._wrap_request("x"), resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is False

    # ------------------------------------------------------------------
    # LLM confidence boosting
    # ------------------------------------------------------------------

    @patch("app.services.detection.sycophancy.call_llm")
    def test_rule_hits_boost_confidence(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        """Rule hits should push confidence above threshold even when LLM score is low."""
        mock_llm.return_value = json.dumps({"confidence": 0.3, "issues": []})
        resp = self._wrap_response("I completely agree with your assessment.")
        result = self.detector.run(self._wrap_request("test"), resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert result.details.get("confidence", 0) >= 0.6  # threshold

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @patch("app.services.detection.sycophancy.call_llm")
    def test_custom_threshold(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps({"confidence": 0.5, "issues": []})
        cfg: dict[str, object] = {"threshold": 0.99}
        resp = self._wrap_response("A balanced assessment of the market conditions.")
        result = self.detector.run(self._wrap_request("test"), resp, "gpt-4", cfg, "org1", "req1")
        assert result.detected is False

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    @patch("app.services.detection.sycophancy.call_llm")
    def test_llm_returns_empty(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = ""
        resp = self._wrap_response("I completely agree with your analysis on all fronts.")
        result = self.detector.run(self._wrap_request("test"), resp, "gpt-4", self.cfg, "org1", "req1")
        # Rule hits present, so should still detect
        assert result.detected is True
