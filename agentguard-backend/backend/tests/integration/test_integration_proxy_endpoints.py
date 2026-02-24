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

from app.models.proxy import ProxyEndpoint
from app.models.user import Organization, User

PREFIX = "/api/v1/proxy-endpoints"


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
async def openai_endpoint(
    db_session: AsyncSession, org: Organization
) -> ProxyEndpoint:
    """Create an OpenAI proxy endpoint in the primary org."""
    ep = ProxyEndpoint(
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
async def other_org_endpoint(
    db_session: AsyncSession, other_org: Organization
) -> ProxyEndpoint:
    """Create a proxy endpoint in the OTHER org for isolation tests."""
    ep = ProxyEndpoint(
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


# ── Create Proxy Endpoint ──────────────────────────────────────────


class TestCreateProxyEndpoint:
    """POST /api/v1/proxy-endpoints/"""

    async def test_create_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
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

    async def test_create_with_config(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
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

    async def test_create_invalid_provider(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
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

    async def test_create_empty_name(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
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

    async def test_create_empty_target_url(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
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

    async def test_create_viewer_forbidden(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ):
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

    async def test_create_member_forbidden(
        self, client: AsyncClient, member_headers: dict[str, str]
    ):
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

    async def test_list_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
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

    async def test_list_pagination(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/?skip=0&limit=1", headers=auth_headers
        )
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
        resp = await client.get(
            f"{PREFIX}/{openai_endpoint.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "OpenAI Production"
        assert body["provider"] == "openai"

    async def test_get_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/{uuid.uuid4()}", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_get_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/{uuid.uuid4()}")
        assert resp.status_code == 401


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
            json={"target_url": "https://api.openai.com/v2"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_update_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.patch(
            f"{PREFIX}/{uuid.uuid4()}",
            json={"name": "Ghost"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_no_auth(self, client: AsyncClient):
        resp = await client.patch(
            f"{PREFIX}/{uuid.uuid4()}", json={"name": "Hacked"}
        )
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
        resp = await client.delete(
            f"{PREFIX}/{openai_endpoint.id}", headers=auth_headers
        )
        assert resp.status_code == 204

    async def test_delete_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.delete(
            f"{PREFIX}/{uuid.uuid4()}", headers=auth_headers
        )
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
        resp = await client.get(
            f"{PREFIX}/{openai_endpoint.id}", headers=other_org_headers
        )
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
        resp = await client.delete(
            f"{PREFIX}/{openai_endpoint.id}", headers=other_org_headers
        )
        assert resp.status_code == 404
