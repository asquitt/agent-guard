"""Request tracing router — search and inspect proxy requests."""

# pyright: reportGeneralTypeIssues=false, reportArgumentType=false

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db, require_permission
from app.models.incident import Incident
from app.models.proxy import ProxyRequest
from app.models.user import Organization, User
from app.schemas.traces import (
    TraceDetailResponse,
    TraceIncident,
    TraceListItem,
    TraceListResponse,
)

router = APIRouter()


@router.get("", response_model=TraceListResponse)
async def list_traces(
    model: str | None = None,
    status_code: int | None = Query(default=None, alias="statusCode"),
    has_incidents: bool | None = Query(default=None, alias="hasIncidents"),
    q: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _user: User = Depends(require_permission("incidents:read")),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> TraceListResponse:
    """List proxy requests with optional filtering."""
    base = select(ProxyRequest).where(ProxyRequest.org_id == org.id)

    if model:
        base = base.where(ProxyRequest.model == model)
    if status_code is not None:
        base = base.where(ProxyRequest.status_code == status_code)
    if q:
        base = base.where(ProxyRequest.path.ilike(f"%{q}%"))

    # Count total
    count_q = select(func.count()).select_from(base.subquery())
    count_result = await db.execute(count_q)
    total = count_result.scalar_one()

    # Fetch requests
    result = await db.execute(
        base.order_by(ProxyRequest.created_at.desc()).offset(skip).limit(limit)
    )
    requests = result.scalars().all()

    # Batch-fetch incident counts for these request IDs
    req_ids = [r.id for r in requests]
    incident_counts: dict[str, int] = {}
    if req_ids:
        ic_result = await db.execute(
            select(
                Incident.proxy_request_id,
                func.count(Incident.id),
            )
            .where(Incident.proxy_request_id.in_(req_ids))
            .group_by(Incident.proxy_request_id)
        )
        for row in ic_result.all():
            incident_counts[str(row[0])] = row[1]

    items: list[TraceListItem] = []
    for req in requests:
        count = incident_counts.get(str(req.id), 0)
        if has_incidents is True and count == 0:
            continue
        if has_incidents is False and count > 0:
            continue
        items.append(
            TraceListItem(
                id=req.id,
                method=req.method,
                path=req.path,
                model=req.model,
                status_code=req.status_code,
                latency_ms=req.latency_ms,
                input_tokens=req.input_tokens,
                output_tokens=req.output_tokens,
                cost_usd=req.cost_usd,
                incident_count=count,
                created_at=req.created_at,
            )
        )

    return TraceListResponse(items=items, total=total)


@router.get("/{trace_id}", response_model=TraceDetailResponse)
async def get_trace_detail(
    trace_id: UUID,
    _user: User = Depends(require_permission("incidents:read")),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> TraceDetailResponse:
    """Get full trace detail with request/response bodies and linked incidents."""
    result = await db.execute(
        select(ProxyRequest).where(
            ProxyRequest.id == trace_id,
            ProxyRequest.org_id == org.id,
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found")

    # Fetch linked incidents
    inc_result = await db.execute(
        select(Incident)
        .where(Incident.proxy_request_id == trace_id)
        .order_by(Incident.created_at.asc())
    )
    incidents = inc_result.scalars().all()

    return TraceDetailResponse(
        id=req.id,
        method=req.method,
        path=req.path,
        model=req.model,
        status_code=req.status_code,
        latency_ms=req.latency_ms,
        input_tokens=req.input_tokens,
        output_tokens=req.output_tokens,
        cost_usd=req.cost_usd,
        request_body=req.request_body,
        response_body=req.response_body,
        incidents=[
            TraceIncident(
                id=inc.id,
                severity=inc.severity,
                category=inc.category,
                title=inc.title,
                status=inc.status,
                action_taken=inc.action_taken,
                created_at=inc.created_at,
            )
            for inc in incidents
        ],
        created_at=req.created_at,
        updated_at=req.updated_at,
    )
