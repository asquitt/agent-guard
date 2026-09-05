"""Health check service — detailed component status."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal


async def check_components() -> dict[str, Any]:
    """Check all infrastructure components and return structured status.

    Returns dict with 'status' and 'components' list.
    """
    components: list[dict[str, Any]] = []

    # Database
    db_status = await _check_database()
    components.append(db_status)

    # Redis
    redis_status = await _check_redis()
    components.append(redis_status)

    # Celery workers (best-effort, non-blocking)
    celery_status = await _check_celery()
    components.append(celery_status)

    # Derive overall status
    statuses = [c["status"] for c in components]
    if all(s == "ok" for s in statuses):
        overall = "healthy"
    elif any(s == "error" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"

    return {"status": overall, "components": components}


async def _check_database() -> dict[str, Any]:
    """Check database connectivity with SELECT 1."""
    start = time.monotonic()
    try:
        async with AsyncSessionLocal() as session:  # pyright: ignore[reportGeneralTypeIssues]
            await session.execute(text("SELECT 1"))
        elapsed = int((time.monotonic() - start) * 1000)
        return {"name": "database", "status": "ok", "response_time_ms": elapsed}
    except Exception:
        elapsed = int((time.monotonic() - start) * 1000)
        return {
            "name": "database",
            "status": "error",
            "response_time_ms": elapsed,
            "message": "Database unavailable",
        }


async def _check_redis() -> dict[str, Any]:
    """Check Redis connectivity with PING."""
    start = time.monotonic()
    redis_client: Any = None
    available = False
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        available = True
    except Exception:
        pass
    finally:
        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception:
                available = False

    elapsed = int((time.monotonic() - start) * 1000)
    if available:
        return {"name": "redis", "status": "ok", "response_time_ms": elapsed}
    return {
        "name": "redis",
        "status": "error",
        "response_time_ms": elapsed,
        "message": "Redis unavailable",
    }


async def _check_celery() -> dict[str, Any]:
    """Check if Celery workers are reachable.

    Uses a short timeout since worker ping can be slow.
    Falls back to 'unknown' if inspection times out.
    """
    start = time.monotonic()
    try:
        from app.tasks.celery_app import celery_app

        def ping_workers():
            inspector = celery_app.control.inspect(timeout=2.0)
            return inspector.ping()

        # Celery inspection is synchronous. Keep it off the API event loop and
        # bound the caller's wait even if the transport ignores its own timeout.
        ping_result = await asyncio.wait_for(
            asyncio.to_thread(ping_workers),
            timeout=2.5,
        )
        elapsed = int((time.monotonic() - start) * 1000)

        if ping_result:
            worker_count = len(ping_result)
            return {
                "name": "celery",
                "status": "ok",
                "response_time_ms": elapsed,
                "message": f"{worker_count} worker(s) active",
            }
        return {"name": "celery", "status": "degraded", "response_time_ms": elapsed, "message": "No workers found"}
    except Exception:
        elapsed = int((time.monotonic() - start) * 1000)
        return {
            "name": "celery",
            "status": "degraded",
            "response_time_ms": elapsed,
            "message": "Worker status unavailable",
        }
