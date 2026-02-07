"""Pydantic schemas for request tracing endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TraceListItem(BaseModel):
    """Proxy request summary for trace listing."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    method: str
    path: str
    model: str | None
    status_code: int | None = Field(serialization_alias="statusCode")
    latency_ms: int | None = Field(serialization_alias="latencyMs")
    input_tokens: int | None = Field(serialization_alias="inputTokens")
    output_tokens: int | None = Field(serialization_alias="outputTokens")
    cost_usd: float | None = Field(serialization_alias="costUsd")
    incident_count: int = Field(default=0, serialization_alias="incidentCount")
    created_at: datetime = Field(serialization_alias="createdAt")


class TraceListResponse(BaseModel):
    """Paginated list of traces."""

    items: list[TraceListItem]
    total: int


class TraceIncident(BaseModel):
    """Incident summary within a trace."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    severity: str
    category: str
    title: str
    status: str
    action_taken: str | None = Field(serialization_alias="actionTaken")
    created_at: datetime = Field(serialization_alias="createdAt")


class TraceDetailResponse(BaseModel):
    """Full trace detail with request/response and linked incidents."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    method: str
    path: str
    model: str | None
    status_code: int | None = Field(serialization_alias="statusCode")
    latency_ms: int | None = Field(serialization_alias="latencyMs")
    input_tokens: int | None = Field(serialization_alias="inputTokens")
    output_tokens: int | None = Field(serialization_alias="outputTokens")
    cost_usd: float | None = Field(serialization_alias="costUsd")
    request_body: str | None = Field(serialization_alias="requestBody")
    response_body: str | None = Field(serialization_alias="responseBody")
    incidents: list[TraceIncident]
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")
