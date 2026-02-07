"""Webhook management and delivery service."""

# pyright: reportCallIssue=false

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.alert import AlertDestination

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0


def sign_payload(payload: dict[str, Any], secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    body = json.dumps(payload, sort_keys=True, default=str)
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


async def create_webhook(
    db: AsyncSession,
    org_id: UUID,
    name: str,
    url: str,
    secret: str | None = None,
    event_types: list[str] | None = None,
    min_severity: str = "info",
) -> AlertDestination:
    """Create a webhook endpoint (stored as AlertDestination type=webhook)."""
    dest = AlertDestination(
        org_id=org_id,
        name=name,
        destination_type="webhook",
        config={
            "url": url,
            "secret": secret or "",
            "event_types": event_types or ["incident.created", "incident.resolved"],
            "min_severity": min_severity,
        },
        is_active=True,
    )
    db.add(dest)
    await db.commit()
    await db.refresh(dest)
    return dest


async def list_webhooks(
    db: AsyncSession,
    org_id: UUID,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[AlertDestination], int]:
    """List webhook-type alert destinations for org."""
    base = select(AlertDestination).where(
        AlertDestination.org_id == org_id,
        AlertDestination.destination_type == "webhook",
    )
    count_q = select(func.count(AlertDestination.id)).where(
        AlertDestination.org_id == org_id,
        AlertDestination.destination_type == "webhook",
    )

    total = (await db.execute(count_q)).scalar_one()
    result = await db.execute(base.order_by(AlertDestination.created_at.desc()).offset(skip).limit(limit))
    return list(result.scalars().all()), total


async def get_webhook(db: AsyncSession, org_id: UUID, webhook_id: UUID) -> AlertDestination:
    """Get single webhook, scoped to org."""
    result = await db.execute(
        select(AlertDestination).where(
            AlertDestination.id == webhook_id,
            AlertDestination.org_id == org_id,
            AlertDestination.destination_type == "webhook",
        )
    )
    dest = result.scalar_one_or_none()
    if dest is None:
        raise NotFoundError(f"Webhook {webhook_id} not found")
    return dest


async def update_webhook(
    db: AsyncSession,
    org_id: UUID,
    webhook_id: UUID,
    name: str | None = None,
    url: str | None = None,
    secret: str | None = None,
    event_types: list[str] | None = None,
    min_severity: str | None = None,
    is_active: bool | None = None,
) -> AlertDestination:
    """Update webhook fields."""
    dest = await get_webhook(db, org_id, webhook_id)
    if name is not None:
        dest.name = name  # type: ignore[assignment]
    if is_active is not None:
        dest.is_active = is_active  # type: ignore[assignment]

    config = dest.config if isinstance(dest.config, dict) else {}
    if url is not None:
        config["url"] = url
    if secret is not None:
        config["secret"] = secret
    if event_types is not None:
        config["event_types"] = event_types
    if min_severity is not None:
        config["min_severity"] = min_severity
    dest.config = config  # type: ignore[assignment]

    await db.commit()
    await db.refresh(dest)
    return dest


async def delete_webhook(db: AsyncSession, org_id: UUID, webhook_id: UUID) -> None:
    """Delete a webhook."""
    dest = await get_webhook(db, org_id, webhook_id)
    await db.delete(dest)
    await db.commit()


def deliver_webhook_with_signature(
    url: str,
    secret: str,
    event_type: str,
    payload: dict[str, Any],
) -> tuple[int | None, str | None]:
    """Deliver webhook with HMAC signature. Returns (status_code, error)."""
    full_payload = {"event": event_type, "data": payload}

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if secret:
        sig = sign_payload(full_payload, secret)
        headers["X-AgentGuard-Signature"] = f"sha256={sig}"

    try:
        resp = httpx.post(url, json=full_payload, headers=headers, timeout=_TIMEOUT)
        if resp.status_code >= 400:
            return resp.status_code, f"HTTP {resp.status_code}"
        return resp.status_code, None
    except httpx.HTTPError as e:
        return None, str(e)


def to_webhook_response(dest: AlertDestination) -> dict[str, Any]:
    """Convert AlertDestination to webhook response dict."""
    config = dest.config if isinstance(dest.config, dict) else {}
    return {
        "id": dest.id,
        "name": dest.name,
        "url": config.get("url", ""),
        "event_types": config.get("event_types", []),
        "min_severity": config.get("min_severity", "info"),
        "is_active": dest.is_active,
        "created_at": dest.created_at,
        "updated_at": dest.updated_at,
    }
