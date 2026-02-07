"""add environment to api_keys and proxy_endpoints

Revision ID: c4e92f1b8a7d
Revises: b7f8c2a91d34
Create Date: 2026-02-07
"""

from alembic import op
import sqlalchemy as sa

revision = "c4e92f1b8a7d"
down_revision = "b7f8c2a91d34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "api_keys",
        sa.Column("environment", sa.String(20), nullable=False, server_default="production"),
    )
    op.add_column(
        "proxy_endpoints",
        sa.Column("environment", sa.String(20), nullable=False, server_default="production"),
    )


def downgrade() -> None:
    op.drop_column("proxy_endpoints", "environment")
    op.drop_column("api_keys", "environment")
