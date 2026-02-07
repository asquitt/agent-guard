"""Pydantic schemas for alert endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import AlertDestinationType


class AlertDestinationCreateRequest(BaseModel):
    """Request to create an alert destination."""

    name: str = Field(min_length=1, max_length=255)
    destination_type: str
    config: dict[str, Any] | None = None

    @field_validator("destination_type")
    @classmethod
    def validate_destination_type(cls, v: str) -> str:
        valid = [t.value for t in AlertDestinationType]
        if v not in valid:
            msg = f"Destination type must be one of: {', '.join(valid)}"
            raise ValueError(msg)
        return v


class AlertDestinationUpdateRequest(BaseModel):
    """Request to update an alert destination."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    config: dict[str, Any] | None = None


class AlertDestinationResponse(BaseModel):
    """Alert destination details."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    destination_type: str = Field(serialization_alias="destinationType")
    config: dict[str, Any]
    is_active: bool = Field(serialization_alias="isActive")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class AlertDestinationListResponse(BaseModel):
    """Paginated list of alert destinations."""

    items: list[AlertDestinationResponse]
    total: int


class AlertResponse(BaseModel):
    """Alert details."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    incident_id: UUID = Field(serialization_alias="incidentId")
    destination_id: UUID = Field(serialization_alias="destinationId")
    status: str
    sent_at: datetime | None = Field(serialization_alias="sentAt")
    error_message: str | None = Field(serialization_alias="errorMessage")
    created_at: datetime = Field(serialization_alias="createdAt")


class AlertListResponse(BaseModel):
    """Paginated list of alerts."""

    items: list[AlertResponse]
    total: int
