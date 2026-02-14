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
    CategoryRisk,
    DailyDetectionCount,
    DashboardMetricsResponse,
    DetectionEfficacyResponse,
    IncidentCountBySeverity,
    IncidentCountByStatus,
    RecentIncidentSummary,
    RiskScoreResponse,
    RiskTrendPoint,
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


# ---------------------------------------------------------------------------
# Time-Series Analytics
# ---------------------------------------------------------------------------


class TimeSeriesBucket(BaseModel):
    """A single time bucket with aggregated metrics."""

    model_config = ConfigDict(populate_by_name=True)

    bucket: str  # ISO datetime string
    incidents: int = 0
    requests: int = 0
    avg_latency_ms: float | None = Field(default=None, serialization_alias="avgLatencyMs")
    total_cost_usd: float = Field(default=0.0, serialization_alias="totalCostUsd")
    total_tokens: int = Field(default=0, serialization_alias="totalTokens")
    detections: int = 0
    error_count: int = Field(default=0, serialization_alias="errorCount")


class TimeSeriesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    buckets: list[TimeSeriesBucket]
    granularity: str
    period_days: int = Field(serialization_alias="periodDays")


@router.get("/time-series", response_model=TimeSeriesResponse)
async def get_time_series(
    days: int = Query(default=7, ge=1, le=365),
    granularity: str = Query(default="auto", pattern="^(hourly|daily|auto)$"),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> TimeSeriesResponse:
    """Get time-series analytics data bucketed by hour or day."""
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    org_id = UUID(str(org.id))

    # Auto-select granularity: hourly for <=3 days, daily otherwise
    if granularity == "auto":
        granularity = "hourly" if days <= 3 else "daily"

    trunc_fn = func.date_trunc("hour" if granularity == "hourly" else "day", ProxyRequest.created_at)
    incident_trunc = func.date_trunc("hour" if granularity == "hourly" else "day", Incident.created_at)

    # Request metrics by bucket
    req_result = await db.execute(
        select(
            trunc_fn.label("bucket"),
            func.count(ProxyRequest.id).label("requests"),
            func.avg(cast(ProxyRequest.latency_ms, Float)).label("avg_latency"),
            func.coalesce(func.sum(ProxyRequest.cost_usd), 0).label("total_cost"),
            func.coalesce(
                func.sum(ProxyRequest.input_tokens) + func.sum(ProxyRequest.output_tokens), 0
            ).label("total_tokens"),
            func.count(case((ProxyRequest.status_code >= 400, 1))).label("errors"),
        )
        .where(ProxyRequest.org_id == org_id, ProxyRequest.created_at >= cutoff)
        .group_by(trunc_fn)
        .order_by(trunc_fn)
    )
    req_rows = {str(r.bucket): r for r in req_result.all()}

    # Incident counts by bucket
    inc_result = await db.execute(
        select(
            incident_trunc.label("bucket"),
            func.count(Incident.id).label("incidents"),
        )
        .where(Incident.org_id == org_id, Incident.created_at >= cutoff)
        .group_by(incident_trunc)
        .order_by(incident_trunc)
    )
    inc_map: dict[str, int] = {str(r.bucket): r.incidents for r in inc_result.all()}

    # Detection counts (incidents are detections)
    det_result = await db.execute(
        select(
            incident_trunc.label("bucket"),
            func.count(Incident.id).label("detections"),
        )
        .where(
            Incident.org_id == org_id,
            Incident.created_at >= cutoff,
            Incident.detector_id.is_not(None),
        )
        .group_by(incident_trunc)
        .order_by(incident_trunc)
    )
    det_map: dict[str, int] = {str(r.bucket): r.detections for r in det_result.all()}

    # Merge all buckets
    all_keys = sorted(set(list(req_rows.keys()) + list(inc_map.keys()) + list(det_map.keys())))

    buckets = []
    for key in all_keys:
        req = req_rows.get(key)
        buckets.append(
            TimeSeriesBucket(
                bucket=key,
                incidents=inc_map.get(key, 0),
                requests=req.requests if req else 0,
                avg_latency_ms=round(req.avg_latency, 1) if req and req.avg_latency else None,
                total_cost_usd=round(float(req.total_cost or 0), 4) if req else 0.0,
                total_tokens=int(req.total_tokens or 0) if req else 0,
                detections=det_map.get(key, 0),
                error_count=int(req.errors or 0) if req else 0,
            )
        )

    return TimeSeriesResponse(
        buckets=buckets,
        granularity=granularity,
        period_days=days,
    )


# ---------------------------------------------------------------------------
# Risk Score
# ---------------------------------------------------------------------------


@router.get("/risk-score", response_model=RiskScoreResponse)
async def get_risk_score(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> RiskScoreResponse:
    """Get composite risk score for the organization."""
    data = await dashboard_service.get_risk_score(db, UUID(str(org.id)), days)
    return RiskScoreResponse(
        overall_score=data["overall_score"],
        grade=data["grade"],
        trend_direction=data["trend_direction"],
        categories=[CategoryRisk(**c) for c in data["categories"]],
        trend=[RiskTrendPoint(**t) for t in data["trend"]],
        total_incidents=data["total_incidents"],
        open_incidents=data["open_incidents"],
        critical_open=data["critical_open"],
        period_days=data["period_days"],
    )
