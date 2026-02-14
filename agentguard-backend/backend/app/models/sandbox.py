"""Sandbox model for capability-based agent execution environments."""

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Sandbox(TimestampMixin, Base):
    __tablename__ = "sandboxes"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    image = Column(String(512), nullable=False, default="agentguard/sandbox-base:latest")
    is_active = Column(Boolean, nullable=False, default=True)

    # Capability-based permissions: [{type, target, expires_at}]
    capabilities = Column(JSONB, nullable=False, server_default="[]")

    # Resource constraints: {cpu_shares, memory_mb, max_tokens, timeout_seconds}
    resource_limits = Column(JSONB, nullable=False, server_default="{}")

    # Network policy: {allowed_hosts, allowed_ports, deny_all_egress}
    network_policy = Column(JSONB, nullable=False, server_default="{}")

    # Environment variables (secrets masked in logs)
    environment = Column(JSONB, nullable=False, server_default="{}")

    metadata_ = Column("metadata", JSONB, nullable=False, server_default="{}")

    # Relationships
    organization = relationship("Organization", back_populates="sandboxes")
    agent = relationship("Agent", back_populates="sandboxes")
    executions = relationship(
        "SandboxExecution", back_populates="sandbox", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_sandboxes_org_id_status", "org_id", "status"),
        Index("ix_sandboxes_org_id_agent_id", "org_id", "agent_id"),
    )
