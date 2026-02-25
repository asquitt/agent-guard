"""Integration tests for detectors.py router.

Endpoints:
  POST   /api/v1/detectors/
  GET    /api/v1/detectors/
  GET    /api/v1/detectors/{id}
  PATCH  /api/v1/detectors/{id}
  DELETE /api/v1/detectors/{id}
  POST   /api/v1/detectors/{id}/rules
  DELETE /api/v1/detectors/{id}/rules/{rule_id}
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.detector import Detector
from app.models.user import Organization, User

PREFIX = "/api/v1/detectors"


# ── Create Detector ──────────────────────────────────────────────────


class TestCreateDetector:
    """POST /api/v1/detectors/"""

    async def test_create_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/",
            json={
                "name": "My PII Detector",
                "category": "pii_leak",
                "action_mode": "monitor",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "My PII Detector"
        assert body["category"] == "pii_leak"
        assert "id" in body

    async def test_create_with_rules(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/",
            json={
                "name": "PII With Rules",
                "category": "pii_leak",
                "action_mode": "block",
                "rules": [
                    {
                        "name": "SSN Rule",
                        "rule_type": "regex",
                        "parameters": {"pattern": r"\d{3}-\d{2}-\d{4}"},
                    }
                ],
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["rules"]) == 1

    async def test_create_invalid_category(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/",
            json={
                "name": "Bad Category",
                "category": "nonexistent_category",
                "action_mode": "monitor",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_invalid_action_mode(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/",
            json={
                "name": "Bad Mode",
                "category": "pii_leak",
                "action_mode": "explode",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_no_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{PREFIX}/",
            json={"name": "X", "category": "pii_leak"},
        )
        assert resp.status_code == 401

    async def test_create_viewer_forbidden(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/",
            json={"name": "X", "category": "pii_leak"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403


# ── List Detectors ───────────────────────────────────────────────────


class TestListDetectors:
    """GET /api/v1/detectors/"""

    async def test_list_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(f"{PREFIX}/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_list_with_detectors(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        pii_detector: Detector,
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


# ── Get Detector ─────────────────────────────────────────────────────


class TestGetDetector:
    """GET /api/v1/detectors/{id}"""

    async def test_get_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        pii_detector: Detector,
    ):
        resp = await client.get(
            f"{PREFIX}/{pii_detector.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "PII Leak Detector"
        assert body["category"] == "pii_leak"

    async def test_get_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/{uuid4()}", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_get_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/{uuid4()}")
        assert resp.status_code == 401


# ── Update Detector ──────────────────────────────────────────────────


class TestUpdateDetector:
    """PATCH /api/v1/detectors/{id}"""

    async def test_update_name(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        pii_detector: Detector,
    ):
        resp = await client.patch(
            f"{PREFIX}/{pii_detector.id}",
            json={"name": "Renamed Detector"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Detector"

    async def test_update_toggle_active(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        pii_detector: Detector,
    ):
        resp = await client.patch(
            f"{PREFIX}/{pii_detector.id}",
            json={"is_active": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        is_active = resp.json().get("is_active", resp.json().get("isActive"))
        assert is_active is False

    async def test_update_action_mode(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        pii_detector: Detector,
    ):
        resp = await client.patch(
            f"{PREFIX}/{pii_detector.id}",
            json={"action_mode": "block"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        mode = resp.json().get("action_mode", resp.json().get("actionMode"))
        assert mode == "block"

    async def test_update_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.patch(
            f"{PREFIX}/{uuid4()}",
            json={"name": "Ghost"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_no_auth(self, client: AsyncClient):
        resp = await client.patch(
            f"{PREFIX}/{uuid4()}", json={"name": "Hacked"}
        )
        assert resp.status_code == 401

    async def test_update_viewer_forbidden(
        self,
        client: AsyncClient,
        viewer_headers: dict[str, str],
        pii_detector: Detector,
    ):
        resp = await client.patch(
            f"{PREFIX}/{pii_detector.id}",
            json={"name": "Viewer Attempt"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403


# ── Delete Detector ──────────────────────────────────────────────────


class TestDeleteDetector:
    """DELETE /api/v1/detectors/{id}"""

    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        pii_detector: Detector,
    ):
        resp = await client.delete(
            f"{PREFIX}/{pii_detector.id}", headers=auth_headers
        )
        assert resp.status_code == 204

    async def test_delete_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.delete(
            f"{PREFIX}/{uuid4()}", headers=auth_headers
        )
        assert resp.status_code == 404

    async def test_delete_no_auth(self, client: AsyncClient):
        resp = await client.delete(f"{PREFIX}/{uuid4()}")
        assert resp.status_code == 401


# ── Add Rule ─────────────────────────────────────────────────────────


class TestAddRule:
    """POST /api/v1/detectors/{id}/rules"""

    async def test_add_rule_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        pii_detector: Detector,
    ):
        resp = await client.post(
            f"{PREFIX}/{pii_detector.id}/rules",
            json={
                "name": "Email Pattern",
                "rule_type": "regex",
                "parameters": {"pattern": r"[a-z]+@[a-z]+\.[a-z]+"},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Email Pattern"

    async def test_add_rule_detector_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/{uuid4()}/rules",
            json={"name": "X", "rule_type": "regex"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_add_rule_no_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{PREFIX}/{uuid4()}/rules",
            json={"name": "X", "rule_type": "regex"},
        )
        assert resp.status_code == 401


# ── Delete Rule ──────────────────────────────────────────────────────


class TestDeleteRule:
    """DELETE /api/v1/detectors/{id}/rules/{rule_id}"""

    async def test_delete_rule_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        pii_detector: Detector,
    ):
        # Add a rule first
        create_resp = await client.post(
            f"{PREFIX}/{pii_detector.id}/rules",
            json={"name": "To Delete", "rule_type": "regex"},
            headers=auth_headers,
        )
        rule_id = create_resp.json()["id"]

        # Delete it
        resp = await client.delete(
            f"{PREFIX}/{pii_detector.id}/rules/{rule_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    async def test_delete_rule_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        pii_detector: Detector,
    ):
        resp = await client.delete(
            f"{PREFIX}/{pii_detector.id}/rules/{uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ── Tenant Isolation ─────────────────────────────────────────────────


class TestDetectorTenantIsolation:
    """Cross-org detector access blocked."""

    async def test_other_org_cannot_see_detector(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        pii_detector: Detector,
    ):
        resp = await client.get(
            f"{PREFIX}/{pii_detector.id}", headers=other_org_headers
        )
        assert resp.status_code == 404

    async def test_other_org_list_is_empty(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        pii_detector: Detector,
    ):
        resp = await client.get(f"{PREFIX}/", headers=other_org_headers)
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert str(pii_detector.id) not in ids

    async def test_other_org_cannot_update_detector(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        pii_detector: Detector,
    ):
        resp = await client.patch(
            f"{PREFIX}/{pii_detector.id}",
            json={"name": "Stolen"},
            headers=other_org_headers,
        )
        assert resp.status_code == 404

    async def test_other_org_cannot_delete_detector(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        pii_detector: Detector,
    ):
        resp = await client.delete(
            f"{PREFIX}/{pii_detector.id}", headers=other_org_headers
        )
        assert resp.status_code == 404
