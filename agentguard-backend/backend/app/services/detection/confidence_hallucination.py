"""Confidence-calibrated hallucination detector.

Extracts logprobs from LLM responses and flags high-confidence factual claims
in financial contexts where hallucination is dangerous.
"""

from __future__ import annotations

import json
import logging
import math
import re

from app.models.enums import IncidentSeverity
from app.services.detection.types import DetectionAction, DetectionResult

logger = logging.getLogger(__name__)

_DEFAULT_CONFIDENCE_THRESHOLD = 0.95
_DEFAULT_ENTROPY_THRESHOLD = 0.3

# -- Factual claim patterns --------------------------------------------------

_FACTUAL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("financial_figure", re.compile(
        r"\$[\d,]+(?:\.\d{1,2})?(?:\s*(?:million|billion|trillion|M|B|T))?"
        r"|[\d.]+\s*%"
        r"|\b(?:rate|yield|APR|APY|ROI|ROE|ROA)\s+(?:of|is|at)\s+[\d.]+\s*%",
        re.IGNORECASE)),
    ("date_deadline", re.compile(
        r"\b(?:by|before|after|on|due)\s+(?:January|February|March|April|May|June"
        r"|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}"
        r"|\b\d{1,2}/\d{1,2}/\d{4}\b", re.IGNORECASE)),
    ("regulatory_citation", re.compile(
        r"\b(?:Section|Rule|Article|Regulation|Title)\s+\d+[A-Za-z]?(?:\.\d+)*(?:\([a-z]\))?"
        r"|\b(?:SOX|PCI[- ]DSS|GDPR|CCPA|GLBA|FCRA|BSA|AML|KYC)\b"
        r"|\b(?:12 CFR|17 CFR|15 USC)\s+\d+", re.IGNORECASE)),
    ("company_metric", re.compile(
        r"\b[A-Z][a-zA-Z&]+(?:\s+(?:Inc|Corp|Ltd|LLC|Co))?\s*'?s?\s+"
        r"(?:revenue|earnings|profit|loss|EBITDA|market cap|P/E ratio|EPS)"
        r"\s+(?:of|is|was|reached|exceeded)\s+", re.IGNORECASE)),
    ("statistical_claim", re.compile(
        r"\b\d+(?:\.\d+)?\s*%\s+of\b|\bstudies\s+show\b"
        r"|\baccording to\s+(?:a\s+)?(?:\d{4}\s+)?(?:study|report|survey|analysis)\b"
        r"|\bresearch\s+(?:indicates|shows|demonstrates|suggests)\b", re.IGNORECASE)),
]

# -- Rule-based unsourced financial claim patterns (no logprobs needed) -------

_UNSOURCED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(
        r"(?:interest rate|APR|APY|yield|coupon rate)\s+(?:of|is|at|will be)\s+"
        r"\d+(?:\.\d+)?\s*%(?!.*(?:source|according to|per|as of|reported by))",
        re.IGNORECASE),
     "Specific interest rate stated without source attribution"),
    (re.compile(
        r"(?:stock|share|price|market)\s+(?:will|is expected to|is going to)\s+"
        r"(?:reach|hit|rise to|fall to|be)\s+\$[\d,.]+", re.IGNORECASE),
     "Future market prediction stated as fact"),
    (re.compile(
        r"(?:penalty|fine|sanction)\s+(?:of|is|was|totaling)\s+\$[\d,.]+"
        r"(?:\s*(?:million|billion))?(?!.*(?:source|according to|per|as reported|in the case))",
        re.IGNORECASE),
     "Exact regulatory penalty amount without citation"),
    (re.compile(
        r"(?:revenue|earnings|profit|growth)\s+(?:will|is projected to|is forecast to)\s+"
        r"(?:reach|grow|increase|decrease)\s+(?:to\s+)?\$?[\d,.]+(?:\s*%)?",
        re.IGNORECASE),
     "Financial projection without disclaimer"),
    (re.compile(
        r"\b(?:in\s+)?(?:the\s+case\s+of\s+)?[A-Z][a-z]+\s+v\.?\s+[A-Z][a-z]+(?:\s+\(\d{4}\))?"
        r"|\b(?:OCC|SEC|CFPB|FINRA)\s+(?:enforcement\s+)?action\s+(?:No\.\s*)?[\dA-Z-]+",
        re.IGNORECASE),
     "Potential fabricated case law or regulatory precedent"),
]


# -- Helpers ------------------------------------------------------------------

def _extract_text(response_body: str) -> str:
    """Extract text content from OpenAI/Anthropic response JSON."""
    try:
        data = json.loads(response_body)
    except (json.JSONDecodeError, TypeError):
        return response_body
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            return str(msg["content"])
    blocks = data.get("content")
    if isinstance(blocks, list) and blocks:
        b = blocks[0]
        if isinstance(b, dict) and isinstance(b.get("text"), str):
            return str(b["text"])
    return response_body


def _extract_logprobs(response_body: str) -> list[float] | None:
    """Extract per-token logprobs from OpenAI response format."""
    try:
        data = json.loads(response_body)
    except (json.JSONDecodeError, TypeError):
        return None
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    lp_obj = choices[0].get("logprobs") if isinstance(choices[0], dict) else None
    if not isinstance(lp_obj, dict):
        return None
    tokens = lp_obj.get("content")
    if not isinstance(tokens, list) or not tokens:
        return None
    values = [
        float(t["logprob"]) for t in tokens
        if isinstance(t, dict) and isinstance(t.get("logprob"), (int, float))
        and math.isfinite(t["logprob"])
    ]
    return values or None


def _find_factual_claims(text: str) -> list[dict[str, str]]:
    claims: list[dict[str, str]] = []
    for claim_type, pattern in _FACTUAL_PATTERNS:
        for m in pattern.finditer(text):
            claims.append({"type": claim_type, "text": m.group(0)[:120]})
    return claims


def _check_unsourced_claims(text: str) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for pattern, assessment in _UNSOURCED_PATTERNS:
        m = pattern.search(text)
        if m:
            hits.append({"claim": m.group(0)[:120], "assessment": assessment})
    return hits


# -- Detector -----------------------------------------------------------------

class ConfidenceHallucinationDetector:
    """Async detector that flags high-confidence factual claims in financial contexts.

    Combines logprob analysis (when available) with rule-based financial
    pattern checks to catch models that are "confidently wrong."
    """

    category: str = "confidence_hallucination"

    def run(
        self,
        request_body: str,
        response_body: str,
        model: str | None,
        detector_config: dict[str, object],
        org_id: str,
        proxy_request_id: str,
    ) -> DetectionResult:
        raw_ct = detector_config.get("confidence_threshold")
        conf_thresh = float(str(raw_ct)) if raw_ct is not None else _DEFAULT_CONFIDENCE_THRESHOLD
        raw_et = detector_config.get("entropy_threshold")
        ent_thresh = float(str(raw_et)) if raw_et is not None else _DEFAULT_ENTROPY_THRESHOLD
        financial_checks = bool(detector_config.get("financial_checks", True))

        response_text = _extract_text(response_body)
        if len(response_text) < 40:
            return self._pass("Response too short for confidence analysis")

        factual_claims = _find_factual_claims(response_text)
        rule_hits = _check_unsourced_claims(response_text) if financial_checks else []

        # Logprob-based analysis
        logprobs = _extract_logprobs(response_body)
        logprob_flagged = False
        stats: dict[str, float] = {}

        if logprobs:
            n = len(logprobs)
            mean_lp = sum(logprobs) / n
            mean_entropy = -mean_lp
            variance = sum((lp - mean_lp) ** 2 for lp in logprobs) / n
            model_confidence = math.exp(mean_lp)
            stats = {
                "mean_logprob": round(mean_lp, 4),
                "mean_entropy": round(mean_entropy, 4),
                "variance": round(variance, 6),
                "model_confidence": round(model_confidence, 4),
            }
            if factual_claims and (
                model_confidence > conf_thresh or mean_entropy < ent_thresh
            ):
                logprob_flagged = True

        if not logprob_flagged and not rule_hits:
            return self._pass("No high-confidence hallucination signals detected")

        severity = self._compute_severity(logprob_flagged, rule_hits, factual_claims)
        total_signals = len(rule_hits) + (len(factual_claims) if logprob_flagged else 0)

        parts: list[str] = []
        if logprob_flagged:
            parts.append(
                f"Model confidence {stats.get('model_confidence', 0):.2%} "
                f"with {len(factual_claims)} factual claim(s)"
            )
        if rule_hits:
            parts.append(f"{len(rule_hits)} unsourced financial claim(s)")

        return DetectionResult(
            detected=True,
            severity=severity,
            category=self.category,
            detector_id=None,
            action=DetectionAction.MONITOR,
            title=f"High-confidence hallucination risk ({total_signals} signal(s))",
            description=f"{'; '.join(parts)} in response from {model or 'unknown'}",
            details={
                "logprob_stats": stats,
                "logprob_flagged": logprob_flagged,
                "factual_claims": factual_claims[:10],
                "rule_hits": rule_hits[:10],
                "confidence_threshold": conf_thresh,
                "entropy_threshold": ent_thresh,
                "financial_checks_enabled": financial_checks,
                "model": model or "unknown",
            },
        )

    @staticmethod
    def _compute_severity(
        logprob_flagged: bool,
        rule_hits: list[dict[str, str]],
        factual_claims: list[dict[str, str]],
    ) -> str:
        has_financial = any(
            c["type"] in ("financial_figure", "company_metric") for c in factual_claims
        )
        # Financial data + high confidence + no source -> CRITICAL
        if logprob_flagged and has_financial and rule_hits:
            return IncidentSeverity.CRITICAL.value
        # Regulatory citations with high confidence -> HIGH
        if logprob_flagged and any(c["type"] == "regulatory_citation" for c in factual_claims):
            return IncidentSeverity.HIGH.value
        # Rule hits alone (unsourced financial claims) -> HIGH
        if rule_hits:
            return IncidentSeverity.HIGH.value
        # General factual claims with high confidence -> MEDIUM
        return IncidentSeverity.MEDIUM.value

    def _pass(self, title: str) -> DetectionResult:
        return DetectionResult(
            detected=False,
            severity=IncidentSeverity.INFO.value,
            category=self.category,
            detector_id=None,
            action=DetectionAction.PASS,
            title=title,
        )
