"""Compliance report model for async report generation."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ComplianceReport(Base):
    """Tracks compliance report generation requests and results."""

    __tablename__ = "compliance_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    report_type = Column(String(50), nullable=False)  # access_audit, incident_summary, etc.
    status = Column(String(20), nullable=False, default="pending")  # pending/generating/completed/failed
    date_from = Column(DateTime(timezone=True), nullable=False)
    date_to = Column(DateTime(timezone=True), nullable=False)
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization")

    __table_args__ = (
        Index("ix_compliance_reports_org_created", "org_id", "created_at"),
    )
