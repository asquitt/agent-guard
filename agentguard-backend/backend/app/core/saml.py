"""SAML 2.0 helper utilities for python3-saml integration."""

import logging
from typing import Any
from xml.etree import ElementTree

from app.core.config import settings
from app.models.sso_config import SSOConfig

logger = logging.getLogger(__name__)

SAML_NS = {
    "md": "urn:oasis:names:tc:SAML:2.0:metadata",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}


def build_saml_settings(sso_config: SSOConfig, org_slug: str) -> dict[str, Any]:
    """Build the settings dict for python3-saml from our SSOConfig model.

    Uses SSO_SP_ENTITY_ID_BASE and SSO_ACS_URL_BASE from app config,
    falling back to FRONTEND_URL-based defaults for local dev.
    """
    sp_entity_id_base = settings.SSO_SP_ENTITY_ID_BASE or f"{settings.FRONTEND_URL}/saml/sp"
    acs_url_base = settings.SSO_ACS_URL_BASE or f"{settings.FRONTEND_URL}/api/v1/auth/saml/acs"

    return {
        "strict": True,
        "debug": settings.DEBUG,
        "sp": {
            "entityId": f"{sp_entity_id_base}/{org_slug}",
            "assertionConsumerService": {
                "url": f"{acs_url_base}/{org_slug}",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
        },
        "idp": {
            "entityId": sso_config.saml_entity_id or "",  # type: ignore[truthy-bool]
            "singleSignOnService": {
                "url": sso_config.saml_sso_url or "",  # type: ignore[truthy-bool]
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": sso_config.saml_x509_cert or "",  # type: ignore[truthy-bool]
        },
        "security": {
            "authnRequestsSigned": False,
            "wantAssertionsSigned": True,
            "wantNameIdEncrypted": False,
            "allowedClockDrift": 60,  # 60s tolerance for clock skew
        },
    }


def parse_saml_metadata_xml(xml_str: str) -> dict[str, str]:
    """Parse IdP metadata XML and extract entity_id, sso_url, x509_cert.

    Returns dict with keys: entity_id, sso_url, x509_cert (any may be empty).
    """
    result: dict[str, str] = {"entity_id": "", "sso_url": "", "x509_cert": ""}

    try:
        root = ElementTree.fromstring(xml_str)  # noqa: S314
    except ElementTree.ParseError:
        logger.warning("Failed to parse SAML metadata XML")
        return result

    # Entity ID from root element
    result["entity_id"] = root.get("entityID", "")

    # SSO URL from SingleSignOnService
    for sso in root.iter(f"{{{SAML_NS['md']}}}SingleSignOnService"):
        binding = sso.get("Binding", "")
        if "HTTP-Redirect" in binding:
            result["sso_url"] = sso.get("Location", "")
            break
    # Fall back to POST binding if no redirect
    if not result["sso_url"]:
        for sso in root.iter(f"{{{SAML_NS['md']}}}SingleSignOnService"):
            result["sso_url"] = sso.get("Location", "")
            break

    # X.509 certificate
    for cert_elem in root.iter(f"{{{SAML_NS['ds']}}}X509Certificate"):
        if cert_elem.text:
            result["x509_cert"] = cert_elem.text.strip()
            break

    return result
