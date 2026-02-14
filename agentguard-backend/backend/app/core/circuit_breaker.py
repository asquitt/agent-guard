"""Circuit breaker for upstream LLM provider calls.

Prevents hammering failing providers during outages. Uses a simple
state machine: CLOSED -> OPEN -> HALF_OPEN -> CLOSED.
"""

import logging
import time
from enum import IntEnum

logger = logging.getLogger(__name__)


class State(IntEnum):
    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2


class CircuitBreaker:
    """Thread-safe circuit breaker for a single provider."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 2,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = State.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0
        self._half_open_calls = 0

    @property
    def state(self) -> State:
        if self._state == State.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = State.HALF_OPEN
                self._half_open_calls = 0
                logger.info("Circuit breaker '%s' transitioning to HALF_OPEN", self.name)
        return self._state

    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        current = self.state
        if current == State.CLOSED:
            return True
        if current == State.HALF_OPEN:
            return self._half_open_calls < self.half_open_max_calls
        return False  # OPEN

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == State.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._state = State.CLOSED
                self._failure_count = 0
                logger.info("Circuit breaker '%s' recovered -> CLOSED", self.name)
        elif self._state == State.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == State.HALF_OPEN:
            self._state = State.OPEN
            logger.warning("Circuit breaker '%s' re-opened from HALF_OPEN", self.name)
        elif self._failure_count >= self.failure_threshold:
            self._state = State.OPEN
            logger.warning(
                "Circuit breaker '%s' OPEN after %d failures",
                self.name, self._failure_count,
            )

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = State.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0


# Per-provider circuit breakers (created lazily)
_breakers: dict[str, CircuitBreaker] = {}


def get_breaker(provider: str) -> CircuitBreaker:
    """Get or create a circuit breaker for a provider."""
    if provider not in _breakers:
        _breakers[provider] = CircuitBreaker(
            name=provider,
            failure_threshold=5,
            recovery_timeout=30.0,
            half_open_max_calls=2,
        )
    return _breakers[provider]
