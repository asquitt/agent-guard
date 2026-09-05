"""Pydantic schemas for proxy endpoint configuration."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import Provider
from app.services.proxy_endpoint_security import sanitize_endpoint_config


class ProxyEndpointCreateRequest(BaseModel):
    """Request to create a new proxy endpoint."""

    name: str = Field(min_length=1, max_length=255)
    provider: str
    target_url: str = Field(min_length=1, max_length=2048)
    config: dict[str, Any] | None = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        valid = [p.value for p in Provider]
        if v not in valid:
            msg = f"Provider must be one of: {', '.join(valid)}"
            raise ValueError(msg)
        return v


class ProxyEndpointUpdateRequest(BaseModel):
    """Request to update a proxy endpoint."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    target_url: str | None = Field(default=None, min_length=1, max_length=2048)
    is_active: bool | None = None
    config: dict[str, Any] | None = None


class ProxyEndpointResponse(BaseModel):
    """Proxy endpoint details."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    provider: str
    target_url: str = Field(serialization_alias="targetUrl")
    is_active: bool = Field(serialization_alias="isActive")
    config: dict[str, Any] | None
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")

    @field_validator("config", mode="before")
    @classmethod
    def redact_legacy_credentials(cls, value: object) -> object:
        """Never serialize provider credentials from legacy endpoint rows."""
        return sanitize_endpoint_config(value)


class ProxyEndpointListResponse(BaseModel):
    """Paginated list of proxy endpoints."""

    items: list[ProxyEndpointResponse]
    total: int
