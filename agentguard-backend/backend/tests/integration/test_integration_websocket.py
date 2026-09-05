"""Integration coverage for single-use WebSocket authentication tickets."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import Response, WebSocketDisconnect
from httpx import ASGITransport, AsyncClient

from app.api.websocket import limiter as websocket_ticket_limiter
from app.main import app


@pytest.fixture(autouse=True)
def _reset_websocket_ticket_rate_limit() -> None:
    """Keep each ticket contract test independent of limiter state."""
    websocket_ticket_limiter.reset()


class FakePubSub:
    def __init__(self) -> None:
        self.subscribe = AsyncMock()
        self.unsubscribe = AsyncMock()
        self.close = AsyncMock()

    async def get_message(self, **_kwargs: Any) -> None:
        return None


class FakeRedis:
    """Small Redis double with shared storage and atomic GETDEL semantics."""

    def __init__(self, store: dict[str, str] | None = None) -> None:
        self.store = store if store is not None else {}
        self.set_calls: list[tuple[str, str, int | None, bool | None]] = []
        self.getdel_calls: list[str] = []
        self.pubsub_instance = FakePubSub()
        self.closed = False

    async def set(
        self,
        key: str,
        value: str,
        *,
        ex: int | None = None,
        nx: bool | None = None,
    ) -> bool:
        self.set_calls.append((key, value, ex, nx))
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    async def getdel(self, key: str) -> str | None:
        self.getdel_calls.append(key)
        return self.store.pop(key, None)

    def pubsub(self) -> FakePubSub:
        return self.pubsub_instance

    async def aclose(self) -> None:
        self.closed = True


def _session_context(db_session: Any) -> AsyncMock:
    context = AsyncMock()
    context.__aenter__ = AsyncMock(return_value=db_session)
    context.__aexit__ = AsyncMock(return_value=None)
    return context


def _websocket(protocols: list[str], *, disconnect: bool = True) -> AsyncMock:
    ws = AsyncMock()
    ws.headers = {"sec-websocket-protocol": ", ".join(protocols)}
    ws.query_params = {}
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.send_json = AsyncMock()
    if disconnect:
        ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
    return ws


class TestWebSocketRoutes:
    async def test_regular_http_request_to_socket_is_rejected(self) -> None:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/ws/events")

        assert response.status_code in (400, 403, 404, 405, 426)

    def test_ticket_and_socket_routes_are_registered(self) -> None:
        routes = [route.path for route in app.routes if hasattr(route, "path")]  # type: ignore[attr-defined]
        assert "/api/v1/ws/ticket" in routes
        assert "/ws/events" in routes


class TestTicketIssuance:
    async def test_ticket_endpoint_requires_user_authentication(self) -> None:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/ws/ticket")

        assert response.status_code in (401, 403)

    async def test_ticket_is_opaque_and_only_its_digest_is_stored(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        user: Any,
    ) -> None:
        redis = FakeRedis()

        with patch("app.api.websocket.aioredis.from_url", return_value=redis):
            response = await client.post("/api/v1/ws/ticket", headers=auth_headers)

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["pragma"] == "no-cache"
        body = response.json()
        ticket = body["ticket"]
        assert re.fullmatch(r"[A-Za-z0-9_-]{43}", ticket)
        assert body["expiresIn"] <= 30

        assert len(redis.set_calls) == 1
        key, stored_payload, ttl, only_if_absent = redis.set_calls[0]
        digest = hashlib.sha256(ticket.encode("ascii")).hexdigest()
        assert key == f"ws:ticket:{digest}"
        assert ticket not in key
        assert ticket not in stored_payload
        assert ttl == body["expiresIn"]
        assert ttl is not None and ttl <= 30
        assert only_if_absent is True
        assert json.loads(stored_payload) == {
            "user_id": str(user.id),
            "org_id": str(user.org_id),
        }
        assert redis.closed is True

    async def test_ticket_endpoint_returns_generic_503_when_redis_fails(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        redis = FakeRedis()
        redis.set = AsyncMock(side_effect=RuntimeError("redis://secret@cache unavailable"))

        with patch("app.api.websocket.aioredis.from_url", return_value=redis):
            response = await client.post("/api/v1/ws/ticket", headers=auth_headers)

        assert response.status_code == 503
        assert response.json() == {"detail": "WebSocket ticket service unavailable"}
        assert "redis" not in response.text.lower()
        assert "secret" not in response.text.lower()
        assert redis.closed is True

    async def test_ticket_handler_explicitly_marks_capability_non_cacheable(
        self,
        user: Any,
    ) -> None:
        from app.api.websocket import create_websocket_ticket

        redis = FakeRedis()
        response = Response()
        undecorated_handler = create_websocket_ticket.__wrapped__  # type: ignore[attr-defined]

        with patch("app.api.websocket.aioredis.from_url", return_value=redis):
            result = await undecorated_handler(
                request=AsyncMock(),
                response=response,
                current_user=user,
            )

        assert "ticket" in result
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["pragma"] == "no-cache"
        assert redis.closed is True

    async def test_ticket_issuance_is_rate_limited_per_client_ip(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        redis_clients: list[FakeRedis] = []

        def new_redis_client(*_args: Any, **_kwargs: Any) -> FakeRedis:
            redis_client = FakeRedis()
            redis_clients.append(redis_client)
            return redis_client

        with patch(
            "app.api.websocket.aioredis.from_url",
            side_effect=new_redis_client,
        ):
            responses = [await client.post("/api/v1/ws/ticket", headers=auth_headers) for _request_number in range(11)]

        assert [response.status_code for response in responses[:10]] == [200] * 10
        assert responses[10].status_code == 429
        assert len(redis_clients) == 10
        assert all(redis_client.closed for redis_client in redis_clients)


class TestTicketProtocolParsing:
    @pytest.mark.parametrize(
        "protocols",
        [
            [],
            ["agentguard.v1"],
            ["agentguard.ticket.abc"],
            ["agentguard.ticket.abc", "agentguard.v1"],
            ["agentguard.v1", "agentguard.ticket.abc", "extra"],
            ["agentguard.v1", "agentguard.ticket.contains.dot"],
        ],
    )
    async def test_missing_or_malformed_subprotocols_close_with_4001(
        self,
        protocols: list[str],
    ) -> None:
        from app.api.websocket import websocket_events

        ws = _websocket(protocols)
        with patch("app.api.websocket.aioredis.from_url") as redis_factory:
            await websocket_events(ws)

        ws.accept.assert_not_called()
        ws.close.assert_called_once_with(code=4001, reason="Authentication failed")
        redis_factory.assert_not_called()

    async def test_query_jwt_is_not_an_authentication_path(self) -> None:
        from app.api.websocket import websocket_events

        ws = _websocket([])
        ws.query_params = {"token": "long-lived-access-token"}

        with patch("app.api.websocket.aioredis.from_url") as redis_factory:
            await websocket_events(ws)

        ws.accept.assert_not_called()
        ws.close.assert_called_once_with(code=4001, reason="Authentication failed")
        redis_factory.assert_not_called()


class TestTicketConsumption:
    async def test_ticket_is_consumed_once_and_only_safe_protocol_is_echoed(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        db_session: Any,
        user: Any,
    ) -> None:
        from app.api.websocket import websocket_events

        shared_store: dict[str, str] = {}
        issue_redis = FakeRedis(shared_store)
        consume_redis = FakeRedis(shared_store)
        pubsub_redis = FakeRedis(shared_store)
        replay_redis = FakeRedis(shared_store)
        redis_connections = iter([issue_redis, consume_redis, pubsub_redis, replay_redis])

        with (
            patch(
                "app.api.websocket.aioredis.from_url",
                side_effect=lambda *_args, **_kwargs: next(redis_connections),
            ),
            patch(
                "app.api.websocket.AsyncSessionLocal",
                return_value=_session_context(db_session),
            ),
        ):
            response = await client.post("/api/v1/ws/ticket", headers=auth_headers)
            ticket = response.json()["ticket"]
            protocols = ["agentguard.v1", f"agentguard.ticket.{ticket}"]

            ws = _websocket(protocols)
            await websocket_events(ws)

            replay_ws = _websocket(protocols)
            await websocket_events(replay_ws)

        assert response.status_code == 200
        ws.accept.assert_called_once_with(subprotocol="agentguard.v1")
        ws.send_json.assert_called_once_with({"type": "connected", "data": {"orgId": str(user.org_id)}})
        pubsub_redis.pubsub_instance.subscribe.assert_awaited_once_with(f"org:{user.org_id}:events")

        expected_key = f"ws:ticket:{hashlib.sha256(ticket.encode('ascii')).hexdigest()}"
        assert consume_redis.getdel_calls == [expected_key]
        assert replay_redis.getdel_calls == [expected_key]
        assert ticket not in expected_key
        assert shared_store == {}

        replay_ws.accept.assert_not_called()
        replay_ws.close.assert_called_once_with(code=4001, reason="Authentication failed")
        assert issue_redis.closed is True
        assert consume_redis.closed is True
        assert pubsub_redis.closed is True
        assert replay_redis.closed is True

    async def test_expired_ticket_closes_with_4001(self) -> None:
        from app.api.websocket import websocket_events

        ticket = "a" * 43
        ws = _websocket(["agentguard.v1", f"agentguard.ticket.{ticket}"])
        redis = FakeRedis()

        with patch("app.api.websocket.aioredis.from_url", return_value=redis):
            await websocket_events(ws)

        ws.accept.assert_not_called()
        ws.close.assert_called_once_with(code=4001, reason="Authentication failed")
        assert redis.closed is True

    async def test_cross_org_ticket_is_consumed_and_rejected(
        self,
        db_session: Any,
        user: Any,
    ) -> None:
        from app.api.websocket import websocket_events

        ticket = "b" * 43
        key = f"ws:ticket:{hashlib.sha256(ticket.encode('ascii')).hexdigest()}"
        redis = FakeRedis({key: json.dumps({"user_id": str(user.id), "org_id": str(uuid.uuid4())})})
        ws = _websocket(["agentguard.v1", f"agentguard.ticket.{ticket}"])

        with (
            patch("app.api.websocket.aioredis.from_url", return_value=redis),
            patch(
                "app.api.websocket.AsyncSessionLocal",
                return_value=_session_context(db_session),
            ),
        ):
            await websocket_events(ws)

        ws.accept.assert_not_called()
        ws.close.assert_called_once_with(code=4001, reason="Authentication failed")
        assert key not in redis.store

    @pytest.mark.parametrize(
        "payload",
        [
            "not-json",
            "{}",
            '{"user_id":"not-a-uuid","org_id":"also-not-a-uuid"}',
            '{"user_id":"00000000-0000-0000-0000-000000000000"}',
        ],
    )
    async def test_malformed_ticket_payload_is_rejected(self, payload: str) -> None:
        from app.api.websocket import websocket_events

        ticket = "c" * 43
        key = f"ws:ticket:{hashlib.sha256(ticket.encode('ascii')).hexdigest()}"
        redis = FakeRedis({key: payload})
        ws = _websocket(["agentguard.v1", f"agentguard.ticket.{ticket}"])

        with patch("app.api.websocket.aioredis.from_url", return_value=redis):
            await websocket_events(ws)

        ws.accept.assert_not_called()
        ws.close.assert_called_once_with(code=4001, reason="Authentication failed")
        assert key not in redis.store

    async def test_redis_failure_during_consume_fails_closed(self) -> None:
        from app.api.websocket import websocket_events

        ticket = "d" * 43
        redis = FakeRedis()
        redis.getdel = AsyncMock(side_effect=RuntimeError("redis secret detail"))
        ws = _websocket(["agentguard.v1", f"agentguard.ticket.{ticket}"])

        with patch("app.api.websocket.aioredis.from_url", return_value=redis):
            await websocket_events(ws)

        ws.accept.assert_not_called()
        ws.close.assert_called_once_with(code=4001, reason="Authentication failed")
        assert redis.closed is True

    async def test_database_failure_during_consume_fails_closed(
        self,
        user: Any,
    ) -> None:
        from app.api.websocket import websocket_events

        ticket = "e" * 43
        key = f"ws:ticket:{hashlib.sha256(ticket.encode('ascii')).hexdigest()}"
        redis = FakeRedis({key: json.dumps({"user_id": str(user.id), "org_id": str(user.org_id)})})
        ws = _websocket(["agentguard.v1", f"agentguard.ticket.{ticket}"])

        with (
            patch("app.api.websocket.aioredis.from_url", return_value=redis),
            patch(
                "app.api.websocket.AsyncSessionLocal",
                side_effect=RuntimeError("postgresql://secret@db unavailable"),
            ),
            patch("app.api.websocket.logger.warning") as warning,
        ):
            await websocket_events(ws)

        ws.accept.assert_not_called()
        ws.close.assert_called_once_with(code=4001, reason="Authentication failed")
        warning.assert_called_once_with("WebSocket ticket identity revalidation failed")
        assert "secret" not in str(warning.call_args_list)
        assert redis.closed is True


class TestRedisListener:
    async def test_listener_forwards_bytes_message(self) -> None:
        from app.api.websocket import _redis_listener

        ws = AsyncMock()
        pubsub = AsyncMock()
        pubsub.get_message = AsyncMock(
            side_effect=[
                {
                    "type": "message",
                    "data": b'{"type":"incident","data":{"id":"test"}}',
                },
                asyncio.CancelledError(),
            ]
        )

        with pytest.raises(asyncio.CancelledError):
            await _redis_listener(ws, pubsub)

        ws.send_text.assert_awaited_once_with('{"type":"incident","data":{"id":"test"}}')

    async def test_event_task_exception_is_consumed_and_cleaned_up(self) -> None:
        from app.api.websocket import websocket_events

        ticket = "f" * 43
        user_id = str(uuid.uuid4())
        org_id = str(uuid.uuid4())
        redis = FakeRedis()
        redis.pubsub_instance.get_message = AsyncMock(side_effect=RuntimeError("redis://secret@cache stream failed"))
        ws = _websocket(
            ["agentguard.v1", f"agentguard.ticket.{ticket}"],
            disconnect=False,
        )
        never_received = asyncio.Event()

        async def wait_for_message() -> None:
            await never_received.wait()

        ws.receive_text = AsyncMock(side_effect=wait_for_message)

        with (
            patch(
                "app.api.websocket._consume_ticket",
                new=AsyncMock(return_value=(user_id, org_id)),
            ),
            patch(
                "app.api.websocket.aioredis.from_url",
                return_value=redis,
            ),
            patch("app.api.websocket.logger.warning") as warning,
        ):
            await websocket_events(ws)

        warning.assert_any_call("WebSocket event stream failed for user=%s org=%s", user_id, org_id)
        assert "secret" not in str(warning.call_args_list)
        redis.pubsub_instance.unsubscribe.assert_awaited_once_with(f"org:{org_id}:events")
        redis.pubsub_instance.close.assert_awaited_once()
        assert redis.closed is True
