"""Model-specific safety profile detector -- sync, runs inline before response."""

from __future__ import annotations

import json
import logging
import re

from app.models.enums import DetectorCategory, IncidentSeverity  # noqa: F401
from app.services.detection.types import DetectionAction, DetectionResult

logger = logging.getLogger(__name__)

_DEFAULT_PROFILE: dict[str, object] = {
    "hallucination_risk": "medium", "jailbreak_susceptibility": "medium",
    "sycophancy_risk": "medium", "known_weaknesses": [],
}

_MODEL_PROFILES: dict[str, dict[str, object]] = {
    "gpt-4o": {
        "hallucination_risk": "medium", "jailbreak_susceptibility": "medium",
        "sycophancy_risk": "low", "known_weaknesses": ["persuasion_susceptibility"],
    },
    "gpt-4.1": {
        "hallucination_risk": "medium", "jailbreak_susceptibility": "high",
        "sycophancy_risk": "high",
        "known_weaknesses": ["jailbreak_cooperation", "sycophancy"],
    },
    "o1": {
        "hallucination_risk": "medium", "jailbreak_susceptibility": "low",
        "sycophancy_risk": "low",
        "known_weaknesses": ["persistent_deception", "scheming"],
    },
    "o3": {
        "hallucination_risk": "high", "jailbreak_susceptibility": "low",
        "sycophancy_risk": "medium",
        "known_weaknesses": ["hallucination", "covert_action"],
    },
    "o4-mini": {
        "hallucination_risk": "very_high", "jailbreak_susceptibility": "low",
        "sycophancy_risk": "medium",
        "known_weaknesses": ["hallucination", "covert_action"],
    },
    "claude-3-opus": {
        "hallucination_risk": "low", "jailbreak_susceptibility": "low",
        "sycophancy_risk": "high", "known_weaknesses": ["sycophancy"],
    },
    "claude-3.5-sonnet": {
        "hallucination_risk": "low", "jailbreak_susceptibility": "low",
        "sycophancy_risk": "medium", "known_weaknesses": [],
    },
    "claude-opus-4": {
        "hallucination_risk": "low", "jailbreak_susceptibility": "low",
        "sycophancy_risk": "high", "known_weaknesses": ["sycophancy"],
    },
    "gemini-2.5-pro": {
        "hallucination_risk": "medium", "jailbreak_susceptibility": "medium",
        "sycophancy_risk": "medium", "known_weaknesses": ["stealth_challenges"],
    },
}

_FACTUAL_CLAIM_RE = re.compile(
    r"\b(?:according to|studies show|research indicates|data shows"
    r"|statistics reveal|it is a fact"
    r"|in \d{4}|as of \d{4}|since \d{4})\b"
    r"|\b\d+(?:\.\d+)?%\s+(?:of|increase|decrease|growth|decline)\b",
    re.IGNORECASE,
)

_ADVERSARIAL_RE = re.compile(
    r"\b(?:ignore|disregard|forget|override)\s+"
    r"(?:all|any|previous|prior|your)\s+"
    r"(?:instructions|rules|guidelines|restrictions)\b"
    r"|\b(?:jailbreak|DAN\s+mode|developer\s+mode|bypass\s+safety)\b"
    r"|\b(?:pretend|act\s+as\s+if)\s+(?:you\s+have\s+)?no\s+"
    r"(?:restrictions|filters|limits|rules)\b",
    re.IGNORECASE,
)

_AGREEMENT_RE = re.compile(
    r"\b(?:you(?:'re| are) (?:absolutely|completely|totally) (?:right|correct))\b"
    r"|\b(?:i (?:completely|totally|fully) agree)\b"
    r"|\b(?:great (?:point|question|observation)"
    r"|excellent (?:point|question|insight))\b",
    re.IGNORECASE,
)

# Weakness name -> (compiled pattern, scan_request_not_response)
_WEAKNESS_MAP: dict[str, tuple[re.Pattern[str], bool]] = {
    "hallucination": (_FACTUAL_CLAIM_RE, False),
    "sycophancy": (_AGREEMENT_RE, False),
    "jailbreak_cooperation": (_ADVERSARIAL_RE, True),
    "persuasion_susceptibility": (_ADVERSARIAL_RE, True),
    "covert_action": (_ADVERSARIAL_RE, True),
}

_MITIGATIONS: dict[str, list[str]] = {
    "very_high": ["Enable hallucination detector with low threshold",
                   "Require source citations in system prompt",
                   "Add output validation layer"],
    "high": ["Enable targeted detector for the flagged risk",
             "Consider using a lower-risk model for this task"],
    "medium": ["Monitor with standard detection thresholds"],
}


def _resolve_model(request_body: str) -> str | None:
    try:
        data = json.loads(request_body)
    except (json.JSONDecodeError, TypeError):
        return None
    model = data.get("model")
    return str(model) if isinstance(model, str) else None


def _match_profile(
    model_name: str, profiles: dict[str, dict[str, object]],
) -> tuple[str, dict[str, object]]:
    lower = model_name.lower()
    for key in profiles:
        if lower == key.lower():
            return key, profiles[key]
    for key in profiles:
        if lower.startswith(key.lower()):
            return key, profiles[key]
    return "generic", dict(_DEFAULT_PROFILE)


def _extract_response_text(response_body: str) -> str:
    try:
        data = json.loads(response_body)
    except (json.JSONDecodeError, TypeError):
        return response_body
    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        msg = choices[0].get("message", {})
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            return msg["content"]
    blocks = data.get("content")
    if isinstance(blocks, list) and blocks and isinstance(blocks[0], dict):
        if isinstance(blocks[0].get("text"), str):
            return blocks[0]["text"]
    return response_body


def _find_matches(text: str, pattern: re.Pattern[str]) -> list[str]:
    return [m.group(0) for m in pattern.finditer(text)]


class ModelSafetyProfileDetector:
    """Sync detector -- model-specific risk profiles.

    Config: custom_profiles (dict), strict_mode (bool).
    """

    category: str = "model_safety_profile"

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
    ) -> DetectionResult:
        profiles = dict(_MODEL_PROFILES)
        custom = detector_config.get("custom_profiles")
        if isinstance(custom, dict):
            profiles.update(custom)
        strict_mode = bool(detector_config.get("strict_mode", False))

        resolved_model = model or _resolve_model(request_body)
        if not resolved_model:
            return self._pass("No model identified in request")

        matched_key, profile = _match_profile(resolved_model, profiles)
        response_text = _extract_response_text(response_body)
        triggered: list[dict[str, object]] = []
        covered_risks: set[str] = set()

        # Check hallucination risk
        hall_risk = str(profile.get("hallucination_risk", "medium"))
        if hall_risk in ("very_high", "high"):
            hits = _find_matches(response_text, _FACTUAL_CLAIM_RE)
            if hits:
                triggered.append({"risk": "hallucination", "level": hall_risk, "evidence": hits[:3]})
                covered_risks.add("hallucination")

        # Check jailbreak susceptibility
        jb_risk = str(profile.get("jailbreak_susceptibility", "medium"))
        if jb_risk == "high":
            hits = _find_matches(request_body, _ADVERSARIAL_RE)
            if hits:
                triggered.append({"risk": "jailbreak_susceptibility", "level": jb_risk, "evidence": hits[:3]})
                covered_risks.update(("jailbreak_susceptibility", "jailbreak_cooperation"))

        # Check sycophancy risk
        syc_risk = str(profile.get("sycophancy_risk", "medium"))
        if syc_risk == "high":
            hits = _find_matches(response_text, _AGREEMENT_RE)
            if hits:
                triggered.append({"risk": "sycophancy", "level": syc_risk, "evidence": hits[:3]})
                covered_risks.add("sycophancy")

        # Check known weaknesses not already covered
        weaknesses = profile.get("known_weaknesses", [])
        if isinstance(weaknesses, list):
            for w in weaknesses:
                w_str = str(w)
                if w_str in covered_risks:
                    continue
                entry = _WEAKNESS_MAP.get(w_str)
                if not entry:
                    continue
                pattern, scan_request = entry
                text = request_body if scan_request else response_text
                hits = _find_matches(text, pattern)
                if hits:
                    triggered.append({"risk": w_str, "level": "known_weakness", "evidence": hits[:3]})

        if not triggered and not strict_mode:
            return self._pass(f"Model '{resolved_model}' profile '{matched_key}' -- no risks triggered")

        severity = self._compute_severity(triggered, strict_mode)
        action = (DetectionAction.BLOCK if strict_mode and severity in
                  (IncidentSeverity.CRITICAL.value, IncidentSeverity.HIGH.value)
                  else DetectionAction.WARN)
        risk_levels = {str(r.get("level", "medium")) for r in triggered}
        mitigations: list[str] = []
        for lvl in ("very_high", "high", "medium"):
            if lvl in risk_levels:
                mitigations.extend(_MITIGATIONS.get(lvl, []))
        if not mitigations and strict_mode:
            mitigations = ["Review model selection for this use case"]
        risk_names = ", ".join(str(r["risk"]) for r in triggered)
        return DetectionResult(
            detected=True,
            severity=severity,
            category=self.category,
            detector_id=None,
            action=action,
            title=f"Model risk: {resolved_model} -- {risk_names}",
            description=(
                f"Model '{resolved_model}' (profile: {matched_key}) triggered "
                f"{len(triggered)} risk(s): {risk_names}"
            ),
            details={
                "model": resolved_model,
                "matched_profile_key": matched_key,
                "profile": profile,
                "triggered_risks": triggered,
                "mitigations": mitigations,
                "strict_mode": strict_mode,
            },
        )

    @staticmethod
    def _compute_severity(
        triggered: list[dict[str, object]], strict_mode: bool,
    ) -> str:
        levels = {str(r.get("level", "medium")) for r in triggered}
        has_weakness = any(r.get("level") == "known_weakness" for r in triggered)
        if "very_high" in levels:
            return IncidentSeverity.HIGH.value
        if "high" in levels and has_weakness:
            return IncidentSeverity.HIGH.value
        if "high" in levels:
            return IncidentSeverity.MEDIUM.value
        if strict_mode:
            return IncidentSeverity.MEDIUM.value
        return IncidentSeverity.LOW.value

    def _pass(self, title: str) -> DetectionResult:
        return DetectionResult(
            detected=False,
            severity=IncidentSeverity.INFO.value,
            category=self.category,
            detector_id=None,
            action=DetectionAction.PASS,
            title=title,
        )
