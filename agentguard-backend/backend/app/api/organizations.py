"""Organization management router."""

# pyright: reportGeneralTypeIssues=false

import ipaddress

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_db, require_admin
from app.models.user import Organization, User
from app.schemas.organizations import MemberListResponse, MemberResponse, OrgDetailResponse, OrgUpdateRequest


class IpAllowlistRequest(BaseModel):
    """Request body for updating IP allowlist."""

    ips: list[str] = Field(default_factory=list, max_length=200)


class IpAllowlistResponse(BaseModel):
    """Current IP allowlist."""

    ips: list[str]
    enabled: bool

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
        current = org.settings or {}
        org.settings = {**current, **body.settings}  # type: ignore[assignment]
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
    count_result = await db.execute(select(func.count(User.id)).where(User.org_id == org.id))
    total = count_result.scalar_one()

    result = await db.execute(
        select(User).where(User.org_id == org.id).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    members = result.scalars().all()
    return MemberListResponse(
        items=[MemberResponse.model_validate(m) for m in members],
        total=total,
    )


def _validate_ip_entry(entry: str) -> str:
    """Validate an IP address or CIDR range. Returns the normalized form."""
    try:
        if "/" in entry:
            net = ipaddress.ip_network(entry, strict=False)
            return str(net)
        else:
            addr = ipaddress.ip_address(entry)
            return str(addr)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid IP address or CIDR range: {entry} ({exc})",
        ) from exc


@router.get("/current/ip-allowlist", response_model=IpAllowlistResponse)
async def get_ip_allowlist(
    org: Organization = Depends(get_current_org),
) -> IpAllowlistResponse:
    """Get the current IP allowlist for proxy access."""
    settings: dict = org.settings or {}  # type: ignore[assignment]
    ips: list[str] = settings.get("ip_allowlist", [])
    return IpAllowlistResponse(ips=ips, enabled=len(ips) > 0)


@router.put("/current/ip-allowlist", response_model=IpAllowlistResponse)
async def update_ip_allowlist(
    body: IpAllowlistRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> IpAllowlistResponse:
    """Replace the IP allowlist. Admin only. Accepts IPs and CIDR ranges."""
    validated = [_validate_ip_entry(ip.strip()) for ip in body.ips if ip.strip()]
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for ip in validated:
        if ip not in seen:
            seen.add(ip)
            unique.append(ip)

    current = org.settings or {}
    org.settings = {**current, "ip_allowlist": unique}  # type: ignore[assignment]
    await db.commit()
    await db.refresh(org)
    return IpAllowlistResponse(ips=unique, enabled=len(unique) > 0)
