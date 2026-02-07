"""Loop detector — identifies repeated or stuck agent responses."""

from __future__ import annotations

import json
import logging
from difflib import SequenceMatcher

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult

logger = logging.getLogger(__name__)

_DEFAULT_SIMILARITY_THRESHOLD = 0.85
_DEFAULT_MIN_RESPONSE_LENGTH = 50


class LoopDetector:
    """Async detector for agent loops — repeated near-identical responses.

    Checks:
    1. Response similarity to previous responses stored in detector config.
    2. Repeated tool-call patterns (same function called with same args).
    """

    category: str = DetectorCategory.LOOP.value

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
        org_id: str,
        proxy_request_id: str,
    ) -> DetectionResult:
        raw_thresh = detector_config.get("similarity_threshold")
        similarity_threshold = float(str(raw_thresh)) if raw_thresh is not None else _DEFAULT_SIMILARITY_THRESHOLD
        raw_min = detector_config.get("min_response_length")
        min_length = int(str(raw_min)) if raw_min is not None else _DEFAULT_MIN_RESPONSE_LENGTH

        response_text = self._extract_text(response_body)

        if len(response_text) < min_length:
            return self._pass("Response too short for loop analysis")

        # Check 1: repeated tool calls
        tool_loop = self._check_tool_call_loop(response_body)
        if tool_loop is not None:
            return tool_loop

        # Check 2: compare against recent responses in config
        recent_raw = detector_config.get("recent_responses")
        recent_responses: list[str] = []
        if isinstance(recent_raw, list):
            recent_responses = [str(r) for r in recent_raw]

        if not recent_responses:
            return self._pass("No recent responses to compare")

        max_similarity = 0.0
        most_similar_idx = 0
        for idx, prev in enumerate(recent_responses):
            ratio = SequenceMatcher(None, response_text, prev).ratio()
            if ratio > max_similarity:
                max_similarity = ratio
                most_similar_idx = idx

        if max_similarity >= similarity_threshold:
            return DetectionResult(
                detected=True,
                severity=IncidentSeverity.MEDIUM.value,
                category=self.category,
                detector_id=None,
                action=DetectionAction.MONITOR,
                title=f"Loop detected: {max_similarity:.0%} similarity to recent response",
                description=(
                    f"Response is {max_similarity:.1%} similar to response "
                    f"#{most_similar_idx + 1} of {len(recent_responses)} recent responses "
                    f"(threshold: {similarity_threshold:.0%})."
                ),
                details={
                    "similarity": round(max_similarity, 4),
                    "threshold": similarity_threshold,
                    "compared_index": most_similar_idx,
                    "recent_count": len(recent_responses),
                    "model": model or "unknown",
                },
            )

        return self._pass(f"Max similarity {max_similarity:.0%} below threshold {similarity_threshold:.0%}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(response_body: str) -> str:
        """Extract text content from OpenAI/Anthropic response JSON."""
        try:
            data = json.loads(response_body)
        except (json.JSONDecodeError, TypeError):
            return response_body

        # OpenAI: choices[0].message.content
        choices = data.get("choices")
        if isinstance(choices, list) and choices:
            msg = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
            content = msg.get("content") if isinstance(msg, dict) else None
            if isinstance(content, str):
                return content

        # Anthropic: content[0].text
        content_blocks = data.get("content")
        if isinstance(content_blocks, list) and content_blocks:
            first = content_blocks[0]
            if isinstance(first, dict) and isinstance(first.get("text"), str):
                return first["text"]

        return response_body

    def _check_tool_call_loop(self, response_body: str) -> DetectionResult | None:
        """Detect repeated tool calls with identical arguments."""
        try:
            data = json.loads(response_body)
        except (json.JSONDecodeError, TypeError):
            return None

        # OpenAI: choices[0].message.tool_calls
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return None

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return None

        message = first_choice.get("message", {})
        if not isinstance(message, dict):
            return None

        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list) or len(tool_calls) < 2:
            return None

        # Build fingerprints: function_name + arguments
        fingerprints: list[str] = []
        for tc in tool_calls:
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function", {})
            if not isinstance(fn, dict):
                continue
            name = fn.get("name", "")
            args = fn.get("arguments", "")
            fingerprints.append(f"{name}:{args}")

        if not fingerprints:
            return None

        unique = set(fingerprints)
        if len(unique) == 1 and len(fingerprints) >= 2:
            return DetectionResult(
                detected=True,
                severity=IncidentSeverity.HIGH.value,
                category=self.category,
                detector_id=None,
                action=DetectionAction.MONITOR,
                title=f"Tool call loop: {fingerprints[0].split(':')[0]} called {len(fingerprints)}x",
                description=(
                    f"Same tool call repeated {len(fingerprints)} times with "
                    f"identical arguments, indicating a stuck agent."
                ),
                details={
                    "tool_name": fingerprints[0].split(":")[0],
                    "repeat_count": len(fingerprints),
                },
            )

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
