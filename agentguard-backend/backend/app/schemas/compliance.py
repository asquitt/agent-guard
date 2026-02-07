"""Pydantic schemas for compliance audit logs and reports."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    user_id: UUID | None = Field(None, serialization_alias="userId")
    action: str
    resource_type: str = Field(serialization_alias="resourceType")
    resource_id: UUID | None = Field(None, serialization_alias="resourceId")
    details: dict[str, Any]
    ip_address: str | None = Field(None, serialization_alias="ipAddress")
    entry_hash: str | None = Field(None, serialization_alias="entryHash")
    created_at: datetime = Field(serialization_alias="createdAt")


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int


class ChainVerificationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    valid: bool
    checked: int
    broken_at: UUID | None = Field(None, serialization_alias="brokenAt")


class ComplianceReportRequest(BaseModel):
    report_type: str = Field(pattern="^(access_audit|incident_summary|detection_efficacy|configuration_changes)$")
    date_from: datetime
    date_to: datetime


class ComplianceReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    report_type: str = Field(serialization_alias="reportType")
    status: str
    date_from: datetime = Field(serialization_alias="dateFrom")
    date_to: datetime = Field(serialization_alias="dateTo")
    file_size_bytes: int | None = Field(None, serialization_alias="fileSizeBytes")
    error_message: str | None = Field(None, serialization_alias="errorMessage")
    created_at: datetime = Field(serialization_alias="createdAt")
    completed_at: datetime | None = Field(None, serialization_alias="completedAt")


class ComplianceReportListResponse(BaseModel):
    items: list[ComplianceReportResponse]
    total: int


# --- Compliance Framework Scoring ---


class RequirementScore(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    violation_count: int = Field(serialization_alias="violationCount")


class FrameworkScore(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    total_violations: int = Field(serialization_alias="totalViolations")
    requirements: list[RequirementScore]


class ComplianceScoreResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    frameworks: list[FrameworkScore]
    period_days: int = Field(serialization_alias="periodDays")
