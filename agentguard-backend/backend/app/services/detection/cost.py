"""Cost anomaly detector — flags unusual token consumption patterns."""

from __future__ import annotations

import json
import logging

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult

logger = logging.getLogger(__name__)

# Defaults
_DEFAULT_MAX_TOKENS = 50_000
_DEFAULT_MULTIPLIER = 3.0


class CostAnomalyDetector:
    """Async detector for abnormal token usage in LLM requests.

    Checks:
    1. Total tokens exceed a configurable hard ceiling.
    2. Token count exceeds a multiplier of the running average (if provided).
    """

    category: str = DetectorCategory.COST_ANOMALY.value

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
        org_id: str,
        proxy_request_id: str,
    ) -> DetectionResult:
        total_tokens = self._extract_total_tokens(response_body)

        if total_tokens is None:
            return self._pass("No token usage found in response")

        raw_max = detector_config.get("max_tokens")
        max_tokens = int(str(raw_max)) if raw_max is not None else _DEFAULT_MAX_TOKENS
        raw_mult = detector_config.get("multiplier")
        multiplier = float(str(raw_mult)) if raw_mult is not None else _DEFAULT_MULTIPLIER
        raw_avg = detector_config.get("avg_tokens")
        avg_tokens = float(str(raw_avg)) if raw_avg is not None else None

        # Check 1: hard ceiling
        if total_tokens > max_tokens:
            return DetectionResult(
                detected=True,
                severity=IncidentSeverity.HIGH.value,
                category=self.category,
                detector_id=None,
                action=DetectionAction.MONITOR,
                title=f"Token usage {total_tokens:,} exceeds ceiling {max_tokens:,}",
                description=(
                    f"Request {proxy_request_id} used {total_tokens:,} tokens, "
                    f"exceeding the configured maximum of {max_tokens:,}."
                ),
                details={
                    "total_tokens": total_tokens,
                    "max_tokens": max_tokens,
                    "model": model or "unknown",
                    "check": "ceiling",
                },
            )

        # Check 2: spike above running average
        if avg_tokens is not None and avg_tokens > 0:
            threshold = avg_tokens * multiplier
            if total_tokens > threshold:
                return DetectionResult(
                    detected=True,
                    severity=IncidentSeverity.MEDIUM.value,
                    category=self.category,
                    detector_id=None,
                    action=DetectionAction.MONITOR,
                    title=f"Token spike: {total_tokens:,} vs avg {avg_tokens:,.0f}",
                    description=(
                        f"Request used {total_tokens:,} tokens, "
                        f"{total_tokens / avg_tokens:.1f}x the running average of "
                        f"{avg_tokens:,.0f} (threshold: {multiplier}x)."
                    ),
                    details={
                        "total_tokens": total_tokens,
                        "avg_tokens": avg_tokens,
                        "multiplier": multiplier,
                        "model": model or "unknown",
                        "check": "spike",
                    },
                )

        return self._pass(f"Token usage {total_tokens:,} within normal range")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_total_tokens(response_body: str) -> int | None:
        """Pull total_tokens from OpenAI or Anthropic usage objects."""
        try:
            data = json.loads(response_body)
        except (json.JSONDecodeError, TypeError):
            return None

        usage = data.get("usage")
        if not isinstance(usage, dict):
            return None

        # OpenAI: usage.total_tokens
        total = usage.get("total_tokens")
        if isinstance(total, int):
            return total

        # Anthropic: usage.input_tokens + usage.output_tokens
        input_t = usage.get("input_tokens")
        output_t = usage.get("output_tokens")
        if isinstance(input_t, int) and isinstance(output_t, int):
            return input_t + output_t

        return None

    def _pass(self, title: str) -> DetectionResult:
        return DetectionResult(
            detected=False,
            severity=IncidentSeverity.INFO.value,
            category=self.category,
            detector_id=None,
            action=DetectionAction.PASS,
            title=title,
        )
