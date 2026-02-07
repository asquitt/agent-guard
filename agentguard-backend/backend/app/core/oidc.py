"""OIDC helper utilities for authlib integration."""

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.models.sso_config import SSOConfig

logger = logging.getLogger(__name__)


def build_oidc_redirect_uri(org_slug: str) -> str:
    """Build the OIDC redirect URI for a given org slug."""
    base = settings.SSO_OIDC_REDIRECT_URI_BASE or f"{settings.FRONTEND_URL}/api/v1/auth/oidc/callback"
    return f"{base}/{org_slug}"


async def fetch_oidc_discovery(issuer_or_discovery_url: str) -> dict[str, Any] | None:
    """Fetch the OIDC discovery document from the issuer's well-known endpoint.

    Accepts either an issuer URL or a direct discovery URL.
    Returns the parsed JSON document, or None on failure.
    """
    url = issuer_or_discovery_url
    if not url.endswith("/.well-known/openid-configuration"):
        url = url.rstrip("/") + "/.well-known/openid-configuration"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("Failed to fetch OIDC discovery from %s: %s", url, e)
        return None


def build_authorization_url(
    sso_config: SSOConfig,
    discovery: dict[str, Any],
    org_slug: str,
    state: str,
) -> str:
    """Build the OIDC authorization URL to redirect the user to the IdP."""
    auth_endpoint = discovery.get("authorization_endpoint", "")
    redirect_uri = build_oidc_redirect_uri(org_slug)

    params = {
        "response_type": "code",
        "client_id": sso_config.oidc_client_id or "",  # type: ignore[truthy-bool]
        "redirect_uri": redirect_uri,
        "scope": "openid email profile",
        "state": state,
    }
    from urllib.parse import urlencode

    return f"{auth_endpoint}?{urlencode(params)}"


async def exchange_code_for_tokens(
    sso_config: SSOConfig,
    discovery: dict[str, Any],
    code: str,
    org_slug: str,
) -> dict[str, Any] | None:
    """Exchange an authorization code for tokens at the IdP's token endpoint.

    Returns the token response JSON (includes id_token, access_token), or None on failure.
    """
    token_endpoint = discovery.get("token_endpoint", "")
    redirect_uri = build_oidc_redirect_uri(org_slug)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": sso_config.oidc_client_id or "",  # type: ignore[truthy-bool]
                    "client_secret": sso_config.oidc_client_secret or "",  # type: ignore[truthy-bool]
                },
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.error("OIDC token exchange failed: %s", e)
        return None


async def fetch_userinfo(
    discovery: dict[str, Any], access_token: str
) -> dict[str, Any] | None:
    """Fetch user info from the OIDC userinfo endpoint."""
    userinfo_endpoint = discovery.get("userinfo_endpoint", "")
    if not userinfo_endpoint:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("Failed to fetch userinfo: %s", e)
        return None
