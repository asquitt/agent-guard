"""Pydantic schemas for billing endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BillingStatusResponse(BaseModel):
    """Current billing status for an organization."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    plan_tier: str = Field(serialization_alias="planTier")
    subscription_status: str | None = Field(default=None, serialization_alias="subscriptionStatus")
    current_period_end: datetime | None = Field(default=None, serialization_alias="currentPeriodEnd")
    monthly_request_count: int = Field(serialization_alias="monthlyRequestCount")
    request_limit: int | None = Field(serialization_alias="requestLimit")


class CheckoutSessionRequest(BaseModel):
    """Request to create a Stripe Checkout session."""

    price_id: str = Field(alias="priceId")


class CheckoutSessionResponse(BaseModel):
    """Response with Stripe Checkout URL."""

    checkout_url: str = Field(serialization_alias="checkoutUrl")


class CustomerPortalResponse(BaseModel):
    """Response with Stripe Customer Portal URL."""

    portal_url: str = Field(serialization_alias="portalUrl")
