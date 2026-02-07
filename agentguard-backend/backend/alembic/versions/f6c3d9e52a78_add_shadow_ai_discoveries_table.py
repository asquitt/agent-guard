"""add shadow_ai_discoveries table

Revision ID: f6c3d9e52a78
Revises: e5b2c8d41f67
Create Date: 2026-02-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f6c3d9e52a78"
down_revision = "e5b2c8d41f67"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shadow_ai_discoveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("endpoint", sa.String(500), nullable=False),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("source_ip", sa.String(50), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(20), nullable=False, server_default="discovered"),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
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
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shadow_ai_org_id", "shadow_ai_discoveries", ["org_id"])
    op.create_index("ix_shadow_ai_org_provider", "shadow_ai_discoveries", ["org_id", "provider"])
    op.create_index("ix_shadow_ai_org_status", "shadow_ai_discoveries", ["org_id", "status"])
    op.create_index("ix_shadow_ai_org_risk", "shadow_ai_discoveries", ["org_id", "risk_level"])


def downgrade() -> None:
    op.drop_index("ix_shadow_ai_org_risk", table_name="shadow_ai_discoveries")
    op.drop_index("ix_shadow_ai_org_status", table_name="shadow_ai_discoveries")
    op.drop_index("ix_shadow_ai_org_provider", table_name="shadow_ai_discoveries")
    op.drop_index("ix_shadow_ai_org_id", table_name="shadow_ai_discoveries")
    op.drop_table("shadow_ai_discoveries")
