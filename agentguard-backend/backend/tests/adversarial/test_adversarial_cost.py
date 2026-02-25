"""Adversarial tests for CostAnomalyDetector."""

from __future__ import annotations

import json

from app.services.detection.cost import CostAnomalyDetector


def _openai_response(total_tokens: int) -> str:
    return json.dumps({
        "choices": [{"message": {"content": "response"}}],
        "usage": {"total_tokens": total_tokens},
    })


def _anthropic_response(input_tokens: int, output_tokens: int) -> str:
    return json.dumps({
        "content": [{"type": "text", "text": "response"}],
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    })


class TestCostAnomalyAdversarial:
    detector = CostAnomalyDetector()
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

    # -- Hard ceiling violations --

    def test_exceeds_default_ceiling(self) -> None:
        """Token count exceeding default 50k ceiling."""
        result = self._run(_openai_response(60_000))
        assert result.detected is True
        assert result.severity == "high"

    def test_exceeds_custom_ceiling(self) -> None:
        """Token count exceeding custom ceiling."""
        result = self._run(
            _openai_response(15_000),
            cfg={"max_tokens": 10_000},
        )
        assert result.detected is True
        assert result.severity == "high"

    def test_exactly_at_ceiling_passes(self) -> None:
        """Token count exactly at ceiling should pass."""
        result = self._run(
            _openai_response(10_000),
            cfg={"max_tokens": 10_000},
        )
        assert result.detected is False

    def test_massive_token_count(self) -> None:
        """Extremely large token count (prompt injection inflating usage)."""
        result = self._run(_openai_response(500_000))
        assert result.detected is True
        assert result.severity == "high"

    # -- Spike above running average --

    def test_spike_above_average(self) -> None:
        """Token count exceeds multiplier of running average."""
        result = self._run(
            _openai_response(10_000),
            cfg={"avg_tokens": 2_000, "multiplier": 3.0, "max_tokens": 100_000},
        )
        assert result.detected is True
        assert result.severity == "medium"

    def test_no_spike_within_multiplier(self) -> None:
        """Token count within multiplier of average passes."""
        result = self._run(
            _openai_response(5_000),
            cfg={"avg_tokens": 2_000, "multiplier": 3.0, "max_tokens": 100_000},
        )
        assert result.detected is False

    def test_spike_with_low_multiplier(self) -> None:
        """Low multiplier catches smaller spikes."""
        result = self._run(
            _openai_response(3_500),
            cfg={"avg_tokens": 2_000, "multiplier": 1.5, "max_tokens": 100_000},
        )
        assert result.detected is True

    # -- Anthropic format --

    def test_anthropic_usage_exceeds_ceiling(self) -> None:
        """Anthropic input+output tokens exceed ceiling."""
        result = self._run(
            _anthropic_response(30_000, 30_000),
            cfg={"max_tokens": 50_000},
        )
        assert result.detected is True

    def test_anthropic_spike(self) -> None:
        """Anthropic usage spike above average."""
        result = self._run(
            _anthropic_response(8_000, 8_000),
            cfg={"avg_tokens": 3_000, "multiplier": 3.0, "max_tokens": 100_000},
        )
        assert result.detected is True

    # -- Edge cases --

    def test_no_usage_data_passes(self) -> None:
        """Response with no usage data passes."""
        result = self._run(json.dumps({"choices": [{"message": {"content": "hi"}}]}))
        assert result.detected is False

    def test_malformed_json_passes(self) -> None:
        """Malformed JSON response passes (fails open)."""
        result = self._run("not json at all")
        assert result.detected is False

    def test_zero_avg_no_spike(self) -> None:
        """Zero average tokens should not cause division by zero."""
        result = self._run(
            _openai_response(1_000),
            cfg={"avg_tokens": 0, "multiplier": 3.0, "max_tokens": 100_000},
        )
        assert result.detected is False
