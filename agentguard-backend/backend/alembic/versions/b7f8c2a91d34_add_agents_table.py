"""add agents table

Revision ID: b7f8c2a91d34
Revises: a53e5e46e529
Create Date: 2026-02-07 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b7f8c2a91d34'
down_revision: Union[str, None] = 'a53e5e46e529'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner', sa.String(255), nullable=True),
        sa.Column('risk_tier', sa.String(20), nullable=False, server_default='medium'),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('model', sa.String(255), nullable=True),
        sa.Column('frameworks', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_agents_org_id', 'agents', ['org_id'])
    op.create_index('ix_agents_org_id_status', 'agents', ['org_id', 'status'])
    op.create_index('ix_agents_org_id_risk_tier', 'agents', ['org_id', 'risk_tier'])


def downgrade() -> None:
    op.drop_index('ix_agents_org_id_risk_tier', table_name='agents')
    op.drop_index('ix_agents_org_id_status', table_name='agents')
    op.drop_index('ix_agents_org_id', table_name='agents')
    op.drop_table('agents')
