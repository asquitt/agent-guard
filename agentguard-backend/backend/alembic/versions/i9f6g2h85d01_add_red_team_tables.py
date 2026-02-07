"""add red team tables

Revision ID: i9f6g2h85d01
Revises: h8e5f1g74c90
Create Date: 2026-02-07 14:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "i9f6g2h85d01"
down_revision: str | None = "h8e5f1g74c90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "red_team_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("test_categories", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("total_tests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_tests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_tests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("resilience_score", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["endpoint_id"], ["proxy_endpoints.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_red_team_runs_org_id", "red_team_runs", ["org_id"])
    op.create_index("ix_red_team_runs_endpoint_id", "red_team_runs", ["endpoint_id"])
    op.create_index("ix_red_team_runs_org_status", "red_team_runs", ["org_id", "status"])
    op.create_index("ix_red_team_runs_org_created", "red_team_runs", ["org_id", "created_at"])

    op.create_table(
        "red_team_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("test_category", sa.String(50), nullable=False),
        sa.Column("test_name", sa.String(255), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),
        sa.Column("attack_prompt", sa.Text(), nullable=True),
        sa.Column("model_response", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["run_id"], ["red_team_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_red_team_findings_run_id", "red_team_findings", ["run_id"])
    op.create_index("ix_red_team_findings_run_category", "red_team_findings", ["run_id", "test_category"])


def downgrade() -> None:
    op.drop_table("red_team_findings")
    op.drop_table("red_team_runs")
