"""Incident and incident action models."""

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import IncidentStatus


class Incident(TimestampMixin, Base):
    __tablename__ = "incidents"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proxy_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("proxy_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    detector_id = Column(
        UUID(as_uuid=True),
        ForeignKey("detectors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    sandbox_execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sandbox_executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    severity = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default=IncidentStatus.OPEN.value)
    action_taken = Column(String(50), nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=False, server_default="{}")
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization = relationship("Organization", back_populates="incidents")
    proxy_request = relationship("ProxyRequest", back_populates="incidents")
    detector = relationship("Detector", back_populates="incidents")
    sandbox_execution = relationship("SandboxExecution", back_populates="incidents")
    actions = relationship("IncidentAction", back_populates="incident")
    alerts = relationship("Alert", back_populates="incident")
    review_items = relationship("ReviewItem", back_populates="incident")

    __table_args__ = (
        Index("ix_incidents_org_id_status", "org_id", "status"),
        Index("ix_incidents_org_id_severity", "org_id", "severity"),
        Index("ix_incidents_org_id_category", "org_id", "category"),
        Index("ix_incidents_org_id_created_at", "org_id", "created_at"),
    )


class IncidentAction(TimestampMixin, Base):
    __tablename__ = "incident_actions"

    incident_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action_type = Column(String(50), nullable=False)
    details = Column(JSONB, nullable=False, server_default="{}")

    # Relationships
    incident = relationship("Incident", back_populates="actions")
    user = relationship("User", back_populates="incident_actions")

    __table_args__ = (
        Index(
            "ix_incident_actions_incident_id_created_at",
            "incident_id",
            "created_at",
        ),
    )
