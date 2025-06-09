"""Researcher: title_id: nullable=True

Revision ID: bbe8b4e6fcb7
Revises: 170b43535213
Create Date: 2025-06-09 21:14:21.112091

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bbe8b4e6fcb7'
down_revision: Union[str, None] = '170b43535213'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('researchers') as batch_op:
        batch_op.alter_column(
            'title_id',
            existing_type=sa.INTEGER(),
            nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('researchers') as batch_op:
        batch_op.alter_column(
            'title_id',
            existing_type=sa.INTEGER(),
            nullable=False,
        )
    # ### end Alembic commands ###
