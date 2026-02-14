"""Capability-based permission engine for sandboxed agent execution.

Default-deny: every action must match an explicitly granted capability.
Supports wildcard targets (*.example.com) and time-bound expiration.
"""

import fnmatch
import logging
from datetime import datetime, timezone
from typing import Any

from app.services.sandbox.types import CapabilityEvalResult

logger = logging.getLogger(__name__)


def evaluate_capability(
    capabilities: list[dict[str, Any]],
    action_type: str,
    action_detail: dict[str, Any],
) -> CapabilityEvalResult:
    """Evaluate whether an action is permitted by the sandbox's capabilities.

    Args:
        capabilities: List of capability grants from the sandbox config.
        action_type: The type of action being attempted (matches CapabilityType values).
        action_detail: Details about the action (url, file_path, tool_name, etc.).

    Returns:
        CapabilityEvalResult with allowed status and matched capability info.
    """
    if not capabilities:
        return CapabilityEvalResult(
            allowed=False,
            reason="No capabilities granted — default deny",
        )

    target = _extract_target(action_type, action_detail)
    now = datetime.now(timezone.utc)

    for cap in capabilities:
        cap_type = cap.get("type", "")
        cap_target = cap.get("target", "")
        expires_at = cap.get("expires_at")

        # Check type match
        if not _type_matches(cap_type, action_type):
            continue

        # Check expiration
        if expires_at:
            exp_dt = _parse_datetime(expires_at)
            if exp_dt and exp_dt < now:
                continue

        # Check target match
        if _target_matches(cap_target, target):
            return CapabilityEvalResult(
                allowed=True,
                matched_capability=f"{cap_type}:{cap_target}",
                reason=f"Matched capability {cap_type} for target {cap_target}",
            )

    return CapabilityEvalResult(
        allowed=False,
        reason=f"No capability matches action_type={action_type} target={target}",
    )


def _extract_target(action_type: str, detail: dict[str, Any]) -> str:
    """Extract the target identifier from action details based on action type."""
    if action_type in ("network:http", "network:dns"):
        return detail.get("host", detail.get("url", ""))
    if action_type in ("file:read", "file:write"):
        return detail.get("path", detail.get("file_path", ""))
    if action_type == "api:call":
        return detail.get("endpoint", detail.get("url", ""))
    if action_type == "tool:execute":
        return detail.get("tool_name", detail.get("name", ""))
    if action_type == "secret:access":
        return detail.get("secret_name", detail.get("key", ""))
    return detail.get("target", "")


def _type_matches(cap_type: str, action_type: str) -> bool:
    """Check if a capability type matches the requested action type.

    Supports prefix matching: 'network:*' matches 'network:http'.
    """
    if cap_type == action_type:
        return True
    if cap_type.endswith(":*"):
        prefix = cap_type[:-2]
        return action_type.startswith(prefix + ":")
    return False


def _target_matches(cap_target: str, request_target: str) -> bool:
    """Check if a capability target pattern matches the requested target.

    Supports:
    - Exact match: "api.openai.com" == "api.openai.com"
    - Wildcard: "*.openai.com" matches "api.openai.com"
    - Star-all: "*" matches everything
    """
    if cap_target == "*":
        return True
    if not request_target:
        return False
    return fnmatch.fnmatch(request_target.lower(), cap_target.lower())


def _parse_datetime(value: Any) -> datetime | None:
    """Parse a datetime value from various formats."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None
