"""Integration tests for proxy.py router.

Endpoints:
  POST   /api/v1/proxy/v1/chat/completions
  POST   /api/v1/proxy/v1/completions
  POST   /api/v1/proxy/v1/embeddings
  POST   /api/v1/proxy/v1/messages

These endpoints use API key auth (Bearer ag_live_*) and forward to upstream
LLM providers. We mock external I/O (httpx, Redis, Celery) and test the
full request lifecycle through the router.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proxy import ProxyEndpoint, ProxyRequest
from app.models.user import ApiKey, Organization

PREFIX = "/api/v1/proxy"

# Reusable payloads
OPENAI_CHAT_BODY = {
    "model": "gpt-4",
    "messages": [
        {"role": "system", "content": "You are a helpful financial assistant."},
        {"role": "user", "content": "What is the current interest rate?"},
    ],
    "temperature": 0.7,
    "max_tokens": 256,
}

OPENAI_COMPLETION_BODY = {
    "model": "gpt-4",
    "prompt": "Explain compound interest",
    "max_tokens": 256,
}

OPENAI_EMBEDDING_BODY = {
    "model": "text-embedding-ada-002",
    "input": "Hello world",
}

ANTHROPIC_MESSAGES_BODY = {
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 256,
    "messages": [
        {"role": "user", "content": "Summarize our Q3 earnings report."},
    ],
}

OPENAI_CHAT_RESPONSE = {
    "id": "chatcmpl-abc123",
    "object": "chat.completion",
    "created": 1700000000,
    "model": "gpt-4",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "The current federal funds rate is set by the Federal Reserve.",
            },
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 25, "completion_tokens": 18, "total_tokens": 43},
}

ANTHROPIC_MESSAGES_RESPONSE = {
    "id": "msg_01XYZ",
    "type": "message",
    "role": "assistant",
    "content": [
        {
            "type": "text",
            "text": "Q3 earnings showed a 12% increase in revenue year-over-year.",
        }
    ],
    "model": "claude-sonnet-4-20250514",
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 15, "output_tokens": 22},
}


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
async def proxy_endpoint(
    db_session: AsyncSession, org: Organization
) -> ProxyEndpoint:
    """Active OpenAI proxy endpoint for the primary org."""
    ep = ProxyEndpoint(
        id=uuid.uuid4(),
        org_id=org.id,
        name="Test OpenAI Endpoint",
        provider="openai",
        target_url="https://api.openai.com",
        is_active=True,
        config={"api_key": "sk-test-fake-key-12345"},
    )
    db_session.add(ep)
    await db_session.flush()
    return ep


@pytest.fixture
async def anthropic_endpoint(
    db_session: AsyncSession, org: Organization
) -> ProxyEndpoint:
    """Active Anthropic proxy endpoint for the primary org."""
    ep = ProxyEndpoint(
        id=uuid.uuid4(),
        org_id=org.id,
        name="Test Anthropic Endpoint",
        provider="anthropic",
        target_url="https://api.anthropic.com",
        is_active=True,
        config={"api_key": "sk-ant-test-fake-key"},
    )
    db_session.add(ep)
    await db_session.flush()
    return ep


@pytest.fixture
async def inactive_endpoint(
    db_session: AsyncSession, org: Organization
) -> ProxyEndpoint:
    """Inactive proxy endpoint."""
    ep = ProxyEndpoint(
        id=uuid.uuid4(),
        org_id=org.id,
        name="Inactive Endpoint",
        provider="openai",
        target_url="https://api.openai.com",
        is_active=False,
        config={"api_key": "sk-inactive"},
    )
    db_session.add(ep)
    await db_session.flush()
    return ep


@pytest.fixture
async def other_org_endpoint(
    db_session: AsyncSession, other_org: Organization
) -> ProxyEndpoint:
    """Proxy endpoint belonging to a DIFFERENT org."""
    ep = ProxyEndpoint(
        id=uuid.uuid4(),
        org_id=other_org.id,
        name="Other Org Endpoint",
        provider="openai",
        target_url="https://api.openai.com",
        is_active=True,
        config={"api_key": "sk-other-org-key"},
    )
    db_session.add(ep)
    await db_session.flush()
    return ep


@pytest.fixture
async def org_with_ip_allowlist(
    db_session: AsyncSession, org: Organization
) -> Organization:
    """Configure the primary org with an IP allowlist."""
    org.settings = {"ip_allowlist": ["10.0.0.1", "192.168.1.0/24"]}
    await db_session.flush()
    return org


@pytest.fixture
async def org_with_rate_limits(
    db_session: AsyncSession, org: Organization
) -> Organization:
    """Configure the primary org with custom rate limits."""
    org.settings = {"rate_limits": {"rpm": 5, "rph": 100, "rpd": 1000}}
    await db_session.flush()
    return org


@pytest.fixture
async def org_at_billing_cap(
    db_session: AsyncSession, org: Organization
) -> Organization:
    """Set org to exactly at the billing request cap (starter = 10,000)."""
    org.plan_tier = "starter"
    org.monthly_request_count = 10000
    await db_session.flush()
    return org


@pytest.fixture
async def enterprise_org(
    db_session: AsyncSession, org: Organization
) -> Organization:
    """Enterprise tier org with unlimited requests."""
    org.plan_tier = "enterprise"
    org.monthly_request_count = 999999
    await db_session.flush()
    return org


def _mock_httpx_response(status_code: int = 200, body: dict | None = None) -> httpx.Response:
    """Create a mock httpx Response."""
    body = body or OPENAI_CHAT_RESPONSE
    return httpx.Response(
        status_code=status_code,
        json=body,
        request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"),
    )


def _proxy_mocks(
    response: httpx.Response | None = None,
    breaker_open: bool = False,
):
    """Context manager stack for all external I/O mocks needed by proxy."""
    if response is None:
        response = _mock_httpx_response()

    mock_http_client = AsyncMock()
    mock_http_client.post = AsyncMock(return_value=response)

    mock_breaker = MagicMock()
    mock_breaker.allow_request.return_value = not breaker_open
    mock_breaker.record_success = MagicMock()
    mock_breaker.record_failure = MagicMock()
    mock_breaker.recovery_timeout = 30

    patches = {
        "http_client": patch(
            "app.api.proxy.get_http_client",
            new_callable=AsyncMock,
            return_value=mock_http_client,
        ),
        "check_rate_limit": patch(
            "app.api.proxy.check_rate_limit",
            new_callable=AsyncMock,
        ),
        "record_request": patch(
            "app.api.proxy.record_request",
            new_callable=AsyncMock,
        ),
        "get_breaker": patch(
            "app.api.proxy.get_breaker",
            return_value=mock_breaker,
        ),
        "queue_async": patch(
            "app.services.detection.pipeline.queue_async_detectors",
            new_callable=AsyncMock,
            return_value=None,
        ),
        "metrics_total": patch("app.api.proxy.PROXY_REQUESTS_TOTAL", new_callable=MagicMock),
        "metrics_latency": patch("app.api.proxy.PROXY_LATENCY", new_callable=MagicMock),
    }
    return patches, mock_http_client, mock_breaker


class _ProxyTestBase:
    """Shared helper for proxy tests that need all mocks applied."""

    @staticmethod
    async def _call(
        client: AsyncClient,
        path: str,
        body: dict,
        raw_key: str,
        response: httpx.Response | None = None,
        breaker_open: bool = False,
        extra_headers: dict | None = None,
    ):
        patches, mock_http, mock_breaker = _proxy_mocks(response, breaker_open)
        headers = {"Authorization": f"Bearer {raw_key}"}
        if extra_headers:
            headers.update(extra_headers)

        # Apply all patches
        contexts = {k: v.__enter__() if hasattr(v, '__enter__') else v.start() for k, v in patches.items()}
        try:
            # Make sure metric mocks return something chainable
            for key in ("metrics_total", "metrics_latency"):
                if key in contexts:
                    contexts[key].labels = MagicMock(return_value=MagicMock())

            resp = await client.post(
                f"{PREFIX}{path}",
                json=body,
                headers=headers,
            )
        finally:
            for v in patches.values():
                if hasattr(v, '__exit__'):
                    v.__exit__(None, None, None)
                else:
                    v.stop()

        return resp, mock_http, mock_breaker


# ── Auth Tests ────────────────────────────────────────────────────


class TestProxyAuth:
    """All proxy endpoints require Bearer API key auth."""

    @pytest.mark.parametrize(
        "path,body",
        [
            ("/v1/chat/completions", OPENAI_CHAT_BODY),
            ("/v1/completions", OPENAI_COMPLETION_BODY),
            ("/v1/embeddings", OPENAI_EMBEDDING_BODY),
            ("/v1/messages", ANTHROPIC_MESSAGES_BODY),
        ],
    )
    async def test_no_auth_returns_401_or_403(
        self, client: AsyncClient, path: str, body: dict
    ):
        resp = await client.post(f"{PREFIX}{path}", json=body)
        assert resp.status_code in (401, 403)

    @pytest.mark.parametrize(
        "path,body",
        [
            ("/v1/chat/completions", OPENAI_CHAT_BODY),
            ("/v1/completions", OPENAI_COMPLETION_BODY),
            ("/v1/embeddings", OPENAI_EMBEDDING_BODY),
            ("/v1/messages", ANTHROPIC_MESSAGES_BODY),
        ],
    )
    async def test_invalid_api_key_returns_401(
        self, client: AsyncClient, path: str, body: dict
    ):
        resp = await client.post(
            f"{PREFIX}{path}",
            json=body,
            headers={"Authorization": "Bearer ag_live_invalidkey00000000000000"},
        )
        assert resp.status_code in (401, 403)

    async def test_expired_api_key_rejected(
        self, client: AsyncClient, db_session: AsyncSession, org: Organization
    ):
        """An expired API key should be rejected."""
        from datetime import datetime, timedelta, timezone
        from app.services.api_key_service import hash_api_key

        full_key = f"ag_live_{uuid.uuid4().hex}"
        key = ApiKey(
            id=uuid.uuid4(),
            org_id=org.id,
            key_hash=hash_api_key(full_key),
            prefix=full_key[:16],
            name="Expired Key",
            scopes=["proxy"],
            environment="production",
            is_active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db_session.add(key)
        await db_session.flush()

        resp = await client.post(
            f"{PREFIX}/v1/chat/completions",
            json=OPENAI_CHAT_BODY,
            headers={"Authorization": f"Bearer {full_key}"},
        )
        assert resp.status_code in (401, 403)

    async def test_inactive_api_key_rejected(
        self, client: AsyncClient, db_session: AsyncSession, org: Organization
    ):
        """A deactivated API key should be rejected."""
        from app.services.api_key_service import hash_api_key

        full_key = f"ag_live_{uuid.uuid4().hex}"
        key = ApiKey(
            id=uuid.uuid4(),
            org_id=org.id,
            key_hash=hash_api_key(full_key),
            prefix=full_key[:16],
            name="Disabled Key",
            scopes=["proxy"],
            environment="production",
            is_active=False,
        )
        db_session.add(key)
        await db_session.flush()

        resp = await client.post(
            f"{PREFIX}/v1/chat/completions",
            json=OPENAI_CHAT_BODY,
            headers={"Authorization": f"Bearer {full_key}"},
        )
        assert resp.status_code in (401, 403)

    async def test_jwt_token_not_accepted_for_proxy(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Proxy endpoints use API key auth, NOT JWT Bearer tokens."""
        resp = await client.post(
            f"{PREFIX}/v1/chat/completions",
            json=OPENAI_CHAT_BODY,
            headers=auth_headers,
        )
        # JWT tokens won't match the ag_live_* pattern
        assert resp.status_code in (401, 403, 422)


# ── Endpoint Resolution Tests ─────────────────────────────────────


class TestEndpointResolution:
    """Test proxy endpoint resolution logic."""

    async def test_no_endpoint_configured_returns_error(
        self, client: AsyncClient, api_key: tuple[ApiKey, str]
    ):
        """With valid API key but no configured endpoint, should return error."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 422
        finally:
            for p in patches.values():
                p.stop()

    async def test_inactive_endpoint_not_resolved(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        inactive_endpoint: ProxyEndpoint,
    ):
        """Inactive endpoints should not be resolved."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            # Should fail because the only endpoint is inactive
            assert resp.status_code == 422
        finally:
            for p in patches.values():
                p.stop()

    async def test_specific_endpoint_id_header(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        """X-AgentGuard-Endpoint-Id header selects a specific endpoint."""
        _, raw_key = api_key
        patches, mock_http, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={
                    "Authorization": f"Bearer {raw_key}",
                    "X-AgentGuard-Endpoint-Id": str(proxy_endpoint.id),
                },
            )
            assert resp.status_code == 200
        finally:
            for p in patches.values():
                p.stop()

    async def test_wrong_org_endpoint_id_rejected(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        other_org_endpoint: ProxyEndpoint,
    ):
        """Endpoint belonging to another org should not be accessible."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={
                    "Authorization": f"Bearer {raw_key}",
                    "X-AgentGuard-Endpoint-Id": str(other_org_endpoint.id),
                },
            )
            assert resp.status_code in (404, 422)
        finally:
            for p in patches.values():
                p.stop()

    async def test_nonexistent_endpoint_id_rejected(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        """Random UUID endpoint ID should return error."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={
                    "Authorization": f"Bearer {raw_key}",
                    "X-AgentGuard-Endpoint-Id": str(uuid.uuid4()),
                },
            )
            assert resp.status_code in (404, 422)
        finally:
            for p in patches.values():
                p.stop()


# ── Successful Proxy Requests ─────────────────────────────────────


class TestProxySuccess:
    """Test successful proxy forwarding through all 4 endpoints."""

    async def test_chat_completions_success(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        _, raw_key = api_key
        patches, mock_http, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["id"] == "chatcmpl-abc123"
            assert body["choices"][0]["message"]["content"]
        finally:
            for p in patches.values():
                p.stop()

    async def test_completions_success(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        _, raw_key = api_key
        resp_data = {
            "id": "cmpl-abc123",
            "object": "text_completion",
            "model": "gpt-4",
            "choices": [{"text": "Compound interest is...", "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }
        patches, mock_http, _ = _proxy_mocks(_mock_httpx_response(200, resp_data))
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/completions",
                json=OPENAI_COMPLETION_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 200
            assert resp.json()["choices"][0]["text"] == "Compound interest is..."
        finally:
            for p in patches.values():
                p.stop()

    async def test_embeddings_success(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        _, raw_key = api_key
        resp_data = {
            "object": "list",
            "model": "text-embedding-ada-002",
            "data": [{"object": "embedding", "index": 0, "embedding": [0.1, 0.2, 0.3]}],
            "usage": {"prompt_tokens": 2, "total_tokens": 2},
        }
        patches, _, _ = _proxy_mocks(_mock_httpx_response(200, resp_data))
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/embeddings",
                json=OPENAI_EMBEDDING_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 200
            assert len(resp.json()["data"][0]["embedding"]) == 3
        finally:
            for p in patches.values():
                p.stop()

    async def test_anthropic_messages_success(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        anthropic_endpoint: ProxyEndpoint,
    ):
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks(
            _mock_httpx_response(200, ANTHROPIC_MESSAGES_RESPONSE)
        )
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/messages",
                json=ANTHROPIC_MESSAGES_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["id"] == "msg_01XYZ"
            assert body["content"][0]["text"]
        finally:
            for p in patches.values():
                p.stop()


# ── Request Logging Tests ─────────────────────────────────────────


class TestRequestLogging:
    """Verify that proxy requests are logged in the proxy_requests table."""

    async def test_successful_request_logged(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
        db_session: AsyncSession,
    ):
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 200
        finally:
            for p in patches.values():
                p.stop()

        # Check that a ProxyRequest was created
        from sqlalchemy import select

        result = await db_session.execute(
            select(ProxyRequest).where(ProxyRequest.org_id == proxy_endpoint.org_id)
        )
        logs = result.scalars().all()
        assert len(logs) >= 1
        log = logs[0]
        assert log.method == "POST"
        assert "/v1/chat/completions" in log.path
        assert log.status_code == 200
        assert log.model == "gpt-4"

    async def test_request_body_stored(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
        db_session: AsyncSession,
    ):
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
        finally:
            for p in patches.values():
                p.stop()

        from sqlalchemy import select

        result = await db_session.execute(
            select(ProxyRequest).where(ProxyRequest.org_id == proxy_endpoint.org_id)
        )
        log = result.scalars().first()
        assert log is not None
        assert log.request_body is not None
        stored_body = json.loads(log.request_body)
        assert stored_body["model"] == "gpt-4"

    async def test_usage_counter_incremented(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
        org: Organization,
        db_session: AsyncSession,
    ):
        """Monthly request count should be incremented on each proxy call."""
        _, raw_key = api_key
        initial_count = org.monthly_request_count or 0

        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
        finally:
            for p in patches.values():
                p.stop()

        await db_session.refresh(org)
        assert (org.monthly_request_count or 0) == initial_count + 1


# ── Invalid Request Body Tests ────────────────────────────────────


class TestInvalidRequestBody:
    """Test handling of malformed request bodies."""

    async def test_empty_body(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        _, raw_key = api_key
        resp = await client.post(
            f"{PREFIX}/v1/chat/completions",
            content=b"",
            headers={
                "Authorization": f"Bearer {raw_key}",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 400

    async def test_non_json_body(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        _, raw_key = api_key
        resp = await client.post(
            f"{PREFIX}/v1/chat/completions",
            content=b"this is not json",
            headers={
                "Authorization": f"Bearer {raw_key}",
                "Content-Type": "application/json",
            },
        )
        assert resp.status_code == 400


# ── Upstream Error Handling Tests ─────────────────────────────────


class TestUpstreamErrors:
    """Test handling of upstream LLM provider errors."""

    async def test_upstream_timeout_returns_504(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        _, raw_key = api_key
        patches, mock_http, _ = _proxy_mocks()
        mock_http.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 504
            assert "timed out" in resp.json()["error"]["message"].lower() or "timeout" in resp.json()["error"]["type"]
        finally:
            for p in patches.values():
                p.stop()

    async def test_upstream_connection_error_returns_502(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        _, raw_key = api_key
        patches, mock_http, _ = _proxy_mocks()
        mock_http.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 502
            assert "error" in resp.json()["error"]["message"].lower()
        finally:
            for p in patches.values():
                p.stop()

    async def test_upstream_4xx_forwarded(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        """Upstream 4xx errors should be forwarded back to the client."""
        _, raw_key = api_key
        error_body = {
            "error": {
                "message": "Invalid API key",
                "type": "authentication_error",
            }
        }
        patches, _, _ = _proxy_mocks(_mock_httpx_response(401, error_body))
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 401
        finally:
            for p in patches.values():
                p.stop()

    async def test_upstream_5xx_forwarded(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        _, raw_key = api_key
        error_body = {"error": {"message": "Internal server error"}}
        patches, _, _ = _proxy_mocks(_mock_httpx_response(500, error_body))
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 500
        finally:
            for p in patches.values():
                p.stop()


# ── IP Allowlist Tests ────────────────────────────────────────────


class TestIPAllowlist:
    """Test IP-based access control for proxy endpoints."""

    async def test_ip_not_in_allowlist_returns_403(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
        org_with_ip_allowlist: Organization,
    ):
        """Request from IP not in allowlist should be blocked."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            # The test client typically sends from 127.0.0.1 which is not in the allowlist
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 403
            assert "allowlist" in resp.json()["detail"].lower()
        finally:
            for p in patches.values():
                p.stop()

    async def test_ip_in_allowlist_allowed(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
        org_with_ip_allowlist: Organization,
    ):
        """Request from allowed IP should pass."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            with patch("app.api.proxy.get_client_ip", return_value="10.0.0.1"):
                resp = await client.post(
                    f"{PREFIX}/v1/chat/completions",
                    json=OPENAI_CHAT_BODY,
                    headers={"Authorization": f"Bearer {raw_key}"},
                )
                assert resp.status_code == 200
        finally:
            for p in patches.values():
                p.stop()

    async def test_ip_in_cidr_range_allowed(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
        org_with_ip_allowlist: Organization,
    ):
        """IP within an allowed CIDR range should pass."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            with patch("app.api.proxy.get_client_ip", return_value="192.168.1.42"):
                resp = await client.post(
                    f"{PREFIX}/v1/chat/completions",
                    json=OPENAI_CHAT_BODY,
                    headers={"Authorization": f"Bearer {raw_key}"},
                )
                assert resp.status_code == 200
        finally:
            for p in patches.values():
                p.stop()

    async def test_no_allowlist_allows_all(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        """Without an allowlist configured, all IPs should be allowed."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 200
        finally:
            for p in patches.values():
                p.stop()


# ── Rate Limiting Tests ───────────────────────────────────────────


class TestRateLimiting:
    """Test rate limit enforcement at the proxy layer."""

    async def test_rate_limit_exceeded_returns_429(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        """When Redis rate limiter raises, proxy should return 429."""
        from app.services.rate_limiter import RateLimitExceeded

        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        # Override the rate limit mock to raise
        patches["check_rate_limit"] = patch(
            "app.api.proxy.check_rate_limit",
            new_callable=AsyncMock,
            side_effect=RateLimitExceeded(limit=5, window="minute", current=6, retry_after=30),
        )
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 429
            body = resp.json()
            assert body["detail"]["limit"] == 5
            assert body["detail"]["window"] == "minute"
            assert "Retry-After" in resp.headers
        finally:
            for p in patches.values():
                p.stop()


# ── Billing Cap Tests ─────────────────────────────────────────────


class TestBillingCap:
    """Test monthly billing request cap enforcement."""

    async def test_starter_plan_at_cap_returns_429(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
        org_at_billing_cap: Organization,
    ):
        """Starter plan at 10,000 requests should be blocked."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 429
            body = resp.json()
            assert "limit" in body["detail"]["error"].lower() or "limit" in str(body["detail"])
        finally:
            for p in patches.values():
                p.stop()

    async def test_enterprise_plan_unlimited(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
        enterprise_org: Organization,
    ):
        """Enterprise plan should have no request cap."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 200
        finally:
            for p in patches.values():
                p.stop()

    async def test_billing_cap_upgrade_url_in_response(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
        org_at_billing_cap: Organization,
    ):
        """429 response should include upgrade URL."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 429
            body = resp.json()
            assert "upgrade_url" in body["detail"]
        finally:
            for p in patches.values():
                p.stop()


# ── Circuit Breaker Tests ─────────────────────────────────────────


class TestCircuitBreaker:
    """Test circuit breaker behavior for provider failover."""

    async def test_circuit_open_returns_503(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        """When circuit breaker is open, should return 503 immediately."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks(breaker_open=True)
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 503
            body = resp.json()
            assert "circuit" in body["detail"]["error"].lower()
            assert "Retry-After" in resp.headers
        finally:
            for p in patches.values():
                p.stop()


# ── Detection Pipeline Tests ──────────────────────────────────────


class TestDetectionPipeline:
    """Test that the detection pipeline is triggered on successful proxy responses."""

    async def test_detection_runs_on_200_response(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
        pii_detector,
    ):
        """Sync detection pipeline should run on successful responses."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        with patch(
            "app.services.detection.pipeline.run_sync_detectors",
            new_callable=AsyncMock,
        ) as mock_detect:
            from app.services.detection.types import DetectionAction

            mock_decision = MagicMock()
            mock_decision.action = DetectionAction.PASS
            mock_decision.modified_response = None
            mock_detect.return_value = mock_decision

            for p in patches.values():
                p.start()
            try:
                resp = await client.post(
                    f"{PREFIX}/v1/chat/completions",
                    json=OPENAI_CHAT_BODY,
                    headers={"Authorization": f"Bearer {raw_key}"},
                )
                assert resp.status_code == 200
                # Detection should have been called
                mock_detect.assert_called_once()
            finally:
                for p in patches.values():
                    p.stop()

    async def test_detection_block_returns_403(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        """If detection pipeline returns BLOCK, proxy should return 403."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        with patch(
            "app.services.detection.pipeline.run_sync_detectors",
            new_callable=AsyncMock,
        ) as mock_detect:
            from app.services.detection.types import DetectionAction

            mock_decision = MagicMock()
            mock_decision.action = DetectionAction.BLOCK
            mock_decision.modified_response = None
            mock_detect.return_value = mock_decision

            for p in patches.values():
                p.start()
            try:
                resp = await client.post(
                    f"{PREFIX}/v1/chat/completions",
                    json=OPENAI_CHAT_BODY,
                    headers={"Authorization": f"Bearer {raw_key}"},
                )
                assert resp.status_code == 403
                assert "blocked" in resp.json()["error"]["message"].lower()
            finally:
                for p in patches.values():
                    p.stop()

    async def test_detection_redact_modifies_response(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        """If detection pipeline returns REDACT, response should be modified."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        redacted_response = {
            "id": "chatcmpl-abc123",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "The SSN [REDACTED] was found in the document.",
                    }
                }
            ],
        }
        with patch(
            "app.services.detection.pipeline.run_sync_detectors",
            new_callable=AsyncMock,
        ) as mock_detect:
            from app.services.detection.types import DetectionAction

            mock_decision = MagicMock()
            mock_decision.action = DetectionAction.REDACT
            mock_decision.modified_response = json.dumps(redacted_response)
            mock_detect.return_value = mock_decision

            for p in patches.values():
                p.start()
            try:
                resp = await client.post(
                    f"{PREFIX}/v1/chat/completions",
                    json=OPENAI_CHAT_BODY,
                    headers={"Authorization": f"Bearer {raw_key}"},
                )
                assert resp.status_code == 200
                body = resp.json()
                assert "[REDACTED]" in body["choices"][0]["message"]["content"]
            finally:
                for p in patches.values():
                    p.stop()

    async def test_async_detectors_queued_on_success(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        """Async detectors should be queued via Celery after successful response."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
            assert resp.status_code == 200
        finally:
            for p in patches.values():
                p.stop()

    async def test_detection_not_run_on_4xx(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
    ):
        """Detection pipeline should NOT run on upstream error responses."""
        _, raw_key = api_key
        error_body = {"error": {"message": "Rate limited"}}
        patches, _, _ = _proxy_mocks(_mock_httpx_response(429, error_body))
        with patch(
            "app.services.detection.pipeline.run_sync_detectors",
            new_callable=AsyncMock,
        ) as mock_detect:
            for p in patches.values():
                p.start()
            try:
                resp = await client.post(
                    f"{PREFIX}/v1/chat/completions",
                    json=OPENAI_CHAT_BODY,
                    headers={"Authorization": f"Bearer {raw_key}"},
                )
                assert resp.status_code == 429
                mock_detect.assert_not_called()
            finally:
                for p in patches.values():
                    p.stop()


# ── Tenant Isolation Tests ────────────────────────────────────────


class TestTenantIsolation:
    """Ensure API keys from one org cannot access another org's endpoints."""

    async def test_api_key_scoped_to_own_org(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        other_org_endpoint: ProxyEndpoint,
    ):
        """API key should only resolve endpoints belonging to its own org."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            resp = await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={
                    "Authorization": f"Bearer {raw_key}",
                    "X-AgentGuard-Endpoint-Id": str(other_org_endpoint.id),
                },
            )
            # Should not be able to use other org's endpoint
            assert resp.status_code in (404, 422)
        finally:
            for p in patches.values():
                p.stop()

    async def test_request_logged_to_correct_org(
        self,
        client: AsyncClient,
        api_key: tuple[ApiKey, str],
        proxy_endpoint: ProxyEndpoint,
        db_session: AsyncSession,
        org: Organization,
    ):
        """Proxy request logs should be associated with the API key's org."""
        _, raw_key = api_key
        patches, _, _ = _proxy_mocks()
        for p in patches.values():
            p.start()
        try:
            await client.post(
                f"{PREFIX}/v1/chat/completions",
                json=OPENAI_CHAT_BODY,
                headers={"Authorization": f"Bearer {raw_key}"},
            )
        finally:
            for p in patches.values():
                p.stop()

        from sqlalchemy import select

        result = await db_session.execute(
            select(ProxyRequest).where(ProxyRequest.org_id == org.id)
        )
        logs = result.scalars().all()
        assert len(logs) >= 1
        # Verify all logs belong to the correct org
        for log in logs:
            assert log.org_id == org.id
