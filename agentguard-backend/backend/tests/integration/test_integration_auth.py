"""Integration tests for auth.py router.

Endpoints:
  POST /api/v1/auth/register
  POST /api/v1/auth/login
  POST /api/v1/auth/refresh
  POST /api/v1/auth/change-password
  POST /api/v1/auth/forgot-password
  POST /api/v1/auth/reset-password
  GET  /api/v1/auth/me
  PATCH /api/v1/auth/me
  POST /api/v1/auth/logout
  GET  /api/v1/auth/me/notifications
  PUT  /api/v1/auth/me/notifications
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import limiter as registration_limiter
from app.core.config import settings
from app.models.user import Organization, User

PREFIX = "/api/v1/auth"


@pytest.fixture(autouse=True)
def _enable_local_registration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep existing auth lifecycle tests inside the explicit test bypass."""
    registration_limiter.reset()
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "REGISTRATION_ENABLED", True)
    monkeypatch.setattr(settings, "LOCAL_REGISTRATION_BYPASS_ENABLED", True)


# ── Register ─────────────────────────────────────────────────────────


class TestRegister:
    """POST /api/v1/auth/register"""

    @patch("app.services.billing_service.get_or_create_stripe_customer", new_callable=AsyncMock)
    async def test_register_success(self, mock_stripe: AsyncMock, client: AsyncClient):
        resp = await client.post(
            f"{PREFIX}/register",
            json={
                "email": "newuser@example.com",
                "password": "StrongPass1!xx",
                "full_name": "New User",
                "org_name": "New Org",
                "controlled_evaluation_accepted": True,
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    @patch("app.services.billing_service.get_or_create_stripe_customer", new_callable=AsyncMock)
    async def test_register_duplicate_email(self, mock_stripe: AsyncMock, client: AsyncClient):
        """Register same email twice -> 409."""
        payload = {
            "email": "dupe@example.com",
            "password": "StrongPass1!xx",
            "full_name": "Dupe User",
            "org_name": "Dupe Org",
            "controlled_evaluation_accepted": True,
        }
        resp1 = await client.post(f"{PREFIX}/register", json=payload)
        assert resp1.status_code == 201

        # Second attempt with same email
        payload["org_name"] = "Different Org"
        resp2 = await client.post(f"{PREFIX}/register", json=payload)
        assert resp2.status_code == 409

    async def test_register_weak_password(self, client: AsyncClient):
        """Weak password -> 422."""
        resp = await client.post(
            f"{PREFIX}/register",
            json={
                "email": "weak@example.com",
                "password": "short",
                "full_name": "Weak User",
                "org_name": "Weak Org",
                "controlled_evaluation_accepted": True,
            },
        )
        assert resp.status_code == 422

    async def test_register_missing_fields(self, client: AsyncClient):
        """Missing required fields -> 422."""
        resp = await client.post(f"{PREFIX}/register", json={"email": "x@y.com"})
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient):
        """Invalid email format -> 422."""
        resp = await client.post(
            f"{PREFIX}/register",
            json={
                "email": "not-an-email",
                "password": "StrongPass1!xx",
                "full_name": "Bad Email",
                "org_name": "Some Org",
                "controlled_evaluation_accepted": True,
            },
        )
        assert resp.status_code == 422


# ── Login ────────────────────────────────────────────────────────────


class TestLogin:
    """POST /api/v1/auth/login"""

    @patch("app.services.billing_service.get_or_create_stripe_customer", new_callable=AsyncMock)
    async def test_login_success(self, mock_stripe: AsyncMock, client: AsyncClient):
        """Register then login with correct credentials."""
        await client.post(
            f"{PREFIX}/register",
            json={
                "email": "login@example.com",
                "password": "StrongPass1!xx",
                "full_name": "Login User",
                "org_name": "Login Org",
                "controlled_evaluation_accepted": True,
            },
        )
        resp = await client.post(
            f"{PREFIX}/login",
            json={"email": "login@example.com", "password": "StrongPass1!xx"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    async def test_login_wrong_password(self, client: AsyncClient, user: User):
        """Wrong password -> 401."""
        resp = await client.post(
            f"{PREFIX}/login",
            json={"email": "testadmin@agentguard.dev", "password": "WrongPass1!xx"},
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_email(self, client: AsyncClient):
        """Email that doesn't exist -> 401."""
        resp = await client.post(
            f"{PREFIX}/login",
            json={"email": "nobody@example.com", "password": "SomePass1!xx"},
        )
        assert resp.status_code == 401

    async def test_login_missing_fields(self, client: AsyncClient):
        """Missing password -> 422."""
        resp = await client.post(f"{PREFIX}/login", json={"email": "test@example.com"})
        assert resp.status_code == 422


# ── Refresh ──────────────────────────────────────────────────────────


class TestRefresh:
    """POST /api/v1/auth/refresh"""

    @patch("app.services.billing_service.get_or_create_stripe_customer", new_callable=AsyncMock)
    async def test_refresh_success(self, mock_stripe: AsyncMock, client: AsyncClient):
        """Register, then use refresh token to get new tokens."""
        reg = await client.post(
            f"{PREFIX}/register",
            json={
                "email": "refresh@example.com",
                "password": "StrongPass1!xx",
                "full_name": "Refresh User",
                "org_name": "Refresh Org",
                "controlled_evaluation_accepted": True,
            },
        )
        refresh_token = reg.json()["refresh_token"]

        resp = await client.post(
            f"{PREFIX}/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    async def test_refresh_invalid_token(self, client: AsyncClient):
        """Invalid refresh token -> 401."""
        resp = await client.post(
            f"{PREFIX}/refresh",
            json={"refresh_token": "invalid-refresh-token"},
        )
        assert resp.status_code == 401

    async def test_refresh_missing_token(self, client: AsyncClient):
        """Missing refresh_token field -> 422."""
        resp = await client.post(f"{PREFIX}/refresh", json={})
        assert resp.status_code == 422


# ── Change Password ──────────────────────────────────────────────────


class TestChangePassword:
    """POST /api/v1/auth/change-password"""

    async def test_change_password_success(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.post(
            f"{PREFIX}/change-password",
            json={
                "current_password": "TestPassword1!",
                "new_password": "NewStrongPass2!x",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    async def test_change_password_wrong_current(self, client: AsyncClient, auth_headers: dict[str, str]):
        """Wrong current password -> 401."""
        resp = await client.post(
            f"{PREFIX}/change-password",
            json={
                "current_password": "WrongCurrent1!xx",
                "new_password": "NewStrongPass2!x",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 401

    async def test_change_password_no_auth(self, client: AsyncClient):
        """No auth -> 403."""
        resp = await client.post(
            f"{PREFIX}/change-password",
            json={
                "current_password": "TestPassword1!",
                "new_password": "NewStrongPass2!x",
            },
        )
        assert resp.status_code == 401

    async def test_change_password_weak_new(self, client: AsyncClient, auth_headers: dict[str, str]):
        """Weak new password -> 422."""
        resp = await client.post(
            f"{PREFIX}/change-password",
            json={
                "current_password": "TestPassword1!",
                "new_password": "weak",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422


# ── Forgot Password ──────────────────────────────────────────────────


class TestForgotPassword:
    """POST /api/v1/auth/forgot-password"""

    async def test_forgot_password_existing_email(self, client: AsyncClient, user: User):
        """Always returns 200 (prevents email enumeration)."""
        resp = await client.post(
            f"{PREFIX}/forgot-password",
            json={"email": "testadmin@agentguard.dev"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "message" in body

    async def test_forgot_password_nonexistent_email(self, client: AsyncClient):
        """Non-existent email also returns 200."""
        resp = await client.post(
            f"{PREFIX}/forgot-password",
            json={"email": "nobody@nowhere.com"},
        )
        assert resp.status_code == 200

    async def test_forgot_password_invalid_email(self, client: AsyncClient):
        """Invalid email format -> 422."""
        resp = await client.post(
            f"{PREFIX}/forgot-password",
            json={"email": "not-an-email"},
        )
        assert resp.status_code == 422


# ── Reset Password ───────────────────────────────────────────────────


class TestResetPassword:
    """POST /api/v1/auth/reset-password"""

    async def test_reset_password_success(self, client: AsyncClient, user: User):
        """Valid reset token + strong password -> 200 with new tokens."""
        from app.core.auth import create_password_reset_token

        token = create_password_reset_token(str(user.id))
        resp = await client.post(
            f"{PREFIX}/reset-password",
            json={"token": token, "new_password": "ResetPass123!xx"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    async def test_reset_password_invalid_token(self, client: AsyncClient):
        """Invalid token -> 400."""
        resp = await client.post(
            f"{PREFIX}/reset-password",
            json={"token": "invalid-token", "new_password": "ResetPass123!xx"},
        )
        assert resp.status_code == 400

    async def test_reset_password_weak_password(self, client: AsyncClient, user: User):
        """Weak new password -> 422."""
        from app.core.auth import create_password_reset_token

        token = create_password_reset_token(str(user.id))
        resp = await client.post(
            f"{PREFIX}/reset-password",
            json={"token": token, "new_password": "weak"},
        )
        assert resp.status_code == 422


# ── Get Me ───────────────────────────────────────────────────────────


class TestGetMe:
    """GET /api/v1/auth/me"""

    async def test_get_me_success(self, client: AsyncClient, auth_headers: dict[str, str], user: User):
        resp = await client.get(f"{PREFIX}/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "user" in body
        assert "organization" in body
        assert body["user"]["email"] == "testadmin@agentguard.dev"

    async def test_get_me_no_auth(self, client: AsyncClient):
        """No auth -> 403."""
        resp = await client.get(f"{PREFIX}/me")
        assert resp.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        """Bad token -> 401."""
        resp = await client.get(
            f"{PREFIX}/me",
            headers={"Authorization": "Bearer bad-token"},
        )
        assert resp.status_code == 401


# ── Update Profile ───────────────────────────────────────────────────


class TestUpdateProfile:
    """PATCH /api/v1/auth/me"""

    async def test_update_profile_success(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.patch(
            f"{PREFIX}/me",
            json={"full_name": "Updated Name"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        # The response uses serialization_alias "name" for full_name
        assert body.get("name") == "Updated Name" or body.get("full_name") == "Updated Name"

    async def test_update_profile_no_auth(self, client: AsyncClient):
        """No auth -> 403."""
        resp = await client.patch(
            f"{PREFIX}/me",
            json={"full_name": "Hacker"},
        )
        assert resp.status_code == 401


# ── Logout ───────────────────────────────────────────────────────────


class TestLogout:
    """POST /api/v1/auth/logout"""

    async def test_logout_success(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.post(f"{PREFIX}/logout", headers=auth_headers)
        assert resp.status_code == 204

    async def test_logout_no_auth(self, client: AsyncClient):
        """No auth -> 403."""
        resp = await client.post(f"{PREFIX}/logout")
        assert resp.status_code == 401


# ── Notification Preferences ─────────────────────────────────────────


class TestNotificationPreferences:
    """GET /api/v1/auth/me/notifications
    PUT /api/v1/auth/me/notifications
    """

    async def test_get_notifications_default(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.get(f"{PREFIX}/me/notifications", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "preferences" in body
        prefs = body["preferences"]
        assert "email_enabled" in prefs
        assert "min_severity" in prefs

    async def test_update_notifications(self, client: AsyncClient, auth_headers: dict[str, str]):
        resp = await client.put(
            f"{PREFIX}/me/notifications",
            json={
                "email_enabled": False,
                "email_digest": "weekly",
                "min_severity": "high",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["preferences"]["email_enabled"] is False
        assert body["preferences"]["email_digest"] == "weekly"
        assert body["preferences"]["min_severity"] == "high"

    async def test_get_notifications_no_auth(self, client: AsyncClient):
        """No auth -> 403."""
        resp = await client.get(f"{PREFIX}/me/notifications")
        assert resp.status_code == 401

    async def test_update_notifications_no_auth(self, client: AsyncClient):
        """No auth -> 403."""
        resp = await client.put(
            f"{PREFIX}/me/notifications",
            json={"email_enabled": False},
        )
        assert resp.status_code == 401
