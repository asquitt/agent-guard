"""Integration tests for incidents.py router.

Endpoints:
  GET    /api/v1/incidents/stats
  GET    /api/v1/incidents/
  GET    /api/v1/incidents/{id}
  PATCH  /api/v1/incidents/{id}
  POST   /api/v1/incidents/{id}/actions
  POST   /api/v1/incidents/bulk-update
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.models.user import Organization, User

PREFIX = "/api/v1/incidents"


# ── Stats ────────────────────────────────────────────────────────────


class TestIncidentStats:
    """GET /api/v1/incidents/stats"""

    async def test_stats_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(f"{PREFIX}/stats", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert "by_severity" in body or "bySeverity" in body
        assert "by_category" in body or "byCategory" in body
        assert "by_status" in body or "byStatus" in body

    async def test_stats_with_incidents(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        incident: Incident,
    ):
        resp = await client.get(f"{PREFIX}/stats", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1

    async def test_stats_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/stats")
        assert resp.status_code == 401


# ── List Incidents ───────────────────────────────────────────────────


class TestListIncidents:
    """GET /api/v1/incidents/"""

    async def test_list_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(f"{PREFIX}/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_list_with_incidents(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        incident: Incident,
    ):
        resp = await client.get(f"{PREFIX}/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert len(body["items"]) >= 1
        item = body["items"][0]
        assert "id" in item
        assert "severity" in item
        assert "status" in item
        assert "title" in item

    async def test_list_filter_by_severity(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        incident: Incident,
    ):
        resp = await client.get(
            f"{PREFIX}/?severity=high", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        for item in body["items"]:
            assert item["severity"] == "high"

    async def test_list_filter_by_status(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        incident: Incident,
    ):
        resp = await client.get(
            f"{PREFIX}/?status=open", headers=auth_headers
        )
        assert resp.status_code == 200

    async def test_list_pagination(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/?skip=0&limit=1", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) <= 1

    async def test_list_beyond_results(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Pagination beyond results -> empty page."""
        resp = await client.get(
            f"{PREFIX}/?skip=9999", headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    async def test_list_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/")
        assert resp.status_code == 401


# ── Get Incident ─────────────────────────────────────────────────────


class TestGetIncident:
    """GET /api/v1/incidents/{id}"""

    async def test_get_incident_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        incident: Incident,
    ):
        resp = await client.get(
            f"{PREFIX}/{incident.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Test PII leak incident"
        assert body["severity"] == "high"
        assert body["category"] == "pii_leak"
        assert "actions" in body

    async def test_get_incident_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/{uuid4()}", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_get_incident_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/{uuid4()}")
        assert resp.status_code == 401


# ── Update Incident ──────────────────────────────────────────────────


class TestUpdateIncident:
    """PATCH /api/v1/incidents/{id}"""

    async def test_update_status_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        incident: Incident,
    ):
        resp = await client.patch(
            f"{PREFIX}/{incident.id}",
            json={"status": "acknowledged"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "acknowledged"

    async def test_update_invalid_status(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        incident: Incident,
    ):
        resp = await client.patch(
            f"{PREFIX}/{incident.id}",
            json={"status": "invalid_status"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_update_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.patch(
            f"{PREFIX}/{uuid4()}",
            json={"status": "resolved"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_no_auth(self, client: AsyncClient):
        resp = await client.patch(
            f"{PREFIX}/{uuid4()}", json={"status": "resolved"}
        )
        assert resp.status_code == 401

    async def test_update_viewer_forbidden(
        self,
        client: AsyncClient,
        viewer_headers: dict[str, str],
        incident: Incident,
    ):
        """Viewer has incidents:read but NOT incidents:write -> 403."""
        resp = await client.patch(
            f"{PREFIX}/{incident.id}",
            json={"status": "resolved"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403


# ── Add Action ───────────────────────────────────────────────────────


class TestAddAction:
    """POST /api/v1/incidents/{id}/actions"""

    async def test_add_action_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        incident: Incident,
    ):
        resp = await client.post(
            f"{PREFIX}/{incident.id}/actions",
            json={"action_type": "comment", "details": {"text": "Investigating"}},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        action_type = body.get("action_type", body.get("actionType"))
        assert action_type == "comment"

    async def test_add_action_incident_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/{uuid4()}/actions",
            json={"action_type": "comment"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_add_action_no_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{PREFIX}/{uuid4()}/actions",
            json={"action_type": "comment"},
        )
        assert resp.status_code == 401


# ── Bulk Update ──────────────────────────────────────────────────────


class TestBulkUpdate:
    """POST /api/v1/incidents/bulk-update"""

    async def test_bulk_update_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        incident: Incident,
    ):
        resp = await client.post(
            f"{PREFIX}/bulk-update",
            json={
                "incident_ids": [str(incident.id)],
                "status": "resolved",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["updated"] >= 1

    async def test_bulk_update_empty_ids(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Empty incident_ids -> 422 (min_length=1)."""
        resp = await client.post(
            f"{PREFIX}/bulk-update",
            json={"incident_ids": [], "status": "resolved"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_bulk_update_invalid_status(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        incident: Incident,
    ):
        resp = await client.post(
            f"{PREFIX}/bulk-update",
            json={
                "incident_ids": [str(incident.id)],
                "status": "invalid",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_bulk_update_no_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{PREFIX}/bulk-update",
            json={"incident_ids": [str(uuid4())], "status": "resolved"},
        )
        assert resp.status_code == 401


# ── Tenant Isolation ─────────────────────────────────────────────────


class TestIncidentTenantIsolation:
    """Verify cross-org incident access is blocked."""

    async def test_other_org_cannot_see_incident(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        incident: Incident,
    ):
        """Incident from org A is invisible to org B -> 404."""
        resp = await client.get(
            f"{PREFIX}/{incident.id}", headers=other_org_headers
        )
        assert resp.status_code == 404

    async def test_other_org_list_is_empty(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        incident: Incident,
    ):
        """Org B list does not include org A's incidents."""
        resp = await client.get(f"{PREFIX}/", headers=other_org_headers)
        assert resp.status_code == 200
        body = resp.json()
        ids = [item["id"] for item in body["items"]]
        assert str(incident.id) not in ids

    async def test_other_org_cannot_update_incident(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        incident: Incident,
    ):
        """Org B cannot update org A's incident -> 404."""
        resp = await client.patch(
            f"{PREFIX}/{incident.id}",
            json={"status": "resolved"},
            headers=other_org_headers,
        )
        assert resp.status_code == 404

    async def test_other_org_bulk_update_no_effect(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        incident: Incident,
    ):
        """Org B bulk updating org A's incident IDs -> 0 updated."""
        resp = await client.post(
            f"{PREFIX}/bulk-update",
            json={
                "incident_ids": [str(incident.id)],
                "status": "resolved",
            },
            headers=other_org_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] == 0
