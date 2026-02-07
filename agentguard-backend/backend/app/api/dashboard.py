"""Dashboard metrics router."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db
from app.models.user import Organization
from app.schemas.cost_analytics import CostAnalyticsResponse, CostByModel, DailyCost
from app.schemas.dashboard import (
    CategoryEfficacy,
    DailyDetectionCount,
    DashboardMetricsResponse,
    DetectionEfficacyResponse,
    IncidentCountBySeverity,
    IncidentCountByStatus,
    RecentIncidentSummary,
)
from app.schemas.health import ProviderSlaMetrics, SlaMetricsResponse
from app.services import cost_analytics_service, dashboard_service, sla_service

router = APIRouter()


@router.get("/metrics", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> DashboardMetricsResponse:
    """Get aggregate dashboard metrics."""
    metrics = await dashboard_service.get_metrics(db, UUID(str(org.id)))
    return DashboardMetricsResponse(
        total_incidents=metrics["total_incidents"],
        open_incidents=metrics["open_incidents"],
        incidents_by_status=[IncidentCountByStatus(**s) for s in metrics["incidents_by_status"]],
        incidents_by_severity=[IncidentCountBySeverity(**s) for s in metrics["incidents_by_severity"]],
        recent_incidents=[RecentIncidentSummary.model_validate(i) for i in metrics["recent_incidents"]],
    )


@router.get("/cost-analytics", response_model=CostAnalyticsResponse)
async def get_cost_analytics(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> CostAnalyticsResponse:
    """Get cost analytics for the organization."""
    data = await cost_analytics_service.get_cost_analytics(db, UUID(str(org.id)), days)
    return CostAnalyticsResponse(
        total_cost=data["total_cost"],
        total_requests=data["total_requests"],
        total_input_tokens=data["total_input_tokens"],
        total_output_tokens=data["total_output_tokens"],
        cost_by_model=[CostByModel(**m) for m in data["cost_by_model"]],
        daily_costs=[DailyCost(**d) for d in data["daily_costs"]],
        period_days=data["period_days"],
    )


@router.get("/sla-metrics", response_model=SlaMetricsResponse)
async def get_sla_metrics(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> SlaMetricsResponse:
    """Get SLA metrics (latency percentiles, error rates, throughput)."""
    data = await sla_service.get_sla_metrics(db, UUID(str(org.id)), days)
    return SlaMetricsResponse(
        total_requests=data["total_requests"],
        error_rate=data["error_rate"],
        p50_latency_ms=data["p50_latency_ms"],
        p95_latency_ms=data["p95_latency_ms"],
        p99_latency_ms=data["p99_latency_ms"],
        avg_throughput_per_hour=data["avg_throughput_per_hour"],
        uptime_pct=data["uptime_pct"],
        by_provider=[ProviderSlaMetrics(**p) for p in data["by_provider"]],
        period_days=data["period_days"],
    )


@router.get("/detection-efficacy", response_model=DetectionEfficacyResponse)
async def get_detection_efficacy(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> DetectionEfficacyResponse:
    """Get detection efficacy analytics (FP rates, MTTR, trends)."""
    data = await dashboard_service.get_detection_efficacy(db, UUID(str(org.id)), days)
    return DetectionEfficacyResponse(
        categories=[CategoryEfficacy(**c) for c in data["categories"]],
        daily_trend=[DailyDetectionCount(**d) for d in data["daily_trend"]],
        overall_false_positive_rate=data["overall_false_positive_rate"],
        period_days=data["period_days"],
    )
