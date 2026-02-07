"""Authentication API router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_client_ip, get_current_user, get_db
from app.core.exceptions import AuthenticationError, ValidationError
from app.models.user import Organization, User
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    OrgResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service
from app.services.audit_service import write_audit

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Register a new user and organization."""
    client_ip = get_client_ip(request)
    try:
        user, _org = await auth_service.register_user(
            db=db,
            email=body.email,
            password=body.password,
            full_name=body.full_name,
            org_name=body.org_name,
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        )

    await write_audit(db, UUID(str(_org.id)), UUID(str(user.id)), "auth.register", "user", UUID(str(user.id)), ip_address=client_ip)
    await db.commit()
    access, refresh = auth_service.create_token_pair(UUID(str(user.id)))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user and return tokens.

    Returns 403 if the user's organization enforces SSO.
    """
    client_ip = get_client_ip(request)
    try:
        user = await auth_service.authenticate_user(db=db, email=body.email, password=body.password)
    except AuthenticationError:
        # Log failed login attempt if user exists
        existing = await auth_service.get_user_by_email(db, body.email)
        if existing is not None:
            await write_audit(db, UUID(str(existing.org_id)), UUID(str(existing.id)), "auth.login_failed", "user", UUID(str(existing.id)), ip_address=client_ip)
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check SSO enforcement on the user's org
    result = await db.execute(select(Organization).where(Organization.id == user.org_id))
    org = result.scalar_one_or_none()
    if org is not None:
        org_settings: dict = org.settings or {}  # type: ignore[assignment]
        if org_settings.get("sso_enforced"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SSO required for this organization",
                headers={"X-SSO-Org-Slug": str(org.slug)},
            )

    await write_audit(db, UUID(str(user.org_id)), UUID(str(user.id)), "auth.login", "user", UUID(str(user.id)), ip_address=client_ip)
    await db.commit()
    access, refresh = auth_service.create_token_pair(UUID(str(user.id)))
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh access token using refresh token."""
    try:
        user_id = auth_service.decode_refresh_token(body.refresh_token)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    access, new_refresh = auth_service.create_token_pair(UUID(str(user.id)))
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    """Get current user profile and organization."""
    result = await db.execute(select(Organization).where(Organization.id == current_user.org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return MeResponse(
        user=UserResponse.model_validate(current_user),
        organization=OrgResponse.model_validate(org),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Logout - client discards tokens."""
    client_ip = get_client_ip(request)
    await write_audit(db, UUID(str(current_user.org_id)), UUID(str(current_user.id)), "auth.logout", "user", UUID(str(current_user.id)), ip_address=client_ip)
    await db.commit()
    return None
