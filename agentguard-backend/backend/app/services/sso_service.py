"""SSO service layer — config CRUD, JIT user provisioning, org lookup."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole
from app.models.sso_config import SSOConfig
from app.models.user import Organization, User
from app.schemas.sso import SSOConfigCreate, SSOConfigUpdate

logger = logging.getLogger(__name__)


async def get_org_by_slug(db: AsyncSession, slug: str) -> Organization | None:
    """Look up an organization by its slug."""
    result = await db.execute(select(Organization).where(Organization.slug == slug))
    return result.scalar_one_or_none()


async def get_sso_config(db: AsyncSession, org_id: UUID) -> SSOConfig | None:
    """Get the SSO config for an organization."""
    result = await db.execute(
        select(SSOConfig).where(SSOConfig.org_id == org_id, SSOConfig.enabled.is_(True))
    )
    return result.scalar_one_or_none()


async def get_sso_config_by_id(db: AsyncSession, org_id: UUID, config_id: UUID) -> SSOConfig | None:
    """Get a specific SSO config by ID, scoped to org."""
    result = await db.execute(
        select(SSOConfig).where(SSOConfig.id == config_id, SSOConfig.org_id == org_id)
    )
    return result.scalar_one_or_none()


async def create_sso_config(
    db: AsyncSession, org_id: UUID, data: SSOConfigCreate
) -> SSOConfig:
    """Create an SSO config for an organization.

    Disables any existing config for the same org first.
    """
    # Disable existing configs for this org
    existing = await db.execute(
        select(SSOConfig).where(SSOConfig.org_id == org_id)
    )
    for config in existing.scalars().all():
        config.enabled = False  # type: ignore[assignment]

    sso_config = SSOConfig(  # type: ignore[call-arg]
        org_id=org_id,
        provider_type=data.provider_type,
        enabled=True,
        saml_entity_id=data.saml_entity_id,
        saml_sso_url=data.saml_sso_url,
        saml_x509_cert=data.saml_x509_cert,
        saml_metadata_xml=data.saml_metadata_xml,
        oidc_issuer=data.oidc_issuer,
        oidc_client_id=data.oidc_client_id,
        oidc_client_secret=data.oidc_client_secret,
        oidc_discovery_url=data.oidc_discovery_url,
    )
    db.add(sso_config)
    await db.commit()
    await db.refresh(sso_config)
    return sso_config


async def update_sso_config(
    db: AsyncSession, org_id: UUID, config_id: UUID, data: SSOConfigUpdate
) -> SSOConfig | None:
    """Update an SSO config, scoped to org."""
    config = await get_sso_config_by_id(db, org_id, config_id)
    if config is None:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    return config


async def delete_sso_config(db: AsyncSession, org_id: UUID, config_id: UUID) -> bool:
    """Delete an SSO config, scoped to org."""
    config = await get_sso_config_by_id(db, org_id, config_id)
    if config is None:
        return False

    await db.delete(config)
    await db.commit()
    return True


async def find_or_create_sso_user(
    db: AsyncSession,
    org_id: UUID,
    email: str,
    full_name: str,
    provider: str,
    external_id: str,
) -> User:
    """JIT provisioning: find existing user or create new one for SSO login.

    If user exists with same email in the org, link SSO identity.
    If no user exists, create with role=MEMBER and no password.
    """
    # Look for existing user by SSO external ID
    result = await db.execute(
        select(User).where(
            User.sso_provider == provider,
            User.sso_external_id == external_id,
            User.org_id == org_id,
        )
    )
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    # Look for existing user by email in the same org
    result = await db.execute(
        select(User).where(User.email == email, User.org_id == org_id)
    )
    user = result.scalar_one_or_none()
    if user is not None:
        # Link SSO identity to existing account
        user.sso_provider = provider  # type: ignore[assignment]
        user.sso_external_id = external_id  # type: ignore[assignment]
        await db.commit()
        await db.refresh(user)
        logger.info("Linked SSO identity to existing user %s", user.id)
        return user

    # Create new user via JIT provisioning
    user = User(  # type: ignore[call-arg]
        email=email,
        full_name=full_name or email.split("@")[0],
        role=UserRole.MEMBER.value,
        org_id=org_id,
        is_active=True,
        hashed_password=None,
        sso_provider=provider,
        sso_external_id=external_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("JIT provisioned new SSO user %s for org %s", user.id, org_id)
    return user


async def set_sso_enforcement(db: AsyncSession, org: Organization, enforce: bool) -> Organization:
    """Toggle SSO enforcement for an organization."""
    current_settings: dict = dict(org.settings) if org.settings else {}  # type: ignore[arg-type]
    current_settings["sso_enforced"] = enforce
    org.settings = current_settings  # type: ignore[assignment]
    await db.commit()
    await db.refresh(org)
    return org
