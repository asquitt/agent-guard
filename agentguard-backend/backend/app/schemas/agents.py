"""Pydantic schemas for agent registry endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AgentRiskTier, AgentStatus


class AgentCreateRequest(BaseModel):
    """Request to register a new agent."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    owner: str | None = Field(default=None, max_length=255)
    risk_tier: str = AgentRiskTier.MEDIUM.value
    status: str = AgentStatus.DRAFT.value
    provider: str | None = Field(default=None, max_length=50)
    model: str | None = Field(default=None, max_length=255)
    frameworks: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata")

    @field_validator("risk_tier")
    @classmethod
    def validate_risk_tier(cls, v: str) -> str:
        valid = [t.value for t in AgentRiskTier]
        if v not in valid:
            raise ValueError(f"risk_tier must be one of: {', '.join(valid)}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = [s.value for s in AgentStatus]
        if v not in valid:
            raise ValueError(f"status must be one of: {', '.join(valid)}")
        return v


class AgentUpdateRequest(BaseModel):
    """Request to update an existing agent."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    owner: str | None = Field(default=None, max_length=255)
    risk_tier: str | None = None
    status: str | None = None
    provider: str | None = Field(default=None, max_length=50)
    model: str | None = Field(default=None, max_length=255)
    frameworks: list[str] | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata")

    @field_validator("risk_tier")
    @classmethod
    def validate_risk_tier(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = [t.value for t in AgentRiskTier]
        if v not in valid:
            raise ValueError(f"risk_tier must be one of: {', '.join(valid)}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = [s.value for s in AgentStatus]
        if v not in valid:
            raise ValueError(f"status must be one of: {', '.join(valid)}")
        return v


class AgentResponse(BaseModel):
    """Agent details."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    description: str | None
    owner: str | None
    risk_tier: str = Field(serialization_alias="riskTier")
    status: str
    provider: str | None
    model: str | None
    frameworks: list[str]
    tags: list[str]
    metadata_: dict[str, Any] = Field(alias="metadata_", serialization_alias="metadata")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class AgentListResponse(BaseModel):
    """Paginated list of agents."""

    items: list[AgentResponse]
    total: int
