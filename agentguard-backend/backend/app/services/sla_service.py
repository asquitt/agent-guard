"""SLA metrics service — aggregates proxy latency, error rates, throughput."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proxy import ProxyEndpoint, ProxyRequest


async def get_sla_metrics(
    db: AsyncSession, org_id: UUID, days: int = 30
) -> dict[str, Any]:
    """Aggregate SLA metrics from ProxyRequest for the given period.

    Returns dict ready for SlaMetricsResponse serialization.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # --- Overall metrics ---
    result = await db.execute(
        select(
            func.count(ProxyRequest.id).label("total"),
            func.count(ProxyRequest.id).filter(ProxyRequest.status_code >= 400).label("errors"),
            func.percentile_cont(0.5).within_group(ProxyRequest.latency_ms).label("p50"),
            func.percentile_cont(0.95).within_group(ProxyRequest.latency_ms).label("p95"),
            func.percentile_cont(0.99).within_group(ProxyRequest.latency_ms).label("p99"),
        ).where(
            ProxyRequest.org_id == org_id,
            ProxyRequest.created_at >= cutoff,
            ProxyRequest.latency_ms.isnot(None),
        )
    )
    row = result.one()
    total: int = row.total or 0
    errors: int = row.errors or 0
    p50 = float(row.p50) if row.p50 is not None else None
    p95 = float(row.p95) if row.p95 is not None else None
    p99 = float(row.p99) if row.p99 is not None else None

    error_rate = round((errors / total * 100) if total > 0 else 0.0, 2)
    hours = max(days * 24, 1)
    throughput = round(total / hours, 1)
    # Uptime approximation: % of requests that succeeded
    uptime_pct = round(((total - errors) / total * 100) if total > 0 else 100.0, 2)

    # --- Per-provider breakdown ---
    provider_result = await db.execute(
        select(
            ProxyEndpoint.provider,
            func.count(ProxyRequest.id).label("total"),
            func.count(ProxyRequest.id).filter(ProxyRequest.status_code >= 400).label("errors"),
            func.percentile_cont(0.5).within_group(ProxyRequest.latency_ms).label("p50"),
            func.percentile_cont(0.95).within_group(ProxyRequest.latency_ms).label("p95"),
            func.percentile_cont(0.99).within_group(ProxyRequest.latency_ms).label("p99"),
        )
        .join(ProxyEndpoint, ProxyRequest.endpoint_id == ProxyEndpoint.id)
        .where(
            ProxyRequest.org_id == org_id,
            ProxyRequest.created_at >= cutoff,
            ProxyRequest.latency_ms.isnot(None),
        )
        .group_by(ProxyEndpoint.provider)
        .order_by(func.count(ProxyRequest.id).desc())
    )

    by_provider: list[dict[str, Any]] = []
    for prow in provider_result.all():
        ptotal = prow.total or 0
        perrors = prow.errors or 0
        by_provider.append({
            "provider": str(prow.provider),
            "total_requests": ptotal,
            "error_rate": round((perrors / ptotal * 100) if ptotal > 0 else 0.0, 2),
            "p50_latency_ms": float(prow.p50) if prow.p50 is not None else None,
            "p95_latency_ms": float(prow.p95) if prow.p95 is not None else None,
            "p99_latency_ms": float(prow.p99) if prow.p99 is not None else None,
        })

    return {
        "total_requests": total,
        "error_rate": error_rate,
        "p50_latency_ms": p50,
        "p95_latency_ms": p95,
        "p99_latency_ms": p99,
        "avg_throughput_per_hour": throughput,
        "uptime_pct": uptime_pct,
        "by_provider": by_provider,
        "period_days": days,
    }
