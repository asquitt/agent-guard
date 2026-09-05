"""Tests for agentguard.client (sync client)."""

import httpx
import pytest
import respx

from agentguard.client import AgentGuardClient
from agentguard.exceptions import (
    AuthenticationError,
    DetectionBlockedError,
    RateLimitError,
)
from agentguard.types import Incident, IncidentList, ProxyResponse

BASE = "https://guard.example.test"


# ── Construction ─────────────────────────────────────────────────

def test_default_headers():
    client = AgentGuardClient(api_key="ag_test_123", base_url=BASE)
    headers = client._headers()
    assert headers["Authorization"] == "Bearer ag_test_123"
    assert "X-AgentGuard-Endpoint-Id" not in headers
    client.close()


def test_headers_with_endpoint_id():
    client = AgentGuardClient(
        api_key="ag_test_123",
        base_url=BASE,
        endpoint_id="ep-1",
    )
    headers = client._headers()
    assert headers["X-AgentGuard-Endpoint-Id"] == "ep-1"
    client.close()


def test_base_url_trailing_slash_stripped():
    client = AgentGuardClient(api_key="k", base_url="https://example.com/")
    assert client.base_url == "https://example.com"
    client.close()


def test_context_manager():
    with AgentGuardClient(api_key="k", base_url=BASE) as client:
        assert client.api_key == "k"


def test_deployment_base_url_is_required():
    with pytest.raises(TypeError):
        AgentGuardClient(api_key="k")  # pyright: ignore[reportCallIssue]


def test_remote_http_deployment_is_rejected_before_client_construction():
    with pytest.raises(ValueError, match="https"):
        AgentGuardClient(api_key="k", base_url="http://guard.example.test")


# ── proxy() ──────────────────────────────────────────────────────

@respx.mock
def test_proxy_success():
    route = respx.post(f"{BASE}/api/v1/proxy/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"text": "hi"}]})
    )
    with AgentGuardClient(api_key="k", base_url=BASE) as client:
        result = client.proxy("/v1/chat/completions", {"model": "gpt-4", "messages": []})
    assert isinstance(result, ProxyResponse)
    assert result.status_code == 200
    assert result.data["choices"][0]["text"] == "hi"
    assert route.called
    assert route.calls[0].request.headers["Authorization"] == "Bearer k"


@respx.mock
def test_proxy_blocked():
    respx.post(f"{BASE}/api/v1/proxy/v1/chat/completions").mock(
        return_value=httpx.Response(
            403,
            json={
                "error": {
                    "type": "detection_blocked",
                    "message": "Request blocked by security policy",
                }
            },
        )
    )
    with AgentGuardClient(api_key="k", base_url=BASE) as client:
        with pytest.raises(DetectionBlockedError, match="security policy"):
            client.proxy("/v1/chat/completions", {})


@respx.mock
def test_proxy_auth_error():
    respx.post(f"{BASE}/api/v1/proxy/v1/chat/completions").mock(
        return_value=httpx.Response(401, json={"detail": "invalid key"})
    )
    with AgentGuardClient(api_key="bad", base_url=BASE) as client:
        with pytest.raises(AuthenticationError):
            client.proxy("/v1/chat/completions", {})


# ── list_incidents() ─────────────────────────────────────────────

@respx.mock
def test_list_incidents_success():
    route = respx.get(f"{BASE}/api/v1/incidents/").mock(
        return_value=httpx.Response(200, json={
            "items": [
                {"id": "i1", "severity": "high", "category": "pii", "title": "T", "status": "open"}
            ],
            "total": 1,
        })
    )
    with AgentGuardClient(
        api_key="k", base_url=BASE, access_token="user-token"
    ) as client:
        result = client.list_incidents(severity="high")
    assert isinstance(result, IncidentList)
    assert result.total == 1
    assert result.items[0].severity == "high"
    assert route.calls[0].request.headers["Authorization"] == "Bearer user-token"


@respx.mock
def test_list_incidents_empty():
    respx.get(f"{BASE}/api/v1/incidents/").mock(
        return_value=httpx.Response(200, json={"items": [], "total": 0})
    )
    with AgentGuardClient(
        api_key="k", base_url=BASE, access_token="user-token"
    ) as client:
        result = client.list_incidents()
    assert len(result.items) == 0


# ── get_incident() ───────────────────────────────────────────────

@respx.mock
def test_get_incident_success():
    respx.get(f"{BASE}/api/v1/incidents/inc-1").mock(
        return_value=httpx.Response(200, json={
            "id": "inc-1", "severity": "critical", "category": "compliance",
            "title": "SOX Issue", "status": "open",
        })
    )
    with AgentGuardClient(
        api_key="k", base_url=BASE, access_token="user-token"
    ) as client:
        inc = client.get_incident("inc-1")
    assert isinstance(inc, Incident)
    assert inc.id == "inc-1"
    assert inc.severity == "critical"


# ── Retry logic ──────────────────────────────────────────────────

@respx.mock
def test_retry_on_429(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return httpx.Response(429, json={"detail": "rate limited"}, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"items": [], "total": 0})

    respx.get(f"{BASE}/api/v1/incidents/").mock(side_effect=side_effect)
    with AgentGuardClient(
        api_key="k",
        base_url=BASE,
        max_retries=3,
        access_token="user-token",
    ) as client:
        result = client.list_incidents()
    assert result.total == 0
    assert call_count == 3


@respx.mock
def test_retry_on_500(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(500, json={"detail": "server error"})
        return httpx.Response(200, json={"items": [], "total": 0})

    respx.get(f"{BASE}/api/v1/incidents/").mock(side_effect=side_effect)
    with AgentGuardClient(
        api_key="k",
        base_url=BASE,
        max_retries=3,
        access_token="user-token",
    ) as client:
        client.list_incidents()
    assert call_count == 2


@respx.mock
def test_no_retry_on_last_429_attempt():
    """On last attempt, 429 should raise RateLimitError."""
    respx.get(f"{BASE}/api/v1/incidents/").mock(
        return_value=httpx.Response(429, json={"detail": "rate limited"})
    )
    with AgentGuardClient(
        api_key="k",
        base_url=BASE,
        max_retries=1,
        access_token="user-token",
    ) as client:
        with pytest.raises(RateLimitError):
            client.list_incidents()


def test_management_routes_require_user_access_token():
    with AgentGuardClient(api_key="k", base_url=BASE) as client:
        with pytest.raises(ValueError, match="access_token"):
            client.list_incidents()
