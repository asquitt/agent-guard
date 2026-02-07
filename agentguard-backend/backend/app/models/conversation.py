"""Conversation tracking models for multi-turn analysis."""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id = Column(String(255), nullable=False, index=True)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status = Column(String(20), nullable=False, default="active")  # active, completed, escalated, flagged
    risk_score = Column(Float, nullable=False, default=0.0)
    risk_level = Column(String(20), nullable=False, default="low")  # low, medium, high, critical
    turn_count = Column(Integer, nullable=False, server_default="0")
    total_tokens = Column(Integer, nullable=False, server_default="0")
    total_cost_usd = Column(Float, nullable=False, default=0.0)
    escalated_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=False, server_default="{}")

    # Relationships
    organization = relationship("Organization", back_populates="conversations")
    agent = relationship("Agent", back_populates="conversations")
    turns = relationship("ConversationTurn", back_populates="conversation", order_by="ConversationTurn.turn_number")

    __table_args__ = (
        Index("ix_conversations_org_session", "org_id", "session_id"),
        Index("ix_conversations_org_status", "org_id", "status"),
        Index("ix_conversations_org_risk", "org_id", "risk_level"),
        Index("ix_conversations_org_created", "org_id", "created_at"),
    )


class ConversationTurn(TimestampMixin, Base):
    __tablename__ = "conversation_turns"

    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    proxy_request_id = Column(
        UUID(as_uuid=True),
        ForeignKey("proxy_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    turn_number = Column(Integer, nullable=False)
    role = Column(String(20), nullable=False, default="user")  # user, assistant, system
    content_preview = Column(Text, nullable=True)  # First 500 chars for quick display
    risk_delta = Column(Float, nullable=False, default=0.0)
    cumulative_risk = Column(Float, nullable=False, default=0.0)
    detections = Column(JSONB, nullable=False, server_default="[]")  # [{category, severity, title}]
    tokens = Column(Integer, nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="turns")
    proxy_request = relationship("ProxyRequest")

    __table_args__ = (
        Index("ix_conversation_turns_conv_turn", "conversation_id", "turn_number"),
    )
