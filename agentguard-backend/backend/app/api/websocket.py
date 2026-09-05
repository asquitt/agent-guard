"""Authenticated WebSocket ticket issuance and real-time event streaming."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import secrets
from typing import Any
from uuid import UUID

import redis.asyncio as aioredis  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.deps import get_current_user
from app.models.user import Organization, User

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

_SAFE_PROTOCOL = "agentguard.v1"
_TICKET_PROTOCOL_PREFIX = "agentguard.ticket."
_TICKET_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")
_TICKET_TTL_SECONDS = 30
_TICKET_CREATE_ATTEMPTS = 3


def _ticket_key(ticket: str) -> str:
    """Return the Redis key without retaining the bearer ticket itself."""
    digest = hashlib.sha256(ticket.encode("ascii")).hexdigest()
    return f"ws:ticket:{digest}"


async def _close_redis(client: Any) -> None:
    """Close a Redis connection without leaking cleanup errors to callers."""
    if client is None:
        return
    try:
        close = getattr(client, "aclose", None) or getattr(client, "close", None)
        if close is not None:
            result = close()
            if hasattr(result, "__await__"):
                await result
    except Exception:
        logger.warning("WebSocket Redis cleanup failed")


@router.post("/api/v1/ws/ticket")
@limiter.limit("10/minute")
async def create_websocket_ticket(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
) -> dict[str, str | int]:
    """Issue a short-lived, opaque, single-use ticket for a WebSocket upgrade."""
    del request  # Used by SlowAPI to derive the caller key.
    redis_client: Any = None
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        payload = json.dumps(
            {
                "user_id": str(current_user.id),
                "org_id": str(current_user.org_id),
            },
            separators=(",", ":"),
        )

        for _attempt in range(_TICKET_CREATE_ATTEMPTS):
            ticket = secrets.token_urlsafe(32)
            stored = await redis_client.set(
                _ticket_key(ticket),
                payload,
                ex=_TICKET_TTL_SECONDS,
                nx=True,
            )
            if stored:
                response.headers["Cache-Control"] = "no-store"
                response.headers["Pragma"] = "no-cache"
                return {"ticket": ticket, "expiresIn": _TICKET_TTL_SECONDS}
    except Exception:
        logger.warning("WebSocket ticket issuance failed")
    finally:
        await _close_redis(redis_client)

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="WebSocket ticket service unavailable",
    )


def _extract_ticket(ws: WebSocket) -> str | None:
    """Parse the strict pair of supported WebSocket subprotocol values."""
    raw_protocols = ws.headers.get("sec-websocket-protocol", "")
    protocols = [protocol.strip() for protocol in raw_protocols.split(",") if protocol.strip()]
    if len(protocols) != 2 or protocols[0] != _SAFE_PROTOCOL:
        return None

    ticket_protocol = protocols[1]
    if not ticket_protocol.startswith(_TICKET_PROTOCOL_PREFIX):
        return None
    ticket = ticket_protocol[len(_TICKET_PROTOCOL_PREFIX) :]
    if _TICKET_PATTERN.fullmatch(ticket) is None:
        return None
    return ticket


async def _consume_ticket(ticket: str) -> tuple[str, str] | None:
    """Atomically consume and revalidate a ticket's user and organization."""
    redis_client: Any = None
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        raw_payload = await redis_client.getdel(_ticket_key(ticket))
    except Exception:
        logger.warning("WebSocket ticket consumption failed")
        return None
    finally:
        await _close_redis(redis_client)

    if raw_payload is None:
        return None
    if isinstance(raw_payload, bytes):
        try:
            raw_payload = raw_payload.decode("utf-8")
        except UnicodeDecodeError:
            return None

    try:
        payload = json.loads(raw_payload)
        if not isinstance(payload, dict) or set(payload) != {"user_id", "org_id"}:
            return None
        user_id = UUID(payload["user_id"])
        org_id = UUID(payload["org_id"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None

    try:
        async with AsyncSessionLocal() as db:  # type: ignore[attr-defined]
            user_result = await db.execute(
                select(User.id).where(
                    User.id == user_id,
                    User.org_id == org_id,
                    User.is_active.is_(True),
                )
            )
            if user_result.scalar_one_or_none() is None:
                return None

            org_result = await db.execute(select(Organization.id).where(Organization.id == org_id))
            if org_result.scalar_one_or_none() is None:
                return None
    except Exception:
        logger.warning("WebSocket ticket identity revalidation failed")
        return None

    return str(user_id), str(org_id)


async def _redis_listener(
    ws: WebSocket,
    pubsub: Any,
) -> None:
    """Forward Redis pub/sub messages to the WebSocket client."""
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if message and message["type"] == "message":
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            await ws.send_text(data)
        else:
            await asyncio.sleep(0.1)


async def _ws_receiver(ws: WebSocket) -> None:
    """Listen for client messages and detect disconnects."""
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/events")
async def websocket_events(ws: WebSocket) -> None:
    """Stream organization events to a client holding a valid one-use ticket."""
    ticket = _extract_ticket(ws)
    if ticket is None:
        await ws.close(code=4001, reason="Authentication failed")
        return

    auth_result = await _consume_ticket(ticket)
    if auth_result is None:
        await ws.close(code=4001, reason="Authentication failed")
        return

    user_id, org_id = auth_result
    redis_client: Any = None
    pubsub: Any = None
    channel = f"org:{org_id}:events"
    tasks: set[asyncio.Task[Any]] = set()

    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(channel)

        await ws.accept(subprotocol=_SAFE_PROTOCOL)
        logger.info("WebSocket connected: user=%s org=%s", user_id, org_id)
        await ws.send_json(
            {
                "type": "connected",
                "data": {"orgId": org_id},
            }
        )

        tasks = {
            asyncio.create_task(_redis_listener(ws, pubsub)),
            asyncio.create_task(_ws_receiver(ws)),
        }
        done, _pending = await asyncio.wait(
            tasks,
            return_when=asyncio.FIRST_COMPLETED,
        )
        await asyncio.gather(*done)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning("WebSocket event stream failed for user=%s org=%s", user_id, org_id)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if pubsub is not None:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            except Exception:
                logger.warning("WebSocket pub/sub cleanup failed for org=%s", org_id)
        await _close_redis(redis_client)
        logger.info("WebSocket disconnected: user=%s org=%s", user_id, org_id)
