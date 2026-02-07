"""Pydantic schemas for dashboard metrics."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IncidentCountByStatus(BaseModel):
    """Incident count grouped by status."""

    status: str
    count: int


class IncidentCountBySeverity(BaseModel):
    """Incident count grouped by severity."""

    severity: str
    count: int


class RecentIncidentSummary(BaseModel):
    """Lightweight incident for dashboard list."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    title: str
    severity: str
    status: str
    category: str
    created_at: datetime = Field(serialization_alias="createdAt")


class DashboardMetricsResponse(BaseModel):
    """Aggregate dashboard metrics."""

    model_config = ConfigDict(populate_by_name=True)

    total_incidents: int = Field(serialization_alias="totalIncidents")
    open_incidents: int = Field(serialization_alias="openIncidents")
    incidents_by_status: list[IncidentCountByStatus] = Field(serialization_alias="incidentsByStatus")
    incidents_by_severity: list[IncidentCountBySeverity] = Field(serialization_alias="incidentsBySeverity")
    recent_incidents: list[RecentIncidentSummary] = Field(serialization_alias="recentIncidents")


# --- Detection Efficacy Analytics ---


class CategoryEfficacy(BaseModel):
    """Detection statistics for a single detector category."""

    model_config = ConfigDict(populate_by_name=True)

    category: str
    total: int
    resolved: int
    dismissed: int
    open: int
    false_positive_rate: float = Field(serialization_alias="falsePositiveRate")
    mean_time_to_resolve_hours: float | None = Field(None, serialization_alias="meanTimeToResolveHours")


class DailyDetectionCount(BaseModel):
    """Detections per day for trend tracking."""

    model_config = ConfigDict(populate_by_name=True)

    date: str
    count: int


class DetectionEfficacyResponse(BaseModel):
    """Detection efficacy analytics across all categories."""

    model_config = ConfigDict(populate_by_name=True)

    categories: list[CategoryEfficacy]
    daily_trend: list[DailyDetectionCount] = Field(serialization_alias="dailyTrend")
    overall_false_positive_rate: float = Field(serialization_alias="overallFalsePositiveRate")
    period_days: int = Field(serialization_alias="periodDays")
