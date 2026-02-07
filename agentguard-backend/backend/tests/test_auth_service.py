"""Unit tests for auth service — pure functions + mock-based DB tests."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from jose import jwt

from app.core.auth import create_access_token, create_refresh_token, get_password_hash
from app.core.config import settings
from app.core.exceptions import AuthenticationError
from app.services.auth_service import (
    authenticate_user,
    create_token_pair,
    decode_refresh_token,
    generate_slug,
)


# --------------- generate_slug ---------------


class TestGenerateSlug:
    def test_basic(self):
        assert generate_slug("Acme Corp") == "acme-corp"

    def test_special_chars(self):
        result = generate_slug("Hello! World@123")
        assert result == "hello-world123"

    def test_multiple_spaces(self):
        assert generate_slug("  Multiple   Spaces  ") == "multiple-spaces"

    def test_already_slug(self):
        assert generate_slug("already-slug") == "already-slug"

    def test_leading_trailing_hyphens(self):
        assert generate_slug("--test--") == "test"

    def test_empty_after_strip(self):
        assert generate_slug("!!!") == ""


# --------------- Token functions ---------------


class TestCreateTokenPair:
    def test_returns_two_strings(self):
        user_id = uuid.uuid4()
        access, refresh = create_token_pair(user_id)
        assert isinstance(access, str)
        assert isinstance(refresh, str)
        assert access != refresh

    def test_tokens_are_valid_jwts(self):
        user_id = uuid.uuid4()
        access, refresh = create_token_pair(user_id)

        access_payload = jwt.decode(access, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        refresh_payload = jwt.decode(refresh, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        assert access_payload["sub"] == str(user_id)
        assert access_payload["type"] == "access"
        assert refresh_payload["sub"] == str(user_id)
        assert refresh_payload["type"] == "refresh"

    def test_token_version_in_payload(self):
        user_id = uuid.uuid4()
        access, refresh = create_token_pair(user_id, token_version=5)

        access_payload = jwt.decode(access, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        refresh_payload = jwt.decode(refresh, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        assert access_payload["ver"] == 5
        assert refresh_payload["ver"] == 5


class TestDecodeRefreshToken:
    def test_valid_refresh_token(self):
        user_id = uuid.uuid4()
        refresh = create_refresh_token(str(user_id), token_version=3)

        decoded_id, decoded_ver = decode_refresh_token(refresh)
        assert decoded_id == str(user_id)
        assert decoded_ver == 3

    def test_rejects_access_token(self):
        user_id = uuid.uuid4()
        access = create_access_token(str(user_id))

        with pytest.raises(AuthenticationError, match="expected refresh token"):
            decode_refresh_token(access)

    def test_rejects_garbage(self):
        with pytest.raises(AuthenticationError, match="Invalid refresh token"):
            decode_refresh_token("not.a.jwt")

    def test_default_version_is_zero(self):
        user_id = uuid.uuid4()
        refresh = create_refresh_token(str(user_id))

        _, ver = decode_refresh_token(refresh)
        assert ver == 0


# --------------- authenticate_user (mock-based) ---------------


def _make_mock_user(
    password: str = "correct-password",
    is_active: bool = True,
    locked_until: datetime | None = None,
    failed_login_attempts: int = 0,
) -> MagicMock:
    """Build a mock User with hashed password and relevant attrs."""
    user = MagicMock()
    user.hashed_password = get_password_hash(password)
    user.is_active = is_active
    user.locked_until = locked_until
    user.failed_login_attempts = failed_login_attempts
    user.token_version = 0
    return user


def _mock_db_returning(user: MagicMock | None) -> AsyncMock:
    """Mock AsyncSession whose execute().scalar_one_or_none() returns user."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute.return_value = result
    return db


class TestAuthenticateUser:
    @pytest.mark.asyncio
    async def test_success(self):
        user = _make_mock_user(password="good-pass")
        db = _mock_db_returning(user)

        result = await authenticate_user(db, "user@example.com", "good-pass")
        assert result is user

    @pytest.mark.asyncio
    async def test_wrong_password(self):
        user = _make_mock_user(password="good-pass")
        db = _mock_db_returning(user)

        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await authenticate_user(db, "user@example.com", "wrong-pass")

    @pytest.mark.asyncio
    async def test_user_not_found(self):
        db = _mock_db_returning(None)

        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await authenticate_user(db, "nobody@example.com", "any-pass")

    @pytest.mark.asyncio
    async def test_locked_account(self):
        future = datetime.now(timezone.utc) + timedelta(minutes=30)
        user = _make_mock_user(locked_until=future)
        db = _mock_db_returning(user)

        with pytest.raises(AuthenticationError, match="temporarily locked"):
            await authenticate_user(db, "user@example.com", "correct-password")

    @pytest.mark.asyncio
    async def test_inactive_account(self):
        user = _make_mock_user(password="good-pass", is_active=False)
        db = _mock_db_returning(user)

        with pytest.raises(AuthenticationError, match="deactivated"):
            await authenticate_user(db, "user@example.com", "good-pass")
