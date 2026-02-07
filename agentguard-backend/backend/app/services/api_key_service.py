"""API key management service."""

# pyright: reportCallIssue=false

import hashlib
import hmac as _hmac
import secrets
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.models.user import ApiKey
from app.services.audit_service import write_audit

API_KEY_PREFIX = "ag_live_"


def generate_api_key() -> str:
    """Generate a random API key: ag_live_<32 hex chars>."""
    return f"{API_KEY_PREFIX}{secrets.token_hex(16)}"


def hash_api_key(key: str) -> str:
    """HMAC-SHA256 hash of the full API key.

    Keyed hash prevents brute-force if DB is compromised
    (attacker also needs SECRET_KEY).
    """
    return _hmac.new(
        settings.SECRET_KEY.encode(),
        key.encode(),
        hashlib.sha256,
    ).hexdigest()


def extract_prefix(key: str) -> str:
    """Extract display prefix: 'ag_live_' + first 8 random chars."""
    return key[:16]


async def create_api_key(
    db: AsyncSession,
    org_id: UUID,
    name: str,
    scopes: list[str],
    expires_at: datetime | None = None,
    user_id: UUID | None = None,
    ip_address: str | None = None,
) -> tuple[ApiKey, str]:
    """Create a new API key. Returns (model, full_key).

    The full key is only available at creation time.
    """
    full_key = generate_api_key()
    key_hash = hash_api_key(full_key)
    prefix = extract_prefix(full_key)

    api_key = ApiKey(
        org_id=org_id,
        key_hash=key_hash,
        prefix=prefix,
        name=name,
        scopes=scopes,
        expires_at=expires_at,
        is_active=True,
    )
    db.add(api_key)
    await db.flush()
    await write_audit(db, org_id, user_id, "api_key.created", "api_key", api_key.id, {"name": name, "prefix": prefix}, ip_address)
    await db.commit()
    await db.refresh(api_key)
    return api_key, full_key


async def list_api_keys(
    db: AsyncSession,
    org_id: UUID,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[ApiKey], int]:
    """List API keys for an org with pagination."""
    count_result = await db.execute(select(func.count(ApiKey.id)).where(ApiKey.org_id == org_id))
    total = count_result.scalar_one()

    result = await db.execute(
        select(ApiKey).where(ApiKey.org_id == org_id).order_by(ApiKey.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total


async def get_api_key(db: AsyncSession, org_id: UUID, key_id: UUID) -> ApiKey:
    """Get a single API key, scoped to org."""
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id, ApiKey.org_id == org_id))
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise NotFoundError(f"API key {key_id} not found")
    return api_key


async def revoke_api_key(db: AsyncSession, org_id: UUID, key_id: UUID, user_id: UUID | None = None, ip_address: str | None = None) -> ApiKey:
    """Soft-delete (deactivate) an API key."""
    api_key = await get_api_key(db, org_id, key_id)
    api_key.is_active = False  # type: ignore[assignment]
    await write_audit(db, org_id, user_id, "api_key.revoked", "api_key", key_id, {"name": str(api_key.name), "prefix": str(api_key.prefix)}, ip_address)
    await db.commit()
    await db.refresh(api_key)
    return api_key


async def update_api_key(
    db: AsyncSession,
    org_id: UUID,
    key_id: UUID,
    name: str | None = None,
    scopes: list[str] | None = None,
) -> ApiKey:
    """Update API key name and/or scopes."""
    api_key = await get_api_key(db, org_id, key_id)
    if name is not None:
        api_key.name = name  # type: ignore[assignment]
    if scopes is not None:
        api_key.scopes = scopes  # type: ignore[assignment]
    await db.commit()
    await db.refresh(api_key)
    return api_key


async def get_api_key_by_hash(db: AsyncSession, key_hash: str) -> ApiKey | None:
    """Look up an API key by its hash. Used for API key auth."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def update_last_used(db: AsyncSession, api_key: ApiKey) -> None:
    """Update last_used_at timestamp."""
    api_key.last_used_at = func.now()  # type: ignore[assignment]
    await db.commit()
