"""Cost analytics service — aggregates cost and token data from proxy requests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proxy import ProxyRequest


async def get_cost_analytics(
    db: AsyncSession,
    org_id: UUID,
    days: int = 30,
) -> dict:
    """Aggregate cost analytics for an org over a given period."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    base_filter = [
        ProxyRequest.org_id == org_id,
        ProxyRequest.created_at >= cutoff,
    ]

    # Totals
    totals_result = await db.execute(
        select(
            func.coalesce(func.sum(ProxyRequest.cost_usd), 0.0).label("total_cost"),
            func.count(ProxyRequest.id).label("total_requests"),
            func.coalesce(func.sum(ProxyRequest.input_tokens), 0).label("total_input_tokens"),
            func.coalesce(func.sum(ProxyRequest.output_tokens), 0).label("total_output_tokens"),
        ).where(*base_filter)
    )
    totals = totals_result.one()

    # Cost by model
    model_result = await db.execute(
        select(
            ProxyRequest.model,
            func.coalesce(func.sum(ProxyRequest.cost_usd), 0.0).label("cost"),
            func.count(ProxyRequest.id).label("requests"),
            func.coalesce(func.sum(ProxyRequest.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProxyRequest.output_tokens), 0).label("output_tokens"),
        )
        .where(*base_filter, ProxyRequest.model.isnot(None))
        .group_by(ProxyRequest.model)
        .order_by(func.sum(ProxyRequest.cost_usd).desc())
    )
    cost_by_model = [
        {
            "model": row.model,
            "cost": float(row.cost),
            "requests": row.requests,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
        }
        for row in model_result.all()
    ]

    # Daily cost trend
    daily_result = await db.execute(
        select(
            func.date_trunc("day", ProxyRequest.created_at).label("date"),
            func.coalesce(func.sum(ProxyRequest.cost_usd), 0.0).label("cost"),
            func.count(ProxyRequest.id).label("requests"),
            func.coalesce(func.sum(ProxyRequest.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(ProxyRequest.output_tokens), 0).label("output_tokens"),
        )
        .where(*base_filter)
        .group_by(func.date_trunc("day", ProxyRequest.created_at))
        .order_by(func.date_trunc("day", ProxyRequest.created_at).asc())
    )
    daily_costs = [
        {
            "date": row.date.isoformat() if row.date else "",
            "cost": float(row.cost),
            "requests": row.requests,
            "input_tokens": row.input_tokens,
            "output_tokens": row.output_tokens,
        }
        for row in daily_result.all()
    ]

    return {
        "total_cost": float(totals.total_cost),
        "total_requests": totals.total_requests,
        "total_input_tokens": totals.total_input_tokens,
        "total_output_tokens": totals.total_output_tokens,
        "cost_by_model": cost_by_model,
        "daily_costs": daily_costs,
        "period_days": days,
    }
