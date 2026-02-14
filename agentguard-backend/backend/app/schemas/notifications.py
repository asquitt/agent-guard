"""Pydantic schemas for notification preferences."""

from typing import Literal

from pydantic import BaseModel, Field


class NotificationPreferences(BaseModel):
    """User notification preference settings."""

    # Email notifications
    email_enabled: bool = True
    email_digest: Literal["realtime", "hourly", "daily", "weekly", "off"] = "daily"

    # Severity threshold — only notify for incidents at or above this level
    min_severity: Literal["info", "low", "medium", "high", "critical"] = "medium"

    # Category toggles — categories the user wants to be notified about
    categories: list[str] = Field(default_factory=lambda: [
        "hallucination", "pii_leak", "compliance", "cost_anomaly",
        "loop", "prompt_injection", "prompt_extraction", "toxicity",
        "tool_call", "mcp_security",
    ])

    # In-app notifications
    in_app_enabled: bool = True

    # Slack DM (if connected)
    slack_dm_enabled: bool = False

    # Quiet hours (UTC)
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"  # HH:MM UTC
    quiet_hours_end: str = "08:00"  # HH:MM UTC


class NotificationPreferencesResponse(BaseModel):
    """Response wrapper for notification preferences."""

    preferences: NotificationPreferences
