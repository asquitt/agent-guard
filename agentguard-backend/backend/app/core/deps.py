"""FastAPI dependency injection."""

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.enums import ROLE_PERMISSIONS, UserRole
from app.models.user import Organization, User

security = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async with AsyncSessionLocal() as session:  # type: ignore[attr-defined]
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT token.

    Validates access token type, queries User from DB,
    and checks is_active status.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception

        token_type: str | None = payload.get("type")
        if token_type != "access":
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:  # type: ignore[truthy-bool]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is deactivated",
        )

    # Validate token_version — password change invalidates all tokens
    token_ver: int = payload.get("ver", 0)
    user_ver: int = user.token_version or 0  # type: ignore[assignment]
    if token_ver < user_ver:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated (password changed)",
        )

    return user


async def get_current_org(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """Get current user's organization for tenant isolation."""
    result = await db.execute(select(Organization).where(Organization.id == current_user.org_id))
    org = result.scalar_one_or_none()

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return org


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require that the current user has admin or owner role."""
    role = str(current_user.role)
    if role not in (UserRole.ADMIN.value, UserRole.OWNER.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def require_permission(permission: str) -> Any:
    """Create a dependency that checks for a specific permission.

    Usage: `user: User = Depends(require_permission("incidents:write"))`
    """

    async def _check(
        current_user: User = Depends(get_current_user),
    ) -> User:
        role = str(current_user.role)
        perms = ROLE_PERMISSIONS.get(role, frozenset())
        if permission not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return current_user

    return _check


def get_client_ip(request: Request) -> str:
    """Extract client IP, checking X-Forwarded-For for proxied requests."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def get_current_org_from_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    """Authenticate via API key (for proxy routes).

    Expects: Authorization: Bearer ag_live_<hex>
    Hashes the key, looks up in DB, validates active + not expired.
    Updates last_used_at on each use.
    """
    from app.services import api_key_service

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    if not token.startswith("ag_live_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format",
        )

    key_hash = api_key_service.hash_api_key(token)
    api_key = await api_key_service.get_api_key_by_hash(db, key_hash)

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )

    # Check expiry
    if api_key.expires_at is not None:  # type: ignore[union-attr]
        if api_key.expires_at < datetime.now(timezone.utc):  # type: ignore[operator]
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key has expired",
            )

    # Resolve org
    result = await db.execute(select(Organization).where(Organization.id == api_key.org_id))
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Update last used
    await api_key_service.update_last_used(db, api_key)

    return org
