"""Sentry error tracking initialization."""

import os
import re

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.core.config import settings

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")


def _strip_pii(event: dict, hint: dict) -> dict:
    """Redact email addresses from exception messages."""
    if "exception" in event:
        for exc_info in event["exception"].get("values", []):
            if "value" in exc_info:
                exc_info["value"] = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", exc_info["value"])
    return event


def init_sentry() -> None:
    """Initialize Sentry SDK if DSN is configured."""
    if not settings.SENTRY_DSN:
        return

    release = settings.GIT_COMMIT_SHA or os.getenv("GIT_COMMIT_SHA") or "agentguard@0.1.0"
    if release and len(release) > 8 and not release.startswith("agentguard"):
        release = f"agentguard@{release[:12]}"

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration(), CeleryIntegration()],
        traces_sample_rate=1.0 if settings.DEBUG else 0.05,
        profiles_sample_rate=0.1 if settings.DEBUG else 0.01,
        environment=settings.ENVIRONMENT,
        release=release,
        before_send=_strip_pii,
    )
