"""AbroadStudentActivity columns: nullable=True

Revision ID: 170b43535213
Revises: 392c03db99c8
Create Date: 2025-06-06 17:23:28.257504

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '170b43535213'
down_revision: Union[str, None] = '392c03db99c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Use batch_alter_table so that Alembic recreates the SQLite table
    # with the new nullability constraints.
    with op.batch_alter_table("student_activities", recreate="always") as batch_op:
        batch_op.alter_column(
            'description',
            existing_type=sa.String(),
            nullable=True
        )
        batch_op.alter_column(
            'start_date',
            existing_type=sa.DateTime(),
            nullable=True
        )
        batch_op.alter_column(
            'end_date',
            existing_type=sa.DateTime(),
            nullable=True
        )
        batch_op.alter_column(
            'city',
            existing_type=sa.String(),
            nullable=True
        )
        batch_op.alter_column(
            'country',
            existing_type=sa.String(),
            nullable=True
        )
        batch_op.alter_column(
            'host_institution',
            existing_type=sa.String(),
            nullable=True
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("student_activities", recreate="always") as batch_op:
        batch_op.alter_column(
            'host_institution',
            existing_type=sa.String(),
            nullable=False
        )
        batch_op.alter_column(
            'country',
            existing_type=sa.String(),
            nullable=False
        )
        batch_op.alter_column(
            'city',
            existing_type=sa.String(),
            nullable=False
        )
        batch_op.alter_column(
            'end_date',
            existing_type=sa.DateTime(),
            nullable=False
        )
        batch_op.alter_column(
            'start_date',
            existing_type=sa.DateTime(),
            nullable=False
        )
        batch_op.alter_column(
            'description',
            existing_type=sa.String(),
            nullable=False
        )
    # ### end Alembic commands ###
