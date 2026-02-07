"""Pydantic schemas for detector endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ActionMode, DetectorCategory


class DetectorRuleCreateRequest(BaseModel):
    """Request to add a rule to a detector."""

    name: str = Field(min_length=1, max_length=255)
    rule_type: str = Field(min_length=1, max_length=50)
    parameters: dict[str, Any] | None = None
    is_active: bool = True


class DetectorRuleResponse(BaseModel):
    """Single detector rule."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    rule_type: str = Field(serialization_alias="ruleType")
    parameters: dict[str, Any]
    is_active: bool = Field(serialization_alias="isActive")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class DetectorCreateRequest(BaseModel):
    """Request to create a detector with optional inline rules."""

    name: str = Field(min_length=1, max_length=255)
    category: str
    action_mode: str = ActionMode.MONITOR.value
    config: dict[str, Any] | None = None
    rules: list[DetectorRuleCreateRequest] | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid = [c.value for c in DetectorCategory]
        if v not in valid:
            msg = f"Category must be one of: {', '.join(valid)}"
            raise ValueError(msg)
        return v

    @field_validator("action_mode")
    @classmethod
    def validate_action_mode(cls, v: str) -> str:
        valid = [m.value for m in ActionMode]
        if v not in valid:
            msg = f"Action mode must be one of: {', '.join(valid)}"
            raise ValueError(msg)
        return v


class DetectorUpdateRequest(BaseModel):
    """Request to update detector fields."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    action_mode: str | None = None
    config: dict[str, Any] | None = None

    @field_validator("action_mode")
    @classmethod
    def validate_action_mode(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid = [m.value for m in ActionMode]
        if v not in valid:
            msg = f"Action mode must be one of: {', '.join(valid)}"
            raise ValueError(msg)
        return v


class DetectorResponse(BaseModel):
    """Detector details with rules."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    category: str
    is_active: bool = Field(serialization_alias="isActive")
    action_mode: str = Field(serialization_alias="actionMode")
    config: dict[str, Any]
    rules: list[DetectorRuleResponse] = []
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class DetectorListResponse(BaseModel):
    """Paginated list of detectors."""

    items: list[DetectorResponse]
    total: int
