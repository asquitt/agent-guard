"""Validation for credential-bearing AgentGuard deployment URLs."""

from __future__ import annotations

from urllib.parse import urlsplit


def normalize_base_url(base_url: str) -> str:
    """Return a normalized absolute HTTP(S) deployment URL.

    AgentGuard clients attach an organization credential to requests. Requiring
    and validating the destination prevents an omitted or relative URL from
    silently sending that credential to an unintended host.
    """
    value = base_url.strip().rstrip("/")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(
            "base_url must be an absolute http(s) AgentGuard deployment origin"
        )
    if parsed.scheme == "http" and parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError(
            "base_url must use https unless the AgentGuard deployment is on loopback"
        )
    return value
