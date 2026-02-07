"""Organization management router."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db, require_admin
from app.models.user import Organization, User
from app.schemas.organizations import (
    MemberListResponse,
    MemberResponse,
    OrgDetailResponse,
    OrgUpdateRequest,
)

router = APIRouter()


@router.get("/current", response_model=OrgDetailResponse)
async def get_current_organization(
    org: Organization = Depends(get_current_org),
) -> OrgDetailResponse:
    """Get current organization details."""
    return OrgDetailResponse.model_validate(org)


@router.patch("/current", response_model=OrgDetailResponse)
async def update_organization(
    body: OrgUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> OrgDetailResponse:
    """Update organization settings. Admin only."""
    if body.name is not None:
        org.name = body.name  # type: ignore[assignment]
    if body.settings is not None:
        org.settings = body.settings  # type: ignore[assignment]
    await db.commit()
    await db.refresh(org)
    return OrgDetailResponse.model_validate(org)


@router.get("/current/members", response_model=MemberListResponse)
async def list_members(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_org),
) -> MemberListResponse:
    """List organization members with pagination."""
    count_result = await db.execute(
        select(func.count(User.id)).where(User.org_id == org.id)
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(User)
        .where(User.org_id == org.id)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    members = result.scalars().all()
    return MemberListResponse(
        items=[MemberResponse.model_validate(m) for m in members],
        total=total,
    )
