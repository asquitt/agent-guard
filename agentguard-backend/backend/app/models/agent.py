"""Agent registry model for governance and inventory."""

from sqlalchemy import Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Agent(TimestampMixin, Base):
    __tablename__ = "agents"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner = Column(String(255), nullable=True)
    risk_tier = Column(String(20), nullable=False, default="medium")
    status = Column(String(20), nullable=False, default="draft")
    provider = Column(String(50), nullable=True)
    model = Column(String(255), nullable=True)
    frameworks = Column(ARRAY(String), nullable=False, server_default="{}")
    tags = Column(ARRAY(String), nullable=False, server_default="{}")
    metadata_ = Column("metadata", JSONB, nullable=False, server_default="{}")

    # Relationships
    organization = relationship("Organization", back_populates="agents")
    policies = relationship("AgentPolicy", back_populates="agent", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_agents_org_id_status", "org_id", "status"),
        Index("ix_agents_org_id_risk_tier", "org_id", "risk_tier"),
    )
