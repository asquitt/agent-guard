"""add review_queue table

Revision ID: e5b2c8d41f67
Revises: d3a9f7b12c45
Create Date: 2026-02-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e5b2c8d41f67"
down_revision = "d3a9f7b12c45"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_queue",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("proxy_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("escalation_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("escalation_deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("context", postgresql.JSONB(), nullable=False, server_default="{}"),
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
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proxy_request_id"], ["proxy_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_queue_org_id", "review_queue", ["org_id"])
    op.create_index("ix_review_queue_incident_id", "review_queue", ["incident_id"])
    op.create_index("ix_review_queue_org_status", "review_queue", ["org_id", "status"])
    op.create_index("ix_review_queue_org_severity", "review_queue", ["org_id", "severity"])
    op.create_index(
        "ix_review_queue_escalation", "review_queue", ["org_id", "escalation_deadline"]
    )


def downgrade() -> None:
    op.drop_index("ix_review_queue_escalation", table_name="review_queue")
    op.drop_index("ix_review_queue_org_severity", table_name="review_queue")
    op.drop_index("ix_review_queue_org_status", table_name="review_queue")
    op.drop_index("ix_review_queue_incident_id", table_name="review_queue")
    op.drop_index("ix_review_queue_org_id", table_name="review_queue")
    op.drop_table("review_queue")
