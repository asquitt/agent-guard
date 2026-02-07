"""Redis pub/sub event publishing for real-time WebSocket updates."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import redis as sync_redis
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy-initialized clients
_async_redis: aioredis.Redis | None = None
_sync_redis: sync_redis.Redis | None = None


def _get_async_redis() -> aioredis.Redis:
    global _async_redis
    if _async_redis is None:
        _async_redis = aioredis.from_url(settings.REDIS_URL)
    return _async_redis


def _get_sync_redis() -> sync_redis.Redis:
    global _sync_redis
    if _sync_redis is None:
        _sync_redis = sync_redis.from_url(settings.REDIS_URL)
    return _sync_redis


def _build_message(event_type: str, data: dict[str, Any]) -> str:
    return json.dumps({
        "type": event_type,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def publish_event(
    org_id: str,
    event_type: str,
    data: dict[str, Any],
) -> None:
    """Publish event to org's Redis channel (async, for FastAPI handlers)."""
    channel = f"org:{org_id}:events"
    message = _build_message(event_type, data)
    try:
        client = _get_async_redis()
        await client.publish(channel, message)
    except Exception:
        logger.exception("Failed to publish event %s to %s", event_type, channel)


def publish_event_sync(
    org_id: str,
    event_type: str,
    data: dict[str, Any],
) -> None:
    """Publish event to org's Redis channel (sync, for Celery tasks)."""
    channel = f"org:{org_id}:events"
    message = _build_message(event_type, data)
    try:
        client = _get_sync_redis()
        client.publish(channel, message)
    except Exception:
        logger.exception("Failed to publish event %s to %s", event_type, channel)
