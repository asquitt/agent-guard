"""Billing API router — Stripe Checkout, Portal, and Webhook."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db, require_permission
from app.models.user import Organization, User
from app.schemas.billing import (
    BillingStatusResponse,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
    CustomerPortalResponse,
)
from app.services import billing_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status", response_model=BillingStatusResponse)
async def get_billing_status(
    _user: User = Depends(require_permission("billing:read")),
    org: Organization = Depends(get_current_org),
) -> BillingStatusResponse:
    """Get current billing status: plan, usage, limits."""
    data = await billing_service.get_billing_status(org)
    return BillingStatusResponse(**data)


@router.post("/checkout", response_model=CheckoutSessionResponse)
async def create_checkout(
    body: CheckoutSessionRequest,
    _user: User = Depends(require_permission("billing:write")),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> CheckoutSessionResponse:
    """Create a Stripe Checkout session for plan upgrade."""
    url = await billing_service.create_checkout_session(db, org, body.price_id)
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing service is not configured",
        )
    return CheckoutSessionResponse(checkout_url=url)


@router.post("/portal", response_model=CustomerPortalResponse)
async def create_portal(
    _user: User = Depends(require_permission("billing:write")),
    org: Organization = Depends(get_current_org),
    db: AsyncSession = Depends(get_db),
) -> CustomerPortalResponse:
    """Create a Stripe Customer Portal session to manage subscription."""
    url = await billing_service.create_customer_portal_session(db, org)
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing service is not configured",
        )
    return CustomerPortalResponse(portal_url=url)


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle incoming Stripe webhook events.

    No JWT auth — uses Stripe signature verification instead.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    success = await billing_service.handle_webhook_event(db, payload, sig_header)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook verification failed",
        )

    return {"status": "ok"}
