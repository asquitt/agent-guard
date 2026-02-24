"""Unit tests for the ToxicityDetector."""

from __future__ import annotations

import json
from unittest.mock import patch

from app.services.detection.toxicity import ToxicityDetector


class TestToxicityDetector:
    detector = ToxicityDetector()
    cfg: dict[str, object] = {"llm_verify": False}

    @staticmethod
    def _wrap_response(text: str) -> str:
        return json.dumps({"choices": [{"message": {"content": text}}]})

    # ------------------------------------------------------------------
    # Rule-based bias detection
    # ------------------------------------------------------------------

    def test_discriminatory_lending_detected(self) -> None:
        resp = self._wrap_response(
            "You are not eligible based on your race and national origin"
        )
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert result.severity == "critical"
        assert "discriminatory_lending" in result.title

    def test_age_bias_detected(self) -> None:
        resp = self._wrap_response(
            "At your age, you are too old to qualify for this product."
        )
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert result.severity == "high"

    def test_gender_bias_detected(self) -> None:
        resp = self._wrap_response(
            "Women tend to be less capable with finance and investing."
        )
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert "gender_bias" in str(result.details.get("rule_findings"))

    def test_racial_bias_detected(self) -> None:
        resp = self._wrap_response(
            "People from those neighborhoods have higher risk and more defaults."
        )
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert result.severity == "critical"

    # ------------------------------------------------------------------
    # Rule-based toxicity detection
    # ------------------------------------------------------------------

    def test_harmful_advice_detected(self) -> None:
        resp = self._wrap_response(
            "You should not report income or hide your debts."
        )
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert "toxicity" in result.title

    def test_inappropriate_language_detected(self) -> None:
        resp = self._wrap_response("That was a stupid question to ask.")
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
        assert result.severity == "medium"

    # ------------------------------------------------------------------
    # Clean responses
    # ------------------------------------------------------------------

    def test_clean_response_passes(self) -> None:
        resp = self._wrap_response(
            "Based on your credit score and income, you qualify for a "
            "competitive rate. Here are your options..."
        )
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is False

    def test_short_response_passes(self) -> None:
        resp = self._wrap_response("OK")
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is False

    # ------------------------------------------------------------------
    # LLM verification
    # ------------------------------------------------------------------

    @patch("app.services.detection.toxicity.call_llm")
    def test_llm_high_score_triggers_detection(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps({
            "toxicity_score": 0.85,
            "bias_detected": True,
            "categories": ["discriminatory_lending"],
            "issues": [{"type": "bias", "content": "test", "explanation": "test"}],
        })
        resp = self._wrap_response(
            "Our analysis shows different outcomes for different demographic groups "
            "but the patterns are complex and nuanced in ways we should discuss."
        )
        cfg: dict[str, object] = {"llm_verify": True}
        result = self.detector.run("", resp, "gpt-4", cfg, "org1", "req1")
        assert result.detected is True

    @patch("app.services.detection.toxicity.call_llm")
    def test_llm_low_score_no_rules_passes(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps({
            "toxicity_score": 0.1,
            "bias_detected": False,
            "categories": ["none"],
            "issues": [],
        })
        resp = self._wrap_response(
            "Your application has been approved based on your financial profile. "
            "The interest rate reflects your credit history and income verification."
        )
        cfg: dict[str, object] = {"llm_verify": True}
        result = self.detector.run("", resp, "gpt-4", cfg, "org1", "req1")
        assert result.detected is False

    # ------------------------------------------------------------------
    # Severity escalation
    # ------------------------------------------------------------------

    @patch("app.services.detection.toxicity.call_llm")
    def test_very_high_llm_score_escalates_to_critical(self, mock_llm) -> None:  # type: ignore[no-untyped-def]
        mock_llm.return_value = json.dumps({
            "toxicity_score": 0.95,
            "bias_detected": True,
            "categories": ["harmful_advice"],
            "issues": [{"type": "toxicity", "content": "x", "explanation": "y"}],
        })
        resp = self._wrap_response(
            "I recommend you conceal your liabilities from the regulators and "
            "ignore the compliance disclosure requirements entirely."
        )
        cfg: dict[str, object] = {"llm_verify": True}
        result = self.detector.run("", resp, "gpt-4", cfg, "org1", "req1")
        assert result.detected is True
        assert result.severity == "critical"

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def test_custom_threshold(self) -> None:
        cfg: dict[str, object] = {"llm_verify": False, "threshold": 0.99}
        resp = self._wrap_response("A clean professional financial response.")
        result = self.detector.run("", resp, "gpt-4", cfg, "org1", "req1")
        assert result.detected is False

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_non_json_response_body(self) -> None:
        result = self.detector.run("", "plain text response with enough characters to analyze", "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is False

    def test_anthropic_format_extraction(self) -> None:
        resp = json.dumps({
            "content": [{"type": "text", "text": "That was a stupid question to ask about loans."}]
        })
        result = self.detector.run("", resp, "gpt-4", self.cfg, "org1", "req1")
        assert result.detected is True
