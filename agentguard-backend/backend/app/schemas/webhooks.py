"""Pydantic schemas for webhook endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WebhookCreateRequest(BaseModel):
    """Request to register a webhook endpoint."""

    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)
    secret: str | None = Field(default=None, max_length=255)
    event_types: list[str] = Field(
        default_factory=lambda: ["incident.created", "incident.resolved"],
    )
    min_severity: str = "info"


class WebhookUpdateRequest(BaseModel):
    """Request to update a webhook."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    secret: str | None = None
    event_types: list[str] | None = None
    min_severity: str | None = None
    is_active: bool | None = None


class WebhookResponse(BaseModel):
    """Webhook endpoint details."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    url: str
    event_types: list[str] = Field(serialization_alias="eventTypes")
    min_severity: str = Field(serialization_alias="minSeverity")
    is_active: bool = Field(serialization_alias="isActive")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class WebhookListResponse(BaseModel):
    """Paginated list of webhooks."""

    items: list[WebhookResponse]
    total: int


