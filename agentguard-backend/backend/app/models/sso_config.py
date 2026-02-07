"""SSO configuration model for SAML and OIDC providers."""

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class SSOConfig(TimestampMixin, Base):
    __tablename__ = "sso_configs"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_type = Column(String(20), nullable=False)  # "saml" or "oidc"
    enabled = Column(Boolean, nullable=False, default=True)

    # SAML fields
    saml_entity_id = Column(String(500), nullable=True)
    saml_sso_url = Column(String(500), nullable=True)
    saml_x509_cert = Column(Text, nullable=True)
    saml_metadata_xml = Column(Text, nullable=True)

    # OIDC fields
    oidc_issuer = Column(String(500), nullable=True)
    oidc_client_id = Column(String(255), nullable=True)
    oidc_client_secret = Column(String(255), nullable=True)
    oidc_discovery_url = Column(String(500), nullable=True)

    # Relationships
    organization = relationship("Organization", backref="sso_configs")

    __table_args__ = (
        Index("ix_sso_configs_org_provider", "org_id", "provider_type"),
    )
