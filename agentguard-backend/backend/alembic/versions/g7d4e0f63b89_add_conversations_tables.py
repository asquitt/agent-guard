"""add conversations tables

Revision ID: g7d4e0f63b89
Revises: f6c3d9e52a78
Create Date: 2026-02-07 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "g7d4e0f63b89"
down_revision: str | None = "f6c3d9e52a78"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.String(255), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="low"),
        sa.Column("turn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_conversations_org_id", "conversations", ["org_id"])
    op.create_index("ix_conversations_session_id", "conversations", ["session_id"])
    op.create_index("ix_conversations_agent_id", "conversations", ["agent_id"])
    op.create_index("ix_conversations_org_session", "conversations", ["org_id", "session_id"])
    op.create_index("ix_conversations_org_status", "conversations", ["org_id", "status"])
    op.create_index("ix_conversations_org_risk", "conversations", ["org_id", "risk_level"])
    op.create_index("ix_conversations_org_created", "conversations", ["org_id", "created_at"])

    op.create_table(
        "conversation_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("proxy_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("content_preview", sa.Text(), nullable=True),
        sa.Column("risk_delta", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cumulative_risk", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("detections", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("tokens", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proxy_request_id"], ["proxy_requests.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_conversation_turns_conversation_id", "conversation_turns", ["conversation_id"])
    op.create_index("ix_conversation_turns_proxy_request_id", "conversation_turns", ["proxy_request_id"])
    op.create_index("ix_conversation_turns_conv_turn", "conversation_turns", ["conversation_id", "turn_number"])


def downgrade() -> None:
    op.drop_table("conversation_turns")
    op.drop_table("conversations")
