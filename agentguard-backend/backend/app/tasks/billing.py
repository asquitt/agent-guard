"""Celery tasks for billing: usage reset and subscription sync."""

# pyright: reportAttributeAccessIssue=false, reportArgumentType=false

import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.user import Organization
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.billing.reset_monthly_usage",
    max_retries=3,
    default_retry_delay=60,
)
def reset_monthly_usage() -> dict:
    """Reset monthly_request_count for all orgs. Runs 1st of each month.

    Idempotent: uses settings JSONB to track last reset month,
    skipping orgs already reset for the current billing period.
    """
    now = datetime.now(timezone.utc)
    current_month = now.strftime("%Y-%m")

    db = SessionLocal()
    try:
        orgs = db.query(Organization).all()
        count = 0
        for org in orgs:
            org_settings = dict(org.settings or {})
            if org_settings.get("last_monthly_reset") == current_month:
                continue  # Already reset — idempotent skip
            org.monthly_request_count = 0
            org_settings["last_monthly_reset"] = current_month
            org.settings = org_settings
            count += 1
        db.commit()
        logger.info("Reset monthly usage for %d orgs (month=%s)", count, current_month)
        return {"reset_count": count, "month": current_month}
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
        orgs = db.query(Organization).filter(Organization.stripe_subscription_id.isnot(None)).all()
        synced = 0
        for org in orgs:
            try:
                sub = stripe.Subscription.retrieve(org.stripe_subscription_id)
                org.subscription_status = sub.status

                from datetime import datetime, timezone

                org.subscription_current_period_end = datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc)

                # Update plan tier from current price
                if sub.items.data:
                    price_id = sub.items.data[0].price.id
                    from app.services.billing_service import _price_id_to_plan_tier

                    org.plan_tier = _price_id_to_plan_tier(price_id)

                synced += 1
            except stripe.StripeError as e:
                logger.warning("Failed to sync subscription for org %s: %s", org.id, e)

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
