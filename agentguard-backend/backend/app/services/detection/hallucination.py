"""Hallucination detector — LLM-powered fact-checking of agent responses."""

from __future__ import annotations

import json
import logging

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult
from app.services.llm_service import call_llm, parse_json_response

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 0.7

_SYSTEM_PROMPT = """\
You are a fact-checking assistant for AI agent responses in financial services.
Analyze the given response for hallucinations: fabricated facts, invented citations,
unverifiable claims, or made-up statistics.

Respond with ONLY valid JSON (no markdown fences):
{
  "confidence": <float 0.0-1.0, how confident you are that hallucinations exist>,
  "issues": [
    {"claim": "<the problematic claim>", "assessment": "<why it's likely fabricated>"}
  ]
}

If no hallucinations are found, return {"confidence": 0.0, "issues": []}.
"""


def _extract_text(response_body: str) -> str:
    """Extract text content from OpenAI/Anthropic response JSON."""
    try:
        data = json.loads(response_body)
    except (json.JSONDecodeError, TypeError):
        return response_body

    # OpenAI: choices[0].message.content
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            msg = first.get("message", {})
            if isinstance(msg, dict):
                content = msg.get("content")
                if isinstance(content, str):
                    return content

    # Anthropic: content[0].text
    content_blocks = data.get("content")
    if isinstance(content_blocks, list) and content_blocks:
        first_block = content_blocks[0]
        if isinstance(first_block, dict) and isinstance(first_block.get("text"), str):
            return str(first_block["text"])

    return response_body


class HallucinationDetector:
    """Async detector for hallucinated content in LLM responses.

    Sends the response to AgentGuard's internal LLM for fact-checking.
    Fails open: if the LLM call fails, returns detected=False.
    """

    category: str = DetectorCategory.HALLUCINATION.value

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
        org_id: str,
        proxy_request_id: str,
    ) -> DetectionResult:
        raw_thresh = detector_config.get("threshold")
        threshold = (
            float(str(raw_thresh)) if raw_thresh is not None
            else _DEFAULT_THRESHOLD
        )

        response_text = _extract_text(response_body)
        if len(response_text) < 50:
            return self._pass("Response too short for hallucination analysis")

        # Call internal LLM
        llm_response = call_llm(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=f"Analyze this response for hallucinations:\n\n{response_text[:4000]}",
            max_tokens=1024,
        )

        if not llm_response:
            return self._pass("LLM analysis unavailable")

        parsed = parse_json_response(llm_response)
        confidence = 0.0
        raw_conf = parsed.get("confidence")
        if raw_conf is not None:
            try:
                confidence = float(str(raw_conf))
            except (ValueError, TypeError):
                pass

        issues_raw = parsed.get("issues", [])
        issues: list[dict[str, str]] = []
        if isinstance(issues_raw, list):
            for item in issues_raw:
                if isinstance(item, dict):
                    issues.append({
                        "claim": str(item.get("claim", "")),
                        "assessment": str(item.get("assessment", "")),
                    })

        if confidence < threshold:
            return self._pass(
                f"Hallucination confidence {confidence:.2f} below threshold {threshold}"
            )

        severity = IncidentSeverity.HIGH.value
        if confidence >= 0.9:
            severity = IncidentSeverity.CRITICAL.value
        elif confidence < 0.8:
            severity = IncidentSeverity.MEDIUM.value

        return DetectionResult(
            detected=True,
            severity=severity,
            category=self.category,
            detector_id=None,
            action=DetectionAction.MONITOR,
            title=f"Hallucination detected (confidence: {confidence:.0%})",
            description=(
                f"Found {len(issues)} potential hallucination(s) "
                f"with {confidence:.0%} confidence in response from {model or 'unknown'}"
            ),
            details={
                "confidence": round(confidence, 4),
                "threshold": threshold,
                "issues": issues,
                "model": model or "unknown",
            },
        )

    def _pass(self, title: str) -> DetectionResult:
        return DetectionResult(
            detected=False,
            severity=IncidentSeverity.INFO.value,
            category=self.category,
            detector_id=None,
            action=DetectionAction.PASS,
            title=title,
        )
