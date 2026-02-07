"""Agent behavior policy model for governance."""

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class AgentPolicy(TimestampMixin, Base):
    __tablename__ = "agent_policies"

    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, nullable=False, default=1)

    # Policy rules stored as JSONB
    allowed_topics = Column(JSONB, nullable=False, server_default="[]")
    forbidden_topics = Column(JSONB, nullable=False, server_default="[]")
    max_transaction_amount = Column(JSONB, nullable=True)  # {"currency": "USD", "amount": 10000}
    required_disclosures = Column(JSONB, nullable=False, server_default="[]")
    approved_data_sources = Column(JSONB, nullable=False, server_default="[]")
    approved_tools = Column(JSONB, nullable=False, server_default="[]")
    custom_rules = Column(JSONB, nullable=False, server_default="[]")

    # Relationships
    agent = relationship("Agent", back_populates="policies")
    organization = relationship("Organization", back_populates="agent_policies")

    __table_args__ = (
        Index("ix_agent_policies_agent_id_version", "agent_id", "version"),
        Index("ix_agent_policies_org_id", "org_id"),
    )
