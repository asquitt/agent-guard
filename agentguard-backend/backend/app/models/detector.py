"""Detector and detector rule models."""

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin
from app.models.enums import ActionMode


class Detector(TimestampMixin, Base):
    __tablename__ = "detectors"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    action_mode = Column(
        String(50), nullable=False, default=ActionMode.MONITOR.value
    )
    config = Column(JSONB, nullable=False, server_default="{}")

    # Relationships
    organization = relationship("Organization", back_populates="detectors")
    rules = relationship(
        "DetectorRule", back_populates="detector", cascade="all, delete-orphan"
    )
    incidents = relationship("Incident", back_populates="detector")

    __table_args__ = (
        Index("ix_detectors_org_id_is_active", "org_id", "is_active"),
        Index("ix_detectors_org_id_category", "org_id", "category"),
    )


class DetectorRule(TimestampMixin, Base):
    __tablename__ = "detector_rules"

    detector_id = Column(
        UUID(as_uuid=True),
        ForeignKey("detectors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    rule_type = Column(String(50), nullable=False)
    parameters = Column(JSONB, nullable=False, server_default="{}")
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    detector = relationship("Detector", back_populates="rules")
