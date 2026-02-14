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
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MeResponse,
    OrgResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.notifications import NotificationPreferences, NotificationPreferencesResponse
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
    token_ver: int = user.token_version or 0  # type: ignore[assignment]
    access, refresh = auth_service.create_token_pair(UUID(str(user.id)), token_version=token_ver)
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
    Returns 401 with lockout message if too many failed attempts.
    """
    client_ip = get_client_ip(request)
    try:
        user = await auth_service.authenticate_user(db=db, email=body.email, password=body.password)
    except AuthenticationError as e:
        # Log failed login attempt if user exists
        existing = await auth_service.get_user_by_email(db, body.email)
        if existing is not None:
            await write_audit(db, UUID(str(existing.org_id)), UUID(str(existing.id)), "auth.login_failed", "user", UUID(str(existing.id)), ip_address=client_ip)
        await db.commit()

        detail = "Invalid email or password"
        if "locked" in str(e):
            detail = str(e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
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
    token_ver: int = user.token_version or 0  # type: ignore[assignment]
    access, refresh = auth_service.create_token_pair(UUID(str(user.id)), token_version=token_ver)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Refresh access token using refresh token.

    Implements token rotation — returns a new refresh token each time.
    Validates token_version to enforce session invalidation on password change.
    """
    try:
        user_id, token_ver = auth_service.decode_refresh_token(body.refresh_token)
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

    # Validate token_version — password change invalidates all tokens
    current_ver: int = user.token_version or 0  # type: ignore[assignment]
    if token_ver < current_ver:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated (password changed)",
        )

    # Token rotation — issue new pair with current version
    access, new_refresh = auth_service.create_token_pair(UUID(str(user.id)), token_version=current_ver)
    return TokenResponse(access_token=access, refresh_token=new_refresh)


@router.post("/change-password", status_code=status.HTTP_200_OK, response_model=TokenResponse)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Change password. Invalidates all existing sessions and returns new tokens."""
    client_ip = get_client_ip(request)

    # Verify current password
    if not current_user.hashed_password:  # type: ignore[truthy-bool]
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SSO users cannot change password")

    from app.core.auth import verify_password

    if not verify_password(body.current_password, current_user.hashed_password):  # type: ignore[arg-type]
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect")

    await auth_service.change_password(db, current_user, body.new_password)
    await write_audit(
        db, UUID(str(current_user.org_id)), UUID(str(current_user.id)),
        "auth.password_changed", "user", UUID(str(current_user.id)),
        ip_address=client_ip,
    )
    await db.commit()

    # Return new tokens with updated version
    token_ver: int = current_user.token_version or 0  # type: ignore[assignment]
    access, refresh = auth_service.create_token_pair(UUID(str(current_user.id)), token_version=token_ver)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Request a password reset link.

    Always returns 200 to prevent email enumeration.
    In production, this would send an email with the reset link.
    """
    import logging

    from app.core.auth import create_password_reset_token

    logger = logging.getLogger(__name__)

    user = await auth_service.get_user_by_email(db, body.email)
    if user is not None and user.is_active:
        token = create_password_reset_token(str(user.id))
        # In production: send email with reset link containing this token
        # For now, log the token (visible in server logs for dev/testing)
        logger.info(
            "Password reset requested for user_id=%s — token=%s (expires in %d min)",
            user.id,
            token[:20] + "...",
            15,
        )
        await write_audit(
            db, UUID(str(user.org_id)), UUID(str(user.id)),
            "auth.password_reset_requested", "user", UUID(str(user.id)),
            ip_address=get_client_ip(request),
        )
        await db.commit()

    # Always return success to prevent email enumeration
    return {"message": "If an account exists with that email, a password reset link has been sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK, response_model=TokenResponse)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Reset password using a valid reset token."""
    from app.core.auth import decode_password_reset_token

    try:
        user_id = decode_password_reset_token(body.token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    await auth_service.change_password(db, user, body.new_password)
    await write_audit(
        db, UUID(str(user.org_id)), UUID(str(user.id)),
        "auth.password_reset_completed", "user", UUID(str(user.id)),
        ip_address=get_client_ip(request),
    )
    await db.commit()

    # Return new tokens so user is auto-logged in after reset
    token_ver: int = user.token_version or 0  # type: ignore[assignment]
    access, refresh = auth_service.create_token_pair(UUID(str(user.id)), token_version=token_ver)
    return TokenResponse(access_token=access, refresh_token=refresh)


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


@router.get("/me/notifications", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user: User = Depends(get_current_user),
) -> NotificationPreferencesResponse:
    """Get current user's notification preferences."""
    raw: dict = current_user.notification_preferences or {}  # type: ignore[assignment]
    prefs = NotificationPreferences(**raw) if raw else NotificationPreferences()
    return NotificationPreferencesResponse(preferences=prefs)


@router.put("/me/notifications", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    request: Request,
    body: NotificationPreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationPreferencesResponse:
    """Update current user's notification preferences."""
    current_user.notification_preferences = body.model_dump()  # type: ignore[assignment]
    db.add(current_user)
    await write_audit(
        db, UUID(str(current_user.org_id)), UUID(str(current_user.id)),
        "user.notification_preferences_updated", "user", UUID(str(current_user.id)),
        ip_address=get_client_ip(request),
    )
    await db.commit()
    return NotificationPreferencesResponse(preferences=body)
