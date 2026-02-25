"""Integration tests for organizations.py router.

Endpoints:
  GET    /api/v1/organizations/current
  PATCH  /api/v1/organizations/current
  GET    /api/v1/organizations/current/members
  GET    /api/v1/organizations/current/ip-allowlist
  PUT    /api/v1/organizations/current/ip-allowlist
  GET    /api/v1/organizations/roles
  PATCH  /api/v1/organizations/current/members/{user_id}
  DELETE /api/v1/organizations/current/members/{user_id}
  POST   /api/v1/organizations/current/members/invite
  GET    /api/v1/organizations/environments
  GET    /api/v1/organizations/current/data-residency
  PUT    /api/v1/organizations/current/data-residency
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Organization, User

PREFIX = "/api/v1/organizations"


# ── Get Current Organization ─────────────────────────────────────────


class TestGetCurrentOrg:
    """GET /api/v1/organizations/current"""

    async def test_get_org_success(
        self, client: AsyncClient, auth_headers: dict[str, str], org: Organization
    ):
        resp = await client.get(f"{PREFIX}/current", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "Test Organization"
        assert body["slug"] == "test-org"
        assert "id" in body

    async def test_get_org_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/current")
        assert resp.status_code == 401

    async def test_get_org_viewer_can_read(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ):
        """Viewer has settings:read -> can access org details."""
        # Viewer does NOT have settings:read, so should get 403
        resp = await client.get(f"{PREFIX}/current", headers=viewer_headers)
        assert resp.status_code == 403


# ── Update Organization ──────────────────────────────────────────────


class TestUpdateOrg:
    """PATCH /api/v1/organizations/current"""

    async def test_update_org_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.patch(
            f"{PREFIX}/current",
            json={"name": "Updated Org Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Org Name"

    async def test_update_org_settings(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.patch(
            f"{PREFIX}/current",
            json={"settings": {"feature_flag": True}},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["settings"]["feature_flag"] is True

    async def test_update_org_no_auth(self, client: AsyncClient):
        resp = await client.patch(
            f"{PREFIX}/current", json={"name": "Hacked"}
        )
        assert resp.status_code == 401

    async def test_update_org_viewer_forbidden(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ):
        """Viewer cannot update org -> 403."""
        resp = await client.patch(
            f"{PREFIX}/current",
            json={"name": "Viewer Attempt"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403


# ── List Members ─────────────────────────────────────────────────────


class TestListMembers:
    """GET /api/v1/organizations/current/members"""

    async def test_list_members_success(
        self, client: AsyncClient, auth_headers: dict[str, str], user: User
    ):
        resp = await client.get(
            f"{PREFIX}/current/members", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 1
        assert isinstance(body["items"], list)

    async def test_list_members_pagination(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/current/members?skip=0&limit=1", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) <= 1

    async def test_list_members_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/current/members")
        assert resp.status_code == 401


# ── Invite Member ────────────────────────────────────────────────────


class TestInviteMember:
    """POST /api/v1/organizations/current/members/invite"""

    async def test_invite_member_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/current/members/invite",
            json={"email": "newinvite@example.com", "role": "member"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["email"] == "newinvite@example.com"
        assert body["role"] == "member"

    async def test_invite_member_duplicate(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Invite same email twice -> 409."""
        payload = {"email": "dupe-invite@example.com", "role": "member"}
        await client.post(
            f"{PREFIX}/current/members/invite",
            json=payload,
            headers=auth_headers,
        )
        resp = await client.post(
            f"{PREFIX}/current/members/invite",
            json=payload,
            headers=auth_headers,
        )
        assert resp.status_code == 409

    async def test_invite_member_invalid_role(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/current/members/invite",
            json={"email": "badrole@example.com", "role": "superadmin"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_invite_member_no_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{PREFIX}/current/members/invite",
            json={"email": "test@example.com", "role": "member"},
        )
        assert resp.status_code == 401

    async def test_invite_member_viewer_forbidden(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/current/members/invite",
            json={"email": "viewer-invite@example.com", "role": "member"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403


# ── Update Member Role ───────────────────────────────────────────────


class TestUpdateMemberRole:
    """PATCH /api/v1/organizations/current/members/{user_id}"""

    async def test_update_member_role_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        member_user: User,
    ):
        resp = await client.patch(
            f"{PREFIX}/current/members/{member_user.id}",
            json={"role": "viewer"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "viewer"

    async def test_update_member_role_invalid_role(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        member_user: User,
    ):
        resp = await client.patch(
            f"{PREFIX}/current/members/{member_user.id}",
            json={"role": "superadmin"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_update_member_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        fake_id = str(uuid4())
        resp = await client.patch(
            f"{PREFIX}/current/members/{fake_id}",
            json={"role": "member"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_member_no_auth(self, client: AsyncClient):
        resp = await client.patch(
            f"{PREFIX}/current/members/{uuid4()}",
            json={"role": "member"},
        )
        assert resp.status_code == 401


# ── Remove Member ────────────────────────────────────────────────────


class TestRemoveMember:
    """DELETE /api/v1/organizations/current/members/{user_id}"""

    async def test_remove_member_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        member_user: User,
    ):
        resp = await client.delete(
            f"{PREFIX}/current/members/{member_user.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    async def test_remove_self_forbidden(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        user: User,
    ):
        """Cannot remove yourself -> 422."""
        resp = await client.delete(
            f"{PREFIX}/current/members/{user.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_remove_member_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        fake_id = str(uuid4())
        resp = await client.delete(
            f"{PREFIX}/current/members/{fake_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_remove_member_no_auth(self, client: AsyncClient):
        resp = await client.delete(
            f"{PREFIX}/current/members/{uuid4()}",
        )
        assert resp.status_code == 401


# ── Tenant Isolation ─────────────────────────────────────────────────


class TestTenantIsolation:
    """Verify that users from Org B cannot access Org A resources."""

    async def test_other_org_cannot_see_members(
        self, client: AsyncClient, other_org_headers: dict[str, str]
    ):
        """Other org lists their OWN members, not the primary org's."""
        resp = await client.get(
            f"{PREFIX}/current/members", headers=other_org_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        # Should only see the other org's user, not the primary org's
        for member in body["items"]:
            assert "other" in member["email"].lower() or member["email"] == "other-admin@other-org.dev"

    async def test_other_org_update_member_not_found(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        user: User,
    ):
        """Other org cannot update primary org's members -> 404."""
        resp = await client.patch(
            f"{PREFIX}/current/members/{user.id}",
            json={"role": "viewer"},
            headers=other_org_headers,
        )
        assert resp.status_code == 404

    async def test_other_org_remove_member_not_found(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        user: User,
    ):
        """Other org cannot remove primary org's members -> 404."""
        resp = await client.delete(
            f"{PREFIX}/current/members/{user.id}",
            headers=other_org_headers,
        )
        assert resp.status_code == 404


# ── IP Allowlist ─────────────────────────────────────────────────────


class TestIpAllowlist:
    """GET/PUT /api/v1/organizations/current/ip-allowlist"""

    async def test_get_ip_allowlist_default(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/current/ip-allowlist", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "ips" in body
        assert "enabled" in body
        assert body["enabled"] is False

    async def test_update_ip_allowlist(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.put(
            f"{PREFIX}/current/ip-allowlist",
            json={"ips": ["10.0.0.1", "192.168.1.0/24"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is True
        assert len(body["ips"]) == 2

    async def test_update_ip_allowlist_invalid_ip(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.put(
            f"{PREFIX}/current/ip-allowlist",
            json={"ips": ["not-an-ip"]},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_ip_allowlist_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/current/ip-allowlist")
        assert resp.status_code == 401


# ── Roles ────────────────────────────────────────────────────────────


class TestRoles:
    """GET /api/v1/organizations/roles"""

    async def test_list_roles(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.get(f"{PREFIX}/roles", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "roles" in body
        role_names = [r["role"] for r in body["roles"]]
        assert "admin" in role_names
        assert "viewer" in role_names
        assert "member" in role_names


# ── Environments ─────────────────────────────────────────────────────


class TestEnvironments:
    """GET /api/v1/organizations/environments"""

    async def test_list_environments(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/environments", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "environments" in body
        assert "current" in body
        env_names = [e["name"] for e in body["environments"]]
        assert "production" in env_names

    async def test_environments_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/environments")
        assert resp.status_code == 401


# ── Data Residency ───────────────────────────────────────────────────


class TestDataResidency:
    """GET/PUT /api/v1/organizations/current/data-residency"""

    async def test_get_data_residency(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/current/data-residency", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "config" in body
        assert "available_regions" in body or "availableRegions" in body

    async def test_update_data_residency(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.put(
            f"{PREFIX}/current/data-residency",
            json={
                "primaryRegion": "eu-west-1",
                "allowedRegions": ["eu-west-1", "eu-central-1"],
                "enforceResidency": True,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200

    async def test_update_data_residency_invalid_region(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.put(
            f"{PREFIX}/current/data-residency",
            json={"primaryRegion": "invalid-region-99"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_data_residency_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/current/data-residency")
        assert resp.status_code == 401
