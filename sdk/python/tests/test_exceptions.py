"""Tests for agentguard.exceptions."""

import pytest

from agentguard.exceptions import (
    AgentGuardError,
    AuthenticationError,
    CircuitOpenError,
    DetectionBlockedError,
    RateLimitError,
    ValidationError,
    raise_for_status,
)


class _FakeResponse:
    """Minimal response stub for raise_for_status tests."""

    def __init__(self, status_code: int, body: dict | str = "", headers: dict | None = None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}
        self.text = str(body)[:200]

    def json(self):
        if isinstance(self._body, dict):
            return self._body
        raise ValueError("No JSON")


# ── Exception hierarchy ──────────────────────────────────────────

def test_base_error_stores_status_code():
    err = AgentGuardError("fail", status_code=500)
    assert str(err) == "fail"
    assert err.status_code == 500


def test_authentication_error_defaults():
    err = AuthenticationError()
    assert err.status_code == 401
    assert "Invalid" in str(err)


def test_rate_limit_error_retry_after():
    err = RateLimitError(retry_after=30)
    assert err.status_code == 429
    assert err.retry_after == 30


def test_detection_blocked_error():
    err = DetectionBlockedError("PII detected")
    assert err.status_code == 403
    assert "PII" in str(err)


def test_circuit_open_error():
    err = CircuitOpenError()
    assert err.status_code == 503


def test_validation_error():
    err = ValidationError("bad field")
    assert err.status_code == 422


def test_error_inheritance():
    assert issubclass(AuthenticationError, AgentGuardError)
    assert issubclass(RateLimitError, AgentGuardError)
    assert issubclass(DetectionBlockedError, AgentGuardError)
    assert issubclass(CircuitOpenError, AgentGuardError)
    assert issubclass(ValidationError, AgentGuardError)


# ── raise_for_status ─────────────────────────────────────────────

def test_raise_for_status_2xx_no_error():
    resp = _FakeResponse(200)
    raise_for_status(resp)  # should not raise


def test_raise_for_status_401():
    resp = _FakeResponse(401, {"detail": "bad token"})
    with pytest.raises(AuthenticationError, match="bad token"):
        raise_for_status(resp)


def test_raise_for_status_403_detection():
    resp = _FakeResponse(403, {"detail": {"type": "detection", "error": "PII found"}})
    with pytest.raises(DetectionBlockedError, match="PII found"):
        raise_for_status(resp)


def test_raise_for_status_403_generic():
    resp = _FakeResponse(403, {"detail": "forbidden"})
    with pytest.raises(AgentGuardError) as exc_info:
        raise_for_status(resp)
    assert exc_info.value.status_code == 403


def test_raise_for_status_422():
    resp = _FakeResponse(422, {"detail": "invalid field"})
    with pytest.raises(ValidationError):
        raise_for_status(resp)


def test_raise_for_status_429_with_retry_after():
    resp = _FakeResponse(429, {"detail": "too many"}, headers={"retry_after": "10"})
    with pytest.raises(RateLimitError) as exc_info:
        raise_for_status(resp)
    assert exc_info.value.retry_after == 10


def test_raise_for_status_429_no_retry_header():
    resp = _FakeResponse(429, {"detail": "slow down"})
    with pytest.raises(RateLimitError) as exc_info:
        raise_for_status(resp)
    assert exc_info.value.retry_after is None


def test_raise_for_status_503_circuit():
    resp = _FakeResponse(503, {"detail": {"type": "circuit_open", "error": "breaker tripped"}})
    with pytest.raises(CircuitOpenError, match="breaker tripped"):
        raise_for_status(resp)


def test_raise_for_status_503_generic():
    resp = _FakeResponse(503, {"detail": "unavailable"})
    with pytest.raises(AgentGuardError) as exc_info:
        raise_for_status(resp)
    assert exc_info.value.status_code == 503


def test_raise_for_status_500():
    resp = _FakeResponse(500, {"detail": "server error"})
    with pytest.raises(AgentGuardError) as exc_info:
        raise_for_status(resp)
    assert exc_info.value.status_code == 500


def test_raise_for_status_non_json_body():
    resp = _FakeResponse(502, "Bad Gateway")
    with pytest.raises(AgentGuardError):
        raise_for_status(resp)


def test_raise_for_status_403_blocked_in_message():
    resp = _FakeResponse(403, {"detail": "Request blocked by policy"})
    with pytest.raises(DetectionBlockedError):
        raise_for_status(resp)
