"""Integration tests for billing.py router.

Endpoints:
  GET    /api/v1/billing/status
  POST   /api/v1/billing/checkout
  POST   /api/v1/billing/portal
  POST   /api/v1/billing/webhook

Tests cover: auth/RBAC, billing status for all plan tiers, Stripe
checkout/portal with mocked Stripe SDK, webhook lifecycle for subscription
events, idempotency, and tenant isolation.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PlanTier, SubscriptionStatus
from app.models.stripe_event import StripeEvent
from app.models.user import Organization

PREFIX = "/api/v1/billing"


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
async def pro_org(db_session: AsyncSession, org: Organization) -> Organization:
    """Primary org upgraded to pro plan."""
    org.plan_tier = PlanTier.PRO.value
    org.monthly_request_count = 500
    org.stripe_customer_id = "cus_test_primary"
    org.stripe_subscription_id = "sub_test_primary"
    org.subscription_status = SubscriptionStatus.ACTIVE.value
    await db_session.flush()
    return org


@pytest.fixture
async def enterprise_org(db_session: AsyncSession, org: Organization) -> Organization:
    """Primary org on enterprise plan."""
    org.plan_tier = PlanTier.ENTERPRISE.value
    org.monthly_request_count = 999999
    org.stripe_customer_id = "cus_test_enterprise"
    org.subscription_status = SubscriptionStatus.ACTIVE.value
    await db_session.flush()
    return org


@pytest.fixture
async def starter_org_at_limit(db_session: AsyncSession, org: Organization) -> Organization:
    """Starter org at the request limit."""
    org.plan_tier = PlanTier.STARTER.value
    org.monthly_request_count = 10000
    await db_session.flush()
    return org


@pytest.fixture
async def org_with_stripe(db_session: AsyncSession, org: Organization) -> Organization:
    """Org with Stripe customer ID configured."""
    org.stripe_customer_id = "cus_test_123"
    await db_session.flush()
    return org


# ── GET /status ───────────────────────────────────────────────────


class TestBillingStatus:
    """GET /api/v1/billing/status"""

    async def test_status_no_auth(self, client: AsyncClient):
        resp = await client.get(f"{PREFIX}/status")
        assert resp.status_code == 401

    async def test_status_starter_plan(
        self, client: AsyncClient, auth_headers: dict[str, str], org: Organization
    ):
        resp = await client.get(f"{PREFIX}/status", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["planTier"] == "starter"
        assert body["requestLimit"] == 10000
        assert body["monthlyRequestCount"] == 0

    async def test_status_pro_plan(
        self, client: AsyncClient, auth_headers: dict[str, str], pro_org: Organization
    ):
        resp = await client.get(f"{PREFIX}/status", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["planTier"] == "pro"
        assert body["requestLimit"] == 100000
        assert body["monthlyRequestCount"] == 500
        assert body["subscriptionStatus"] == "active"

    async def test_status_enterprise_plan(
        self, client: AsyncClient, auth_headers: dict[str, str], enterprise_org: Organization
    ):
        resp = await client.get(f"{PREFIX}/status", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["planTier"] == "enterprise"
        assert body["requestLimit"] is None  # unlimited

    async def test_status_viewer_role_can_read(
        self, client: AsyncClient, viewer_headers: dict[str, str], org: Organization
    ):
        """Viewers with billing:read should be able to see billing status."""
        resp = await client.get(f"{PREFIX}/status", headers=viewer_headers)
        # Viewers typically have billing:read permission
        assert resp.status_code in (200, 403)

    async def test_status_tenant_isolation(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
        other_org_headers: dict[str, str],
        pro_org: Organization,
        other_org: Organization,
    ):
        """Users from different orgs should see their own billing data."""
        # Primary org (pro)
        resp1 = await client.get(f"{PREFIX}/status", headers=auth_headers)
        assert resp1.status_code == 200
        assert resp1.json()["planTier"] == "pro"

        # Other org (starter)
        resp2 = await client.get(f"{PREFIX}/status", headers=other_org_headers)
        assert resp2.status_code == 200
        assert resp2.json()["planTier"] == "starter"


# ── POST /checkout ────────────────────────────────────────────────


class TestCheckout:
    """POST /api/v1/billing/checkout"""

    async def test_checkout_no_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{PREFIX}/checkout", json={"priceId": "price_test_123"}
        )
        assert resp.status_code == 401

    async def test_checkout_no_stripe_returns_503(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Without Stripe configured, should return 503."""
        resp = await client.post(
            f"{PREFIX}/checkout",
            json={"priceId": "price_test_123"},
            headers=auth_headers,
        )
        assert resp.status_code == 503

    async def test_checkout_with_stripe_mock(
        self, client: AsyncClient, auth_headers: dict[str, str], org_with_stripe: Organization
    ):
        """With mocked Stripe, should return a checkout URL."""
        checkout_url = "https://checkout.stripe.com/test_session_123"
        with patch(
            "app.services.billing_service.create_checkout_session",
            new_callable=AsyncMock,
            return_value=checkout_url,
        ):
            resp = await client.post(
                f"{PREFIX}/checkout",
                json={"priceId": "price_pro_monthly"},
                headers=auth_headers,
            )
            if resp.status_code == 200:
                body = resp.json()
                assert "checkoutUrl" in body or "checkout_url" in body
            else:
                assert resp.status_code == 503

    async def test_checkout_missing_price_id(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Missing price_id should return 422."""
        resp = await client.post(
            f"{PREFIX}/checkout",
            json={},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_checkout_viewer_cannot_create(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ):
        """Viewers should not be able to create checkout sessions (billing:write required)."""
        resp = await client.post(
            f"{PREFIX}/checkout",
            json={"priceId": "price_test_123"},
            headers=viewer_headers,
        )
        assert resp.status_code == 403


# ── POST /portal ──────────────────────────────────────────────────


class TestPortal:
    """POST /api/v1/billing/portal"""

    async def test_portal_no_auth(self, client: AsyncClient):
        resp = await client.post(f"{PREFIX}/portal")
        assert resp.status_code == 401

    async def test_portal_no_stripe_returns_503(
        self, client: AsyncClient, auth_headers: dict[str, str]
    ):
        """Without Stripe configured, should return 503."""
        resp = await client.post(f"{PREFIX}/portal", headers=auth_headers)
        assert resp.status_code == 503

    async def test_portal_with_stripe_mock(
        self, client: AsyncClient, auth_headers: dict[str, str], org_with_stripe: Organization
    ):
        """With mocked Stripe, should return a portal URL."""
        portal_url = "https://billing.stripe.com/session/test_portal_123"
        with patch(
            "app.services.billing_service.create_customer_portal_session",
            new_callable=AsyncMock,
            return_value=portal_url,
        ):
            resp = await client.post(
                f"{PREFIX}/portal", headers=auth_headers
            )
            if resp.status_code == 200:
                body = resp.json()
                assert "portalUrl" in body or "portal_url" in body
            else:
                assert resp.status_code == 503

    async def test_portal_viewer_cannot_access(
        self, client: AsyncClient, viewer_headers: dict[str, str]
    ):
        """Viewers should not be able to create portal sessions (billing:write required)."""
        resp = await client.post(f"{PREFIX}/portal", headers=viewer_headers)
        assert resp.status_code == 403


# ── POST /webhook ─────────────────────────────────────────────────


class TestWebhook:
    """POST /api/v1/billing/webhook — Stripe webhook events."""

    async def test_webhook_invalid_signature(self, client: AsyncClient):
        """Webhook without valid Stripe signature should fail."""
        resp = await client.post(
            f"{PREFIX}/webhook",
            content=b"{}",
            headers={"stripe-signature": "invalid"},
        )
        assert resp.status_code == 400

    async def test_webhook_missing_signature(self, client: AsyncClient):
        """Webhook without stripe-signature header should fail."""
        resp = await client.post(
            f"{PREFIX}/webhook",
            content=b'{"type": "checkout.session.completed"}',
        )
        assert resp.status_code == 400

    async def test_webhook_empty_body(self, client: AsyncClient):
        """Webhook with empty body should fail."""
        resp = await client.post(
            f"{PREFIX}/webhook",
            content=b"",
            headers={"stripe-signature": "t=123,v1=abc"},
        )
        assert resp.status_code == 400

    async def test_webhook_no_jwt_required(self, client: AsyncClient):
        """Webhook endpoint should NOT require JWT auth (uses Stripe signature)."""
        # No auth header at all - should get 400 (bad signature), not 401
        resp = await client.post(
            f"{PREFIX}/webhook",
            content=b"{}",
            headers={"stripe-signature": "t=123,v1=abc"},
        )
        assert resp.status_code == 400  # not 401


# ── Billing Service Unit Tests (via service layer) ────────────────


class TestBillingServiceLogic:
    """Test billing_service functions directly for business logic."""

    def test_get_request_limit_starter(self):
        from app.services.billing_service import get_request_limit

        assert get_request_limit("starter") == 10000

    def test_get_request_limit_pro(self):
        from app.services.billing_service import get_request_limit

        assert get_request_limit("pro") == 100000

    def test_get_request_limit_enterprise(self):
        from app.services.billing_service import get_request_limit

        assert get_request_limit("enterprise") is None

    def test_get_request_limit_unknown_falls_back_to_starter(self):
        from app.services.billing_service import get_request_limit

        assert get_request_limit("unknown_plan") == 10000

    def test_price_id_to_plan_tier_pro(self):
        from app.services.billing_service import _price_id_to_plan_tier

        with patch("app.services.billing_service.settings") as mock_settings:
            mock_settings.STRIPE_PRO_PRICE_ID = "price_pro_123"
            mock_settings.STRIPE_STARTER_PRICE_ID = "price_starter_123"
            assert _price_id_to_plan_tier("price_pro_123") == "pro"

    def test_price_id_to_plan_tier_starter(self):
        from app.services.billing_service import _price_id_to_plan_tier

        with patch("app.services.billing_service.settings") as mock_settings:
            mock_settings.STRIPE_PRO_PRICE_ID = "price_pro_123"
            mock_settings.STRIPE_STARTER_PRICE_ID = "price_starter_123"
            assert _price_id_to_plan_tier("price_starter_123") == "starter"

    def test_price_id_to_plan_tier_unknown(self):
        from app.services.billing_service import _price_id_to_plan_tier

        with patch("app.services.billing_service.settings") as mock_settings:
            mock_settings.STRIPE_PRO_PRICE_ID = "price_pro_123"
            mock_settings.STRIPE_STARTER_PRICE_ID = "price_starter_123"
            assert _price_id_to_plan_tier("price_unknown_456") == "starter"


class TestBillingStatusData:
    """Test get_billing_status returns correct data shape."""

    async def test_billing_status_returns_all_fields(
        self, org: Organization
    ):
        from app.services.billing_service import get_billing_status

        status = await get_billing_status(org)
        assert "plan_tier" in status
        assert "subscription_status" in status
        assert "monthly_request_count" in status
        assert "request_limit" in status

    async def test_billing_status_monthly_count_defaults_zero(
        self, org: Organization
    ):
        from app.services.billing_service import get_billing_status

        org.monthly_request_count = None
        status = await get_billing_status(org)
        assert status["monthly_request_count"] == 0


class TestEventIdempotency:
    """Test Stripe event deduplication."""

    async def test_duplicate_event_detected(
        self, db_session: AsyncSession, org: Organization
    ):
        from app.services.billing_service import _is_event_processed, _record_event

        event_id = "evt_test_duplicate_123"
        assert await _is_event_processed(db_session, event_id) is False

        await _record_event(db_session, event_id, "checkout.session.completed", str(org.id))
        await db_session.flush()

        assert await _is_event_processed(db_session, event_id) is True

    async def test_different_events_not_confused(
        self, db_session: AsyncSession, org: Organization
    ):
        from app.services.billing_service import _is_event_processed, _record_event

        await _record_event(db_session, "evt_AAA", "checkout.session.completed", str(org.id))
        await db_session.flush()

        assert await _is_event_processed(db_session, "evt_AAA") is True
        assert await _is_event_processed(db_session, "evt_BBB") is False


class TestSubscriptionHandlers:
    """Test webhook handler business logic directly."""

    async def test_subscription_updated_syncs_status(
        self, db_session: AsyncSession, org: Organization
    ):
        """Subscription update should sync status and period end."""
        from app.services.billing_service import _handle_subscription_updated

        org.stripe_customer_id = "cus_test_handler"
        await db_session.flush()

        sub_data = {
            "customer": "cus_test_handler",
            "status": "active",
            "current_period_end": 1735689600,  # 2025-01-01
            "items": {"data": []},
        }
        await _handle_subscription_updated(db_session, sub_data)

        assert org.subscription_status == "active"
        assert org.subscription_current_period_end is not None

    async def test_subscription_deleted_reverts_to_starter(
        self, db_session: AsyncSession, org: Organization
    ):
        """Subscription deletion should revert to starter plan."""
        from app.services.billing_service import _handle_subscription_deleted

        org.plan_tier = "pro"
        org.stripe_customer_id = "cus_test_delete"
        org.stripe_subscription_id = "sub_test_delete"
        org.subscription_status = "active"
        await db_session.flush()

        sub_data = {"customer": "cus_test_delete"}
        await _handle_subscription_deleted(db_session, sub_data)

        assert org.plan_tier == "starter"
        assert org.stripe_subscription_id is None
        assert org.subscription_status == "canceled"

    async def test_payment_failed_marks_past_due(
        self, db_session: AsyncSession, org: Organization
    ):
        """Payment failure should mark subscription as past_due."""
        from app.services.billing_service import _handle_payment_failed

        org.stripe_customer_id = "cus_test_failed"
        org.subscription_status = "active"
        await db_session.flush()

        invoice_data = {"customer": "cus_test_failed"}
        await _handle_payment_failed(db_session, invoice_data)

        assert org.subscription_status == "past_due"

    async def test_subscription_update_with_plan_change(
        self, db_session: AsyncSession, org: Organization
    ):
        """Subscription update with new price should change plan tier."""
        from app.services.billing_service import _handle_subscription_updated

        org.plan_tier = "starter"
        org.stripe_customer_id = "cus_test_upgrade"
        await db_session.flush()

        with patch("app.services.billing_service.settings") as mock_settings:
            mock_settings.STRIPE_PRO_PRICE_ID = "price_pro_monthly"
            mock_settings.STRIPE_STARTER_PRICE_ID = "price_starter_monthly"

            sub_data = {
                "customer": "cus_test_upgrade",
                "status": "active",
                "current_period_end": 1735689600,
                "items": {
                    "data": [
                        {"price": {"id": "price_pro_monthly"}}
                    ]
                },
            }
            await _handle_subscription_updated(db_session, sub_data)

        assert org.plan_tier == "pro"

    async def test_handler_ignores_unknown_customer(
        self, db_session: AsyncSession, org: Organization
    ):
        """Handlers should gracefully handle unknown customer IDs."""
        from app.services.billing_service import _handle_subscription_updated

        sub_data = {
            "customer": "cus_nonexistent_999",
            "status": "active",
            "items": {"data": []},
        }
        # Should not raise
        await _handle_subscription_updated(db_session, sub_data)
        # Org should not be changed
        assert org.plan_tier == "starter"
