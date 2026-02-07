"""Pydantic schemas for SSO configuration and auth flows."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SSOConfigCreate(BaseModel):
    provider_type: str = Field(pattern="^(saml|oidc)$")

    # SAML fields
    saml_entity_id: Optional[str] = None
    saml_sso_url: Optional[str] = None
    saml_x509_cert: Optional[str] = None
    saml_metadata_xml: Optional[str] = None

    # OIDC fields
    oidc_issuer: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_discovery_url: Optional[str] = None


class SSOConfigUpdate(BaseModel):
    enabled: Optional[bool] = None

    # SAML fields
    saml_entity_id: Optional[str] = None
    saml_sso_url: Optional[str] = None
    saml_x509_cert: Optional[str] = None
    saml_metadata_xml: Optional[str] = None

    # OIDC fields
    oidc_issuer: Optional[str] = None
    oidc_client_id: Optional[str] = None
    oidc_client_secret: Optional[str] = None
    oidc_discovery_url: Optional[str] = None


class SSOConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    org_id: UUID = Field(serialization_alias="orgId")
    provider_type: str = Field(serialization_alias="providerType")
    enabled: bool

    # SAML fields
    saml_entity_id: Optional[str] = Field(None, serialization_alias="samlEntityId")
    saml_sso_url: Optional[str] = Field(None, serialization_alias="samlSsoUrl")
    saml_x509_cert: Optional[str] = Field(None, serialization_alias="samlX509Cert")

    # OIDC fields (mask secret)
    oidc_issuer: Optional[str] = Field(None, serialization_alias="oidcIssuer")
    oidc_client_id: Optional[str] = Field(None, serialization_alias="oidcClientId")
    oidc_client_secret_set: bool = Field(False, serialization_alias="oidcClientSecretSet")
    oidc_discovery_url: Optional[str] = Field(None, serialization_alias="oidcDiscoveryUrl")

    created_at: datetime = Field(serialization_alias="createdAt")
    updated_at: datetime = Field(serialization_alias="updatedAt")


class SSOEnforceRequest(BaseModel):
    enforce: bool


class SSOTestResult(BaseModel):
    success: bool
    message: str
