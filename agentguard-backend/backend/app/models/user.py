"""User, Organization, and ApiKey models."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import Environment, PlanTier, UserRole


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    plan_tier = Column(String(50), nullable=False, default=PlanTier.STARTER.value)
    stripe_customer_id = Column(String(255), nullable=True, unique=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True)
    subscription_status = Column(String(50), nullable=True)
    subscription_current_period_end = Column(DateTime(timezone=True), nullable=True)
    monthly_request_count = Column(Integer, nullable=False, server_default="0")
    settings = Column(JSONB, nullable=False, server_default="{}")

    # Relationships
    users = relationship("User", back_populates="organization")
    api_keys = relationship("ApiKey", back_populates="organization")
    proxy_endpoints = relationship("ProxyEndpoint", back_populates="organization")
    incidents = relationship("Incident", back_populates="organization")
    detectors = relationship("Detector", back_populates="organization")
    alert_destinations = relationship("AlertDestination", back_populates="organization")
    audit_logs = relationship("AuditLog", back_populates="organization")
    agents = relationship("Agent", back_populates="organization")
    agent_policies = relationship("AgentPolicy", back_populates="organization")
    review_items = relationship("ReviewItem", back_populates="organization")
    shadow_discoveries = relationship("ShadowAIDiscovery", back_populates="organization")
    conversations = relationship("Conversation", back_populates="organization")
    threat_indicators = relationship("ThreatIndicator", back_populates="organization")
    red_team_runs = relationship("RedTeamRun", back_populates="organization")
    sandboxes = relationship("Sandbox", back_populates="organization")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for SSO-only users
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.MEMBER.value)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, default=True)
    sso_provider = Column(String(50), nullable=True)  # e.g. "saml", "oidc"
    sso_external_id = Column(String(255), nullable=True)  # IdP user ID

    # Security hardening
    failed_login_attempts = Column(Integer, nullable=False, server_default="0")
    locked_until = Column(DateTime(timezone=True), nullable=True)
    token_version = Column(Integer, nullable=False, server_default="0")
    password_changed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    incident_actions = relationship("IncidentAction", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

    __table_args__ = (
        Index("ix_users_org_id_email", "org_id", "email"),
        Index("ix_users_sso_lookup", "sso_provider", "sso_external_id"),
    )


class ApiKey(TimestampMixin, Base):
    __tablename__ = "api_keys"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_hash = Column(String(255), nullable=False, unique=True)
    prefix = Column(String(20), nullable=False)
    name = Column(String(255), nullable=False)
    scopes = Column(JSONB, nullable=False, server_default='["proxy"]')
    environment = Column(String(20), nullable=False, default=Environment.PRODUCTION.value)
    is_active = Column(Boolean, nullable=False, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="api_keys")

    __table_args__ = (
        Index("ix_api_keys_prefix", "prefix"),
        Index("ix_api_keys_org_id_is_active", "org_id", "is_active"),
    )
