"""Sentry error tracking initialization."""

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

    environment = (
        getattr(settings, "ENVIRONMENT", None)
        or ("development" if settings.DEBUG else "production")
    )

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FastApiIntegration(), CeleryIntegration()],
        traces_sample_rate=1.0 if settings.DEBUG else 0.1,
        profiles_sample_rate=0.1,
        environment=environment,
        release="agentguard@0.1.0",
        before_send=_strip_pii,
    )
