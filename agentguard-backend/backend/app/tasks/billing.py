"""Celery tasks for billing: usage reset and subscription sync."""

import logging

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import Organization
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.billing.reset_monthly_usage")
def reset_monthly_usage() -> dict:
    """Reset monthly_request_count for all orgs. Runs 1st of each month."""
    db = SessionLocal()
    try:
        orgs = db.query(Organization).all()
        count = 0
        for org in orgs:
            org.monthly_request_count = 0
            count += 1
        db.commit()
        logger.info("Reset monthly usage for %d organizations", count)
        return {"reset_count": count}
    except Exception:
        db.rollback()
        logger.exception("Failed to reset monthly usage")
        raise
    finally:
        db.close()


@celery_app.task(name="app.tasks.billing.sync_subscription_status")
def sync_subscription_status() -> dict:
    """Sync subscription status from Stripe for all subscribed orgs.

    Guards against missed webhooks by fetching current state from Stripe API.
    """
    if not settings.STRIPE_SECRET_KEY:
        logger.info("Stripe not configured — skipping subscription sync")
        return {"synced": 0}

    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY

    db = SessionLocal()
    try:
        orgs = (
            db.query(Organization)
            .filter(Organization.stripe_subscription_id.isnot(None))
            .all()
        )
        synced = 0
        for org in orgs:
            try:
                sub = stripe.Subscription.retrieve(org.stripe_subscription_id)
                org.subscription_status = sub.status

                from datetime import datetime, timezone

                org.subscription_current_period_end = datetime.fromtimestamp(
                    sub.current_period_end, tz=timezone.utc
                )

                # Update plan tier from current price
                if sub.items.data:
                    price_id = sub.items.data[0].price.id
                    from app.services.billing_service import _price_id_to_plan_tier

                    org.plan_tier = _price_id_to_plan_tier(price_id)

                synced += 1
            except stripe.StripeError as e:
                logger.warning(
                    "Failed to sync subscription for org %s: %s", org.id, e
                )

        db.commit()

        if synced > 0:
            from app.core.events import publish_event_sync

            for org in orgs:
                publish_event_sync(
                    str(org.id),
                    "billing.updated",
                    {"plan_tier": org.plan_tier},
                )

        logger.info("Synced subscription status for %d organizations", synced)
        return {"synced": synced}
    except Exception:
        db.rollback()
        logger.exception("Failed to sync subscription status")
        raise
    finally:
        db.close()
