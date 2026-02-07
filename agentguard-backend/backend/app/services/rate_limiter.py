"""Redis-based sliding window rate limiter for proxy requests."""

from __future__ import annotations

import logging
import time

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy-initialized async Redis client
_redis: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL)
    return _redis


class RateLimitExceeded(Exception):
    """Raised when a rate limit is exceeded."""

    def __init__(self, limit: int, window: str, current: int, retry_after: int) -> None:
        self.limit = limit
        self.window = window
        self.current = current
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded: {current}/{limit} per {window}")


# Window durations in seconds
_WINDOWS: dict[str, int] = {
    "minute": 60,
    "hour": 3600,
    "day": 86400,
}


async def check_rate_limit(
    org_id: str,
    requests_per_minute: int | None = None,
    requests_per_hour: int | None = None,
    requests_per_day: int | None = None,
) -> None:
    """Check rate limits for an org using Redis sliding window.

    Raises RateLimitExceeded if any limit is exceeded.
    Uses sorted sets with timestamps for accurate sliding windows.
    """
    now = time.time()
    client = _get_redis()

    checks: list[tuple[str, int, int]] = []  # (window_name, limit, window_seconds)
    if requests_per_minute is not None:
        checks.append(("minute", requests_per_minute, _WINDOWS["minute"]))
    if requests_per_hour is not None:
        checks.append(("hour", requests_per_hour, _WINDOWS["hour"]))
    if requests_per_day is not None:
        checks.append(("day", requests_per_day, _WINDOWS["day"]))

    if not checks:
        return

    try:
        for window_name, limit, window_secs in checks:
            key = f"ratelimit:org:{org_id}:{window_name}"
            cutoff = now - window_secs

            # Count requests in the current window
            count = await client.zcount(key, cutoff, "+inf")

            if count >= limit:
                # Calculate retry-after: time until oldest entry expires
                oldest = await client.zrange(key, 0, 0, withscores=True)
                retry_after = 1
                if oldest:
                    oldest_ts = float(oldest[0][1])
                    retry_after = max(1, int(oldest_ts + window_secs - now))

                raise RateLimitExceeded(
                    limit=limit,
                    window=window_name,
                    current=int(count),
                    retry_after=retry_after,
                )
    except RateLimitExceeded:
        raise
    except Exception:
        # Fail open — if Redis is down, don't block requests
        logger.warning("Rate limit check failed for org %s, allowing request", org_id)


async def record_request(org_id: str) -> None:
    """Record a request for rate limiting purposes.

    Adds current timestamp to sliding window sorted sets.
    Sets TTL to auto-expire old entries.
    """
    now = time.time()
    member = f"{now}"
    client = _get_redis()

    try:
        pipe = client.pipeline(transaction=False)
        for window_name, window_secs in _WINDOWS.items():
            key = f"ratelimit:org:{org_id}:{window_name}"
            cutoff = now - window_secs

            # Add current request timestamp
            pipe.zadd(key, {member: now})
            # Remove expired entries
            pipe.zremrangebyscore(key, "-inf", cutoff)
            # Set TTL to auto-cleanup (2x window for safety)
            pipe.expire(key, window_secs * 2)

        await pipe.execute()
    except Exception:
        # Fail open — recording failure shouldn't block the request
        logger.warning("Rate limit recording failed for org %s", org_id)


async def get_usage(org_id: str) -> dict[str, int]:
    """Get current request counts across all windows (for API/dashboard)."""
    now = time.time()
    client = _get_redis()
    usage: dict[str, int] = {}

    try:
        for window_name, window_secs in _WINDOWS.items():
            key = f"ratelimit:org:{org_id}:{window_name}"
            cutoff = now - window_secs
            count = await client.zcount(key, cutoff, "+inf")
            usage[f"requests_per_{window_name}"] = int(count)
    except Exception:
        logger.warning("Rate limit usage query failed for org %s", org_id)

    return usage
