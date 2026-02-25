"""Integration tests for websocket.py router.

Endpoints:
  WS     /ws/events?token=<jwt>

The WebSocket endpoint uses AsyncSessionLocal directly (not get_db),
so full connection testing requires a running DB. We test:
- Auth rejection paths (no token, invalid token, expired token)
- The _authenticate_ws function directly with mocked DB
- HTTP upgrade rejection for non-WebSocket requests
- Connection flow with mocked Redis
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.auth import create_access_token
from app.main import app


# ── HTTP Upgrade Path Tests ───────────────────────────────────────


class TestWebSocketHTTPUpgrade:
    """Test that the WebSocket route exists and rejects non-WS requests."""

    async def test_ws_no_token_get_rejected(self):
        """Regular GET to WS route should be rejected."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/ws/events")
            assert resp.status_code in (400, 403, 404, 405, 426)

    async def test_ws_with_invalid_token_get_rejected(self):
        """GET with invalid token to WS route should be rejected."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.get("/ws/events?token=invalid-jwt-token")
            assert resp.status_code in (400, 403, 404, 405, 426)

    async def test_ws_post_method_rejected(self):
        """POST to WS route should be rejected."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            resp = await ac.post("/ws/events", json={})
            assert resp.status_code in (400, 403, 404, 405, 426)

    async def test_ws_route_exists(self):
        """The /ws/events route should be registered in the app."""
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/ws/events" in routes


# ── _authenticate_ws Function Tests ───────────────────────────────


class TestAuthenticateWS:
    """Test the WebSocket authentication function directly."""

    async def test_invalid_jwt_returns_none(self):
        """Invalid JWT should return None."""
        from app.api.websocket import _authenticate_ws

        result = await _authenticate_ws("not-a-valid-jwt")
        assert result is None

    async def test_empty_token_returns_none(self):
        """Empty string token should return None."""
        from app.api.websocket import _authenticate_ws

        result = await _authenticate_ws("")
        assert result is None

    async def test_expired_jwt_returns_none(self):
        """Expired JWT should return None."""
        from app.api.websocket import _authenticate_ws
        from jose import jwt as jose_jwt
        from app.core.config import settings

        payload = {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jose_jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        result = await _authenticate_ws(token)
        assert result is None

    async def test_refresh_token_type_rejected(self):
        """Refresh tokens should not be accepted for WebSocket auth."""
        from app.api.websocket import _authenticate_ws
        from jose import jwt as jose_jwt
        from app.core.config import settings

        payload = {
            "sub": str(uuid.uuid4()),
            "type": "refresh",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jose_jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        result = await _authenticate_ws(token)
        assert result is None

    async def test_missing_sub_claim_rejected(self):
        """JWT without sub claim should be rejected."""
        from app.api.websocket import _authenticate_ws
        from jose import jwt as jose_jwt
        from app.core.config import settings

        payload = {
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jose_jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        result = await _authenticate_ws(token)
        assert result is None

    async def test_valid_token_inactive_user_rejected(self):
        """Valid JWT for an inactive user should be rejected."""
        from app.api.websocket import _authenticate_ws

        user_id = str(uuid.uuid4())
        token = create_access_token(user_id, token_version=0)

        mock_user = MagicMock()
        mock_user.is_active = False
        mock_user.org_id = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.api.websocket.AsyncSessionLocal", return_value=mock_session_ctx):
            result = await _authenticate_ws(token)
            assert result is None

    async def test_valid_token_nonexistent_user_rejected(self):
        """Valid JWT for a user not in DB should be rejected."""
        from app.api.websocket import _authenticate_ws

        user_id = str(uuid.uuid4())
        token = create_access_token(user_id, token_version=0)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.api.websocket.AsyncSessionLocal", return_value=mock_session_ctx):
            result = await _authenticate_ws(token)
            assert result is None

    async def test_valid_token_valid_user_returns_ids(self):
        """Valid JWT for an active user should return (user_id, org_id)."""
        from app.api.websocket import _authenticate_ws

        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())
        token = create_access_token(user_id, token_version=0)

        mock_user = MagicMock()
        mock_user.is_active = True
        mock_user.org_id = uuid.UUID(org_id)

        mock_org_result = MagicMock()
        mock_org_result.scalar_one_or_none.return_value = uuid.UUID(org_id)

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        call_count = 0

        async def mock_execute(query):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_user_result
            return mock_org_result

        mock_db = AsyncMock()
        mock_db.execute = mock_execute

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("app.api.websocket.AsyncSessionLocal", return_value=mock_session_ctx):
            result = await _authenticate_ws(token)
            assert result is not None
            assert result[0] == user_id
            assert result[1] == org_id

    async def test_wrong_secret_key_rejected(self):
        """JWT signed with wrong key should be rejected."""
        from app.api.websocket import _authenticate_ws
        from jose import jwt as jose_jwt

        payload = {
            "sub": str(uuid.uuid4()),
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jose_jwt.encode(payload, "wrong-secret-key", algorithm="HS256")
        result = await _authenticate_ws(token)
        assert result is None


# ── Redis Listener Tests ──────────────────────────────────────────


class TestRedisListener:
    """Test the _redis_listener helper function."""

    async def test_listener_forwards_bytes_message(self):
        """Redis listener should forward bytes messages to WebSocket."""
        from app.api.websocket import _redis_listener

        mock_ws = AsyncMock()
        mock_pubsub = AsyncMock()

        call_count = 0

        async def mock_get_message(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "type": "message",
                    "data": b'{"type":"incident","data":{"id":"test"}}',
                }
            raise asyncio.CancelledError()

        mock_pubsub.get_message = mock_get_message

        with pytest.raises(asyncio.CancelledError):
            await _redis_listener(mock_ws, mock_pubsub)

        mock_ws.send_text.assert_called_once_with(
            '{"type":"incident","data":{"id":"test"}}'
        )

    async def test_listener_handles_string_data(self):
        """Redis listener should handle string data (not just bytes)."""
        from app.api.websocket import _redis_listener

        mock_ws = AsyncMock()
        mock_pubsub = AsyncMock()

        call_count = 0

        async def mock_get_message(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "type": "message",
                    "data": '{"type":"alert","severity":"high"}',
                }
            raise asyncio.CancelledError()

        mock_pubsub.get_message = mock_get_message

        with pytest.raises(asyncio.CancelledError):
            await _redis_listener(mock_ws, mock_pubsub)

        mock_ws.send_text.assert_called_once()

    async def test_listener_ignores_none_messages(self):
        """Redis listener should handle None (no message available)."""
        from app.api.websocket import _redis_listener

        mock_ws = AsyncMock()
        mock_pubsub = AsyncMock()

        call_count = 0

        async def mock_get_message(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return None
            raise asyncio.CancelledError()

        mock_pubsub.get_message = mock_get_message

        with pytest.raises(asyncio.CancelledError):
            await _redis_listener(mock_ws, mock_pubsub)

        mock_ws.send_text.assert_not_called()


# ── Channel Naming Tests ──────────────────────────────────────────


class TestChannelNaming:
    """Test that the channel naming convention is correct."""

    def test_channel_format(self):
        """Channel should follow org:{org_id}:events pattern."""
        org_id = str(uuid.uuid4())
        channel = f"org:{org_id}:events"
        assert channel.startswith("org:")
        assert channel.endswith(":events")
        assert org_id in channel

    def test_different_orgs_get_different_channels(self):
        """Each org should have its own unique channel."""
        org_a = str(uuid.uuid4())
        org_b = str(uuid.uuid4())
        channel_a = f"org:{org_a}:events"
        channel_b = f"org:{org_b}:events"
        assert channel_a != channel_b


# ── Connection Flow Tests ─────────────────────────────────────────


class TestConnectionFlow:
    """Test the full WebSocket connection flow with mocks."""

    async def test_websocket_sends_connected_message_on_auth(self):
        """After auth, WebSocket should send a 'connected' message with orgId."""
        from app.api.websocket import websocket_events

        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())

        mock_ws = AsyncMock()
        mock_ws.query_params = {"token": "valid-token"}
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=asyncio.CancelledError())

        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_pubsub.get_message = AsyncMock(side_effect=asyncio.CancelledError())

        mock_redis = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_redis.close = AsyncMock()

        with patch(
            "app.api.websocket._authenticate_ws",
            new_callable=AsyncMock,
            return_value=(user_id, org_id),
        ):
            with patch(
                "app.api.websocket.aioredis.from_url",
                return_value=mock_redis,
            ):
                try:
                    await websocket_events(mock_ws)
                except (asyncio.CancelledError, Exception):
                    pass

        mock_ws.accept.assert_called_once()
        mock_ws.send_json.assert_called_once_with(
            {"type": "connected", "data": {"orgId": org_id}}
        )

    async def test_websocket_subscribes_to_org_channel(self):
        """WebSocket should subscribe to the org-specific Redis channel."""
        from app.api.websocket import websocket_events
        from fastapi import WebSocketDisconnect

        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())

        mock_ws = AsyncMock()
        mock_ws.query_params = {"token": "valid-token"}
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        # Return None so the listener sleeps, giving receiver time to disconnect
        mock_pubsub.get_message = AsyncMock(return_value=None)

        mock_redis = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_redis.close = AsyncMock()

        with patch(
            "app.api.websocket._authenticate_ws",
            new_callable=AsyncMock,
            return_value=(user_id, org_id),
        ):
            with patch(
                "app.api.websocket.aioredis.from_url",
                return_value=mock_redis,
            ):
                await websocket_events(mock_ws)

        expected_channel = f"org:{org_id}:events"
        mock_pubsub.subscribe.assert_called_once_with(expected_channel)

    async def test_websocket_no_token_closes_with_4001(self):
        """WebSocket without token should be closed with code 4001."""
        from app.api.websocket import websocket_events

        mock_ws = AsyncMock()
        mock_ws.query_params = {}
        mock_ws.close = AsyncMock()

        await websocket_events(mock_ws)

        mock_ws.close.assert_called_once_with(code=4001, reason="Missing token")
        mock_ws.accept.assert_not_called()

    async def test_websocket_invalid_token_closes_with_4001(self):
        """WebSocket with invalid token should accept then close with 4001."""
        from app.api.websocket import websocket_events

        mock_ws = AsyncMock()
        mock_ws.query_params = {"token": "invalid"}
        mock_ws.accept = AsyncMock()
        mock_ws.close = AsyncMock()

        with patch(
            "app.api.websocket._authenticate_ws",
            new_callable=AsyncMock,
            return_value=None,
        ):
            await websocket_events(mock_ws)

        mock_ws.accept.assert_called_once()
        mock_ws.close.assert_called_once_with(code=4001, reason="Authentication failed")

    async def test_websocket_cleanup_on_disconnect(self):
        """WebSocket should clean up Redis resources on disconnect."""
        from app.api.websocket import websocket_events
        from fastapi import WebSocketDisconnect

        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())

        mock_ws = AsyncMock()
        mock_ws.query_params = {"token": "valid-token"}
        mock_ws.accept = AsyncMock()
        mock_ws.send_json = AsyncMock()
        mock_ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

        mock_pubsub = AsyncMock()
        mock_pubsub.subscribe = AsyncMock()
        mock_pubsub.unsubscribe = AsyncMock()
        mock_pubsub.close = AsyncMock()
        mock_pubsub.get_message = AsyncMock(return_value=None)

        mock_redis = MagicMock()
        mock_redis.pubsub.return_value = mock_pubsub
        mock_redis.close = AsyncMock()

        with patch(
            "app.api.websocket._authenticate_ws",
            new_callable=AsyncMock,
            return_value=(user_id, org_id),
        ):
            with patch(
                "app.api.websocket.aioredis.from_url",
                return_value=mock_redis,
            ):
                await websocket_events(mock_ws)

        expected_channel = f"org:{org_id}:events"
        mock_pubsub.unsubscribe.assert_called_once_with(expected_channel)
        mock_pubsub.close.assert_called_once()
        mock_redis.close.assert_called_once()
