"""Integration tests for api_keys.py router.

Endpoints:
  POST   /api/v1/api-keys/       (admin)
  GET    /api/v1/api-keys/       (admin)
  DELETE /api/v1/api-keys/{id}   (admin)
  PATCH  /api/v1/api-keys/{id}   (admin)
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Organization, User

PREFIX = "/api/v1/api-keys"


# ── Create API Key ───────────────────────────────────────────────────


class TestCreateApiKey:
    """POST /api/v1/api-keys/"""

    async def test_create_api_key_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/",
            json={"name": "My Key", "scopes": ["proxy"]},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "key" in body
        assert body["key"].startswith("ag_live_")
        assert body["name"] == "My Key"
        assert "id" in body
        assert body["scopes"] == ["proxy"]

    async def test_create_api_key_no_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{PREFIX}/",
            json={"name": "Hacker Key"},
        )
        assert resp.status_code == 401

    async def test_create_api_key_viewer_forbidden(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ):
        """Viewer cannot create API keys -> 403."""
        resp = await client.post(
            f"{PREFIX}/",
            json={"name": "Viewer Key"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403

    async def test_create_api_key_missing_name(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/",
            json={"scopes": ["proxy"]},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_api_key_empty_name(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/",
            json={"name": "", "scopes": ["proxy"]},
            headers=auth_headers,
        )
        assert resp.status_code == 422


# ── List API Keys ────────────────────────────────────────────────────


class TestListApiKeys:
    """GET /api/v1/api-keys/"""

    async def test_list_api_keys_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(f"{PREFIX}/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_list_api_keys_after_create(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Create a key, then list should include it."""
        await client.post(
            f"{PREFIX}/",
            json={"name": "Listed Key"},
            headers=auth_headers,
        )
        resp = await client.get(f"{PREFIX}/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        # List view should NOT include the full key
        for item in body["items"]:
            assert "key" not in item or item.get("key", "") == ""

    async def test_list_api_keys_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/")
        assert resp.status_code == 401

    async def test_list_api_keys_viewer_forbidden(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ):
        resp = await client.get(f"{PREFIX}/", headers=viewer_headers)
        assert resp.status_code == 403


# ── Revoke API Key ───────────────────────────────────────────────────


class TestRevokeApiKey:
    """DELETE /api/v1/api-keys/{key_id}"""

    async def test_revoke_api_key_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        # Create first
        create_resp = await client.post(
            f"{PREFIX}/",
            json={"name": "Revoke Me"},
            headers=auth_headers,
        )
        key_id = create_resp.json()["id"]

        # Revoke
        resp = await client.delete(
            f"{PREFIX}/{key_id}", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        # Should be marked inactive
        is_active = body.get("is_active", body.get("isActive"))
        assert is_active is False

    async def test_revoke_nonexistent_key(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.delete(
            f"{PREFIX}/{uuid4()}", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_revoke_api_key_no_auth(self, client: AsyncClient):
        resp = await client.delete(f"{PREFIX}/{uuid4()}")
        assert resp.status_code == 401


# ── Update API Key ───────────────────────────────────────────────────


class TestUpdateApiKey:
    """PATCH /api/v1/api-keys/{key_id}"""

    async def test_update_api_key_name(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        # Create first
        create_resp = await client.post(
            f"{PREFIX}/",
            json={"name": "Original Name"},
            headers=auth_headers,
        )
        key_id = create_resp.json()["id"]

        # Update
        resp = await client.patch(
            f"{PREFIX}/{key_id}",
            json={"name": "New Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    async def test_update_api_key_scopes(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        create_resp = await client.post(
            f"{PREFIX}/",
            json={"name": "Scope Test", "scopes": ["proxy"]},
            headers=auth_headers,
        )
        key_id = create_resp.json()["id"]

        resp = await client.patch(
            f"{PREFIX}/{key_id}",
            json={"scopes": ["proxy", "admin"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["scopes"] == ["proxy", "admin"]

    async def test_update_nonexistent_key(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.patch(
            f"{PREFIX}/{uuid4()}",
            json={"name": "Ghost"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_api_key_no_auth(self, client: AsyncClient):
        resp = await client.patch(
            f"{PREFIX}/{uuid4()}",
            json={"name": "Hacked"},
        )
        assert resp.status_code == 401


# ── Tenant Isolation ─────────────────────────────────────────────────


class TestApiKeyTenantIsolation:
    """Verify cross-org API key access is blocked."""

    async def test_other_org_cannot_list_keys(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        other_org_headers: dict[str, str],
    ):
        """Create key in org A, list from org B -> empty."""
        await client.post(
            f"{PREFIX}/",
            json={"name": "Org A Key"},
            headers=auth_headers,
        )
        resp = await client.get(f"{PREFIX}/", headers=other_org_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_other_org_cannot_revoke_key(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        other_org_headers: dict[str, str],
    ):
        """Create key in org A, revoke from org B -> 404."""
        create_resp = await client.post(
            f"{PREFIX}/",
            json={"name": "Protected Key"},
            headers=auth_headers,
        )
        key_id = create_resp.json()["id"]

        resp = await client.delete(
            f"{PREFIX}/{key_id}", headers=other_org_headers
        )
        assert resp.status_code == 404

    async def test_other_org_cannot_update_key(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        other_org_headers: dict[str, str],
    ):
        """Create key in org A, update from org B -> 404."""
        create_resp = await client.post(
            f"{PREFIX}/",
            json={"name": "Protected Key"},
            headers=auth_headers,
        )
        key_id = create_resp.json()["id"]

        resp = await client.patch(
            f"{PREFIX}/{key_id}",
            json={"name": "Stolen"},
            headers=other_org_headers,
        )
        assert resp.status_code == 404
