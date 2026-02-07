"""Threat intelligence models — attack patterns and indicators."""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class ThreatIndicator(TimestampMixin, Base):
    __tablename__ = "threat_indicators"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,  # null = global (platform-level) indicator
        index=True,
    )
    indicator_type = Column(String(50), nullable=False, index=True)  # injection_pattern, jailbreak, extraction, exfiltration, social_engineering
    name = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    pattern = Column(Text, nullable=True)  # regex or text pattern
    severity = Column(String(20), nullable=False, default="medium")
    confidence = Column(Float, nullable=False, default=0.5)  # 0.0-1.0
    source = Column(String(100), nullable=False, default="agentguard")  # agentguard, community, manual
    hit_count = Column(Integer, nullable=False, server_default="0")
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)  # noqa: F821
    metadata_ = Column("metadata", JSONB, nullable=False, server_default="{}")

    # Relationships
    organization = relationship("Organization", back_populates="threat_indicators")

    __table_args__ = (
        Index("ix_threat_indicators_type_active", "indicator_type", "is_active"),
        Index("ix_threat_indicators_org_type", "org_id", "indicator_type"),
        Index("ix_threat_indicators_severity", "severity"),
    )
