"""FastAPI dependency injection."""

from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal

security = HTTPBearer()


async def get_db() -> Generator[AsyncSession, None, None]:
    """Get database session dependency."""
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # TODO: Query user from database
    # user = await db.get(User, user_id)
    # if user is None:
    #     raise credentials_exception
    # return user

    return {"id": user_id}  # Placeholder until User model is implemented


async def get_current_org(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's organization for tenant isolation."""
    # TODO: Query organization from database
    # org = await db.get(Organization, current_user.org_id)
    # if org is None:
    #     raise HTTPException(status_code=404, detail="Organization not found")
    # return org

    return {"id": "placeholder-org-id"}  # Placeholder until Organization model is implemented
