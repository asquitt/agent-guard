"""Integration tests for proxy_endpoints.py router.

Endpoints:
  POST   /api/v1/proxy-endpoints/
  GET    /api/v1/proxy-endpoints/
  GET    /api/v1/proxy-endpoints/{id}
  PATCH  /api/v1/proxy-endpoints/{id}
  DELETE /api/v1/proxy-endpoints/{id}
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.proxy_endpoints import limiter as proxy_endpoint_limiter
from app.models.proxy import ProxyEndpoint
from app.models.user import Organization

PREFIX = "/api/v1/proxy-endpoints"


@pytest.fixture(autouse=True)
def _reset_proxy_endpoint_rate_limit() -> None:
    """Keep per-test endpoint validation independent of shared limiter state."""
    proxy_endpoint_limiter.reset()


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
async def openai_endpoint(db_session: AsyncSession, org: Organization) -> ProxyEndpoint:
    """Create an OpenAI proxy endpoint in the primary org."""
    ep = ProxyEndpoint(  # type: ignore[call-arg]
        id=uuid.uuid4(),
        org_id=org.id,
        name="OpenAI Production",
        provider="openai",
        target_url="https://api.openai.com",
        is_active=True,
        config={"model_allowlist": ["gpt-4o"]},
    )
    db_session.add(ep)
    await db_session.flush()
    return ep


@pytest.fixture
async def other_org_endpoint(db_session: AsyncSession, other_org: Organization) -> ProxyEndpoint:
    """Create a proxy endpoint in the OTHER org for isolation tests."""
    ep = ProxyEndpoint(  # type: ignore[call-arg]
        id=uuid.uuid4(),
        org_id=other_org.id,
        name="Other Org Endpoint",
        provider="anthropic",
        target_url="https://api.anthropic.com",
        is_active=True,
        config={},
    )
    db_session.add(ep)
    await db_session.flush()
    return ep


@pytest.fixture
async def legacy_secret_endpoint(db_session: AsyncSession, org: Organization) -> ProxyEndpoint:
    """Model a legacy row that predates write-time credential rejection."""
    ep = ProxyEndpoint(  # type: ignore[call-arg]
        id=uuid.uuid4(),
        org_id=org.id,
        name="Legacy Secret Endpoint",
        provider="openai",
        target_url="https://api.openai.com",
        is_active=True,
        config={
            "api_key": "must-not-leak",
            "nested": {"Authorization": "Bearer must-not-leak"},
            "notes": "innocuous-key-must-not-leak",
            "model_allowlist": ["gpt-4o"],
        },
    )
    db_session.add(ep)
    await db_session.flush()
    return ep


# ── Create Proxy Endpoint ──────────────────────────────────────────


class TestCreateProxyEndpoint:
    """POST /api/v1/proxy-endpoints/"""

    async def test_create_success(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.post(
            f"{PREFIX}/",
            json={
                "name": "Anthropic Claude",
                "provider": "anthropic",
                "target_url": "https://api.anthropic.com",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Anthropic Claude"
        assert body["provider"] == "anthropic"
        assert "id" in body

    async def test_create_with_config(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.post(
            f"{PREFIX}/",
            json={
                "name": "OpenAI GPT-4",
                "provider": "openai",
                "target_url": "https://api.openai.com",
                "config": {"model_allowlist": ["gpt-4o", "gpt-4o-mini"]},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["config"] == {"model_allowlist": ["gpt-4o", "gpt-4o-mini"]}

    @pytest.mark.parametrize(
        "config",
        [
            {"api_key": "provider-secret"},
            {"apiKey": "provider-secret"},
            {"headers": {"Authorization": "Bearer provider-secret"}},
            {"nested": {"client_secret": "provider-secret"}},
            {"auth_token": "provider-secret"},
            {"provider_credential": "provider-secret"},
            {"notes": "sk-secret-under-innocuous-key"},
            {"timeout": 30},
            {"routing": {"model_allowlist": ["gpt-4o"]}},
            {"model_allowlist": "gpt-4o"},
            {"model_allowlist": [{"name": "gpt-4o"}]},
            {"model_allowlist": [""]},
            {"model_allowlist": [" gpt-4o"]},
            {"model_allowlist": ["gpt-4o"], "notes": "not allowed"},
        ],
    )
    async def test_create_rejects_noncanonical_config(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        config: dict,
    ):
        resp = await client.post(
            f"{PREFIX}/",
            json={
                "name": "Secret Endpoint",
                "provider": "openai",
                "target_url": "https://api.openai.com",
                "config": config,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 422
        assert "only model_allowlist" in resp.json()["detail"]

    @pytest.mark.parametrize(
        "target_url",
        [
            "http://api.openai.com",
            "https://127.0.0.1",
            "https://api.openai.com.evil.example",
            "https://api.openai.com/v1",
        ],
    )
    async def test_create_rejects_unapproved_provider_target(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        target_url: str,
    ):
        resp = await client.post(
            f"{PREFIX}/",
            json={
                "name": "Unsafe Endpoint",
                "provider": "openai",
                "target_url": target_url,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 422
        assert "not allowed" in resp.json()["detail"]

    async def test_create_invalid_provider(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.post(
            f"{PREFIX}/",
            json={
                "name": "Bad",
                "provider": "llama_local",
                "target_url": "http://localhost:8080",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_empty_name(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.post(
            f"{PREFIX}/",
            json={
                "name": "",
                "provider": "openai",
                "target_url": "https://api.openai.com",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_empty_target_url(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.post(
            f"{PREFIX}/",
            json={
                "name": "No URL",
                "provider": "openai",
                "target_url": "",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_no_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{PREFIX}/",
            json={
                "name": "X",
                "provider": "openai",
                "target_url": "https://api.openai.com",
            },
        )
        assert resp.status_code == 401

    async def test_create_viewer_forbidden(self, client: AsyncClient, viewer_headers: dict[str, str]):
        """Viewer is not admin -> 403."""
        resp = await client.post(
            f"{PREFIX}/",
            json={
                "name": "X",
                "provider": "openai",
                "target_url": "https://api.openai.com",
            },
            headers=viewer_headers,
        )
        assert resp.status_code == 403

    async def test_create_member_forbidden(self, client: AsyncClient, member_headers: dict[str, str]):
        """Member is not admin -> 403."""
        resp = await client.post(
            f"{PREFIX}/",
            json={
                "name": "X",
                "provider": "openai",
                "target_url": "https://api.openai.com",
            },
            headers=member_headers,
        )
        assert resp.status_code == 403


# ── List Proxy Endpoints ───────────────────────────────────────────


class TestListProxyEndpoints:
    """GET /api/v1/proxy-endpoints/"""

    async def test_list_empty(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.get(f"{PREFIX}/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_list_with_endpoints(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        openai_endpoint: ProxyEndpoint,
    ):
        resp = await client.get(f"{PREFIX}/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1

    async def test_list_redacts_legacy_secret_config(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        legacy_secret_endpoint: ProxyEndpoint,
    ):
        resp = await client.get(f"{PREFIX}/", headers=auth_headers)

        assert resp.status_code == 200
        serialized = str(resp.json())
        assert "must-not-leak" not in serialized
        item = next(row for row in resp.json()["items"] if row["id"] == str(legacy_secret_endpoint.id))
        assert item["config"] == {"model_allowlist": ["gpt-4o"]}

    async def test_list_pagination(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.get(f"{PREFIX}/?skip=0&limit=1", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 1

    async def test_list_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/")
        assert resp.status_code == 401


# ── Get Proxy Endpoint ─────────────────────────────────────────────


class TestGetProxyEndpoint:
    """GET /api/v1/proxy-endpoints/{id}"""

    async def test_get_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        openai_endpoint: ProxyEndpoint,
    ):
        resp = await client.get(f"{PREFIX}/{openai_endpoint.id}", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "OpenAI Production"
        assert body["provider"] == "openai"

    async def test_get_not_found(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.get(f"{PREFIX}/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_get_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/{uuid.uuid4()}")
        assert resp.status_code == 401

    async def test_get_redacts_legacy_secret_config(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        legacy_secret_endpoint: ProxyEndpoint,
    ):
        resp = await client.get(f"{PREFIX}/{legacy_secret_endpoint.id}", headers=auth_headers)

        assert resp.status_code == 200
        serialized = str(resp.json())
        assert "must-not-leak" not in serialized
        assert resp.json()["config"] == {"model_allowlist": ["gpt-4o"]}

    async def test_get_drops_invalid_legacy_allowlist_value(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        openai_endpoint: ProxyEndpoint,
        db_session: AsyncSession,
    ):
        openai_endpoint.config = {"model_allowlist": ["gpt-4o", {"notes": "must-not-leak"}]}  # type: ignore[assignment]
        await db_session.flush()

        resp = await client.get(f"{PREFIX}/{openai_endpoint.id}", headers=auth_headers)

        assert resp.status_code == 200
        assert "must-not-leak" not in resp.text
        assert resp.json()["config"] == {}


# ── Update Proxy Endpoint ──────────────────────────────────────────


class TestUpdateProxyEndpoint:
    """PATCH /api/v1/proxy-endpoints/{id}"""

    async def test_update_name(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        openai_endpoint: ProxyEndpoint,
    ):
        resp = await client.patch(
            f"{PREFIX}/{openai_endpoint.id}",
            json={"name": "Renamed Endpoint"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Endpoint"

    async def test_update_toggle_active(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        openai_endpoint: ProxyEndpoint,
    ):
        resp = await client.patch(
            f"{PREFIX}/{openai_endpoint.id}",
            json={"is_active": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        is_active = resp.json().get("is_active", resp.json().get("isActive"))
        assert is_active is False

    async def test_update_target_url(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        openai_endpoint: ProxyEndpoint,
    ):
        resp = await client.patch(
            f"{PREFIX}/{openai_endpoint.id}",
            json={"target_url": "https://api.openai.com:443"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize(
        "config",
        [
            {"api_key": "must-not-persist"},
            {"notes": "sk-secret-under-innocuous-key"},
            {"model_allowlist": "gpt-4o"},
            {"model_allowlist": ["gpt-4o", {"nested": "not allowed"}]},
            {"model_allowlist": ["gpt-4o"], "timeout": 30},
        ],
    )
    async def test_update_rejects_noncanonical_config(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        openai_endpoint: ProxyEndpoint,
        db_session: AsyncSession,
        config: dict,
    ):
        resp = await client.patch(
            f"{PREFIX}/{openai_endpoint.id}",
            json={"config": config},
            headers=auth_headers,
        )

        assert resp.status_code == 422
        assert "only model_allowlist" in resp.json()["detail"]
        await db_session.refresh(openai_endpoint)
        assert openai_endpoint.config == {"model_allowlist": ["gpt-4o"]}  # type: ignore[reportGeneralTypeIssues]

    async def test_update_not_found(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.patch(
            f"{PREFIX}/{uuid.uuid4()}",
            json={"name": "Ghost"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_no_auth(self, client: AsyncClient):
        resp = await client.patch(f"{PREFIX}/{uuid.uuid4()}", json={"name": "Hacked"})
        assert resp.status_code == 401

    async def test_update_viewer_forbidden(
        self,
        client: AsyncClient,
        viewer_headers: dict[str, str],
        openai_endpoint: ProxyEndpoint,
    ):
        resp = await client.patch(
            f"{PREFIX}/{openai_endpoint.id}",
            json={"name": "Viewer Attempt"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403


# ── Delete Proxy Endpoint ──────────────────────────────────────────


class TestDeleteProxyEndpoint:
    """DELETE /api/v1/proxy-endpoints/{id}"""

    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        openai_endpoint: ProxyEndpoint,
    ):
        resp = await client.delete(f"{PREFIX}/{openai_endpoint.id}", headers=auth_headers)
        assert resp.status_code == 204

    async def test_delete_not_found(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.delete(f"{PREFIX}/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404

    async def test_delete_no_auth(self, client: AsyncClient):
        resp = await client.delete(f"{PREFIX}/{uuid.uuid4()}")
        assert resp.status_code == 401

    async def test_delete_viewer_forbidden(
        self,
        client: AsyncClient,
        viewer_headers: dict[str, str],
        openai_endpoint: ProxyEndpoint,
    ):
        resp = await client.delete(
            f"{PREFIX}/{openai_endpoint.id}",
            headers=viewer_headers,
        )
        assert resp.status_code == 403


# ── Tenant Isolation ────────────────────────────────────────────────


class TestProxyEndpointTenantIsolation:
    """Cross-org proxy endpoint access blocked."""

    async def test_other_org_cannot_see_endpoint(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        openai_endpoint: ProxyEndpoint,
    ):
        resp = await client.get(f"{PREFIX}/{openai_endpoint.id}", headers=other_org_headers)
        assert resp.status_code == 404

    async def test_other_org_list_is_empty(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        openai_endpoint: ProxyEndpoint,
    ):
        resp = await client.get(f"{PREFIX}/", headers=other_org_headers)
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert str(openai_endpoint.id) not in ids

    async def test_other_org_cannot_update_endpoint(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        openai_endpoint: ProxyEndpoint,
    ):
        resp = await client.patch(
            f"{PREFIX}/{openai_endpoint.id}",
            json={"name": "Stolen"},
            headers=other_org_headers,
        )
        assert resp.status_code == 404

    async def test_other_org_cannot_delete_endpoint(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        openai_endpoint: ProxyEndpoint,
    ):
        resp = await client.delete(f"{PREFIX}/{openai_endpoint.id}", headers=other_org_headers)
        assert resp.status_code == 404
