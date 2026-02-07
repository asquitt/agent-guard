"""Human-in-the-loop review queue model."""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class ReviewItem(TimestampMixin, Base):
    __tablename__ = "review_queue"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    proxy_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("proxy_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Review status: pending, approved, rejected, escalated, expired
    status = Column(String(20), nullable=False, default="pending")
    severity = Column(String(20), nullable=False)
    category = Column(String(50), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)

    # Decision tracking
    reviewed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    decision_reason = Column(Text, nullable=True)

    # Escalation
    escalation_level = Column(Integer, nullable=False, server_default="0")
    escalation_deadline = Column(DateTime(timezone=True), nullable=True)

    # Context for reviewer
    context = Column(JSONB, nullable=False, server_default="{}")

    # Relationships
    organization = relationship("Organization", back_populates="review_items")
    incident = relationship("Incident", back_populates="review_items")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    __table_args__ = (
        Index("ix_review_queue_org_status", "org_id", "status"),
        Index("ix_review_queue_org_severity", "org_id", "severity"),
        Index("ix_review_queue_escalation", "org_id", "escalation_deadline"),
    )
