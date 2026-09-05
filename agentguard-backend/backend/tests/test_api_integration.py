"""Integration tests for API endpoints via FastAPI TestClient."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.auth import limiter as registration_limiter
from app.core.config import settings
from app.main import app


@pytest.fixture
async def raw_client():
    """Async HTTP client without DB override (for mocked tests)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as ac:
        yield ac


@pytest.fixture(autouse=True)
def _enable_local_registration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep mocked registration tests inside the explicit test bypass."""
    registration_limiter.reset()
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "REGISTRATION_ENABLED", True)
    monkeypatch.setattr(settings, "LOCAL_REGISTRATION_BYPASS_ENABLED", True)


# ── Health ───────────────────────────────────────────────────────────


class TestHealthEndpoint:
    async def test_returns_healthy(self, raw_client: AsyncClient):
        resp = await raw_client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"


# ── Auth: Register ───────────────────────────────────────────────────


class TestAuthRegister:
    @patch("app.api.auth.auth_service")
    @patch("app.api.auth.write_audit", new_callable=AsyncMock)
    async def test_register_success(
        self,
        mock_audit: AsyncMock,
        mock_auth_svc: MagicMock,
        raw_client: AsyncClient,
    ):
        user_id = uuid4()
        org_id = uuid4()

        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.token_version = 0

        mock_org = MagicMock()
        mock_org.id = org_id

        mock_auth_svc.register_user = AsyncMock(return_value=(mock_user, mock_org))
        mock_auth_svc.create_token_pair.return_value = ("access_tok", "refresh_tok")

        resp = await raw_client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@example.com",
                "password": "StrongPass1!",
                "full_name": "New User",
                "org_name": "New Org",
                "controlled_evaluation_accepted": True,
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["access_token"] == "access_tok"
        assert body["refresh_token"] == "refresh_tok"


# ── Unauthorized Access ──────────────────────────────────────────────


class TestUnauthorizedAccess:
    async def test_incidents_without_auth(self, raw_client: AsyncClient):
        """GET /api/v1/incidents/ without Authorization header returns 401."""
        resp = await raw_client.get("/api/v1/incidents/")
        assert resp.status_code == 401

    async def test_incidents_with_invalid_token(self, raw_client: AsyncClient):
        """GET /api/v1/incidents/ with garbage token returns 401."""
        resp = await raw_client.get(
            "/api/v1/incidents/",
            headers={"Authorization": "Bearer invalid-token-here"},
        )
        assert resp.status_code == 401

    async def test_detectors_without_auth(self, raw_client: AsyncClient):
        """GET /api/v1/detectors/ without auth returns 401."""
        resp = await raw_client.get("/api/v1/detectors/")
        assert resp.status_code == 401

    async def test_dashboard_with_invalid_token(self, raw_client: AsyncClient):
        """GET /api/v1/dashboard/metrics with bad token returns 401."""
        resp = await raw_client.get(
            "/api/v1/dashboard/metrics",
            headers={"Authorization": "Bearer bad.jwt.token"},
        )
        assert resp.status_code == 401
