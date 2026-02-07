"""Pydantic schemas for incident endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import IncidentStatus


class IncidentActionCreateRequest(BaseModel):
    """Request to add an action to an incident."""

    action_type: str = Field(min_length=1, max_length=50)
    details: dict[str, Any] | None = None


class IncidentActionResponse(BaseModel):
    """Incident action detail."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    action_type: str = Field(serialization_alias="actionType")
    user_id: UUID | None = Field(serialization_alias="userId")
    details: dict[str, Any]
    created_at: datetime = Field(serialization_alias="createdAt")


class IncidentUpdateRequest(BaseModel):
    """Update incident status."""

    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = [s.value for s in IncidentStatus]
        if v not in valid:
            msg = f"Status must be one of: {', '.join(valid)}"
            raise ValueError(msg)
        return v


class IncidentResponse(BaseModel):
    """Incident details (list view)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    severity: str
    category: str
    title: str
    description: str | None
    status: str
    action_taken: str | None = Field(serialization_alias="actionTaken")
    proxy_request_id: UUID | None = Field(serialization_alias="proxyRequestId")
    detector_id: UUID | None = Field(serialization_alias="detectorId")
    resolved_at: datetime | None = Field(serialization_alias="resolvedAt")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class IncidentDetailResponse(IncidentResponse):
    """Incident with actions (detail view)."""

    actions: list[IncidentActionResponse] = []


class IncidentListResponse(BaseModel):
    """Paginated list of incidents."""

    items: list[IncidentResponse]
    total: int


class IncidentStatsResponse(BaseModel):
    """Aggregate incident statistics."""

    by_severity: dict[str, int] = Field(serialization_alias="bySeverity")
    by_category: dict[str, int] = Field(serialization_alias="byCategory")
    by_status: dict[str, int] = Field(serialization_alias="byStatus")
    total: int

    model_config = ConfigDict(populate_by_name=True)


class BulkStatusUpdateRequest(BaseModel):
    """Bulk update incident statuses."""

    incident_ids: list[UUID] = Field(min_length=1, max_length=100)
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = [s.value for s in IncidentStatus]
        if v not in valid:
            msg = f"Status must be one of: {', '.join(valid)}"
            raise ValueError(msg)
        return v


class BulkStatusUpdateResponse(BaseModel):
    """Result of bulk status update."""

    updated: int
