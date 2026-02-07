"""Billing service for Stripe integration."""

# pyright: reportCallIssue=false, reportArgumentType=false, reportGeneralTypeIssues=false, reportAttributeAccessIssue=false, reportReturnType=false

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import PlanTier, SubscriptionStatus
from app.models.stripe_event import StripeEvent
from app.models.user import Organization

logger = logging.getLogger(__name__)

# Plan tier request limits
REQUEST_LIMITS: dict[str, int | None] = {
    PlanTier.STARTER.value: 10_000,
    PlanTier.PRO.value: 100_000,
    PlanTier.ENTERPRISE.value: None,  # unlimited
}


def _stripe_available() -> bool:
    """Check if Stripe is configured."""
    return bool(settings.STRIPE_SECRET_KEY)


def get_request_limit(plan_tier: str) -> int | None:
    """Get the monthly request limit for a plan tier. None means unlimited."""
    return REQUEST_LIMITS.get(plan_tier, REQUEST_LIMITS[PlanTier.STARTER.value])


def _price_id_to_plan_tier(price_id: str) -> str:
    """Map a Stripe price ID to a PlanTier value."""
    if price_id == settings.STRIPE_PRO_PRICE_ID:
        return PlanTier.PRO.value
    if price_id == settings.STRIPE_STARTER_PRICE_ID:
        return PlanTier.STARTER.value
    # Unknown price_id — default to starter
    logger.warning("Unknown Stripe price_id: %s", price_id)
    return PlanTier.STARTER.value


async def get_billing_status(org: Organization) -> dict:
    """Get current billing status for an organization."""
    limit = get_request_limit(org.plan_tier)
    return {
        "plan_tier": org.plan_tier,
        "subscription_status": org.subscription_status,
        "current_period_end": org.subscription_current_period_end,
        "monthly_request_count": org.monthly_request_count or 0,
        "request_limit": limit,
    }


async def get_or_create_stripe_customer(db: AsyncSession, org: Organization) -> str | None:
    """Create a Stripe customer for the org if one doesn't exist."""
    if org.stripe_customer_id:
        return org.stripe_customer_id

    if not _stripe_available():
        logger.warning("Stripe not configured — skipping customer creation")
        return None

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        customer = stripe.Customer.create(
            name=org.name,
            metadata={"org_id": str(org.id), "org_slug": org.slug},
        )
        org.stripe_customer_id = customer.id
        await db.commit()
        logger.info("Created Stripe customer %s for org %s", customer.id, org.id)
        return customer.id
    except stripe.StripeError as e:
        logger.exception("Failed to create Stripe customer for org %s: %s", org.id, e)
        await db.rollback()
        return None


async def create_checkout_session(db: AsyncSession, org: Organization, price_id: str) -> str | None:
    """Create a Stripe Checkout Session and return the URL."""
    if not _stripe_available():
        return None

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    customer_id = await get_or_create_stripe_customer(db, org)
    if not customer_id:
        return None

    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=f"{settings.FRONTEND_URL}/dashboard/billing?success=true",
            cancel_url=f"{settings.FRONTEND_URL}/dashboard/billing?canceled=true",
            metadata={"org_id": str(org.id)},
        )
        return session.url
    except stripe.StripeError as e:
        logger.exception("Failed to create checkout session: %s", e)
        return None


async def create_customer_portal_session(db: AsyncSession, org: Organization) -> str | None:
    """Create a Stripe Customer Portal session and return the URL."""
    if not _stripe_available():
        return None

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    customer_id = await get_or_create_stripe_customer(db, org)
    if not customer_id:
        return None

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{settings.FRONTEND_URL}/dashboard/billing",
        )
        return session.url
    except stripe.StripeError as e:
        logger.exception("Failed to create portal session: %s", e)
        return None


async def _is_event_processed(db: AsyncSession, stripe_event_id: str) -> bool:
    """Check if a Stripe event has already been processed (idempotency)."""
    result = await db.execute(select(StripeEvent.id).where(StripeEvent.stripe_event_id == stripe_event_id))
    return result.scalar_one_or_none() is not None


async def _record_event(db: AsyncSession, stripe_event_id: str, event_type: str, org_id: str | None) -> None:
    """Record a processed Stripe event for idempotency."""
    import uuid

    event = StripeEvent(
        id=uuid.uuid4(),
        stripe_event_id=stripe_event_id,
        event_type=event_type,
        org_id=org_id,
        processed_at=datetime.now(timezone.utc),
    )
    db.add(event)


async def handle_webhook_event(db: AsyncSession, payload: bytes, sig_header: str) -> bool:
    """Verify and process a Stripe webhook event. Returns True on success."""
    if not _stripe_available() or not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook secret not configured")
        return False

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except (ValueError, stripe.SignatureVerificationError) as e:
        logger.warning("Invalid Stripe webhook: %s", e)
        return False

    # Idempotency check
    if await _is_event_processed(db, event.id):
        logger.info("Stripe event %s already processed — skipping", event.id)
        return True

    event_type = event.type
    data = event.data.object

    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(db, data)
    elif event_type == "customer.subscription.updated":
        await _handle_subscription_updated(db, data)
    elif event_type == "customer.subscription.deleted":
        await _handle_subscription_deleted(db, data)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(db, data)
    else:
        logger.debug("Unhandled Stripe event type: %s", event_type)

    # Record event as processed
    org_id = await _get_org_id_from_customer(db, data.get("customer"))
    await _record_event(db, event.id, event_type, org_id)
    await db.commit()
    return True


async def _get_org_by_customer_id(db: AsyncSession, customer_id: str) -> Organization | None:
    """Look up org by Stripe customer ID."""
    result = await db.execute(select(Organization).where(Organization.stripe_customer_id == customer_id))
    return result.scalar_one_or_none()


async def _get_org_id_from_customer(db: AsyncSession, customer_id: str | None) -> str | None:
    """Get org ID from Stripe customer ID."""
    if not customer_id:
        return None
    org = await _get_org_by_customer_id(db, customer_id)
    return str(org.id) if org else None


async def _handle_checkout_completed(db: AsyncSession, session_data: dict) -> None:
    """Handle checkout.session.completed — upgrade plan."""
    customer_id = session_data.get("customer")
    subscription_id = session_data.get("subscription")

    org = await _get_org_by_customer_id(db, customer_id)
    if not org:
        logger.warning("No org found for customer %s", customer_id)
        return

    # Determine plan from line items metadata or price lookup
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        sub = stripe.Subscription.retrieve(subscription_id)
        price_id = sub.items.data[0].price.id if sub.items.data else ""
        plan_tier = _price_id_to_plan_tier(price_id)
    except stripe.StripeError:
        plan_tier = PlanTier.PRO.value  # Default upgrade to Pro

    org.plan_tier = plan_tier
    org.stripe_subscription_id = subscription_id
    org.subscription_status = SubscriptionStatus.ACTIVE.value
    if hasattr(sub, "current_period_end"):
        org.subscription_current_period_end = datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc)
    logger.info("Org %s upgraded to %s", org.id, plan_tier)


async def _handle_subscription_updated(db: AsyncSession, sub_data: dict) -> None:
    """Handle customer.subscription.updated — sync status."""
    customer_id = sub_data.get("customer")
    org = await _get_org_by_customer_id(db, customer_id)
    if not org:
        return

    org.subscription_status = sub_data.get("status", org.subscription_status)
    period_end = sub_data.get("current_period_end")
    if period_end:
        org.subscription_current_period_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

    # Update plan tier from price
    items = sub_data.get("items", {}).get("data", [])
    if items:
        price_id = items[0].get("price", {}).get("id", "")
        if price_id:
            org.plan_tier = _price_id_to_plan_tier(price_id)

    logger.info("Org %s subscription updated: %s", org.id, org.subscription_status)


async def _handle_subscription_deleted(db: AsyncSession, sub_data: dict) -> None:
    """Handle customer.subscription.deleted — revert to starter."""
    customer_id = sub_data.get("customer")
    org = await _get_org_by_customer_id(db, customer_id)
    if not org:
        return

    org.plan_tier = PlanTier.STARTER.value
    org.stripe_subscription_id = None
    org.subscription_status = SubscriptionStatus.CANCELED.value
    org.subscription_current_period_end = None
    logger.info("Org %s subscription canceled — reverted to starter", org.id)


async def _handle_payment_failed(db: AsyncSession, invoice_data: dict) -> None:
    """Handle invoice.payment_failed — mark as past due."""
    customer_id = invoice_data.get("customer")
    org = await _get_org_by_customer_id(db, customer_id)
    if not org:
        return

    org.subscription_status = SubscriptionStatus.PAST_DUE.value
    logger.warning("Org %s payment failed — marked past_due", org.id)
