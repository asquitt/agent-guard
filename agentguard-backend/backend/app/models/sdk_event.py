"""SDK event and trace span models for framework integrations."""

import uuid

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class SDKEventRecord(Base):
    """Event captured by an SDK integration (LangChain, etc)."""

    __tablename__ = "sdk_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = Column(String(50), nullable=False, index=True)
    run_id = Column(String(64), nullable=False, default="")
    session_id = Column(String(64), nullable=False, default="", index=True)
    timestamp = Column(BigInteger, nullable=False, default=0)
    payload = Column(JSONB, nullable=False, server_default="{}")
    metadata_ = Column("metadata", JSONB, nullable=False, server_default="{}")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_sdk_events_org_created", "org_id", "created_at"),
        Index("ix_sdk_events_org_session", "org_id", "session_id"),
        Index("ix_sdk_events_org_type", "org_id", "event_type"),
    )


class SDKTraceSpan(Base):
    """OpenTelemetry trace span ingested from SDK exporters."""

    __tablename__ = "sdk_trace_spans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trace_id = Column(String(32), nullable=False, index=True)
    span_id = Column(String(16), nullable=False)
    parent_span_id = Column(String(16), nullable=True)
    name = Column(String(255), nullable=False)
    kind = Column(String(20), nullable=False, default="INTERNAL")
    start_time_ns = Column(BigInteger, nullable=False, default=0)
    end_time_ns = Column(BigInteger, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="UNSET")
    attributes = Column(JSONB, nullable=False, server_default="{}")
    events = Column(JSONB, nullable=False, server_default="[]")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_sdk_traces_org_created", "org_id", "created_at"),
        Index("ix_sdk_traces_trace_id", "trace_id"),
    )
