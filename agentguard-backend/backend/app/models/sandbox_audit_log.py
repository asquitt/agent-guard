"""Sandbox audit log model for immutable action tracking with hash chain."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class SandboxAuditLog(TimestampMixin, Base):
    __tablename__ = "sandbox_audit_logs"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sandbox_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type = Column(String(30), nullable=False)
    action_detail = Column(JSONB, nullable=False, server_default="{}")
    allowed = Column(Boolean, nullable=False)
    capability_matched = Column(String(255), nullable=True)
    entry_hash = Column(String(64), nullable=True)
    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    execution = relationship("SandboxExecution", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_sandbox_audit_logs_execution_id_ts", "execution_id", "timestamp"),
        Index("ix_sandbox_audit_logs_org_id_action_type", "org_id", "action_type"),
    )
