"""Pydantic schemas for organization endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

_SERVER_MANAGED_SETTINGS = frozenset(
    {
        "controlledEvaluationAcceptance",
        "controlled_evaluation_acceptance",
        "onboardingCompleted",
        "onboardingStatus",
        "onboardingEvidence",
        "onboarding_completed",
        "onboarding_status",
        "onboarding_evidence",
    }
)


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

    @field_validator("settings")
    @classmethod
    def reject_server_managed_settings(
        cls,
        value: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Prevent clients from overwriting server-owned evidence and outcomes."""
        if value is None:
            return value

        reserved = sorted(_SERVER_MANAGED_SETTINGS.intersection(value))
        if reserved:
            raise ValueError("Registration acceptance and onboarding truth are server-managed")
        return value


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
