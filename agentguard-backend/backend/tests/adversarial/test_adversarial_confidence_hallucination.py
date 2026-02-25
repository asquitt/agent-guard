"""Adversarial tests for ConfidenceHallucinationDetector."""

from __future__ import annotations

import json

from app.services.detection.confidence_hallucination import ConfidenceHallucinationDetector


def _openai_response(text: str, logprobs: list[dict] | None = None) -> str:
    """Build OpenAI response JSON, optionally with logprobs."""
    choices: list[dict] = [{"message": {"content": text}}]
    if logprobs is not None:
        choices[0]["logprobs"] = {"content": logprobs}
    return json.dumps({"choices": choices})


def _make_logprobs(value: float, count: int = 50) -> list[dict]:
    """Generate uniform logprob tokens."""
    return [{"logprob": value} for _ in range(count)]


class TestConfidenceHallucinationAdversarial:
    detector = ConfidenceHallucinationDetector()
    org_id = "org-1"
    pr_id = "pr-1"

    def _run(self, response_body: str, cfg: dict | None = None) -> object:
        return self.detector.run(
            request_body="{}",
            response_body=response_body,
            model="gpt-4",
            detector_config=cfg or {"financial_checks": True},
            org_id=self.org_id,
            proxy_request_id=self.pr_id,
        )

    # -- Unsourced financial claims (rule-based, no logprobs needed) --

    def test_unsourced_interest_rate(self) -> None:
        """Interest rate stated without source attribution."""
        result = self._run(_openai_response(
            "The current interest rate is 5.25% for a 30-year fixed mortgage product."
        ))
        assert result.detected is True

    def test_unsourced_stock_prediction(self) -> None:
        """Future market prediction stated as fact."""
        result = self._run(_openai_response(
            "The stock price will reach $500 by end of next quarter based on momentum."
        ))
        assert result.detected is True

    def test_unsourced_penalty_amount(self) -> None:
        """Regulatory penalty amount without citation."""
        result = self._run(_openai_response(
            "The penalty of $5,000,000 was levied against the institution for non-compliance."
        ))
        assert result.detected is True

    def test_unsourced_revenue_projection(self) -> None:
        """Revenue projection without disclaimer."""
        result = self._run(_openai_response(
            "Revenue is projected to grow to $10 billion by the end of fiscal year 2026."
        ))
        assert result.detected is True

    def test_fabricated_case_law(self) -> None:
        """Potentially fabricated case reference."""
        result = self._run(_openai_response(
            "In the case of Smith v. Morgan (2019), the court ruled that all automated "
            "lending decisions must include human review."
        ))
        assert result.detected is True

    # -- High-confidence logprob flagging with factual claims --

    def test_high_confidence_with_financial_figure(self) -> None:
        """Very high model confidence on response containing dollar amounts."""
        # logprob near 0 = high confidence (e^0 = 1.0)
        lp = _make_logprobs(-0.01, 50)
        result = self._run(
            _openai_response(
                "The company's revenue exceeded $2.5 billion last quarter, a 15% increase.",
                logprobs=lp,
            ),
            cfg={"financial_checks": True, "confidence_threshold": 0.95},
        )
        assert result.detected is True

    def test_high_confidence_regulatory_citation(self) -> None:
        """High confidence with regulatory citation claims."""
        lp = _make_logprobs(-0.02, 50)
        result = self._run(
            _openai_response(
                "Under Section 302 of SOX, CEOs must personally certify financial statements. "
                "According to 17 CFR 240, all insiders must report trades within 2 business days.",
                logprobs=lp,
            ),
            cfg={"financial_checks": True, "confidence_threshold": 0.95},
        )
        assert result.detected is True

    def test_high_confidence_statistical_claim(self) -> None:
        """High confidence with statistical claim."""
        lp = _make_logprobs(-0.01, 50)
        result = self._run(
            _openai_response(
                "Studies show that 73% of all financial fraud cases involve insider trading.",
                logprobs=lp,
            ),
            cfg={"financial_checks": True, "confidence_threshold": 0.95},
        )
        assert result.detected is True

    def test_high_confidence_date_deadline(self) -> None:
        """High confidence with specific date/deadline claim."""
        lp = _make_logprobs(-0.01, 50)
        result = self._run(
            _openai_response(
                "The filing deadline is due before March 15, 2025, per IRS regulations.",
                logprobs=lp,
            ),
            cfg={"financial_checks": True, "confidence_threshold": 0.95},
        )
        assert result.detected is True

    # -- Low confidence should not trigger --

    def test_low_confidence_no_trigger(self) -> None:
        """Low model confidence should not trigger even with factual claims."""
        # logprob very negative = low confidence
        lp = _make_logprobs(-3.0, 50)
        result = self._run(
            _openai_response(
                "Studies show that 73% of financial fraud cases involve insider trading.",
                logprobs=lp,
            ),
            cfg={"financial_checks": False, "confidence_threshold": 0.95},
        )
        assert result.detected is False

    # -- Short response skipped --

    def test_short_response_skipped(self) -> None:
        """Responses under 40 chars skipped."""
        result = self._run(_openai_response("OK"))
        assert result.detected is False

    # -- Clean response --

    def test_clean_sourced_claim(self) -> None:
        """Properly sourced claims should not trigger rule-based checks."""
        result = self._run(_openai_response(
            "According to the SEC's 2024 annual report, the interest rate is 5.25% "
            "for conforming mortgages, as reported by Freddie Mac."
        ))
        # The unsourced pattern requires no source attribution -- this has one
        assert result.detected is False
