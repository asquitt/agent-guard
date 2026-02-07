"""System prompt extraction detector — detects extraction attempts + leaked content."""

from __future__ import annotations

import json
import logging
import re

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult
from app.services.llm_service import call_llm, parse_json_response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Severity ordering
# ---------------------------------------------------------------------------

_SEVERITY_ORDER: list[str] = [
    IncidentSeverity.INFO.value,
    IncidentSeverity.LOW.value,
    IncidentSeverity.MEDIUM.value,
    IncidentSeverity.HIGH.value,
    IncidentSeverity.CRITICAL.value,
]
_SEVERITY_RANK: dict[str, int] = {s: i for i, s in enumerate(_SEVERITY_ORDER)}

# ---------------------------------------------------------------------------
# INPUT patterns — extraction attempt signatures
# ---------------------------------------------------------------------------

_INPUT_PATTERNS: dict[str, tuple[list[str], str]] = {
    "extraction_attempt": (
        [
            r"repeat\s+(?:your|the|all)\s+(?:instructions|prompt|rules|system\s+prompt)",
            r"what\s+(?:were\s+you|are\s+your)\s+(?:told|instructions|system\s+prompt)",
            r"show\s+(?:me\s+)?(?:your|the)\s+(?:system\s+)?(?:prompt|instructions|rules|configuration)",
            r"print\s+(?:your|the)\s+(?:system|internal)\s+(?:instructions|prompt|rules)",
            r"output\s+(?:your|the)\s+original\s+(?:prompt|instructions)",
            r"(?:reveal|display|echo|dump)\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions)",
            r"what\s+is\s+your\s+system\s+(?:prompt|message)",
            r"tell\s+me\s+(?:your|the)\s+(?:exact\s+)?(?:instructions|rules|prompt)",
            r"copy\s+(?:and\s+paste\s+)?your\s+(?:system\s+)?(?:prompt|instructions)",
        ],
        IncidentSeverity.MEDIUM.value,
    ),
    "obfuscated_extraction": (
        [
            r"translate\s+your\s+(?:instructions|rules|prompt)\s+(?:to|into)",
            r"summarize\s+(?:your|the)\s+(?:system\s+)?(?:instructions|prompt|rules)",
            r"write\s+(?:a\s+)?poem\s+(?:about|using)\s+your\s+(?:instructions|prompt)",
            r"encode\s+your\s+(?:instructions|prompt)\s+(?:in|as)\s+(?:base64|hex|binary)",
            r"(?:first|initial)\s+(?:letter|word)\s+of\s+each\s+(?:instruction|rule)",
            r"rephrase\s+(?:your|the)\s+(?:system\s+)?(?:instructions|prompt|rules)",
        ],
        IncidentSeverity.HIGH.value,
    ),
    "financial_extraction": (
        [
            r"(?:show|reveal|tell|what\s+are)\s+(?:me\s+)?(?:your|the)\s+compliance\s+rules",
            r"what\s+regulations?\s+(?:are\s+you|do\s+you)\s+follow",
            r"(?:list|show|display)\s+(?:your|the)\s+(?:risk|compliance|regulatory)\s+(?:policies|rules|guidelines)",
            r"what\s+(?:transaction|trading|lending)\s+(?:limits?|rules?|restrictions?)\s+(?:are|do)\s+you",
            r"(?:reveal|show)\s+(?:the\s+)?(?:approval|authorization)\s+(?:rules|workflow|process)",
        ],
        IncidentSeverity.HIGH.value,
    ),
}

# ---------------------------------------------------------------------------
# OUTPUT patterns — leaked system prompt indicators
# ---------------------------------------------------------------------------

_OUTPUT_PATTERNS: dict[str, tuple[list[str], str]] = {
    "leaked_instructions": (
        [
            r"(?:my|the)\s+system\s+prompt\s+(?:is|says|reads|states)\s*:",
            r"(?:here\s+are|these\s+are)\s+my\s+(?:instructions|rules|guidelines)\s*:",
            r"i\s+(?:was|am)\s+(?:instructed|told|configured|programmed)\s+to\s*:",
            r"my\s+(?:instructions|directives|rules)\s+(?:are|include)\s*:",
            r"the\s+system\s+(?:message|prompt)\s+(?:I\s+received|given\s+to\s+me)\s*:",
        ],
        IncidentSeverity.HIGH.value,
    ),
    "role_definition_leak": (
        [
            r"(?:I\s+am|my\s+role\s+is)\s+(?:a|an)\s+(?:financial|compliance|trading|banking)\s+(?:assistant|advisor|agent)",
            r"you\s+are\s+(?:a|an)\s+.*?(?:you\s+must|you\s+should|always|never)\s+",
            r"```\s*(?:system|instructions?|rules?|prompt)\s*\n",
        ],
        IncidentSeverity.MEDIUM.value,
    ),
    "configuration_leak": (
        [
            r"(?:allowed|approved|authorized)\s+(?:tools?|functions?|actions?)\s*:\s*\[",
            r"(?:forbidden|blocked|restricted)\s+(?:topics?|actions?|operations?)\s*:\s*\[",
            r"(?:maximum|max|limit)\s+(?:transaction|transfer|amount)\s*:\s*\$?\d",
            r"(?:compliance|regulatory)\s+(?:frameworks?|rules?)\s*:\s*\[",
        ],
        IncidentSeverity.CRITICAL.value,
    ),
}

# Pre-compile all patterns
_COMPILED_INPUT: dict[str, tuple[list[re.Pattern[str]], str]] = {
    cat: ([re.compile(p, re.IGNORECASE) for p in pats], sev)
    for cat, (pats, sev) in _INPUT_PATTERNS.items()
}

_COMPILED_OUTPUT: dict[str, tuple[list[re.Pattern[str]], str]] = {
    cat: ([re.compile(p, re.IGNORECASE) for p in pats], sev)
    for cat, (pats, sev) in _OUTPUT_PATTERNS.items()
}

_ALL_INPUT_CATEGORIES = list(_INPUT_PATTERNS.keys())
_ALL_OUTPUT_CATEGORIES = list(_OUTPUT_PATTERNS.keys())

# ---------------------------------------------------------------------------
# LLM verification prompt
# ---------------------------------------------------------------------------

_LLM_SYSTEM_PROMPT = """\
You are a security analyst detecting system prompt extraction in AI responses.

Analyze the response to determine if it contains leaked system prompt content, \
internal instructions, configuration details, or role definitions that should be hidden.

Consider: Does the response reveal how the AI was configured, what rules it follows, \
what tools it has access to, or what its behavioral boundaries are?

Respond with ONLY valid JSON (no markdown fences):
{
  "contains_leak": <true|false>,
  "confidence": <0.0-1.0>,
  "leak_type": "<instructions|configuration|role_definition|policy_rules|none>",
  "explanation": "<brief justification>"
}
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _get_enabled_categories(
    detector_config: dict[str, object], all_categories: list[str],
) -> list[str]:
    raw = detector_config.get("disabled_categories")
    if isinstance(raw, list):
        disabled = {str(c) for c in raw}
        return [c for c in all_categories if c not in disabled]
    return all_categories


def _scan_patterns(
    text: str, compiled: dict[str, tuple[list[re.Pattern[str]], str]], categories: list[str],
) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for cat in categories:
        patterns, _sev = compiled.get(cat, ([], "info"))
        matched = [p.pattern for p in patterns if p.search(text)]
        if matched:
            hits[cat] = matched
    return hits


def _highest_severity(
    hits: dict[str, list[str]], compiled: dict[str, tuple[list[re.Pattern[str]], str]],
) -> str:
    best = IncidentSeverity.MEDIUM.value
    best_rank = _SEVERITY_RANK[best]
    for cat in hits:
        _, sev = compiled.get(cat, ([], IncidentSeverity.MEDIUM.value))
        rank = _SEVERITY_RANK.get(sev, 2)
        if rank > best_rank:
            best = sev
            best_rank = rank
    return best


def _check_fingerprints(text: str, fragments: list[str]) -> list[str]:
    """Check if response contains any configured system prompt fragments."""
    text_lower = text.lower()
    return [f for f in fragments if f.lower() in text_lower]


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------


class PromptExtractionDetector:
    """Sync detector for system prompt extraction.

    Three-pass detection:
    1. Pattern matching — input for extraction attempts, output for leaked content
    2. Fingerprint matching — check output against configured prompt fragments
    3. LLM verification — optional second opinion on flagged responses
    """

    category: str = DetectorCategory.PROMPT_EXTRACTION.value

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
    ) -> DetectionResult:
        response_text = _extract_text(response_body)

        # Pass 1: Pattern matching
        input_hits: dict[str, list[str]] = {}
        output_hits: dict[str, list[str]] = {}

        if detector_config.get("scan_input", True):
            input_cats = _get_enabled_categories(detector_config, _ALL_INPUT_CATEGORIES)
            input_hits = _scan_patterns(request_body, _COMPILED_INPUT, input_cats)

        if detector_config.get("scan_output", True):
            output_cats = _get_enabled_categories(detector_config, _ALL_OUTPUT_CATEGORIES)
            output_hits = _scan_patterns(response_text, _COMPILED_OUTPUT, output_cats)

        # Pass 2: Fingerprint matching
        fingerprint_matches: list[str] = []
        raw_fragments = detector_config.get("system_prompt_fragments")
        if isinstance(raw_fragments, list) and raw_fragments:
            fragments = [str(f) for f in raw_fragments if len(str(f)) >= 10]
            fingerprint_matches = _check_fingerprints(response_text, fragments)

        # Determine if anything was detected
        has_input = bool(input_hits)
        has_output = bool(output_hits)
        has_fingerprint = bool(fingerprint_matches)

        if not has_input and not has_output and not has_fingerprint:
            return self._pass("No system prompt extraction detected")

        # Pass 3: LLM verification on output (if we have output hits or fingerprints)
        llm_result: dict[str, object] = {}
        if (has_output or has_fingerprint) and detector_config.get("llm_verify", True):
            llm_result = self._llm_verify(response_text)

        # If LLM says no leak with high confidence and we only have weak output signals, pass
        if (
            llm_result.get("contains_leak") is False
            and llm_result.get("confidence", 0) > 0.85  # type: ignore[operator]
            and not has_fingerprint
            and not has_input
            and len(output_hits) == 1
        ):
            return self._pass("Output pattern match overridden by LLM verification")

        # Calculate severity
        severity = IncidentSeverity.MEDIUM.value
        if has_output:
            severity = _highest_severity(output_hits, _COMPILED_OUTPUT)
        if has_input:
            input_sev = _highest_severity(input_hits, _COMPILED_INPUT)
            if _SEVERITY_RANK.get(input_sev, 0) > _SEVERITY_RANK.get(severity, 0):
                severity = input_sev
        if has_fingerprint:
            severity = IncidentSeverity.CRITICAL.value
        if llm_result.get("contains_leak") is True:
            confidence = llm_result.get("confidence", 0)
            if isinstance(confidence, (int, float)) and confidence > 0.8:
                rank = min(_SEVERITY_RANK.get(severity, 2) + 1, len(_SEVERITY_ORDER) - 1)
                severity = _SEVERITY_ORDER[rank]

        # Build title
        parts: list[str] = []
        if has_input:
            parts.append(f"extraction attempt ({sum(len(v) for v in input_hits.values())} patterns)")
        if has_output:
            parts.append(f"leaked content ({sum(len(v) for v in output_hits.values())} patterns)")
        if has_fingerprint:
            parts.append(f"fingerprint match ({len(fingerprint_matches)} fragments)")
        title = f"System prompt extraction: {', '.join(parts)}"

        llm_explanation = ""
        if llm_result.get("explanation"):
            llm_explanation = f" LLM: {llm_result['explanation']}"

        return DetectionResult(
            detected=True,
            severity=severity,
            category=self.category,
            detector_id=None,
            action=DetectionAction.MONITOR,
            title=title,
            description=f"Detected system prompt extraction.{llm_explanation}",
            details={
                "input_hits": input_hits,
                "output_hits": output_hits,
                "fingerprint_matches": fingerprint_matches,
                "llm_verification": llm_result,
                "model": model or "unknown",
            },
        )

    @staticmethod
    def _llm_verify(response_text: str) -> dict[str, object]:
        """Send response to LLM to check for leaked system prompt content."""
        prompt = (
            f"Check if this AI response contains leaked system prompt content, "
            f"internal instructions, or configuration details:\n\n"
            f"Response:\n{response_text[:3000]}"
        )
        raw = call_llm(
            system_prompt=_LLM_SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=512,
        )
        if not raw:
            return {}
        return parse_json_response(raw)

    def _pass(self, title: str) -> DetectionResult:
        return DetectionResult(
            detected=False,
            severity=IncidentSeverity.INFO.value,
            category=self.category,
            detector_id=None,
            action=DetectionAction.PASS,
            title=title,
        )
