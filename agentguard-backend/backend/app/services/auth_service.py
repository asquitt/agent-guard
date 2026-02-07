"""Authentication service layer."""

# pyright: reportCallIssue=false

import re
from uuid import UUID

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
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
) -> tuple[User, Organization]:
    """Register a new user and organization atomically.

    First user in the org is always ADMIN.
    Raises ValidationError if email or org slug already exists.
    """
    existing = await get_user_by_email(db, email)
    if existing is not None:
        raise ValidationError("Email already registered")

    slug = generate_slug(org_name)
    slug_result = await db.execute(select(Organization).where(Organization.slug == slug))
    if slug_result.scalar_one_or_none() is not None:
        raise ValidationError("Organization name already taken")

    org = Organization(  # type: ignore[call-arg]
        name=org_name,
        slug=slug,
        plan_tier=PlanTier.STARTER.value,
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
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValidationError("Email or organization name already taken")

    await db.refresh(user)
    await db.refresh(org)

    # Create Stripe customer (non-blocking — don't fail registration)
    try:
        from app.services.billing_service import get_or_create_stripe_customer

        await get_or_create_stripe_customer(db, org)
    except Exception:
        import logging

        logging.getLogger(__name__).warning(
            "Failed to create Stripe customer for org %s — will retry later",
            org.id,
        )

    return user, org


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User:
    """Validate email/password and return user.

    Returns generic error to prevent email enumeration.
    """
    user = await get_user_by_email(db, email)
    if user is None:
        raise AuthenticationError("Invalid email or password")
    if not verify_password(password, user.hashed_password):  # type: ignore[arg-type]
        raise AuthenticationError("Invalid email or password")
    if not user.is_active:  # type: ignore[truthy-bool]
        raise AuthenticationError("Account is deactivated")
    return user


def create_token_pair(user_id: UUID) -> tuple[str, str]:
    """Create access + refresh token pair."""
    access = create_access_token(subject=str(user_id))
    refresh = create_refresh_token(subject=str(user_id))
    return access, refresh


def decode_refresh_token(token: str) -> str:
    """Decode and validate a refresh token. Returns user_id.

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

    return user_id
