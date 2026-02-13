"""Conversation-level analysis router — track multi-turn sessions and risk."""

# pyright: reportGeneralTypeIssues=false, reportArgumentType=false, reportCallIssue=false

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db
from app.models.conversation import Conversation, ConversationTurn
from app.models.user import Organization

router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

RISK_THRESHOLDS = {"low": 0.0, "medium": 30.0, "high": 60.0, "critical": 80.0}


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    session_id: str = Field(serialization_alias="sessionId")
    agent_id: UUID | None = Field(default=None, serialization_alias="agentId")
    status: str
    risk_score: float = Field(serialization_alias="riskScore")
    risk_level: str = Field(serialization_alias="riskLevel")
    turn_count: int = Field(serialization_alias="turnCount")
    total_tokens: int = Field(serialization_alias="totalTokens")
    total_cost_usd: float = Field(serialization_alias="totalCostUsd")
    escalated_at: datetime | None = Field(default=None, serialization_alias="escalatedAt")
    completed_at: datetime | None = Field(default=None, serialization_alias="completedAt")
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int


class TurnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    turn_number: int = Field(serialization_alias="turnNumber")
    role: str
    content_preview: str | None = Field(default=None, serialization_alias="contentPreview")
    risk_delta: float = Field(serialization_alias="riskDelta")
    cumulative_risk: float = Field(serialization_alias="cumulativeRisk")
    detections: list[dict]
    tokens: int | None = None
    proxy_request_id: UUID | None = Field(default=None, serialization_alias="proxyRequestId")
    created_at: datetime = Field(serialization_alias="createdAt")


class ConversationDetailResponse(ConversationResponse):
    turns: list[TurnResponse]


class ConversationCreateRequest(BaseModel):
    session_id: str = Field(alias="sessionId")
    agent_id: UUID | None = Field(default=None, alias="agentId")


class TurnCreateRequest(BaseModel):
    role: str = "user"
    content_preview: str | None = Field(default=None, alias="contentPreview")
    risk_delta: float = Field(default=0.0, alias="riskDelta")
    proxy_request_id: UUID | None = Field(default=None, alias="proxyRequestId")
    detections: list[dict] = Field(default_factory=list)
    tokens: int | None = None


class ConversationStatsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_conversations: int = Field(serialization_alias="totalConversations")
    active_count: int = Field(serialization_alias="activeCount")
    escalated_count: int = Field(serialization_alias="escalatedCount")
    flagged_count: int = Field(serialization_alias="flaggedCount")
    avg_risk_score: float = Field(serialization_alias="avgRiskScore")
    avg_turns: float = Field(serialization_alias="avgTurns")
    by_risk_level: list[dict] = Field(serialization_alias="byRiskLevel")


def _risk_level_for_score(score: float) -> str:
    if score >= RISK_THRESHOLDS["critical"]:
        return "critical"
    if score >= RISK_THRESHOLDS["high"]:
        return "high"
    if score >= RISK_THRESHOLDS["medium"]:
        return "medium"
    return "low"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    status_filter: str | None = Query(default=None, alias="status"),
    risk_level: str | None = Query(default=None, alias="riskLevel"),
    agent_id: UUID | None = Query(default=None, alias="agentId"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ConversationListResponse:
    """List conversations with optional filters."""
    base = select(Conversation).where(Conversation.org_id == org.id)

    if status_filter:
        base = base.where(Conversation.status == status_filter)
    if risk_level:
        base = base.where(Conversation.risk_level == risk_level)
    if agent_id:
        base = base.where(Conversation.agent_id == agent_id)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    result = await db.execute(
        base.order_by(Conversation.created_at.desc()).offset(skip).limit(limit)
    )
    items = [ConversationResponse.model_validate(c) for c in result.scalars().all()]
    return ConversationListResponse(items=items, total=total)


@router.get("/stats", response_model=ConversationStatsResponse)
async def get_conversation_stats(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ConversationStatsResponse:
    """Aggregate conversation statistics."""
    cutoff = func.now() - text(f"interval '{days} days'")

    # Counts by status
    status_q = select(
        Conversation.status, func.count(Conversation.id)
    ).where(
        Conversation.org_id == org.id,
        Conversation.created_at >= cutoff,
    ).group_by(Conversation.status)
    status_result = await db.execute(status_q)
    status_counts: dict[str, int] = {row[0]: row[1] for row in status_result.all()}

    # Risk level breakdown
    risk_q = select(
        Conversation.risk_level, func.count(Conversation.id)
    ).where(
        Conversation.org_id == org.id,
        Conversation.created_at >= cutoff,
    ).group_by(Conversation.risk_level)
    risk_result = await db.execute(risk_q)
    by_risk = [{"riskLevel": row[0], "count": row[1]} for row in risk_result.all()]

    # Averages
    avg_q = select(
        func.count(Conversation.id),
        func.coalesce(func.avg(Conversation.risk_score), 0.0),
        func.coalesce(func.avg(Conversation.turn_count), 0.0),
    ).where(
        Conversation.org_id == org.id,
        Conversation.created_at >= cutoff,
    )
    avg_result = await db.execute(avg_q)
    row = avg_result.one()

    return ConversationStatsResponse(
        total_conversations=row[0],
        active_count=status_counts.get("active", 0),
        escalated_count=status_counts.get("escalated", 0),
        flagged_count=status_counts.get("flagged", 0),
        avg_risk_score=round(float(row[1]), 2),
        avg_turns=round(float(row[2]), 1),
        by_risk_level=by_risk,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ConversationDetailResponse:
    """Get conversation detail with all turns."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.org_id == org.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    turns_result = await db.execute(
        select(ConversationTurn)
        .where(ConversationTurn.conversation_id == conversation_id)
        .order_by(ConversationTurn.turn_number.asc())
    )
    turns = [TurnResponse.model_validate(t) for t in turns_result.scalars().all()]

    return ConversationDetailResponse(
        id=conv.id,
        session_id=conv.session_id,
        agent_id=conv.agent_id,
        status=conv.status,
        risk_score=conv.risk_score,
        risk_level=conv.risk_level,
        turn_count=conv.turn_count,
        total_tokens=conv.total_tokens,
        total_cost_usd=conv.total_cost_usd,
        escalated_at=conv.escalated_at,
        completed_at=conv.completed_at,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        turns=turns,
    )


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreateRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ConversationResponse:
    """Start a new conversation session."""
    conv = Conversation(
        org_id=org.id,
        session_id=body.session_id,
        agent_id=body.agent_id,
        status="active",
        risk_score=0.0,
        risk_level="low",
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return ConversationResponse.model_validate(conv)


@router.post("/{conversation_id}/turns", response_model=TurnResponse, status_code=status.HTTP_201_CREATED)
async def add_turn(
    conversation_id: UUID,
    body: TurnCreateRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> TurnResponse:
    """Add a turn to a conversation, updating risk scores."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.org_id == org.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    new_turn_number = conv.turn_count + 1  # type: ignore[operator]
    new_risk = (conv.risk_score or 0.0) + body.risk_delta  # type: ignore[operator]
    new_risk = max(0.0, min(100.0, new_risk))  # clamp 0-100

    turn = ConversationTurn(
        conversation_id=conv.id,
        proxy_request_id=body.proxy_request_id,
        turn_number=new_turn_number,
        role=body.role,
        content_preview=body.content_preview[:500] if body.content_preview else None,
        risk_delta=body.risk_delta,
        cumulative_risk=new_risk,
        detections=body.detections,
        tokens=body.tokens,
    )
    db.add(turn)

    # Update conversation aggregates
    conv.turn_count = new_turn_number  # type: ignore[assignment]
    conv.risk_score = new_risk  # type: ignore[assignment]
    conv.risk_level = _risk_level_for_score(new_risk)  # type: ignore[assignment]
    if body.tokens:
        conv.total_tokens = (conv.total_tokens or 0) + body.tokens  # type: ignore[assignment,operator]

    # Auto-escalate if risk crosses critical threshold
    if new_risk >= RISK_THRESHOLDS["critical"] and conv.status != "escalated":
        conv.status = "escalated"  # type: ignore[assignment]
        conv.escalated_at = datetime.now(timezone.utc)  # type: ignore[assignment]

    await db.commit()
    await db.refresh(turn)
    return TurnResponse.model_validate(turn)


@router.patch("/{conversation_id}/status")
async def update_conversation_status(
    conversation_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ConversationResponse:
    """Update conversation status (complete, flag, escalate)."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.org_id == org.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    new_status = body.get("status")
    valid_statuses = {"active", "completed", "escalated", "flagged"}
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Status must be one of: {', '.join(sorted(valid_statuses))}",
        )

    conv.status = new_status  # type: ignore[assignment]
    if new_status == "completed":
        conv.completed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
    elif new_status == "escalated" and not conv.escalated_at:
        conv.escalated_at = datetime.now(timezone.utc)  # type: ignore[assignment]

    await db.commit()
    await db.refresh(conv)
    return ConversationResponse.model_validate(conv)
