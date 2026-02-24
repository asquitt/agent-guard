"""Shared fixtures for integration tests.

Extends the root conftest.py fixtures with multi-org and role-based
fixtures needed for tenant isolation and authorization tests.
"""

import uuid

import pytest
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token
from app.models.user import ApiKey, Organization, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Reuse the test DB setup from root conftest (auto-discovered by pytest).
# We only add fixtures that the root conftest doesn't provide.

TEST_PASSWORD = "TestPassword1!"
STRONG_PASSWORD = "StrongPass1!xx"


# --------------- Second Organization (for tenant isolation) ---------------


@pytest.fixture
async def other_org(db_session: AsyncSession) -> Organization:
    """Create a SECOND organization for tenant isolation tests."""
    organization = Organization(
        id=uuid.uuid4(),
        name="Other Organization",
        slug="other-org",
        plan_tier="starter",
        settings={},
    )
    db_session.add(organization)
    await db_session.flush()
    return organization


@pytest.fixture
async def other_user(db_session: AsyncSession, other_org: Organization) -> User:
    """Create an admin user in the OTHER organization."""
    test_user = User(
        id=uuid.uuid4(),
        email="other-admin@other-org.dev",
        hashed_password=pwd_context.hash(TEST_PASSWORD),
        full_name="Other Admin",
        role="admin",
        org_id=other_org.id,
        is_active=True,
        token_version=0,
        failed_login_attempts=0,
    )
    db_session.add(test_user)
    await db_session.flush()
    return test_user


@pytest.fixture
def other_org_headers(other_user: User) -> dict[str, str]:
    """Auth headers for a user in a DIFFERENT org (tenant isolation)."""
    token = create_access_token(str(other_user.id), token_version=0)
    return {"Authorization": f"Bearer {token}"}


# --------------- Role-specific users (same org as primary) ---------------


@pytest.fixture
async def viewer_user(db_session: AsyncSession, org: Organization) -> User:
    """Create a viewer user (read-only) in the primary org."""
    test_user = User(
        id=uuid.uuid4(),
        email="viewer@agentguard.dev",
        hashed_password=pwd_context.hash(TEST_PASSWORD),
        full_name="Viewer User",
        role="viewer",
        org_id=org.id,
        is_active=True,
        token_version=0,
        failed_login_attempts=0,
    )
    db_session.add(test_user)
    await db_session.flush()
    return test_user


@pytest.fixture
def viewer_headers(viewer_user: User) -> dict[str, str]:
    """Auth headers for a viewer (read-only) user."""
    token = create_access_token(str(viewer_user.id), token_version=0)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def member_user(db_session: AsyncSession, org: Organization) -> User:
    """Create a member user in the primary org."""
    test_user = User(
        id=uuid.uuid4(),
        email="member@agentguard.dev",
        hashed_password=pwd_context.hash(TEST_PASSWORD),
        full_name="Member User",
        role="member",
        org_id=org.id,
        is_active=True,
        token_version=0,
        failed_login_attempts=0,
    )
    db_session.add(test_user)
    await db_session.flush()
    return test_user


@pytest.fixture
def member_headers(member_user: User) -> dict[str, str]:
    """Auth headers for a member user."""
    token = create_access_token(str(member_user.id), token_version=0)
    return {"Authorization": f"Bearer {token}"}


# --------------- API Key fixtures ---------------


@pytest.fixture
async def api_key(db_session: AsyncSession, org: Organization) -> tuple[ApiKey, str]:
    """Create an API key for the primary org. Returns (ApiKey, full_key)."""
    import hashlib

    full_key = f"ag_live_{uuid.uuid4().hex}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()

    key = ApiKey(
        id=uuid.uuid4(),
        org_id=org.id,
        key_hash=key_hash,
        prefix=full_key[:16],
        name="Test Key",
        scopes=["proxy"],
        environment="production",
        is_active=True,
    )
    db_session.add(key)
    await db_session.flush()
    return key, full_key
