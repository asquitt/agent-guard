"""User, Organization, and ApiKey models."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import PlanTier, UserRole


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"

    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    plan_tier = Column(String(50), nullable=False, default=PlanTier.STARTER.value)
    stripe_customer_id = Column(String(255), nullable=True, unique=True)
    settings = Column(JSONB, nullable=False, server_default="{}")

    # Relationships
    users = relationship("User", back_populates="organization")
    api_keys = relationship("ApiKey", back_populates="organization")
    proxy_endpoints = relationship("ProxyEndpoint", back_populates="organization")
    incidents = relationship("Incident", back_populates="organization")
    detectors = relationship("Detector", back_populates="organization")
    alert_destinations = relationship("AlertDestination", back_populates="organization")
    audit_logs = relationship("AuditLog", back_populates="organization")


class User(TimestampMixin, Base):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.MEMBER.value)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    incident_actions = relationship("IncidentAction", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

    __table_args__ = (
        Index("ix_users_org_id_email", "org_id", "email"),
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
    is_active = Column(Boolean, nullable=False, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="api_keys")

    __table_args__ = (
        Index("ix_api_keys_prefix", "prefix"),
        Index("ix_api_keys_org_id_is_active", "org_id", "is_active"),
    )
