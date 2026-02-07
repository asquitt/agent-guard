"""Pydantic schemas for organization endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrgDetailResponse(BaseModel):
    """Full organization details including settings."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    slug: str
    plan_tier: str = Field(serialization_alias="planTier")
    settings: dict[str, Any]
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class OrgUpdateRequest(BaseModel):
    """Request to update organization name/settings."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    settings: dict[str, Any] | None = None


class MemberResponse(BaseModel):
    """Organization member profile."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    email: str
    full_name: str = Field(serialization_alias="name")
    role: str
    is_active: bool = Field(serialization_alias="isActive")
    created_at: datetime = Field(serialization_alias="createdAt")


class MemberListResponse(BaseModel):
    """Paginated list of organization members."""

    items: list[MemberResponse]
    total: int
