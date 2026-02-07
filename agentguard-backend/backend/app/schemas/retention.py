"""Pydantic schemas for data retention API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RetentionPolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    org_id: UUID = Field(serialization_alias="orgId")
    proxy_requests_days: int = Field(serialization_alias="proxyRequestsDays")
    incidents_days: int = Field(serialization_alias="incidentsDays")
    audit_logs_days: int = Field(serialization_alias="auditLogsDays")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class RetentionPolicyUpdate(BaseModel):
    proxy_requests_days: int | None = Field(None, ge=0, le=3650, alias="proxyRequestsDays")
    incidents_days: int | None = Field(None, ge=0, le=3650, alias="incidentsDays")
    audit_logs_days: int | None = Field(None, ge=0, le=3650, alias="auditLogsDays")

    model_config = ConfigDict(populate_by_name=True)


class DataArchiveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    org_id: UUID = Field(serialization_alias="orgId")
    table_name: str = Field(serialization_alias="tableName")
    start_date: datetime = Field(serialization_alias="startDate")
    end_date: datetime = Field(serialization_alias="endDate")
    file_path: str = Field(serialization_alias="filePath")
    row_count: int = Field(serialization_alias="rowCount")
    file_size_bytes: int = Field(serialization_alias="fileSizeBytes")
    status: str
    error_message: str | None = Field(serialization_alias="errorMessage")
    created_at: datetime = Field(serialization_alias="createdAt")


class DataArchiveListResponse(BaseModel):
    items: list[DataArchiveResponse]
    total: int
