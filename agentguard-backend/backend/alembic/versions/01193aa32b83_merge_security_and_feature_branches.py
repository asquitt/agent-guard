"""merge security and feature branches

Revision ID: 01193aa32b83
Revises: 7ed74d7e38c7, i9f6g2h85d01
Create Date: 2026-02-13 04:31:07.631263

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01193aa32b83'
down_revision: Union[str, None] = ('7ed74d7e38c7', 'i9f6g2h85d01')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
