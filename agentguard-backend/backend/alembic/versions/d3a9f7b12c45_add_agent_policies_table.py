"""add agent_policies table

Revision ID: d3a9f7b12c45
Revises: c4e92f1b8a7d
Create Date: 2026-02-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d3a9f7b12c45"
down_revision = "c4e92f1b8a7d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("allowed_topics", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("forbidden_topics", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("max_transaction_amount", postgresql.JSONB(), nullable=True),
        sa.Column("required_disclosures", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("approved_data_sources", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("approved_tools", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("custom_rules", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_policies_agent_id", "agent_policies", ["agent_id"])
    op.create_index("ix_agent_policies_org_id", "agent_policies", ["org_id"])
    op.create_index(
        "ix_agent_policies_agent_id_version",
        "agent_policies",
        ["agent_id", "version"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_policies_agent_id_version", table_name="agent_policies")
    op.drop_index("ix_agent_policies_org_id", table_name="agent_policies")
    op.drop_index("ix_agent_policies_agent_id", table_name="agent_policies")
    op.drop_table("agent_policies")
