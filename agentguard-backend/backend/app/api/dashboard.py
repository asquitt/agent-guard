"""Dashboard metrics router."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db
from app.models.user import Organization
from app.schemas.cost_analytics import CostAnalyticsResponse, CostByModel, DailyCost
from app.schemas.dashboard import (
    DashboardMetricsResponse,
    IncidentCountBySeverity,
    IncidentCountByStatus,
    RecentIncidentSummary,
)
from app.services import cost_analytics_service, dashboard_service

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
