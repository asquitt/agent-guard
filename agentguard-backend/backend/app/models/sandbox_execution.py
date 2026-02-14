"""Sandbox execution model for tracking ephemeral container runs."""

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class SandboxExecution(TimestampMixin, Base):
    __tablename__ = "sandbox_executions"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sandbox_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sandboxes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(20), nullable=False, default="pending")
    container_id = Column(String(128), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    exit_code = Column(Integer, nullable=True)
    trigger = Column(String(20), nullable=False, default="api")
    error_message = Column(Text, nullable=True)

    # Resource usage: {cpu_seconds, memory_peak_mb, tokens_used, network_bytes}
    resource_usage = Column(JSONB, nullable=False, server_default="{}")

    # Relationships
    organization = relationship("Organization")
    sandbox = relationship("Sandbox", back_populates="executions")
    audit_logs = relationship(
        "SandboxAuditLog", back_populates="execution", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_sandbox_executions_org_id_status", "org_id", "status"),
        Index("ix_sandbox_executions_sandbox_id_status", "sandbox_id", "status"),
    )
