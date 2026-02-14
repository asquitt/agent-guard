"""add ai_models table for model registry

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-14 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False, server_default="latest"),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model_type", sa.String(50), nullable=False, server_default="llm"),
        sa.Column("license_type", sa.String(100), nullable=True),
        sa.Column("model_hash", sa.String(128), nullable=True),
        sa.Column("repository_url", sa.String(512), nullable=True),
        sa.Column("model_card_url", sa.String(512), nullable=True),
        sa.Column("release_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parameter_count", sa.String(20), nullable=True),
        sa.Column("context_window", sa.Integer(), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("risk_factors", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("compliance_frameworks", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("known_limitations", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("security_issues", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("pii_handling", sa.String(20), nullable=False, server_default="strict"),
        sa.Column("training_data_sources", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("training_cutoff", sa.String(20), nullable=True),
        sa.Column("model_dependencies", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("capabilities", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("approval_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("approval_notes", sa.String(1000), nullable=True),
        sa.Column("owner_email", sa.String(255), nullable=True),
        sa.Column("is_deprecated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("total_requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_incidents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ai_models_org_id", "ai_models", ["org_id"])
    op.create_index("ix_ai_models_risk_level", "ai_models", ["risk_level"])
    op.create_index("ix_ai_models_approval_status", "ai_models", ["approval_status"])
    op.create_index("ix_ai_models_org_provider", "ai_models", ["org_id", "provider"])
    op.create_index("ix_ai_models_org_name", "ai_models", ["org_id", "model_name"])
    op.create_index("ix_ai_models_org_risk", "ai_models", ["org_id", "risk_level"])
    op.create_index("ix_ai_models_org_status", "ai_models", ["org_id", "approval_status"])


def downgrade() -> None:
    op.drop_table("ai_models")
