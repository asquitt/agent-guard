"""add sdk_events and sdk_trace_spans tables

Revision ID: a1b2c3d4e5f6
Revises: 8822459aa6a2
Create Date: 2026-02-14 11:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "8822459aa6a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sdk_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("run_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("session_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("timestamp", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_sdk_events_org_id", "sdk_events", ["org_id"])
    op.create_index("ix_sdk_events_event_type", "sdk_events", ["event_type"])
    op.create_index("ix_sdk_events_session_id", "sdk_events", ["session_id"])
    op.create_index(
        "ix_sdk_events_org_created", "sdk_events", ["org_id", "created_at"]
    )
    op.create_index(
        "ix_sdk_events_org_session", "sdk_events", ["org_id", "session_id"]
    )
    op.create_index(
        "ix_sdk_events_org_type", "sdk_events", ["org_id", "event_type"]
    )

    op.create_table(
        "sdk_trace_spans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trace_id", sa.String(32), nullable=False),
        sa.Column("span_id", sa.String(16), nullable=False),
        sa.Column("parent_span_id", sa.String(16), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="INTERNAL"),
        sa.Column("start_time_ns", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("end_time_ns", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="UNSET"),
        sa.Column("attributes", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("events", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["org_id"], ["organizations.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_sdk_trace_spans_org_id", "sdk_trace_spans", ["org_id"])
    op.create_index("ix_sdk_trace_spans_trace_id", "sdk_trace_spans", ["trace_id"])
    op.create_index(
        "ix_sdk_traces_org_created", "sdk_trace_spans", ["org_id", "created_at"]
    )
    op.create_index(
        "ix_sdk_traces_trace_id", "sdk_trace_spans", ["trace_id"]
    )


def downgrade() -> None:
    op.drop_table("sdk_trace_spans")
    op.drop_table("sdk_events")
