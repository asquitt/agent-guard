"""Dashboard metrics router."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db
from app.models.user import Organization
from app.schemas.dashboard import (
    DashboardMetricsResponse,
    IncidentCountBySeverity,
    IncidentCountByStatus,
    RecentIncidentSummary,
)
from app.services import dashboard_service

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
        incidents_by_status=[
            IncidentCountByStatus(**s) for s in metrics["incidents_by_status"]
        ],
        incidents_by_severity=[
            IncidentCountBySeverity(**s) for s in metrics["incidents_by_severity"]
        ],
        recent_incidents=[
            RecentIncidentSummary.model_validate(i)
            for i in metrics["recent_incidents"]
        ],
    )
