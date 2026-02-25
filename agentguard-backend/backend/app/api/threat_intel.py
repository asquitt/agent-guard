"""Threat intelligence feed router — attack patterns and indicators."""

# pyright: reportGeneralTypeIssues=false, reportArgumentType=false, reportCallIssue=false

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db, require_admin, require_permission
from app.models.threat_intel import ThreatIndicator
from app.models.user import Organization, User

router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

INDICATOR_TYPES = [
    "injection_pattern",
    "jailbreak",
    "extraction",
    "exfiltration",
    "social_engineering",
    "mcp_exploit",
    "tool_abuse",
]


class IndicatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    indicator_type: str = Field(serialization_alias="indicatorType")
    name: str
    description: str | None = None
    pattern: str | None = None
    severity: str
    confidence: float
    source: str
    hit_count: int = Field(serialization_alias="hitCount")
    last_seen_at: datetime | None = Field(default=None, serialization_alias="lastSeenAt")
    is_active: bool = Field(serialization_alias="isActive")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class IndicatorListResponse(BaseModel):
    items: list[IndicatorResponse]
    total: int


class IndicatorCreateRequest(BaseModel):
    indicator_type: str = Field(alias="indicatorType")
    name: str
    description: str | None = None
    pattern: str | None = None
    severity: str = "medium"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = "manual"


class IndicatorUpdateRequest(BaseModel):
    is_active: bool | None = None
    pattern: str | None = None
    severity: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    description: str | None = None


class ThreatSummaryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_indicators: int = Field(serialization_alias="totalIndicators")
    active_indicators: int = Field(serialization_alias="activeIndicators")
    total_hits: int = Field(serialization_alias="totalHits")
    by_type: list[dict] = Field(serialization_alias="byType")
    by_severity: list[dict] = Field(serialization_alias="bySeverity")
    top_indicators: list[dict] = Field(serialization_alias="topIndicators")
    recent_indicators: list[IndicatorResponse] = Field(serialization_alias="recentIndicators")


# ---------------------------------------------------------------------------
# Seed data — platform-level threat indicators
# ---------------------------------------------------------------------------

_SEED_INDICATORS: list[dict[str, object]] = [
    {
        "indicator_type": "injection_pattern",
        "name": "DAN jailbreak variant",
        "description": "Do Anything Now prompt injection that bypasses safety guidelines",
        "pattern": r"(?i)(do anything now|DAN mode|ignore previous|ignore all instructions)",
        "severity": "critical",
        "confidence": 0.9,
        "source": "agentguard",
    },
    {
        "indicator_type": "injection_pattern",
        "name": "Role-play injection",
        "description": "Attacker uses role-play scenarios to bypass content policies",
        "pattern": r"(?i)(pretend you are|act as if|you are now|roleplay as)",
        "severity": "high",
        "confidence": 0.7,
        "source": "agentguard",
    },
    {
        "indicator_type": "extraction",
        "name": "System prompt extraction via repetition",
        "description": "Asks model to repeat or reveal its system instructions",
        "pattern": r"(?i)(repeat your (instructions|prompt|rules)|show me your system)",
        "severity": "high",
        "confidence": 0.85,
        "source": "agentguard",
    },
    {
        "indicator_type": "exfiltration",
        "name": "Data exfiltration via markdown",
        "description": "Uses markdown image tags to exfiltrate data to external URLs",
        "pattern": r"!\[.*?\]\(https?://(?!.*(?:openai|anthropic|google))",
        "severity": "critical",
        "confidence": 0.8,
        "source": "agentguard",
    },
    {
        "indicator_type": "jailbreak",
        "name": "Token smuggling",
        "description": "Splits forbidden words across tokens or uses Unicode to bypass filters",
        "pattern": r"(?i)(base64|\\u[0-9a-f]{4}|&#x[0-9a-f]+;)",
        "severity": "high",
        "confidence": 0.6,
        "source": "agentguard",
    },
    {
        "indicator_type": "social_engineering",
        "name": "Authority impersonation",
        "description": "Claims to be administrator, developer, or Anthropic/OpenAI staff",
        "pattern": r"(?i)(i am (the|an?) (admin|developer|engineer)|this is (OpenAI|Anthropic) staff)",
        "severity": "high",
        "confidence": 0.75,
        "source": "agentguard",
    },
    {
        "indicator_type": "mcp_exploit",
        "name": "MCP tool chain escalation",
        "description": "Attempts to chain MCP tools for privilege escalation",
        "pattern": r"(?i)(execute_command|shell|run_process).*?(read_file|write_file|env_var)",
        "severity": "critical",
        "confidence": 0.7,
        "source": "agentguard",
    },
    {
        "indicator_type": "tool_abuse",
        "name": "Rapid-fire financial transfers",
        "description": "Multiple transfer/payment tool calls in rapid succession",
        "pattern": r"(?i)(transfer|send_money|wire|payment).*?(transfer|send_money|wire|payment)",
        "severity": "critical",
        "confidence": 0.85,
        "source": "agentguard",
    },
]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=IndicatorListResponse)
async def list_indicators(
    indicator_type: str | None = Query(default=None, alias="indicatorType"),
    severity: str | None = None,
    source: str | None = None,
    is_active: bool | None = Query(default=None, alias="isActive"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("detectors:read")),
    org: Organization = Depends(get_current_org),
) -> IndicatorListResponse:
    """List threat indicators (org-specific + platform-level)."""
    base = select(ThreatIndicator).where(
        (ThreatIndicator.org_id == org.id) | (ThreatIndicator.org_id.is_(None))
    )

    if indicator_type:
        base = base.where(ThreatIndicator.indicator_type == indicator_type)
    if severity:
        base = base.where(ThreatIndicator.severity == severity)
    if source:
        base = base.where(ThreatIndicator.source == source)
    if is_active is not None:
        base = base.where(ThreatIndicator.is_active == is_active)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        base.order_by(ThreatIndicator.hit_count.desc()).offset(skip).limit(limit)
    )
    items = [IndicatorResponse.model_validate(i) for i in result.scalars().all()]
    return IndicatorListResponse(items=items, total=total)


@router.get("/summary", response_model=ThreatSummaryResponse)
async def get_threat_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("detectors:read")),
    org: Organization = Depends(get_current_org),
) -> ThreatSummaryResponse:
    """Aggregate threat intelligence summary."""
    org_filter = (ThreatIndicator.org_id == org.id) | (ThreatIndicator.org_id.is_(None))

    # Totals
    totals_q = select(
        func.count(ThreatIndicator.id),
        func.count(ThreatIndicator.id).filter(ThreatIndicator.is_active == True),  # noqa: E712
        func.coalesce(func.sum(ThreatIndicator.hit_count), 0),
    ).where(org_filter)
    row = (await db.execute(totals_q)).one()

    # By type
    type_q = select(
        ThreatIndicator.indicator_type, func.count(ThreatIndicator.id)
    ).where(org_filter).group_by(ThreatIndicator.indicator_type)
    by_type = [{"type": r[0], "count": r[1]} for r in (await db.execute(type_q)).all()]

    # By severity
    sev_q = select(
        ThreatIndicator.severity, func.count(ThreatIndicator.id)
    ).where(org_filter).group_by(ThreatIndicator.severity)
    by_severity = [{"severity": r[0], "count": r[1]} for r in (await db.execute(sev_q)).all()]

    # Top indicators by hits
    top_q = select(ThreatIndicator).where(
        org_filter, ThreatIndicator.hit_count > 0
    ).order_by(ThreatIndicator.hit_count.desc()).limit(5)
    top_items = (await db.execute(top_q)).scalars().all()
    top_indicators = [
        {"name": i.name, "type": i.indicator_type, "hits": i.hit_count, "severity": i.severity}
        for i in top_items
    ]

    # Recent indicators
    recent_q = select(ThreatIndicator).where(org_filter).order_by(
        ThreatIndicator.created_at.desc()
    ).limit(5)
    recent = [IndicatorResponse.model_validate(i) for i in (await db.execute(recent_q)).scalars().all()]

    return ThreatSummaryResponse(
        total_indicators=row[0],
        active_indicators=row[1],
        total_hits=row[2],
        by_type=by_type,
        by_severity=by_severity,
        top_indicators=top_indicators,
        recent_indicators=recent,
    )


@router.get("/types")
async def list_indicator_types(
    _user: User = Depends(require_permission("detectors:read")),
    _org: Organization = Depends(get_current_org),
) -> dict[str, list[str]]:
    """List available indicator types."""
    return {"types": INDICATOR_TYPES}


@router.post("", response_model=IndicatorResponse, status_code=status.HTTP_201_CREATED)
async def create_indicator(
    body: IndicatorCreateRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("detectors:write")),
    org: Organization = Depends(get_current_org),
) -> IndicatorResponse:
    """Create a custom threat indicator for this organization."""
    if body.indicator_type not in INDICATOR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"indicator_type must be one of: {', '.join(INDICATOR_TYPES)}",
        )

    indicator = ThreatIndicator(
        org_id=org.id,
        indicator_type=body.indicator_type,
        name=body.name,
        description=body.description,
        pattern=body.pattern,
        severity=body.severity,
        confidence=body.confidence,
        source=body.source,
        is_active=True,
    )
    db.add(indicator)
    await db.commit()
    await db.refresh(indicator)
    return IndicatorResponse.model_validate(indicator)


@router.patch("/{indicator_id}", response_model=IndicatorResponse)
async def update_indicator(
    indicator_id: UUID,
    body: IndicatorUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_permission("detectors:write")),
    org: Organization = Depends(get_current_org),
) -> IndicatorResponse:
    """Update a threat indicator (toggle active, update pattern, etc.)."""
    result = await db.execute(
        select(ThreatIndicator).where(
            ThreatIndicator.id == indicator_id,
            ThreatIndicator.org_id == org.id,
        )
    )
    indicator = result.scalar_one_or_none()
    if not indicator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Indicator not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(indicator, field, value)

    await db.commit()
    await db.refresh(indicator)
    return IndicatorResponse.model_validate(indicator)


@router.post("/seed", status_code=status.HTTP_201_CREATED)
async def seed_platform_indicators(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> dict[str, int]:
    """Seed platform-level threat indicators (idempotent)."""
    created = 0
    for seed in _SEED_INDICATORS:
        # Check if already exists
        existing = await db.execute(
            select(ThreatIndicator).where(
                ThreatIndicator.org_id.is_(None),
                ThreatIndicator.name == seed["name"],
            )
        )
        if existing.scalar_one_or_none():
            continue
        indicator = ThreatIndicator(**seed)  # type: ignore[arg-type]
        db.add(indicator)
        created += 1

    if created:
        await db.commit()
    return {"seeded": created}
