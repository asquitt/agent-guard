"""Alert delivery — send notifications to Slack, email, PagerDuty, webhooks."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0


def deliver_slack(config: dict[str, Any], payload: dict[str, Any]) -> str | None:
    """Send alert to Slack via incoming webhook. Returns error message or None."""
    webhook_url = config.get("webhook_url", "")
    if not webhook_url:
        return "Missing webhook_url in config"

    severity = payload.get("severity", "info")
    color = {"critical": "#FF0000", "high": "#FF6600", "medium": "#FFD700"}.get(severity, "#36A64F")

    body = {
        "attachments": [
            {
                "color": color,
                "title": payload.get("title", "AgentGuard Alert"),
                "text": payload.get("description", ""),
                "fields": [
                    {"title": "Severity", "value": severity, "short": True},
                    {"title": "Category", "value": payload.get("category", ""), "short": True},
                    {"title": "Status", "value": payload.get("status", "open"), "short": True},
                ],
                "footer": "AgentGuard",
            }
        ]
    }

    try:
        resp = httpx.post(str(webhook_url), json=body, timeout=_TIMEOUT)
        resp.raise_for_status()
        return None
    except httpx.HTTPError as e:
        return f"Slack delivery failed: {e}"


def deliver_pagerduty(config: dict[str, Any], payload: dict[str, Any]) -> str | None:
    """Send alert to PagerDuty via Events API v2. Returns error message or None."""
    routing_key = config.get("routing_key", "")
    if not routing_key:
        return "Missing routing_key in config"

    severity_map = {
        "critical": "critical",
        "high": "error",
        "medium": "warning",
        "low": "info",
        "info": "info",
    }
    pd_severity = severity_map.get(payload.get("severity", "info"), "info")

    body = {
        "routing_key": routing_key,
        "event_action": "trigger",
        "payload": {
            "summary": payload.get("title", "AgentGuard Alert"),
            "source": "agentguard",
            "severity": pd_severity,
            "custom_details": {
                "category": payload.get("category", ""),
                "description": payload.get("description", ""),
                "incident_id": payload.get("incident_id", ""),
            },
        },
    }

    try:
        resp = httpx.post(
            "https://events.pagerduty.com/v2/enqueue",
            json=body,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return None
    except httpx.HTTPError as e:
        return f"PagerDuty delivery failed: {e}"


def deliver_email(config: dict[str, Any], payload: dict[str, Any]) -> str | None:
    """Send alert via email (webhook-based for now). Returns error message or None."""
    webhook_url = config.get("webhook_url", "")
    if not webhook_url:
        return "Missing webhook_url in email config (use SendGrid/SMTP webhook)"

    body = {
        "to": config.get("to_email", ""),
        "subject": f"[AgentGuard] {payload.get('severity', 'info').upper()}: {payload.get('title', 'Alert')}",
        "body": payload.get("description", ""),
        "metadata": {
            "category": payload.get("category", ""),
            "incident_id": payload.get("incident_id", ""),
        },
    }

    try:
        resp = httpx.post(str(webhook_url), json=body, timeout=_TIMEOUT)
        resp.raise_for_status()
        return None
    except httpx.HTTPError as e:
        return f"Email delivery failed: {e}"


def deliver_webhook(config: dict[str, Any], payload: dict[str, Any]) -> str | None:
    """Send alert to a generic webhook. Returns error message or None."""
    url = config.get("url", "")
    if not url:
        return "Missing url in webhook config"

    headers = {"Content-Type": "application/json"}
    secret = config.get("secret")
    if secret:
        headers["X-AgentGuard-Secret"] = str(secret)

    try:
        resp = httpx.post(str(url), json=payload, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        return None
    except httpx.HTTPError as e:
        return f"Webhook delivery failed: {e}"


def deliver_siem(config: dict[str, Any], payload: dict[str, Any]) -> str | None:
    """Send alert to a SIEM destination in the configured format. Returns error or None."""
    from app.services.siem_service import format_incident

    url = config.get("url", "")
    if not url:
        return "Missing url in SIEM config"

    fmt = config.get("format", "cef")
    try:
        formatted = format_incident(payload, fmt)
    except ValueError as e:
        return str(e)

    headers: dict[str, str] = {"Content-Type": "application/json"}
    auth_header = config.get("auth_header")
    if auth_header:
        headers["Authorization"] = str(auth_header)

    # CEF and LEEF are strings; wrap in JSON for HTTP delivery
    if isinstance(formatted, str):
        body: Any = {"raw": formatted}
    else:
        body = formatted

    try:
        resp = httpx.post(str(url), json=body, headers=headers, timeout=_TIMEOUT)
        resp.raise_for_status()
        return None
    except httpx.HTTPError as e:
        return f"SIEM delivery ({fmt}) failed: {e}"


# Dispatcher
_DELIVER_MAP: dict[str, Any] = {
    "slack": deliver_slack,
    "pagerduty": deliver_pagerduty,
    "email": deliver_email,
    "webhook": deliver_webhook,
    "siem": deliver_siem,
}


def deliver(
    destination_type: str,
    config: dict[str, Any],
    payload: dict[str, Any],
) -> str | None:
    """Dispatch alert to the appropriate delivery method. Returns error or None."""
    handler = _DELIVER_MAP.get(destination_type)
    if handler is None:
        return f"Unknown destination type: {destination_type}"
    return handler(config, payload)
