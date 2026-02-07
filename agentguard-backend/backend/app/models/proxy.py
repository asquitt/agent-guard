"""Proxy endpoint and request models."""

from sqlalchemy import Boolean, Column, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import Environment


class ProxyEndpoint(TimestampMixin, Base):
    __tablename__ = "proxy_endpoints"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    provider = Column(String(50), nullable=False)
    target_url = Column(String(2048), nullable=False)
    environment = Column(String(20), nullable=False, default=Environment.PRODUCTION.value)
    is_active = Column(Boolean, nullable=False, default=True)
    config = Column(JSONB, nullable=False, server_default="{}")

    # Relationships
    organization = relationship("Organization", back_populates="proxy_endpoints")
    proxy_requests = relationship("ProxyRequest", back_populates="endpoint")

    __table_args__ = (Index("ix_proxy_endpoints_org_id_is_active", "org_id", "is_active"),)


class ProxyRequest(TimestampMixin, Base):
    __tablename__ = "proxy_requests"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint_id = Column(
        UUID(as_uuid=True),
        ForeignKey("proxy_endpoints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    method = Column(String(10), nullable=False, default="POST")
    path = Column(String(2048), nullable=False)
    request_body = Column(Text, nullable=True)
    response_body = Column(Text, nullable=True)
    status_code = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    model = Column(String(255), nullable=True)
    cost_usd = Column(Float, nullable=True)

    # Relationships
    endpoint = relationship("ProxyEndpoint", back_populates="proxy_requests")
    incidents = relationship("Incident", back_populates="proxy_request")

    __table_args__ = (
        Index("ix_proxy_requests_org_id_created_at", "org_id", "created_at"),
        Index("ix_proxy_requests_org_id_model", "org_id", "model"),
        Index("ix_proxy_requests_org_id_endpoint_id", "org_id", "endpoint_id"),
    )
