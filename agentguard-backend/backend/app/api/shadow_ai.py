"""Shadow AI discovery router — detect and manage unauthorized AI usage."""

# pyright: reportGeneralTypeIssues=false, reportCallIssue=false, reportArgumentType=false

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db, require_permission
from app.models.proxy import ProxyRequest
from app.models.shadow_ai import ShadowAIDiscovery
from app.models.user import Organization, User

router = APIRouter()

# Known AI provider domains for classification
KNOWN_AI_PROVIDERS: dict[str, str] = {
    "api.openai.com": "openai",
    "api.anthropic.com": "anthropic",
    "generativelanguage.googleapis.com": "google_gemini",
    "api.cohere.ai": "cohere",
    "api-inference.huggingface.co": "huggingface",
    "api.mistral.ai": "mistral",
    "api.together.xyz": "together",
    "api.replicate.com": "replicate",
    "api.fireworks.ai": "fireworks",
    "api.groq.com": "groq",
    "api.perplexity.ai": "perplexity",
    "bedrock-runtime.*.amazonaws.com": "aws_bedrock",
    "*.openai.azure.com": "azure_openai",
}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class DiscoveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    provider: str
    endpoint: str
    department: str | None
    source_ip: str | None = Field(serialization_alias="sourceIp")
    risk_level: str = Field(serialization_alias="riskLevel")
    status: str
    request_count: int = Field(serialization_alias="requestCount")
    first_seen_at: datetime = Field(serialization_alias="firstSeenAt")
    last_seen_at: datetime = Field(serialization_alias="lastSeenAt")
    metadata_: dict[str, object] = Field(alias="metadata_", serialization_alias="metadata")
    created_at: datetime = Field(serialization_alias="createdAt")


class DiscoveryListResponse(BaseModel):
    items: list[DiscoveryResponse]
    total: int


class DiscoverySummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_discovered: int = Field(serialization_alias="totalDiscovered")
    monitored_count: int = Field(serialization_alias="monitoredCount")
    unmonitored_count: int = Field(serialization_alias="unmonitoredCount")
    blocked_count: int = Field(serialization_alias="blockedCount")
    total_unmonitored_requests: int = Field(serialization_alias="totalUnmonitoredRequests")
    total_monitored_requests: int = Field(serialization_alias="totalMonitoredRequests")
    coverage_pct: float = Field(serialization_alias="coveragePct")
    by_provider: list[dict[str, object]] = Field(serialization_alias="byProvider")
    by_risk: list[dict[str, object]] = Field(serialization_alias="byRisk")


class ReportDiscoveryRequest(BaseModel):
    """Report a discovered AI service usage."""

    provider: str = Field(min_length=1, max_length=100)
    endpoint: str = Field(min_length=1, max_length=500)
    department: str | None = None
    source_ip: str | None = Field(default=None, alias="sourceIp")
    risk_level: str = "medium"
    request_count: int = Field(default=1, ge=1, alias="requestCount")
    metadata: dict[str, object] = Field(default_factory=dict)


class UpdateStatusRequest(BaseModel):
    """Update the status of a discovered service."""

    status: str = Field(pattern="^(discovered|monitored|blocked|approved)$")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=DiscoveryListResponse)
async def list_discoveries(
    discovery_status: str | None = Query(default=None, alias="status"),
    provider: str | None = None,
    risk_level: str | None = Query(default=None, alias="riskLevel"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("incidents:read")),
    org: Organization = Depends(get_current_org),
) -> DiscoveryListResponse:
    """List discovered AI services."""
    base = select(ShadowAIDiscovery).where(ShadowAIDiscovery.org_id == org.id)

    if discovery_status:
        base = base.where(ShadowAIDiscovery.status == discovery_status)
    if provider:
        base = base.where(ShadowAIDiscovery.provider == provider)
    if risk_level:
        base = base.where(ShadowAIDiscovery.risk_level == risk_level)

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar_one()

    result = await db.execute(
        base.order_by(ShadowAIDiscovery.last_seen_at.desc()).offset(skip).limit(limit)
    )
    items = result.scalars().all()

    return DiscoveryListResponse(
        items=[DiscoveryResponse.model_validate(d) for d in items],
        total=total,
    )


@router.get("/summary", response_model=DiscoverySummaryResponse)
async def get_discovery_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("incidents:read")),
    org: Organization = Depends(get_current_org),
) -> DiscoverySummaryResponse:
    """Get shadow AI discovery summary with coverage metrics."""
    from datetime import timedelta

    org_id = UUID(str(org.id))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Status counts
    status_result = await db.execute(
        select(ShadowAIDiscovery.status, func.count(ShadowAIDiscovery.id))
        .where(ShadowAIDiscovery.org_id == org_id)
        .group_by(ShadowAIDiscovery.status)
    )
    status_counts: dict[str, int] = {r[0]: r[1] for r in status_result.all()}

    # Unmonitored request total
    unmon_result = await db.execute(
        select(func.coalesce(func.sum(ShadowAIDiscovery.request_count), 0))
        .where(
            ShadowAIDiscovery.org_id == org_id,
            ShadowAIDiscovery.status.in_(["discovered", "blocked"]),
        )
    )
    total_unmonitored = int(unmon_result.scalar_one())

    # Monitored requests from proxy
    mon_result = await db.execute(
        select(func.count(ProxyRequest.id))
        .where(ProxyRequest.org_id == org_id, ProxyRequest.created_at >= cutoff)
    )
    total_monitored = int(mon_result.scalar_one())

    # By provider
    provider_result = await db.execute(
        select(
            ShadowAIDiscovery.provider,
            func.count(ShadowAIDiscovery.id),
            func.sum(ShadowAIDiscovery.request_count),
        )
        .where(ShadowAIDiscovery.org_id == org_id)
        .group_by(ShadowAIDiscovery.provider)
        .order_by(func.sum(ShadowAIDiscovery.request_count).desc())
    )
    by_provider = [
        {"provider": r[0], "services": r[1], "requests": int(r[2] or 0)}
        for r in provider_result.all()
    ]

    # By risk level
    risk_result = await db.execute(
        select(ShadowAIDiscovery.risk_level, func.count(ShadowAIDiscovery.id))
        .where(ShadowAIDiscovery.org_id == org_id)
        .group_by(ShadowAIDiscovery.risk_level)
    )
    by_risk = [{"riskLevel": r[0], "count": r[1]} for r in risk_result.all()]

    total_all = total_monitored + total_unmonitored
    coverage = (total_monitored / total_all * 100) if total_all > 0 else 100.0

    total_discovered = sum(status_counts.values())

    return DiscoverySummaryResponse(
        total_discovered=total_discovered,
        monitored_count=status_counts.get("monitored", 0) + status_counts.get("approved", 0),
        unmonitored_count=status_counts.get("discovered", 0),
        blocked_count=status_counts.get("blocked", 0),
        total_unmonitored_requests=total_unmonitored,
        total_monitored_requests=total_monitored,
        coverage_pct=round(coverage, 1),
        by_provider=by_provider,
        by_risk=by_risk,
    )


@router.post("", response_model=DiscoveryResponse, status_code=status.HTTP_201_CREATED)
async def report_discovery(
    body: ReportDiscoveryRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("incidents:write")),
    org: Organization = Depends(get_current_org),
) -> DiscoveryResponse:
    """Report a discovered AI service usage (from network proxy integration)."""
    now = datetime.now(timezone.utc)

    # Check if this endpoint already exists for the org
    existing_result = await db.execute(
        select(ShadowAIDiscovery).where(
            ShadowAIDiscovery.org_id == org.id,
            ShadowAIDiscovery.provider == body.provider,
            ShadowAIDiscovery.endpoint == body.endpoint,
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        # Update existing discovery
        existing.request_count = (existing.request_count or 0) + body.request_count  # type: ignore[assignment]
        existing.last_seen_at = now  # type: ignore[assignment]
        if body.source_ip:
            existing.source_ip = body.source_ip  # type: ignore[assignment]
        await db.commit()
        await db.refresh(existing)
        return DiscoveryResponse.model_validate(existing)

    discovery = ShadowAIDiscovery(
        org_id=org.id,
        provider=body.provider,
        endpoint=body.endpoint,
        department=body.department,
        source_ip=body.source_ip,
        risk_level=body.risk_level,
        status="discovered",
        request_count=body.request_count,
        first_seen_at=now,
        last_seen_at=now,
        metadata_=body.metadata,
    )
    db.add(discovery)
    await db.commit()
    await db.refresh(discovery)
    return DiscoveryResponse.model_validate(discovery)


@router.patch("/{discovery_id}", response_model=DiscoveryResponse)
async def update_discovery_status(
    discovery_id: UUID,
    body: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("incidents:write")),
    org: Organization = Depends(get_current_org),
) -> DiscoveryResponse:
    """Update the status of a discovered AI service."""
    result = await db.execute(
        select(ShadowAIDiscovery).where(
            ShadowAIDiscovery.id == discovery_id,
            ShadowAIDiscovery.org_id == org.id,
        )
    )
    discovery = result.scalar_one_or_none()
    if not discovery:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery not found")

    discovery.status = body.status  # type: ignore[assignment]
    await db.commit()
    await db.refresh(discovery)
    return DiscoveryResponse.model_validate(discovery)


@router.get("/providers", response_model=list[dict[str, str]])
async def list_known_providers(
    _user: User = Depends(require_permission("incidents:read")),
    _org: Organization = Depends(get_current_org),
) -> list[dict[str, str]]:
    """List known AI provider domains for network proxy configuration."""
    return [
        {"domain": domain, "provider": provider}
        for domain, provider in KNOWN_AI_PROVIDERS.items()
    ]
