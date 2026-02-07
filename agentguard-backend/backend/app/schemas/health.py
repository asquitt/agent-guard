"""Health and SLA metrics schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ComponentHealth(BaseModel):
    """Health status for a single infrastructure component."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    status: str  # "ok" | "degraded" | "error"
    response_time_ms: int | None = Field(default=None, serialization_alias="responseTimeMs")
    message: str | None = None


class DetailedHealthResponse(BaseModel):
    """Full health status with per-component breakdown."""

    model_config = ConfigDict(populate_by_name=True)

    status: str  # "healthy" | "degraded" | "unhealthy"
    components: list[ComponentHealth]


class ProviderSlaMetrics(BaseModel):
    """SLA metrics for a single provider."""

    model_config = ConfigDict(populate_by_name=True)

    provider: str
    total_requests: int = Field(serialization_alias="totalRequests")
    error_rate: float = Field(serialization_alias="errorRate")
    p50_latency_ms: float | None = Field(default=None, serialization_alias="p50LatencyMs")
    p95_latency_ms: float | None = Field(default=None, serialization_alias="p95LatencyMs")
    p99_latency_ms: float | None = Field(default=None, serialization_alias="p99LatencyMs")


class SlaMetricsResponse(BaseModel):
    """Aggregate SLA metrics across all proxy requests."""

    model_config = ConfigDict(populate_by_name=True)

    total_requests: int = Field(serialization_alias="totalRequests")
    error_rate: float = Field(serialization_alias="errorRate")
    p50_latency_ms: float | None = Field(default=None, serialization_alias="p50LatencyMs")
    p95_latency_ms: float | None = Field(default=None, serialization_alias="p95LatencyMs")
    p99_latency_ms: float | None = Field(default=None, serialization_alias="p99LatencyMs")
    avg_throughput_per_hour: float = Field(serialization_alias="avgThroughputPerHour")
    uptime_pct: float = Field(serialization_alias="uptimePct")
    by_provider: list[ProviderSlaMetrics] = Field(serialization_alias="byProvider")
    period_days: int = Field(serialization_alias="periodDays")
