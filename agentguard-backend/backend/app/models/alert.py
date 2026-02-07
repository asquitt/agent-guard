"""Alert and alert destination models."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import AlertStatus


class AlertDestination(TimestampMixin, Base):
    __tablename__ = "alert_destinations"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    destination_type = Column(String(50), nullable=False)
    config = Column(JSONB, nullable=False, server_default="{}")
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    organization = relationship("Organization", back_populates="alert_destinations")
    alerts = relationship("Alert", back_populates="destination")

    __table_args__ = (Index("ix_alert_destinations_org_id_is_active", "org_id", "is_active"),)


class Alert(TimestampMixin, Base):
    __tablename__ = "alerts"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    incident_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    destination_id = Column(
        UUID(as_uuid=True),
        ForeignKey("alert_destinations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(50), nullable=False, default=AlertStatus.PENDING.value)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    incident = relationship("Incident", back_populates="alerts")
    destination = relationship("AlertDestination", back_populates="alerts")

    __table_args__ = (
        Index("ix_alerts_org_id_status", "org_id", "status"),
        Index("ix_alerts_incident_id_status", "incident_id", "status"),
    )
