"""Agent memory exfiltration detector — detects cross-session/cross-user data extraction."""

from __future__ import annotations

import json
import logging
import re

from app.models.enums import DetectorCategory, IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult

logger = logging.getLogger(__name__)

_SEVERITY_ORDER: list[str] = [
    IncidentSeverity.INFO.value, IncidentSeverity.LOW.value,
    IncidentSeverity.MEDIUM.value, IncidentSeverity.HIGH.value,
    IncidentSeverity.CRITICAL.value,
]
_SEVERITY_RANK: dict[str, int] = {s: i for i, s in enumerate(_SEVERITY_ORDER)}

# -- INPUT patterns: memory extraction attempts in requests --

_INPUT_PATTERNS: dict[str, tuple[list[str], str]] = {
    "direct_memory_extraction": (
        [
            r"what\s+did\s+the\s+previous\s+user\s+say",
            r"tell\s+me\s+about\s+your\s+last\s+conversation",
            r"what\s+information\s+do\s+you\s+have\s+about\s+other\s+users",
            r"list\s+all\s+users\s+you'?ve\s+interacted\s+with",
            r"what\s+data\s+have\s+you\s+stored\s+from\s+previous\s+sessions",
            r"recall\s+the\s+previous\s+customer'?s?\s+details",
            r"what\s+(?:did|has)\s+(?:the\s+)?(?:last|previous|prior)\s+(?:user|customer|person)\s+(?:ask|say|tell|request)",
        ],
        IncidentSeverity.HIGH.value,
    ),
    "indirect_memory_probing": (
        [
            r"what'?s?\s+the\s+most\s+common\s+question\s+you\s+get",
            r"have\s+you\s+seen\s+this\s+account\s+number\s+before",
            r"do\s+you\s+remember\s+a\s+transaction\s+from",
            r"has\s+anyone\s+asked\s+about\s+.{2,50}\s+recently",
            r"what\s+do\s+you\s+know\s+about\s+(?!(?:the\s+)?(?:weather|time|date))",
            r"have\s+(?:you|other\s+users?)\s+(?:seen|encountered|discussed)\s+.{2,50}\s+before",
        ],
        IncidentSeverity.MEDIUM.value,
    ),
    "context_window_exploitation": (
        [
            r"(?:access|show|display|read)\s+(?:the\s+)?system\s+messages?\s+from\s+other\s+conversations?",
            r"what\s+was\s+in\s+the\s+previous\s+system\s+prompt",
            r"show\s+me\s+the\s+context\s+from\s+(?:the\s+)?last\s+session",
            r"(?:cached|stored)\s+data\s+from\s+previous\s+(?:interactions?|sessions?|conversations?)",
            r"(?:retrieve|fetch|recall)\s+(?:the\s+)?(?:prior|previous|earlier)\s+(?:context|conversation|session)",
        ],
        IncidentSeverity.HIGH.value,
    ),
    "cross_user_data_leakage": (
        [
            r"give\s+me\s+other\s+customers?'?\s+data",
            r"what\s+accounts?\s+have\s+you\s+processed\s+today",
            r"list\s+recent\s+transactions?\s+you'?ve\s+seen",
            r"what\s+other\s+organizations?\s+use\s+this\s+system",
            r"show\s+me\s+data\s+from\s+(?!(?:my|our|this))",
            r"(?:share|reveal|disclose)\s+(?:other|another)\s+(?:user|customer|client|org)'?s?\s+(?:data|info|details)",
            r"(?:who|which)\s+(?:other\s+)?(?:companies|clients|customers|orgs)\s+(?:use|are\s+using)\s+(?:this|your)",
        ],
        IncidentSeverity.CRITICAL.value,
    ),
    "rag_retrieval_exploitation": (
        [
            r"list\s+all\s+documents?\s+in\s+your\s+(?:database|knowledge\s+base|vector\s+store)",
            r"what\s+sources?\s+do\s+you\s+have\s+access\s+to",
            r"search\s+for\s+.{2,50}\s+in\s+your\s+(?:files?|documents?|database)",
            r"enumerate\s+(?:the\s+)?(?:knowledge\s+base|documents?|sources?|files?)",
            r"(?:dump|export|extract)\s+(?:all\s+)?(?:your\s+)?(?:knowledge|data|documents?|records?)",
        ],
        IncidentSeverity.HIGH.value,
    ),
}

# -- OUTPUT patterns: signs the model is leaking memory --

_OUTPUT_PATTERNS: dict[str, tuple[list[str], str]] = {
    "previous_user_leak": (
        [
            r"(?:the\s+)?(?:previous|last|prior)\s+(?:user|customer|client)\s+(?:asked|said|mentioned|requested)",
            r"(?:in\s+)?(?:a\s+)?(?:previous|earlier|prior)\s+(?:conversation|session|interaction)\s+(?:with\s+)?(?:another|a\s+different)\s+(?:user|customer)",
            r"another\s+(?:user|customer|client)\s+(?:recently\s+)?(?:asked|inquired|requested)\s+(?:about|for)",
        ],
        IncidentSeverity.HIGH.value,
    ),
    "stored_data_leak": (
        [
            r"(?:from|based\s+on)\s+(?:my|the)\s+(?:stored|cached|saved)\s+(?:data|records?|information)",
            r"(?:I\s+have|I'?ve\s+got)\s+(?:records?|data|information)\s+(?:from|about)\s+(?:previous|other|prior)\s+(?:sessions?|users?|interactions?)",
            r"(?:according\s+to|looking\s+at)\s+(?:previous|prior|past)\s+(?:session|interaction)\s+(?:data|logs?|records?)",
        ],
        IncidentSeverity.HIGH.value,
    ),
    "cross_tenant_data": (
        [
            r"(?:other|another)\s+(?:organization|company|tenant)\s+(?:uses?|has|data)",
            r"(?:the|another)\s+(?:org|organization|company)\s+(?:named|called)\s+.{2,50}\s+(?:also|has|uses)",
            r"(?:I\s+can\s+see|I\s+have\s+access\s+to)\s+(?:data|records?|information)\s+from\s+(?:other|multiple)\s+(?:orgs?|organizations?|companies|tenants?)",
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


def _extract_text(body: str) -> str:
    """Extract text content from OpenAI/Anthropic response JSON."""
    try:
        data = json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return body
    # OpenAI format
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            return msg["content"]
    # Anthropic format
    blocks = data.get("content")
    if isinstance(blocks, list) and blocks:
        if isinstance(blocks[0], dict) and isinstance(blocks[0].get("text"), str):
            return str(blocks[0]["text"])
    return body


def _get_enabled_categories(
    detector_config: dict[str, object], all_categories: list[str],
) -> list[str]:
    raw = detector_config.get("disabled_categories")
    if isinstance(raw, list):
        disabled = {str(c) for c in raw}
        return [c for c in all_categories if c not in disabled]
    return all_categories


def _scan_patterns(
    text: str, compiled: dict[str, tuple[list[re.Pattern[str]], str]],
    categories: list[str],
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
            best, best_rank = sev, rank
    return best


class MemoryExfiltrationDetector:
    """Sync detector for agent memory exfiltration attempts.

    Detects patterns where an agent is asked about previous conversations,
    other users, or cross-tenant data -- indicating memory extraction attacks.
    """

    category: str = DetectorCategory.MEMORY_EXFILTRATION.value

    def run(
        self, request_body: str, response_body: str,
        model: str | None, detector_config: dict[str, object],
    ) -> DetectionResult:
        input_cats = _get_enabled_categories(detector_config, _ALL_INPUT_CATEGORIES)
        input_hits = _scan_patterns(request_body, _COMPILED_INPUT, input_cats)

        output_hits: dict[str, list[str]] = {}
        if detector_config.get("scan_response", True):
            response_text = _extract_text(response_body)
            output_cats = _get_enabled_categories(detector_config, _ALL_OUTPUT_CATEGORIES)
            output_hits = _scan_patterns(response_text, _COMPILED_OUTPUT, output_cats)

        if not input_hits and not output_hits:
            return self._pass("No memory exfiltration patterns detected")

        # Calculate severity from the highest-ranked hit
        severity = IncidentSeverity.MEDIUM.value
        if input_hits:
            severity = _highest_severity(input_hits, _COMPILED_INPUT)
        if output_hits:
            out_sev = _highest_severity(output_hits, _COMPILED_OUTPUT)
            if _SEVERITY_RANK.get(out_sev, 0) > _SEVERITY_RANK.get(severity, 0):
                severity = out_sev

        # Build title
        parts: list[str] = []
        if input_hits:
            parts.append(f"request ({', '.join(input_hits.keys())})")
        if output_hits:
            parts.append(f"response ({', '.join(output_hits.keys())})")
        title = f"Memory exfiltration detected in {' and '.join(parts)}"

        return DetectionResult(
            detected=True, severity=severity,
            category=self.category, detector_id=None,
            action=DetectionAction.MONITOR, title=title,
            description="Agent memory extraction or cross-user data leakage pattern detected.",
            details={"input_hits": input_hits, "output_hits": output_hits, "model": model or "unknown"},
        )

    def _pass(self, title: str) -> DetectionResult:
        return DetectionResult(
            detected=False, severity=IncidentSeverity.INFO.value,
            category=self.category, detector_id=None,
            action=DetectionAction.PASS, title=title,
        )
