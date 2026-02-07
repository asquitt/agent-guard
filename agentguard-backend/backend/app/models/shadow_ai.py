"""Shadow AI discovery model for tracking unauthorized AI usage."""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class ShadowAIDiscovery(TimestampMixin, Base):
    __tablename__ = "shadow_ai_discoveries"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Discovered provider info
    provider = Column(String(100), nullable=False)  # openai, anthropic, etc.
    endpoint = Column(String(500), nullable=False)  # api.openai.com/v1/chat/completions
    department = Column(String(255), nullable=True)
    source_ip = Column(String(50), nullable=True)

    # Classification
    risk_level = Column(String(20), nullable=False, default="medium")  # low, medium, high, critical
    status = Column(String(20), nullable=False, default="discovered")  # discovered, monitored, blocked, approved

    # Usage stats
    request_count = Column(Integer, nullable=False, server_default="1")
    first_seen_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=False)

    # Additional metadata
    metadata_ = Column("metadata", JSONB, nullable=False, server_default="{}")

    # Relationships
    organization = relationship("Organization", back_populates="shadow_discoveries")

    __table_args__ = (
        Index("ix_shadow_ai_org_provider", "org_id", "provider"),
        Index("ix_shadow_ai_org_status", "org_id", "status"),
        Index("ix_shadow_ai_org_risk", "org_id", "risk_level"),
    )
