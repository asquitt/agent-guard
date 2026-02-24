"""Tests for agentguard.async_client."""

import httpx
import pytest
import respx

from agentguard.async_client import AsyncAgentGuardClient
from agentguard.exceptions import AuthenticationError, DetectionBlockedError
from agentguard.types import Incident, IncidentList, ProxyResponse

BASE = "https://api.agentguard.app"

pytestmark = pytest.mark.asyncio


# ── Construction ─────────────────────────────────────────────────

async def test_default_headers():
    client = AsyncAgentGuardClient(api_key="ag_test_456")
    headers = client._headers()
    assert headers["Authorization"] == "Bearer ag_test_456"
    await client.close()


async def test_headers_with_endpoint_id():
    client = AsyncAgentGuardClient(api_key="k", endpoint_id="ep-2")
    assert client._headers()["X-AgentGuard-Endpoint-Id"] == "ep-2"
    await client.close()


async def test_async_context_manager():
    async with AsyncAgentGuardClient(api_key="k") as client:
        assert client.api_key == "k"


# ── proxy() ──────────────────────────────────────────────────────

@respx.mock
async def test_proxy_success():
    respx.post(f"{BASE}/api/v1/proxy/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"text": "hi"}]})
    )
    async with AsyncAgentGuardClient(api_key="k") as client:
        result = await client.proxy("/v1/chat/completions", {"model": "gpt-4"})
    assert isinstance(result, ProxyResponse)
    assert result.status_code == 200


@respx.mock
async def test_proxy_blocked():
    respx.post(f"{BASE}/api/v1/proxy/v1/chat/completions").mock(
        return_value=httpx.Response(
            403, json={"detail": {"type": "detection", "error": "blocked"}}
        )
    )
    async with AsyncAgentGuardClient(api_key="k") as client:
        with pytest.raises(DetectionBlockedError):
            await client.proxy("/v1/chat/completions", {})


@respx.mock
async def test_proxy_auth_error():
    respx.post(f"{BASE}/api/v1/proxy/v1/chat/completions").mock(
        return_value=httpx.Response(401, json={"detail": "unauthorized"})
    )
    async with AsyncAgentGuardClient(api_key="bad") as client:
        with pytest.raises(AuthenticationError):
            await client.proxy("/v1/chat/completions", {})


# ── list_incidents() ─────────────────────────────────────────────

@respx.mock
async def test_list_incidents():
    respx.get(f"{BASE}/api/v1/incidents/").mock(
        return_value=httpx.Response(200, json={
            "items": [
                {"id": "i1", "severity": "medium", "category": "cost", "title": "T", "status": "open"}
            ],
            "total": 1,
        })
    )
    async with AsyncAgentGuardClient(api_key="k") as client:
        result = await client.list_incidents(severity="medium")
    assert isinstance(result, IncidentList)
    assert result.total == 1


@respx.mock
async def test_list_incidents_empty():
    respx.get(f"{BASE}/api/v1/incidents/").mock(
        return_value=httpx.Response(200, json={"items": [], "total": 0})
    )
    async with AsyncAgentGuardClient(api_key="k") as client:
        result = await client.list_incidents()
    assert len(result.items) == 0


# ── get_incident() ───────────────────────────────────────────────

@respx.mock
async def test_get_incident():
    respx.get(f"{BASE}/api/v1/incidents/inc-99").mock(
        return_value=httpx.Response(200, json={
            "id": "inc-99", "severity": "low", "category": "loop",
            "title": "Loop", "status": "resolved",
        })
    )
    async with AsyncAgentGuardClient(api_key="k") as client:
        inc = await client.get_incident("inc-99")
    assert isinstance(inc, Incident)
    assert inc.id == "inc-99"


# ── Retry logic ──────────────────────────────────────────────────

@respx.mock
async def test_retry_on_500(monkeypatch):
    async def _noop_sleep(_):
        pass

    monkeypatch.setattr("asyncio.sleep", _noop_sleep)
    call_count = 0

    def side_effect(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(500, json={"detail": "error"})
        return httpx.Response(200, json={"items": [], "total": 0})

    respx.get(f"{BASE}/api/v1/incidents/").mock(side_effect=side_effect)
    async with AsyncAgentGuardClient(api_key="k", max_retries=3) as client:
        result = await client.list_incidents()
    assert result.total == 0
    assert call_count == 2
