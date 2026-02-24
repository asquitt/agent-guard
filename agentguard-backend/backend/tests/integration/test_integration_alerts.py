"""Integration tests for alerts.py router.

Endpoints:
  POST   /api/v1/alerts/destinations
  GET    /api/v1/alerts/destinations
  PATCH  /api/v1/alerts/destinations/{dest_id}
  DELETE /api/v1/alerts/destinations/{dest_id}
  POST   /api/v1/alerts/destinations/{dest_id}/test
  GET    /api/v1/alerts/
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert, AlertDestination
from app.models.incident import Incident
from app.models.user import Organization, User

PREFIX = "/api/v1/alerts"


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
async def slack_destination(
    db_session: AsyncSession, org: Organization
) -> AlertDestination:
    """Create a Slack alert destination in the primary org."""
    dest = AlertDestination(
        id=uuid.uuid4(),
        org_id=org.id,
        name="Slack #security",
        destination_type="slack",
        config={"webhook_url": "https://hooks.slack.test/T000/B000/xxx"},
        is_active=True,
    )
    db_session.add(dest)
    await db_session.flush()
    return dest


@pytest.fixture
async def alert_record(
    db_session: AsyncSession,
    org: Organization,
    incident: Incident,
    slack_destination: AlertDestination,
) -> Alert:
    """Create a test alert linking an incident to a destination."""
    alert = Alert(
        id=uuid.uuid4(),
        org_id=org.id,
        incident_id=incident.id,
        destination_id=slack_destination.id,
        status="sent",
    )
    db_session.add(alert)
    await db_session.flush()
    return alert


@pytest.fixture
async def other_org_destination(
    db_session: AsyncSession, other_org: Organization
) -> AlertDestination:
    """Create a destination in the OTHER org for isolation tests."""
    dest = AlertDestination(
        id=uuid.uuid4(),
        org_id=other_org.id,
        name="Other Org Slack",
        destination_type="slack",
        config={"webhook_url": "https://hooks.slack.test/OTHER"},
        is_active=True,
    )
    db_session.add(dest)
    await db_session.flush()
    return dest


# ── Create Destination ──────────────────────────────────────────────


class TestCreateDestination:
    """POST /api/v1/alerts/destinations"""

    async def test_create_success(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/destinations",
            json={
                "name": "PagerDuty On-Call",
                "destination_type": "pagerduty",
                "config": {"routing_key": "R000abc"},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "PagerDuty On-Call"
        dest_type = body.get("destination_type", body.get("destinationType"))
        assert dest_type == "pagerduty"
        assert "id" in body

    async def test_create_minimal(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Name + destination_type only (no config)."""
        resp = await client.post(
            f"{PREFIX}/destinations",
            json={"name": "Email Alerts", "destination_type": "email"},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    async def test_create_invalid_destination_type(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/destinations",
            json={"name": "Bad", "destination_type": "telegram"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_empty_name(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/destinations",
            json={"name": "", "destination_type": "slack"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_create_no_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{PREFIX}/destinations",
            json={"name": "X", "destination_type": "slack"},
        )
        assert resp.status_code == 401

    async def test_create_viewer_forbidden(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ):
        """Viewer is not admin -> 403."""
        resp = await client.post(
            f"{PREFIX}/destinations",
            json={"name": "X", "destination_type": "slack"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403

    async def test_create_member_forbidden(
        self, client: AsyncClient, member_headers: dict[str, str]
    ):
        """Member is not admin -> 403."""
        resp = await client.post(
            f"{PREFIX}/destinations",
            json={"name": "X", "destination_type": "slack"},
            headers=member_headers,
        )
        assert resp.status_code == 403


# ── List Destinations ───────────────────────────────────────────────


class TestListDestinations:
    """GET /api/v1/alerts/destinations"""

    async def test_list_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/destinations", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_list_with_destination(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        slack_destination: AlertDestination,
    ):
        resp = await client.get(
            f"{PREFIX}/destinations", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        item = body["items"][0]
        assert item["name"] == "Slack #security"

    async def test_list_pagination(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(
            f"{PREFIX}/destinations?skip=0&limit=1", headers=auth_headers
        )
        assert resp.status_code == 200
        assert len(resp.json()["items"]) <= 1

    async def test_list_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/destinations")
        assert resp.status_code == 401

    async def test_list_viewer_allowed(
        self,
        client: AsyncClient,
        viewer_headers: dict[str, str],
        slack_destination: AlertDestination,
    ):
        """Viewer has alerts:read -> can list destinations."""
        resp = await client.get(
            f"{PREFIX}/destinations", headers=viewer_headers
        )
        assert resp.status_code == 200


# ── Update Destination ──────────────────────────────────────────────


class TestUpdateDestination:
    """PATCH /api/v1/alerts/destinations/{dest_id}"""

    async def test_update_name(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        slack_destination: AlertDestination,
    ):
        resp = await client.patch(
            f"{PREFIX}/destinations/{slack_destination.id}",
            json={"name": "Renamed Slack"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Slack"

    async def test_update_toggle_active(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        slack_destination: AlertDestination,
    ):
        resp = await client.patch(
            f"{PREFIX}/destinations/{slack_destination.id}",
            json={"is_active": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        is_active = resp.json().get("is_active", resp.json().get("isActive"))
        assert is_active is False

    async def test_update_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.patch(
            f"{PREFIX}/destinations/{uuid.uuid4()}",
            json={"name": "Ghost"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_update_no_auth(self, client: AsyncClient):
        resp = await client.patch(
            f"{PREFIX}/destinations/{uuid.uuid4()}",
            json={"name": "Hacked"},
        )
        assert resp.status_code == 401

    async def test_update_viewer_forbidden(
        self,
        client: AsyncClient,
        viewer_headers: dict[str, str],
        slack_destination: AlertDestination,
    ):
        resp = await client.patch(
            f"{PREFIX}/destinations/{slack_destination.id}",
            json={"name": "Viewer Attempt"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403


# ── Delete Destination ──────────────────────────────────────────────


class TestDeleteDestination:
    """DELETE /api/v1/alerts/destinations/{dest_id}"""

    async def test_delete_success(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        slack_destination: AlertDestination,
    ):
        resp = await client.delete(
            f"{PREFIX}/destinations/{slack_destination.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204

    async def test_delete_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.delete(
            f"{PREFIX}/destinations/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_delete_no_auth(self, client: AsyncClient):
        resp = await client.delete(
            f"{PREFIX}/destinations/{uuid.uuid4()}"
        )
        assert resp.status_code == 401

    async def test_delete_viewer_forbidden(
        self,
        client: AsyncClient,
        viewer_headers: dict[str, str],
        slack_destination: AlertDestination,
    ):
        resp = await client.delete(
            f"{PREFIX}/destinations/{slack_destination.id}",
            headers=viewer_headers,
        )
        assert resp.status_code == 403


# ── Test Destination ────────────────────────────────────────────────


class TestTestDestination:
    """POST /api/v1/alerts/destinations/{dest_id}/test"""

    async def test_test_destination_not_found(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.post(
            f"{PREFIX}/destinations/{uuid.uuid4()}/test",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    async def test_test_no_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{PREFIX}/destinations/{uuid.uuid4()}/test"
        )
        assert resp.status_code == 401

    async def test_test_viewer_forbidden(
        self,
        client: AsyncClient,
        viewer_headers: dict[str, str],
        slack_destination: AlertDestination,
    ):
        resp = await client.post(
            f"{PREFIX}/destinations/{slack_destination.id}/test",
            headers=viewer_headers,
        )
        assert resp.status_code == 403


# ── List Alerts ─────────────────────────────────────────────────────


class TestListAlerts:
    """GET /api/v1/alerts/"""

    async def test_list_empty(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        resp = await client.get(f"{PREFIX}/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_list_with_alerts(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        alert_record: Alert,
    ):
        resp = await client.get(f"{PREFIX}/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        item = body["items"][0]
        assert "id" in item
        assert "status" in item

    async def test_list_filter_by_incident(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        alert_record: Alert,
        incident: Incident,
    ):
        resp = await client.get(
            f"{PREFIX}/?incident_id={incident.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1

    async def test_list_filter_by_destination(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        alert_record: Alert,
        slack_destination: AlertDestination,
    ):
        resp = await client.get(
            f"{PREFIX}/?destination_id={slack_destination.id}",
            headers=auth_headers,
        )
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

    async def test_list_viewer_allowed(
        self,
        client: AsyncClient,
        viewer_headers: dict[str, str],
        alert_record: Alert,
    ):
        """Viewer has alerts:read -> can list alerts."""
        resp = await client.get(f"{PREFIX}/", headers=viewer_headers)
        assert resp.status_code == 200


# ── Tenant Isolation ────────────────────────────────────────────────


class TestAlertTenantIsolation:
    """Cross-org alert/destination access blocked."""

    async def test_other_org_cannot_see_destination(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        slack_destination: AlertDestination,
    ):
        """Listing destinations from other org should not include primary org's."""
        resp = await client.get(
            f"{PREFIX}/destinations", headers=other_org_headers
        )
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert str(slack_destination.id) not in ids

    async def test_other_org_cannot_update_destination(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        slack_destination: AlertDestination,
    ):
        resp = await client.patch(
            f"{PREFIX}/destinations/{slack_destination.id}",
            json={"name": "Stolen"},
            headers=other_org_headers,
        )
        assert resp.status_code == 404

    async def test_other_org_cannot_delete_destination(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        slack_destination: AlertDestination,
    ):
        resp = await client.delete(
            f"{PREFIX}/destinations/{slack_destination.id}",
            headers=other_org_headers,
        )
        assert resp.status_code == 404

    async def test_other_org_alerts_list_is_empty(
        self,
        client: AsyncClient,
        other_org_headers: dict[str, str],
        alert_record: Alert,
    ):
        """Other org list does not include primary org's alerts."""
        resp = await client.get(f"{PREFIX}/", headers=other_org_headers)
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert str(alert_record.id) not in ids
