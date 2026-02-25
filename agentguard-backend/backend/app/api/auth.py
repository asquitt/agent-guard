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
    LoginResponse,
    MeResponse,
    MfaLoginVerifyRequest,
    MfaSetupResponse,
    MfaVerifyRequest,
    OrgResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from app.schemas.notifications import NotificationPreferences, NotificationPreferencesResponse
from app.services import auth_service, mfa_service
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


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """Authenticate user and return tokens (or MFA challenge).

    Returns 403 if the user's organization enforces SSO.
    Returns 401 with lockout message if too many failed attempts.
    If MFA is enabled, returns mfa_required=True with a temporary mfa_token.
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

    # If MFA is enabled, return a temporary token instead of full access
    if user.mfa_enabled is True:  # type: ignore[comparison-overlap]
        from app.core.auth import create_mfa_token

        mfa_token = create_mfa_token(str(user.id))
        await write_audit(db, UUID(str(user.org_id)), UUID(str(user.id)), "auth.mfa_challenge", "user", UUID(str(user.id)), ip_address=client_ip)
        await db.commit()
        return LoginResponse(mfa_required=True, mfa_token=mfa_token)

    await write_audit(db, UUID(str(user.org_id)), UUID(str(user.id)), "auth.login", "user", UUID(str(user.id)), ip_address=client_ip)
    await db.commit()
    token_ver: int = user.token_version or 0  # type: ignore[assignment]
    access, refresh = auth_service.create_token_pair(UUID(str(user.id)), token_version=token_ver)
    return LoginResponse(access_token=access, refresh_token=refresh)


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
    """
    import logging

    from app.core.auth import create_password_reset_token
    from app.core.config import settings
    from app.services.email_service import send_password_reset_email

    logger = logging.getLogger(__name__)

    user = await auth_service.get_user_by_email(db, body.email)
    if user is not None and user.is_active is True:  # type: ignore[comparison-overlap]
        token = create_password_reset_token(str(user.id))
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        send_password_reset_email(str(user.email), reset_url)
        logger.info(
            "Password reset requested for user_id=%s",
            user.id,
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


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: Request,
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update current user's profile (name)."""
    if body.full_name is not None:
        current_user.full_name = body.full_name  # type: ignore[assignment]
    db.add(current_user)
    await write_audit(
        db, UUID(str(current_user.org_id)), UUID(str(current_user.id)),
        "user.profile_updated", "user", UUID(str(current_user.id)),
        ip_address=get_client_ip(request),
    )
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


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


# ---------------------------------------------------------------------------
# MFA endpoints
# ---------------------------------------------------------------------------


@router.post("/mfa/verify-login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def mfa_verify_login(
    request: Request,
    body: MfaLoginVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Complete login by verifying TOTP code after password authentication.

    Accepts either a 6-digit TOTP code or an 8-char backup code.
    """
    from app.core.auth import decode_mfa_token

    client_ip = get_client_ip(request)
    try:
        user_id = decode_mfa_token(body.mfa_token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA token",
        )

    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if user is None or user.mfa_enabled is not True or user.totp_secret is None:  # type: ignore[comparison-overlap]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA session",
        )

    # Try TOTP code first, then backup code
    if mfa_service.verify_totp_code(str(user.totp_secret), body.code):
        pass  # Valid TOTP
    elif mfa_service.verify_backup_code(user, body.code):
        await mfa_service.consume_backup_code(db, user, body.code)
    else:
        await write_audit(db, UUID(str(user.org_id)), UUID(str(user.id)), "auth.mfa_failed", "user", UUID(str(user.id)), ip_address=client_ip)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA code",
        )

    await write_audit(db, UUID(str(user.org_id)), UUID(str(user.id)), "auth.login", "user", UUID(str(user.id)), ip_address=client_ip)
    await db.commit()
    token_ver: int = user.token_version or 0  # type: ignore[assignment]
    access, refresh = auth_service.create_token_pair(UUID(str(user.id)), token_version=token_ver)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MfaSetupResponse:
    """Start MFA enrollment — returns QR code and backup codes.

    Does NOT enable MFA until confirmed with a valid TOTP code via /mfa/confirm-setup.
    """
    if current_user.mfa_enabled is True:  # type: ignore[comparison-overlap]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )

    secret, qr_b64, backup_codes = await mfa_service.setup_totp(db, current_user)
    await write_audit(
        db, UUID(str(current_user.org_id)), UUID(str(current_user.id)),
        "auth.mfa_setup_started", "user", UUID(str(current_user.id)),
        ip_address=get_client_ip(request),
    )
    await db.commit()
    return MfaSetupResponse(secret=secret, qr_code=qr_b64, backup_codes=backup_codes)


@router.post("/mfa/confirm-setup", status_code=status.HTTP_200_OK)
async def mfa_confirm_setup(
    request: Request,
    body: MfaVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Confirm MFA setup by verifying a TOTP code from the authenticator app."""
    if current_user.mfa_enabled is True:  # type: ignore[comparison-overlap]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is already enabled",
        )

    success = await mfa_service.confirm_totp_setup(db, current_user, body.code)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid TOTP code — please try again",
        )

    await write_audit(
        db, UUID(str(current_user.org_id)), UUID(str(current_user.id)),
        "auth.mfa_enabled", "user", UUID(str(current_user.id)),
        ip_address=get_client_ip(request),
    )
    await db.commit()
    return {"message": "MFA has been enabled successfully"}


@router.post("/mfa/disable", status_code=status.HTTP_200_OK)
async def mfa_disable(
    request: Request,
    body: MfaVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Disable MFA. Requires a valid TOTP code for verification."""
    if current_user.mfa_enabled is not True:  # type: ignore[comparison-overlap]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not enabled",
        )

    if current_user.totp_secret is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA configuration is invalid",
        )

    if not mfa_service.verify_totp_code(str(current_user.totp_secret), body.code):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code",
        )

    await mfa_service.disable_mfa(db, current_user)
    await write_audit(
        db, UUID(str(current_user.org_id)), UUID(str(current_user.id)),
        "auth.mfa_disabled", "user", UUID(str(current_user.id)),
        ip_address=get_client_ip(request),
    )
    await db.commit()
    return {"message": "MFA has been disabled"}
