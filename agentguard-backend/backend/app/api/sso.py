"""SSO configuration and authentication routes."""

# pyright: reportGeneralTypeIssues=false

import logging
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_client_ip, get_current_org, get_db, require_admin
from app.models.user import Organization, User
from app.schemas.sso import (
    SSOConfigCreate,
    SSOConfigResponse,
    SSOConfigUpdate,
    SSOEnforceRequest,
    SSOTestResult,
)
from app.services import auth_service, sso_service

logger = logging.getLogger(__name__)

router = APIRouter()

# ─── Config Management (Admin Only) ──────────────────────────────────────────


@router.post("/config", response_model=SSOConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_sso_config(
    body: SSOConfigCreate,
    org: Organization = Depends(get_current_org),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    client_ip: str = Depends(get_client_ip),
) -> SSOConfigResponse:
    """Create SSO configuration for the current organization."""
    config = await sso_service.create_sso_config(db, UUID(str(org.id)), body, user_id=UUID(str(admin_user.id)), ip_address=client_ip)
    return _to_response(config)


@router.get("/config", response_model=SSOConfigResponse)
async def get_sso_config(
    org: Organization = Depends(get_current_org),
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SSOConfigResponse:
    """Get the active SSO configuration for the current organization."""
    config = await sso_service.get_sso_config(db, UUID(str(org.id)))
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured")
    return _to_response(config)


@router.put("/config/{config_id}", response_model=SSOConfigResponse)
async def update_sso_config(
    config_id: UUID,
    body: SSOConfigUpdate,
    org: Organization = Depends(get_current_org),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    client_ip: str = Depends(get_client_ip),
) -> SSOConfigResponse:
    """Update SSO configuration."""
    config = await sso_service.update_sso_config(db, UUID(str(org.id)), config_id, body, user_id=UUID(str(admin_user.id)), ip_address=client_ip)
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO config not found")
    return _to_response(config)


@router.delete("/config/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sso_config(
    config_id: UUID,
    org: Organization = Depends(get_current_org),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    client_ip: str = Depends(get_client_ip),
) -> None:
    """Delete SSO configuration."""
    deleted = await sso_service.delete_sso_config(db, UUID(str(org.id)), config_id, user_id=UUID(str(admin_user.id)), ip_address=client_ip)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO config not found")


@router.post("/config/test", response_model=SSOTestResult)
async def test_sso_connection(
    org: Organization = Depends(get_current_org),
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SSOTestResult:
    """Test the SSO connection by validating the configuration."""
    config = await sso_service.get_sso_config(db, UUID(str(org.id)))
    if config is None:
        return SSOTestResult(success=False, message="SSO not configured")

    if config.provider_type == "saml":
        # Validate SAML config has required fields
        if not config.saml_entity_id or not config.saml_sso_url:
            return SSOTestResult(success=False, message="SAML entity ID and SSO URL are required")
        if not config.saml_x509_cert:
            return SSOTestResult(success=False, message="IdP X.509 certificate is required")
        return SSOTestResult(success=True, message="SAML configuration is valid")

    if config.provider_type == "oidc":
        if not config.oidc_client_id or not config.oidc_client_secret:
            return SSOTestResult(success=False, message="OIDC client ID and secret are required")
        discovery_url = str(config.oidc_discovery_url or config.oidc_issuer or "")
        if not discovery_url:
            return SSOTestResult(success=False, message="OIDC issuer or discovery URL is required")
        from app.core.oidc import fetch_oidc_discovery

        doc = await fetch_oidc_discovery(discovery_url)
        if doc is None:
            return SSOTestResult(success=False, message="Failed to fetch OIDC discovery document")
        return SSOTestResult(success=True, message="OIDC connection successful")

    return SSOTestResult(success=False, message=f"Unknown provider type: {config.provider_type}")


@router.patch("/enforce")
async def toggle_sso_enforcement(
    body: SSOEnforceRequest,
    org: Organization = Depends(get_current_org),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    client_ip: str = Depends(get_client_ip),
) -> dict:
    """Enable or disable SSO enforcement for the organization."""
    if body.enforce:
        # Verify SSO is configured before enforcing
        config = await sso_service.get_sso_config(db, UUID(str(org.id)))
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Configure SSO before enabling enforcement",
            )
    org = await sso_service.set_sso_enforcement(db, org, body.enforce, user_id=UUID(str(admin_user.id)), ip_address=client_ip)
    return {"sso_enforced": body.enforce}


# ─── SSO Login Flow (Public) ─────────────────────────────────────────────────


@router.get("/check")
async def check_sso_requirement(
    email: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Check if SSO is required for a given email's organization.

    Returns the org slug and SSO status. Used by the frontend login page
    to redirect to SSO when enforcement is active.
    """
    from app.services.auth_service import get_user_by_email

    user = await get_user_by_email(db, email)
    if user is None:
        # Don't reveal whether user exists
        return {"sso_required": False}

    from sqlalchemy import select

    from app.models.user import Organization

    result = await db.execute(select(Organization).where(Organization.id == user.org_id))
    org = result.scalar_one_or_none()
    if org is None:
        return {"sso_required": False}

    org_settings: dict = org.settings or {}  # type: ignore[assignment]
    sso_enforced = org_settings.get("sso_enforced", False)

    if sso_enforced:
        return {"sso_required": True, "org_slug": org.slug}
    return {"sso_required": False}


@router.get("/initiate/{org_slug}")
async def initiate_sso_login(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """SP-initiated SSO login. Redirects user to their IdP.

    For SAML: builds AuthnRequest and redirects to IdP SSO URL.
    For OIDC: redirects to IdP authorization endpoint.
    """
    org = await sso_service.get_org_by_slug(db, org_slug)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    config = await sso_service.get_sso_config(db, UUID(str(org.id)))
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SSO not configured")

    if config.provider_type == "saml":
        return _initiate_saml_login(config, org_slug)

    if config.provider_type == "oidc":
        return await _initiate_oidc_login(config, org_slug)

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown SSO provider type")


@router.post("/saml/acs/{org_slug}")
async def saml_acs(
    org_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """SAML Assertion Consumer Service callback.

    Validates the SAML response, extracts user attributes,
    performs JIT provisioning, issues JWT, and redirects to frontend.
    """
    org = await sso_service.get_org_by_slug(db, org_slug)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    config = await sso_service.get_sso_config(db, UUID(str(org.id)))
    if config is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SSO not configured")

    # Parse form data
    form_data = await request.form()
    saml_response = form_data.get("SAMLResponse", "")
    if not saml_response:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing SAMLResponse")

    # Validate SAML response using python3-saml
    from onelogin.saml2.auth import OneLogin_Saml2_Auth

    from app.core.saml import build_saml_settings

    saml_settings = build_saml_settings(config, org_slug)
    request_data = _build_saml_request_data(request, str(saml_response))
    auth = OneLogin_Saml2_Auth(request_data, saml_settings)
    auth.process_response()

    errors = auth.get_errors()
    if errors:
        logger.error("SAML validation errors for org %s: %s", org_slug, errors)
        return _redirect_with_error(f"SAML validation failed: {', '.join(errors)}")

    if not auth.is_authenticated():
        return _redirect_with_error("SAML authentication failed")

    # Extract attributes
    attrs = auth.get_attributes()
    name_id = str(auth.get_nameid() or "")
    email = str(attrs.get("email", [name_id])[0]) if attrs.get("email") else name_id
    full_name = ""
    if attrs.get("firstName"):
        full_name = attrs["firstName"][0]
        if attrs.get("lastName"):
            full_name += f" {attrs['lastName'][0]}"
    elif attrs.get("displayName"):
        full_name = attrs["displayName"][0]

    # JIT provision and issue tokens
    user = await sso_service.find_or_create_sso_user(
        db, UUID(str(org.id)), email, full_name, "saml", name_id
    )
    access, refresh = auth_service.create_token_pair(UUID(str(user.id)))

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/sso/callback?token={access}&refresh={refresh}",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/oidc/callback/{org_slug}")
async def oidc_callback(
    org_slug: str,
    code: str = "",
    state: str = "",
    error: str = "",
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """OIDC authorization code callback.

    Exchanges the code for tokens, fetches user info,
    performs JIT provisioning, and redirects to frontend.
    """
    if error:
        return _redirect_with_error(f"OIDC error: {error}")
    if not code:
        return _redirect_with_error("Missing authorization code")

    org = await sso_service.get_org_by_slug(db, org_slug)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    config = await sso_service.get_sso_config(db, UUID(str(org.id)))
    if config is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SSO not configured")

    from app.core.oidc import exchange_code_for_tokens, fetch_oidc_discovery, fetch_userinfo

    discovery_url = str(config.oidc_discovery_url or config.oidc_issuer or "")
    discovery = await fetch_oidc_discovery(discovery_url)
    if discovery is None:
        return _redirect_with_error("Failed to fetch OIDC provider configuration")

    token_resp = await exchange_code_for_tokens(config, discovery, code, org_slug)
    if token_resp is None:
        return _redirect_with_error("Failed to exchange authorization code")

    access_token = token_resp.get("access_token", "")
    userinfo = await fetch_userinfo(discovery, access_token)
    if userinfo is None:
        return _redirect_with_error("Failed to fetch user information")

    email = userinfo.get("email", "")
    if not email:
        return _redirect_with_error("Email not provided by identity provider")

    full_name = userinfo.get("name", "")
    external_id = userinfo.get("sub", email)

    user = await sso_service.find_or_create_sso_user(
        db, UUID(str(org.id)), email, full_name, "oidc", external_id
    )
    ag_access, ag_refresh = auth_service.create_token_pair(UUID(str(user.id)))

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/sso/callback?token={ag_access}&refresh={ag_refresh}",
        status_code=status.HTTP_302_FOUND,
    )


@router.get("/saml/metadata/{org_slug}")
async def saml_metadata(
    org_slug: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Return SP metadata XML for IdP configuration."""
    org = await sso_service.get_org_by_slug(db, org_slug)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    config = await sso_service.get_sso_config(db, UUID(str(org.id)))

    from app.core.saml import build_saml_settings

    # Build settings (use config if available, otherwise create minimal SP metadata)
    if config and config.provider_type == "saml":
        saml_settings = build_saml_settings(config, org_slug)
    else:
        # Return basic SP metadata even if no IdP configured yet
        from app.models.sso_config import SSOConfig

        stub = SSOConfig()  # type: ignore[call-arg]
        saml_settings = build_saml_settings(stub, org_slug)

    from onelogin.saml2.settings import OneLogin_Saml2_Settings

    sp_settings = OneLogin_Saml2_Settings(saml_settings, sp_validation_only=True)
    metadata = sp_settings.get_sp_metadata()
    errors = sp_settings.validate_metadata(metadata)
    if errors:
        logger.warning("SP metadata validation errors: %s", errors)

    return Response(content=metadata, media_type="application/xml")


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _to_response(config) -> SSOConfigResponse:  # type: ignore[no-untyped-def]
    """Convert SSOConfig model to response schema, masking secrets."""
    return SSOConfigResponse(
        id=config.id,
        org_id=config.org_id,
        provider_type=config.provider_type,
        enabled=config.enabled,
        saml_entity_id=config.saml_entity_id,
        saml_sso_url=config.saml_sso_url,
        saml_x509_cert=config.saml_x509_cert,
        oidc_issuer=config.oidc_issuer,
        oidc_client_id=config.oidc_client_id,
        oidc_client_secret_set=bool(config.oidc_client_secret),
        oidc_discovery_url=config.oidc_discovery_url,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


def _build_saml_request_data(request: Request, saml_response: str) -> dict:
    """Build the request dict that python3-saml expects."""
    return {
        "https": "on" if request.url.scheme == "https" else "off",
        "http_host": request.url.hostname or "localhost",
        "server_port": request.url.port or (443 if request.url.scheme == "https" else 80),
        "script_name": str(request.url.path),
        "post_data": {"SAMLResponse": saml_response},
    }


def _redirect_with_error(message: str) -> RedirectResponse:
    """Redirect to frontend with an error message."""
    from urllib.parse import quote

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/sso/callback?error={quote(message)}",
        status_code=status.HTTP_302_FOUND,
    )


def _initiate_saml_login(config, org_slug: str) -> RedirectResponse:  # type: ignore[no-untyped-def]
    """Build SAML AuthnRequest and redirect to IdP."""
    from onelogin.saml2.auth import OneLogin_Saml2_Auth

    from app.core.saml import build_saml_settings

    saml_settings = build_saml_settings(config, org_slug)
    # Use a minimal request data dict for redirect binding
    request_data = {
        "https": "on",
        "http_host": "localhost",
        "server_port": 443,
        "script_name": f"/api/v1/auth/sso/initiate/{org_slug}",
    }
    auth = OneLogin_Saml2_Auth(request_data, saml_settings)
    redirect_url = auth.login()
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)


async def _initiate_oidc_login(config, org_slug: str) -> RedirectResponse:  # type: ignore[no-untyped-def]
    """Build OIDC authorization URL and redirect to IdP."""
    from app.core.oidc import build_authorization_url, fetch_oidc_discovery

    discovery_url = str(config.oidc_discovery_url or config.oidc_issuer or "")
    discovery = await fetch_oidc_discovery(discovery_url)
    if discovery is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach OIDC provider",
        )

    state = secrets.token_urlsafe(32)
    redirect_url = build_authorization_url(config, discovery, org_slug, state)
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
