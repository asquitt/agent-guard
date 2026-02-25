"""Organization management router."""

# pyright: reportGeneralTypeIssues=false, reportCallIssue=false

import ipaddress
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_org, get_current_user, get_db, require_admin, require_permission
from app.models.enums import ROLE_PERMISSIONS, Environment, UserRole
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
    _user: User = Depends(require_permission("settings:read")),
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
    _user: User = Depends(require_permission("settings:read")),
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
    _user: User = Depends(require_permission("settings:read")),
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


class RoleInfo(BaseModel):
    role: str
    permissions: list[str]


class RolesResponse(BaseModel):
    roles: list[RoleInfo]


@router.get("/roles", response_model=RolesResponse)
async def list_roles(
    _user: User = Depends(get_current_user),
) -> RolesResponse:
    """List all available roles and their permissions."""
    return RolesResponse(
        roles=[
            RoleInfo(role=role.value, permissions=sorted(ROLE_PERMISSIONS.get(role.value, frozenset())))
            for role in UserRole
        ]
    )


class UpdateMemberRoleRequest(BaseModel):
    role: str

    @classmethod
    def validate_role(cls, v: str) -> str:
        valid = [r.value for r in UserRole]
        if v not in valid:
            raise ValueError(f"role must be one of: {', '.join(valid)}")
        return v


@router.patch("/current/members/{user_id}", response_model=MemberResponse)
async def update_member_role(
    user_id: UUID,
    body: UpdateMemberRoleRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> MemberResponse:
    """Update a member's role. Admin/owner only."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.org_id == org.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    valid_roles = [r.value for r in UserRole]
    if body.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )

    member.role = body.role  # type: ignore[assignment]
    await db.commit()
    await db.refresh(member)
    return MemberResponse.model_validate(member)


@router.delete("/current/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> None:
    """Remove a member from the organization. Admin/owner only.

    Cannot remove yourself or the last owner.
    """
    # Prevent self-removal
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot remove yourself from the organization",
        )

    result = await db.execute(
        select(User).where(User.id == user_id, User.org_id == org.id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # Prevent removing last owner
    if str(member.role) == UserRole.OWNER.value:
        owner_count = await db.execute(
            select(func.count(User.id)).where(
                User.org_id == org.id, User.role == UserRole.OWNER.value
            )
        )
        if (owner_count.scalar_one() or 0) <= 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cannot remove the last owner of the organization",
            )

    member.is_active = False  # type: ignore[assignment]
    await db.commit()


class InviteMemberRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: str = "member"


@router.post("/current/members/invite", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    body: InviteMemberRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> MemberResponse:
    """Invite a new member to the organization. Admin/owner only.

    If the user already exists, they are added to the org. Otherwise a
    placeholder account is created (password set on first login).
    """
    from uuid import uuid4

    from app.core.auth import get_password_hash

    valid_roles = [r.value for r in UserRole]
    if body.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )

    # Check if already a member
    existing = await db.execute(
        select(User).where(User.email == body.email.lower(), User.org_id == org.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization",
        )

    # Create placeholder account with random password (user resets on first login)
    placeholder_hash = get_password_hash(uuid4().hex)
    new_user = User(
        id=uuid4(),
        email=body.email.lower(),
        hashed_password=placeholder_hash,
        full_name=body.email.split("@")[0],
        role=body.role,
        org_id=org.id,
        is_active=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Send invite email with password reset link (non-blocking)
    try:
        from app.core.auth import create_password_reset_token
        from app.core.config import settings
        from app.services.email_service import send_invite_email

        reset_token = create_password_reset_token(str(new_user.id))
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        inviter_name = str(admin_user.full_name) or str(admin_user.email)
        send_invite_email(
            to_email=body.email.lower(),
            org_name=str(org.name),
            role=body.role,
            inviter_name=inviter_name,
            reset_url=reset_url,
        )
    except Exception:
        import logging
        logging.getLogger(__name__).warning(
            "Failed to send invite email to %s — user created but email not delivered",
            body.email,
        )

    return MemberResponse.model_validate(new_user)


# ---------------------------------------------------------------------------
# Environments
# ---------------------------------------------------------------------------


class EnvironmentInfo(BaseModel):
    name: str
    label: str


class EnvironmentsResponse(BaseModel):
    environments: list[EnvironmentInfo]
    current: str


@router.get("/environments", response_model=EnvironmentsResponse)
async def list_environments(
    _user: User = Depends(require_permission("settings:read")),
    org: Organization = Depends(get_current_org),
) -> EnvironmentsResponse:
    """List available environments and the org's default."""
    settings_dict: dict = org.settings or {}  # type: ignore[assignment]
    current = settings_dict.get("default_environment", Environment.PRODUCTION.value)
    return EnvironmentsResponse(
        environments=[
            EnvironmentInfo(name=e.value, label=e.value.replace("_", " ").title())
            for e in Environment
        ],
        current=current,
    )


# ---------------------------------------------------------------------------
# Data Residency & Sovereignty Controls
# ---------------------------------------------------------------------------

AVAILABLE_REGIONS = [
    {"id": "us-east-1", "name": "US East", "country": "US"},
    {"id": "us-west-2", "name": "US West", "country": "US"},
    {"id": "eu-west-1", "name": "EU (Ireland)", "country": "IE"},
    {"id": "eu-central-1", "name": "EU (Frankfurt)", "country": "DE"},
    {"id": "ap-southeast-1", "name": "APAC (Singapore)", "country": "SG"},
    {"id": "ap-northeast-1", "name": "APAC (Tokyo)", "country": "JP"},
]


class RegionInfo(BaseModel):
    id: str
    name: str
    country: str


class ProviderRegionRule(BaseModel):
    """Which providers are allowed in a given region."""

    region: str
    allowed_providers: list[str] = Field(serialization_alias="allowedProviders")


class DataResidencyConfig(BaseModel):
    """Data residency settings for the organization."""

    primary_region: str = Field(serialization_alias="primaryRegion")
    allowed_regions: list[str] = Field(serialization_alias="allowedRegions")
    provider_rules: list[ProviderRegionRule] = Field(serialization_alias="providerRules")
    enforce_residency: bool = Field(serialization_alias="enforceResidency")
    encryption_key_id: str | None = Field(default=None, serialization_alias="encryptionKeyId")


class DataResidencyResponse(BaseModel):
    config: DataResidencyConfig
    available_regions: list[RegionInfo] = Field(serialization_alias="availableRegions")


class DataResidencyUpdateRequest(BaseModel):
    """Update data residency settings."""

    primary_region: str | None = Field(default=None, alias="primaryRegion")
    allowed_regions: list[str] | None = Field(default=None, alias="allowedRegions")
    provider_rules: list[ProviderRegionRule] | None = Field(default=None, alias="providerRules")
    enforce_residency: bool | None = Field(default=None, alias="enforceResidency")
    encryption_key_id: str | None = Field(default=None, alias="encryptionKeyId")


@router.get("/current/data-residency", response_model=DataResidencyResponse)
async def get_data_residency(
    _user: User = Depends(require_permission("settings:read")),
    org: Organization = Depends(get_current_org),
) -> DataResidencyResponse:
    """Get the organization's data residency configuration."""
    settings_dict: dict = org.settings or {}  # type: ignore[assignment]
    residency = settings_dict.get("data_residency", {})

    config = DataResidencyConfig(
        primary_region=residency.get("primary_region", "us-east-1"),
        allowed_regions=residency.get("allowed_regions", ["us-east-1"]),
        provider_rules=[
            ProviderRegionRule(**r) for r in residency.get("provider_rules", [])
        ],
        enforce_residency=residency.get("enforce_residency", False),
        encryption_key_id=residency.get("encryption_key_id"),
    )
    return DataResidencyResponse(
        config=config,
        available_regions=[RegionInfo(**r) for r in AVAILABLE_REGIONS],
    )


@router.put("/current/data-residency", response_model=DataResidencyResponse)
async def update_data_residency(
    body: DataResidencyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
    org: Organization = Depends(get_current_org),
) -> DataResidencyResponse:
    """Update data residency settings. Admin only."""
    settings_dict: dict = org.settings or {}  # type: ignore[assignment]
    current = settings_dict.get("data_residency", {})

    valid_region_ids = {r["id"] for r in AVAILABLE_REGIONS}

    update = body.model_dump(exclude_unset=True, by_alias=False)
    if "primary_region" in update:
        if update["primary_region"] not in valid_region_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid region: {update['primary_region']}",
            )
        current["primary_region"] = update["primary_region"]

    if "allowed_regions" in update:
        invalid = set(update["allowed_regions"]) - valid_region_ids
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid regions: {', '.join(invalid)}",
            )
        current["allowed_regions"] = update["allowed_regions"]

    if "provider_rules" in update and update["provider_rules"] is not None:
        current["provider_rules"] = [
            r.model_dump(by_alias=False) for r in body.provider_rules  # type: ignore[union-attr]
        ]

    if "enforce_residency" in update:
        current["enforce_residency"] = update["enforce_residency"]

    if "encryption_key_id" in update:
        current["encryption_key_id"] = update["encryption_key_id"]

    org.settings = {**settings_dict, "data_residency": current}  # type: ignore[assignment]
    await db.commit()
    await db.refresh(org)

    config = DataResidencyConfig(
        primary_region=current.get("primary_region", "us-east-1"),
        allowed_regions=current.get("allowed_regions", ["us-east-1"]),
        provider_rules=[
            ProviderRegionRule(**r) for r in current.get("provider_rules", [])
        ],
        enforce_residency=current.get("enforce_residency", False),
        encryption_key_id=current.get("encryption_key_id"),
    )
    return DataResidencyResponse(
        config=config,
        available_regions=[RegionInfo(**r) for r in AVAILABLE_REGIONS],
    )
