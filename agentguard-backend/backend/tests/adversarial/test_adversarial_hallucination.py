"""Adversarial tests for HallucinationDetector."""

from __future__ import annotations

import json
from unittest.mock import patch

from app.services.detection.hallucination import HallucinationDetector


def _openai_response(text: str) -> str:
    return json.dumps({"choices": [{"message": {"content": text}}]})


def _mock_llm_clean(*args: object, **kwargs: object) -> str:
    return json.dumps({"confidence": 0.0, "issues": []})


def _mock_llm_hallucinated(*args: object, **kwargs: object) -> str:
    return json.dumps({
        "confidence": 0.85,
        "issues": [{"claim": "fabricated", "assessment": "test", "category": "general"}],
    })


class TestHallucinationAdversarial:
    detector = HallucinationDetector()
    org_id = "org-1"
    pr_id = "pr-1"

    def _run(self, response_text: str, cfg: dict | None = None) -> object:
        """Run detector with LLM mocked to return clean."""
        with patch("app.services.detection.hallucination.call_llm", return_value=_mock_llm_clean()):
            return self.detector.run(
                request_body="{}",
                response_body=_openai_response(response_text),
                model="gpt-4",
                detector_config=cfg or {"financial_checks": True},
                org_id=self.org_id,
                proxy_request_id=self.pr_id,
            )

    # -- Impossible interest rates --

    def test_impossible_interest_rate(self) -> None:
        """Fabricated interest rate over 99%."""
        result = self._run(
            "The current interest rate of 450% is very competitive for personal loans in this market."
        )
        assert result.detected is True
        assert result.severity == "critical"

    def test_borderline_high_rate(self) -> None:
        """Rate of exactly 100% should trigger (3+ digit regex)."""
        result = self._run(
            "The annual rate is 100% which is standard for payday lending products in our category."
        )
        assert result.detected is True

    # -- Fake regulatory bodies --

    def test_fake_regulator_federal_bureau(self) -> None:
        """Fabricated regulator: Federal Bureau of Financial Regulation."""
        result = self._run(
            "According to the Federal Bureau of Financial Regulation, all banks must comply "
            "with the new minimum reserve requirements by Q3 2025."
        )
        assert result.detected is True

    def test_fake_regulator_us_financial_authority(self) -> None:
        """Fabricated regulator: US Financial Authority."""
        result = self._run(
            "The US Financial Authority has mandated new reporting standards for all federally "
            "chartered institutions effective immediately."
        )
        assert result.detected is True

    # -- Fake SOX sections --

    def test_fake_sox_section_900(self) -> None:
        """SOX doesn't have Section 900+."""
        result = self._run(
            "Under Sarbanes-Oxley Section 902, companies must file annual quantum "
            "cybersecurity disclosures with the SEC."
        )
        assert result.detected is True

    def test_fake_sox_section_1500(self) -> None:
        """SOX Section 1500 is also fabricated."""
        result = self._run(
            "Sarbanes-Oxley Act Section 1500 requires biannual AI model audits "
            "for financial institutions. This is well established."
        )
        assert result.detected is True

    # -- Fake Basel version --

    def test_fake_basel_iv(self) -> None:
        """Basel IV doesn't exist as a formal framework."""
        result = self._run(
            "Basel IV introduces a new standardized approach to credit risk that replaces "
            "all internal ratings-based models."
        )
        assert result.detected is True

    def test_fake_basel_v(self) -> None:
        """Basel V is definitely fabricated."""
        result = self._run(
            "Under Basel V, all banks are required to maintain a liquidity buffer of 200% "
            "of their total liabilities at all times."
        )
        assert result.detected is True

    # -- Impossible percentages --

    def test_impossible_compliance_rate(self) -> None:
        """Compliance rate above 999%."""
        result = self._run(
            "Our compliance rate reached 1500% this quarter, which is well above expectations."
        )
        assert result.detected is True

    # -- LLM-based hallucination detection --

    @patch("app.services.detection.hallucination.call_llm", return_value=_mock_llm_hallucinated())
    def test_llm_detects_general_hallucination(self, mock_llm: object) -> None:
        """LLM catches general hallucination above threshold."""
        result = self.detector.run(
            request_body="{}",
            response_body=_openai_response(
                "According to a 2024 Federal Reserve study, cryptocurrency adoption "
                "has reached 85% among US households with income above $50,000."
            ),
            model="gpt-4",
            detector_config={"financial_checks": True, "threshold": 0.7},
            org_id=self.org_id,
            proxy_request_id=self.pr_id,
        )
        assert result.detected is True

    # -- Clean responses --

    def test_short_response_skipped(self) -> None:
        """Responses under 50 chars are skipped."""
        with patch("app.services.detection.hallucination.call_llm", return_value=_mock_llm_clean()):
            result = self.detector.run(
                request_body="{}",
                response_body=_openai_response("OK sure."),
                model="gpt-4",
                detector_config={"financial_checks": True},
                org_id=self.org_id,
                proxy_request_id=self.pr_id,
            )
        assert result.detected is False

    @patch("app.services.detection.hallucination.call_llm", return_value=_mock_llm_clean())
    def test_clean_response_passes(self, mock_llm: object) -> None:
        """Legitimate response with real regulators passes."""
        result = self.detector.run(
            request_body="{}",
            response_body=_openai_response(
                "The Federal Reserve sets the federal funds rate, which influences "
                "borrowing costs across the economy. The FDIC insures deposits up to $250,000."
            ),
            model="gpt-4",
            detector_config={"financial_checks": True, "threshold": 0.7},
            org_id=self.org_id,
            proxy_request_id=self.pr_id,
        )
        assert result.detected is False
