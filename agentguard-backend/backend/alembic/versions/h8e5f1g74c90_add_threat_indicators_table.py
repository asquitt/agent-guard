"""add threat indicators table

Revision ID: h8e5f1g74c90
Revises: g7d4e0f63b89
Create Date: 2026-02-07 13:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "h8e5f1g74c90"
down_revision: str | None = "g7d4e0f63b89"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "threat_indicators",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("indicator_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("pattern", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("source", sa.String(100), nullable=False, server_default="agentguard"),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_threat_indicators_org_id", "threat_indicators", ["org_id"])
    op.create_index("ix_threat_indicators_indicator_type", "threat_indicators", ["indicator_type"])
    op.create_index("ix_threat_indicators_type_active", "threat_indicators", ["indicator_type", "is_active"])
    op.create_index("ix_threat_indicators_org_type", "threat_indicators", ["org_id", "indicator_type"])
    op.create_index("ix_threat_indicators_severity", "threat_indicators", ["severity"])


def downgrade() -> None:
    op.drop_table("threat_indicators")
