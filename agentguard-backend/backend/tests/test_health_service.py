"""Regression tests for the public detailed health response."""

import asyncio
import time as wall_time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import redis.asyncio as aioredis
from httpx import ASGITransport, AsyncClient

from app.core import database as database_module
from app.main import app
from app.services import health_service
from app.tasks.celery_app import celery_app


class _SequenceClock:
    def __init__(self, values: list[float]) -> None:
        self._values = iter(values)

    def monotonic(self) -> float:
        return next(self._values)


def _session_context(db_session: AsyncMock) -> AsyncMock:
    context = AsyncMock()
    context.__aenter__ = AsyncMock(return_value=db_session)
    context.__aexit__ = AsyncMock(return_value=None)
    return context


@pytest.mark.parametrize(
    ("ping_error", "close_error", "expected_status"),
    [
        (None, None, "ok"),
        (RuntimeError("redis://secret@cache unavailable"), None, "error"),
        (None, RuntimeError("redis cleanup failed"), "error"),
    ],
)
async def test_redis_health_always_closes_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    ping_error: Exception | None,
    close_error: Exception | None,
    expected_status: str,
) -> None:
    """Redis health must close its client on success and every failure path."""
    redis_client = SimpleNamespace(
        ping=AsyncMock(side_effect=ping_error),
        aclose=AsyncMock(side_effect=close_error),
    )
    monkeypatch.setattr(health_service.aioredis, "from_url", lambda _url: redis_client)

    result = await health_service._check_redis()

    assert result["status"] == expected_status
    if expected_status == "error":
        assert result["message"] == "Redis unavailable"
        assert "secret" not in str(result)
    redis_client.aclose.assert_awaited_once()


@pytest.mark.parametrize(
    ("ping_error", "close_error", "expected_status", "expected_http_status"),
    [
        (None, None, "ok", 200),
        (RuntimeError("redis://secret@cache unavailable"), None, "error", 503),
        (None, RuntimeError("redis cleanup failed"), "error", 503),
    ],
)
async def test_readiness_always_closes_redis_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    ping_error: Exception | None,
    close_error: Exception | None,
    expected_status: str,
    expected_http_status: int,
) -> None:
    """The readiness probe owns and closes its Redis client deterministically."""
    db_session = AsyncMock()
    db_session.execute = AsyncMock(return_value=None)
    monkeypatch.setattr(
        database_module,
        "AsyncSessionLocal",
        lambda: _session_context(db_session),
    )
    redis_client = SimpleNamespace(
        ping=AsyncMock(side_effect=ping_error),
        aclose=AsyncMock(side_effect=close_error),
    )
    monkeypatch.setattr(aioredis, "from_url", lambda _url: redis_client)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == expected_http_status
    assert response.json()["checks"] == {"database": "ok", "redis": expected_status}
    assert "secret" not in response.text
    redis_client.aclose.assert_awaited_once()


async def test_detailed_health_redacts_dependency_exceptions(monkeypatch) -> None:
    """Infrastructure errors must not disclose connection details to callers."""
    database_error = (
        "could not connect to postgresql://agentguard:db-password@db.internal:5432/agentguard\n"
        "Traceback: socket failure"
    )
    redis_error = "redis://:redis-password@cache.internal:6379/0 connection refused"
    celery_error = "amqp://worker:broker-password@rabbit.internal:5672/ unavailable"

    def unavailable_database():
        raise RuntimeError(database_error)

    def unavailable_redis(_url: str):
        raise RuntimeError(redis_error)

    class UnavailableInspector:
        def ping(self):
            raise RuntimeError(celery_error)

    monkeypatch.setattr(health_service, "AsyncSessionLocal", unavailable_database)
    monkeypatch.setattr(health_service.aioredis, "from_url", unavailable_redis)
    monkeypatch.setattr(
        celery_app.control,
        "inspect",
        lambda timeout: UnavailableInspector(),
    )
    monkeypatch.setattr(
        health_service,
        "time",
        SimpleNamespace(monotonic=_SequenceClock([0, 1, 2, 4, 5, 8]).monotonic),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/detailed")

    assert response.status_code == 503
    assert response.json() == {
        "status": "unhealthy",
        "components": [
            {
                "name": "database",
                "status": "error",
                "response_time_ms": 1000,
                "message": "Database unavailable",
            },
            {
                "name": "redis",
                "status": "error",
                "response_time_ms": 2000,
                "message": "Redis unavailable",
            },
            {
                "name": "celery",
                "status": "degraded",
                "response_time_ms": 3000,
                "message": "Worker status unavailable",
            },
        ],
    }
    for sensitive_value in (
        "db-password",
        "db.internal",
        "redis-password",
        "cache.internal",
        "broker-password",
        "rabbit.internal",
        "Traceback",
    ):
        assert sensitive_value not in response.text


async def test_celery_health_retains_safe_worker_count(monkeypatch) -> None:
    """A successful worker ping may expose the useful aggregate count only."""

    class HealthyInspector:
        def ping(self):
            return {"worker-a": {"ok": "pong"}, "worker-b": {"ok": "pong"}}

    monkeypatch.setattr(
        celery_app.control,
        "inspect",
        lambda timeout: HealthyInspector(),
    )
    monkeypatch.setattr(
        health_service,
        "time",
        SimpleNamespace(monotonic=_SequenceClock([10, 11]).monotonic),
    )

    result = await health_service._check_celery()

    assert result == {
        "name": "celery",
        "status": "ok",
        "response_time_ms": 1000,
        "message": "2 worker(s) active",
    }


async def test_celery_health_does_not_block_the_event_loop(monkeypatch) -> None:
    """A slow synchronous worker inspection must not stall unrelated API work."""

    class SlowInspector:
        def ping(self):
            wall_time.sleep(0.2)
            return {"worker-a": {"ok": "pong"}}

    monkeypatch.setattr(
        celery_app.control,
        "inspect",
        lambda timeout: SlowInspector(),
    )

    health_task = asyncio.create_task(health_service._check_celery())
    await asyncio.wait_for(asyncio.sleep(0.01), timeout=0.1)

    assert not health_task.done()
    assert (await health_task)["status"] == "ok"
