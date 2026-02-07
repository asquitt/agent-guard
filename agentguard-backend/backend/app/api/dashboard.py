"""Dashboard metrics router."""

# pyright: reportGeneralTypeIssues=false, reportArgumentType=false

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Float, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db
from app.models.incident import Incident
from app.models.proxy import ProxyRequest
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


# ---------------------------------------------------------------------------
# Provider Performance Comparison
# ---------------------------------------------------------------------------


class ProviderPerformance(BaseModel):
    """Performance metrics for a single model/provider."""

    model_config = ConfigDict(populate_by_name=True)

    model: str
    total_requests: int = Field(serialization_alias="totalRequests")
    error_rate: float = Field(serialization_alias="errorRate")
    avg_latency_ms: float | None = Field(default=None, serialization_alias="avgLatencyMs")
    p95_latency_ms: float | None = Field(default=None, serialization_alias="p95LatencyMs")
    total_cost_usd: float = Field(serialization_alias="totalCostUsd")
    avg_cost_per_request: float = Field(serialization_alias="avgCostPerRequest")
    total_input_tokens: int = Field(serialization_alias="totalInputTokens")
    total_output_tokens: int = Field(serialization_alias="totalOutputTokens")
    incident_count: int = Field(serialization_alias="incidentCount")
    incident_rate: float = Field(serialization_alias="incidentRate")


class ProviderComparisonResponse(BaseModel):
    providers: list[ProviderPerformance]
    period_days: int = Field(serialization_alias="periodDays")


@router.get("/provider-comparison", response_model=ProviderComparisonResponse)
async def get_provider_comparison(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ProviderComparisonResponse:
    """Compare performance across models/providers."""
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    org_id = UUID(str(org.id))

    # Aggregate proxy request stats by model
    result = await db.execute(
        select(
            ProxyRequest.model,
            func.count(ProxyRequest.id).label("total"),
            func.count(
                case((ProxyRequest.status_code >= 400, 1))
            ).label("errors"),
            func.avg(cast(ProxyRequest.latency_ms, Float)).label("avg_latency"),
            func.percentile_cont(0.95).within_group(
                cast(ProxyRequest.latency_ms, Float)
            ).label("p95_latency"),
            func.coalesce(func.sum(ProxyRequest.cost_usd), 0).label("total_cost"),
            func.coalesce(func.sum(ProxyRequest.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProxyRequest.output_tokens), 0).label("output_tokens"),
        )
        .where(
            ProxyRequest.org_id == org_id,
            ProxyRequest.created_at >= cutoff,
            ProxyRequest.model.is_not(None),
        )
        .group_by(ProxyRequest.model)
        .order_by(func.count(ProxyRequest.id).desc())
    )
    rows = result.all()

    # Batch-fetch incident counts per model
    inc_result = await db.execute(
        select(
            ProxyRequest.model,
            func.count(Incident.id).label("incidents"),
        )
        .join(Incident, Incident.proxy_request_id == ProxyRequest.id)
        .where(
            ProxyRequest.org_id == org_id,
            ProxyRequest.created_at >= cutoff,
            ProxyRequest.model.is_not(None),
        )
        .group_by(ProxyRequest.model)
    )
    incident_map: dict[str, int] = {str(r[0]): r[1] for r in inc_result.all()}

    providers = []
    for row in rows:
        model_name = str(row.model) if row.model else "unknown"
        total = row.total or 0
        errors = row.errors or 0
        inc_count = incident_map.get(model_name, 0)
        total_cost = float(row.total_cost or 0)

        providers.append(
            ProviderPerformance(
                model=model_name,
                total_requests=total,
                error_rate=(errors / total * 100) if total > 0 else 0.0,
                avg_latency_ms=round(row.avg_latency, 1) if row.avg_latency else None,
                p95_latency_ms=round(row.p95_latency, 1) if row.p95_latency else None,
                total_cost_usd=round(total_cost, 4),
                avg_cost_per_request=round(total_cost / total, 6) if total > 0 else 0.0,
                total_input_tokens=int(row.input_tokens or 0),
                total_output_tokens=int(row.output_tokens or 0),
                incident_count=inc_count,
                incident_rate=(inc_count / total * 100) if total > 0 else 0.0,
            )
        )

    return ProviderComparisonResponse(providers=providers, period_days=days)
