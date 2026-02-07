"""WebSocket endpoint for real-time event streaming."""

from __future__ import annotations

import asyncio
import json
import logging

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.user import Organization, User

logger = logging.getLogger(__name__)
router = APIRouter()


async def _authenticate_ws(token: str) -> tuple[str, str] | None:
    """Validate JWT and return (user_id, org_id) or None on failure."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if user_id is None or token_type != "access":
            return None
    except JWTError:
        return None

    async with AsyncSessionLocal() as db:  # type: ignore[attr-defined]
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:  # type: ignore[truthy-bool]
            return None

        org_id = str(user.org_id)
        result = await db.execute(
            select(Organization.id).where(Organization.id == org_id)
        )
        if result.scalar_one_or_none() is None:
            return None

    return (user_id, org_id)


async def _redis_listener(
    ws: WebSocket,
    pubsub: aioredis.client.PubSub,
) -> None:
    """Forward Redis pub/sub messages to WebSocket client."""
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
    """Listen for client messages (ping/pong, detect disconnect)."""
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/events")
async def websocket_events(ws: WebSocket) -> None:
    """Stream real-time events to authenticated clients via WebSocket."""
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=4001, reason="Missing token")
        return

    auth_result = await _authenticate_ws(token)
    if auth_result is None:
        await ws.accept()
        await ws.close(code=4001, reason="Authentication failed")
        return

    user_id, org_id = auth_result

    await ws.accept()
    logger.info("WebSocket connected: user=%s org=%s", user_id, org_id)

    await ws.send_json({
        "type": "connected",
        "data": {"orgId": org_id},
    })

    redis_client = aioredis.from_url(settings.REDIS_URL)
    pubsub = redis_client.pubsub()
    channel = f"org:{org_id}:events"

    try:
        await pubsub.subscribe(channel)

        listener = asyncio.create_task(_redis_listener(ws, pubsub))
        receiver = asyncio.create_task(_ws_receiver(ws))

        done, pending = await asyncio.wait(
            [listener, receiver],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error for user=%s org=%s", user_id, org_id)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await redis_client.close()
        logger.info("WebSocket disconnected: user=%s org=%s", user_id, org_id)
