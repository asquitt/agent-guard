"""Internal LLM service for detection analysis (hallucination & compliance)."""

from __future__ import annotations

import json
import logging
import time

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_OPENAI_URL = "https://api.openai.com/v1/chat/completions"
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# Simple sliding-window rate limiter (per-process)
_request_timestamps: list[float] = []


def _rate_limit_ok() -> bool:
    """Return True if we're within the RPM budget."""
    now = time.monotonic()
    window = 60.0
    rpm = settings.DETECTION_LLM_RPM

    # Prune old timestamps
    while _request_timestamps and _request_timestamps[0] < now - window:
        _request_timestamps.pop(0)

    if len(_request_timestamps) >= rpm:
        return False

    _request_timestamps.append(now)
    return True


def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1024,
    timeout: float = 30.0,
) -> str:
    """Call the internal detection LLM and return the response text.

    Returns empty string on any failure (rate limit, API error, timeout).
    Callers must handle empty string gracefully.
    """
    if not _rate_limit_ok():
        logger.warning("Detection LLM rate limit exceeded (%d RPM)", settings.DETECTION_LLM_RPM)
        return ""

    provider = settings.DETECTION_LLM_PROVIDER.lower()

    try:
        if provider == "anthropic":
            return _call_anthropic(system_prompt, user_prompt, max_tokens, timeout)
        return _call_openai(system_prompt, user_prompt, max_tokens, timeout)
    except Exception:
        logger.exception("Detection LLM call failed (provider=%s)", provider)
        return ""


def _call_openai(system_prompt: str, user_prompt: str, max_tokens: int, timeout: float) -> str:
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        logger.warning("OPENAI_API_KEY not set, skipping detection LLM call")
        return ""

    resp = httpx.post(
        _OPENAI_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": settings.DETECTION_LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.0,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    choices = data.get("choices", [])
    if choices and isinstance(choices[0], dict):
        msg = choices[0].get("message", {})
        if isinstance(msg, dict):
            return str(msg.get("content", ""))
    return ""


def _call_anthropic(system_prompt: str, user_prompt: str, max_tokens: int, timeout: float) -> str:
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, skipping detection LLM call")
        return ""

    resp = httpx.post(
        _ANTHROPIC_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.DETECTION_LLM_MODEL,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.0,
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    content_blocks = data.get("content", [])
    if content_blocks and isinstance(content_blocks[0], dict):
        return str(content_blocks[0].get("text", ""))
    return ""


def parse_json_response(raw: str) -> dict[str, object]:
    """Best-effort JSON parse from LLM response. Returns empty dict on failure."""
    text = raw.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except (json.JSONDecodeError, TypeError):
        pass
    return {}
