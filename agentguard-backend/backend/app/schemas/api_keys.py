"""Pydantic schemas for API key endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreateRequest(BaseModel):
    """Request to create a new API key."""

    name: str = Field(min_length=1, max_length=255)
    scopes: list[str] = Field(default=["proxy"])
    expires_at: datetime | None = None


class ApiKeyCreateResponse(BaseModel):
    """Returned ONCE on creation — includes the full key."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    key: str = ""
    prefix: str
    name: str
    scopes: list[str]
    is_active: bool = Field(serialization_alias="isActive")
    expires_at: datetime | None = Field(serialization_alias="expiresAt")
    created_at: datetime = Field(serialization_alias="createdAt")


class ApiKeyResponse(BaseModel):
    """List/detail view — no full key, only prefix."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    prefix: str
    name: str
    scopes: list[str]
    is_active: bool = Field(serialization_alias="isActive")
    last_used_at: datetime | None = Field(serialization_alias="lastUsedAt")
    expires_at: datetime | None = Field(serialization_alias="expiresAt")
    created_at: datetime = Field(serialization_alias="createdAt")


class ApiKeyUpdateRequest(BaseModel):
    """Request to update API key name/scopes."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    scopes: list[str] | None = None


class ApiKeyListResponse(BaseModel):
    """Paginated list of API keys."""

    items: list[ApiKeyResponse]
    total: int
