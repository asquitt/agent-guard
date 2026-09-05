"""Authentication service layer."""

# pyright: reportCallIssue=false

import re
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, create_refresh_token, get_password_hash, verify_password
from app.core.config import settings
from app.core.exceptions import AuthenticationError, ValidationError
from app.models.enums import PlanTier, UserRole
from app.models.user import Organization, User


def generate_slug(name: str) -> str:
    """Convert org name to URL-safe slug.

    'Acme Corp' -> 'acme-corp'
    'My   Company!!!' -> 'my-company'
    """
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug)
    return slug.strip("-")


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Query user by email."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    full_name: str,
    org_name: str,
    controlled_evaluation_accepted: Literal[True],
) -> tuple[User, Organization]:
    """Stage a new user, organization, and acceptance in one transaction.

    First user in the org is always ADMIN.
    The caller owns the transaction commit so its audit record is atomic too.
    Raises ValidationError if email or org slug already exists.
    """
    existing = await get_user_by_email(db, email)
    if existing is not None:
        raise ValidationError("Email already registered")

    slug = generate_slug(org_name)
    slug_result = await db.execute(select(Organization).where(Organization.slug == slug))
    if slug_result.scalar_one_or_none() is not None:
        raise ValidationError("Organization name already taken")

    if controlled_evaluation_accepted is not True:
        raise ValidationError("Controlled evaluation acceptance is required")

    accepted_at = datetime.now(timezone.utc)
    org = Organization(  # type: ignore[call-arg]
        name=org_name,
        slug=slug,
        plan_tier=PlanTier.STARTER.value,
        settings={
            "controlled_evaluation_acceptance": {
                "version": settings.CONTROLLED_EVALUATION_ACCEPTANCE_VERSION,
                "accepted_at": accepted_at.isoformat(),
            }
        },
    )
    db.add(org)
    await db.flush()

    user = User(  # type: ignore[call-arg]
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        role=UserRole.ADMIN.value,
        org_id=org.id,
        is_active=True,
        password_changed_at=accepted_at,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ValidationError("Email or organization name already taken")

    await db.refresh(user)
    await db.refresh(org)

    return user, org


def _is_account_locked(user: User) -> bool:
    """Check if the user account is currently locked."""
    locked_until = user.locked_until  # type: ignore[union-attr]
    if locked_until is None:
        return False
    now = datetime.now(timezone.utc)
    if locked_until.tzinfo is None:
        # Treat naive datetimes as UTC
        return now.replace(tzinfo=None) < locked_until
    return now < locked_until


async def _record_failed_login(db: AsyncSession, user: User) -> None:
    """Increment failed attempts and lock account if threshold reached."""
    attempts = (user.failed_login_attempts or 0) + 1  # type: ignore[operator]
    user.failed_login_attempts = attempts  # type: ignore[assignment]

    if attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
        user.locked_until = datetime.now(timezone.utc) + timedelta(  # type: ignore[assignment]
            minutes=settings.ACCOUNT_LOCKOUT_MINUTES,
        )
    await db.flush()


async def _reset_failed_login(db: AsyncSession, user: User) -> None:
    """Clear failed login counter on successful auth."""
    if user.failed_login_attempts:  # type: ignore[truthy-bool]
        user.failed_login_attempts = 0  # type: ignore[assignment]
        user.locked_until = None  # type: ignore[assignment]
        await db.flush()


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User:
    """Validate email/password and return user.

    Returns generic error to prevent email enumeration.
    SSO-only users (no password hash) cannot use password login.
    Enforces account lockout after MAX_FAILED_LOGIN_ATTEMPTS.
    """
    user = await get_user_by_email(db, email)
    if user is None:
        raise AuthenticationError("Invalid email or password")

    # Check account lockout
    if _is_account_locked(user):
        raise AuthenticationError("Account is temporarily locked due to too many failed login attempts")

    if not user.hashed_password:  # type: ignore[truthy-bool]
        raise AuthenticationError("Invalid email or password")

    if not verify_password(password, user.hashed_password):  # type: ignore[arg-type]
        await _record_failed_login(db, user)
        raise AuthenticationError("Invalid email or password")

    if not user.is_active:  # type: ignore[truthy-bool]
        raise AuthenticationError("Account is deactivated")

    # Successful login — reset counter
    await _reset_failed_login(db, user)
    return user


def create_token_pair(user_id: UUID, token_version: int = 0) -> tuple[str, str]:
    """Create access + refresh token pair.

    Embeds token_version so tokens can be invalidated on password change.
    """
    access = create_access_token(subject=str(user_id), token_version=token_version)
    refresh = create_refresh_token(subject=str(user_id), token_version=token_version)
    return access, refresh


def decode_refresh_token(token: str) -> tuple[str, int]:
    """Decode and validate a refresh token.

    Returns (user_id, token_version).
    Validates type="refresh" to prevent token confusion attacks.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise AuthenticationError(f"Invalid refresh token: {e}")

    token_type = payload.get("type")
    if token_type != "refresh":
        raise AuthenticationError("Invalid token type: expected refresh token")

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise AuthenticationError("Invalid refresh token: missing subject")

    token_version: int = payload.get("ver", 0)
    return user_id, token_version


async def change_password(
    db: AsyncSession,
    user: User,
    new_password: str,
) -> None:
    """Change a user's password and invalidate all existing tokens."""
    user.hashed_password = get_password_hash(new_password)  # type: ignore[assignment]
    user.token_version = (user.token_version or 0) + 1  # type: ignore[operator, assignment]
    user.password_changed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
    await db.flush()
