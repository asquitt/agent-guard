"""Human-in-the-loop review queue router."""

# pyright: reportGeneralTypeIssues=false, reportCallIssue=false, reportArgumentType=false

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_current_user, get_db
from app.models.review_queue import ReviewItem
from app.models.user import Organization, User

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ReviewItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    incident_id: UUID | None = Field(serialization_alias="incidentId")
    proxy_request_id: UUID | None = Field(serialization_alias="proxyRequestId")
    status: str
    severity: str
    category: str | None
    title: str
    description: str | None
    reviewed_by: UUID | None = Field(serialization_alias="reviewedBy")
    reviewed_at: datetime | None = Field(serialization_alias="reviewedAt")
    decision_reason: str | None = Field(serialization_alias="decisionReason")
    escalation_level: int = Field(serialization_alias="escalationLevel")
    escalation_deadline: datetime | None = Field(serialization_alias="escalationDeadline")
    context: dict[str, object]
    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class ReviewListResponse(BaseModel):
    items: list[ReviewItemResponse]
    total: int


class ReviewDecisionRequest(BaseModel):
    """Approve or reject a review item."""

    decision: str = Field(pattern="^(approved|rejected)$")
    reason: str | None = None


class ReviewStatsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    pending: int
    approved: int
    rejected: int
    escalated: int
    expired: int
    avg_review_time_minutes: float | None = Field(
        default=None, serialization_alias="avgReviewTimeMinutes"
    )


class ReviewCreateRequest(BaseModel):
    """Manually queue an item for review."""

    incident_id: UUID | None = Field(default=None, alias="incidentId")
    severity: str
    category: str | None = None
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    escalation_minutes: int | None = Field(default=None, alias="escalationMinutes")
    context: dict[str, object] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=ReviewListResponse)
async def list_review_items(
    review_status: str | None = Query(default=None, alias="status"),
    severity: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ReviewListResponse:
    """List review queue items with optional filtering."""
    base = select(ReviewItem).where(ReviewItem.org_id == org.id)

    if review_status:
        base = base.where(ReviewItem.status == review_status)
    if severity:
        base = base.where(ReviewItem.severity == severity)

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar_one()

    result = await db.execute(
        base.order_by(ReviewItem.created_at.desc()).offset(skip).limit(limit)
    )
    items = result.scalars().all()

    return ReviewListResponse(
        items=[ReviewItemResponse.model_validate(i) for i in items],
        total=total,
    )


@router.get("/stats", response_model=ReviewStatsResponse)
async def get_review_stats(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ReviewStatsResponse:
    """Get review queue statistics."""
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Status counts
    status_result = await db.execute(
        select(
            ReviewItem.status,
            func.count(ReviewItem.id),
        )
        .where(ReviewItem.org_id == org.id, ReviewItem.created_at >= cutoff)
        .group_by(ReviewItem.status)
    )
    counts: dict[str, int] = {row[0]: row[1] for row in status_result.all()}

    # Average review time for completed reviews
    avg_result = await db.execute(
        select(
            func.avg(
                func.extract("epoch", ReviewItem.reviewed_at - ReviewItem.created_at) / 60
            )
        ).where(
            ReviewItem.org_id == org.id,
            ReviewItem.reviewed_at.is_not(None),
            ReviewItem.created_at >= cutoff,
        )
    )
    avg_minutes = avg_result.scalar_one()

    return ReviewStatsResponse(
        pending=counts.get("pending", 0),
        approved=counts.get("approved", 0),
        rejected=counts.get("rejected", 0),
        escalated=counts.get("escalated", 0),
        expired=counts.get("expired", 0),
        avg_review_time_minutes=round(avg_minutes, 1) if avg_minutes else None,
    )


@router.post("", response_model=ReviewItemResponse, status_code=status.HTTP_201_CREATED)
async def create_review_item(
    body: ReviewCreateRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ReviewItemResponse:
    """Manually queue an item for human review."""
    from datetime import timedelta

    deadline = None
    if body.escalation_minutes:
        deadline = datetime.now(timezone.utc) + timedelta(minutes=body.escalation_minutes)

    item = ReviewItem(
        org_id=org.id,
        incident_id=body.incident_id,
        status="pending",
        severity=body.severity,
        category=body.category,
        title=body.title,
        description=body.description,
        escalation_deadline=deadline,
        context=body.context,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return ReviewItemResponse.model_validate(item)


@router.post("/{item_id}/decide", response_model=ReviewItemResponse)
async def decide_review_item(
    item_id: UUID,
    body: ReviewDecisionRequest,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
    user: User = Depends(get_current_user),
) -> ReviewItemResponse:
    """Approve or reject a review queue item."""
    result = await db.execute(
        select(ReviewItem).where(ReviewItem.id == item_id, ReviewItem.org_id == org.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found")
    if item.status not in ("pending", "escalated"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot decide on item with status '{item.status}'",
        )

    item.status = body.decision  # type: ignore[assignment]
    item.reviewed_by = user.id  # type: ignore[assignment]
    item.reviewed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
    item.decision_reason = body.reason  # type: ignore[assignment]

    await db.commit()
    await db.refresh(item)
    return ReviewItemResponse.model_validate(item)


@router.post("/{item_id}/escalate", response_model=ReviewItemResponse)
async def escalate_review_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> ReviewItemResponse:
    """Manually escalate a review item."""
    result = await db.execute(
        select(ReviewItem).where(ReviewItem.id == item_id, ReviewItem.org_id == org.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found")

    item.status = "escalated"  # type: ignore[assignment]
    item.escalation_level = (item.escalation_level or 0) + 1  # type: ignore[assignment]

    await db.commit()
    await db.refresh(item)
    return ReviewItemResponse.model_validate(item)
