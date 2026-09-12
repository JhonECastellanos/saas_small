"""add unit_of_measure to variants

Revision: 1c0df8145617
Anterior: 7c8b9ba73ebf
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1c0df8145617"
down_revision: Union[str, None] = "7c8b9ba73ebf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("variants", schema=None) as batch_op:
        batch_op.add_column(sa.Column("unit_of_measure", sa.String(length=10), nullable=True))
    op.execute("UPDATE variants SET unit_of_measure = 'unidad' WHERE unit_of_measure IS NULL")
    with op.batch_alter_table("variants", schema=None) as batch_op:
        batch_op.alter_column("unit_of_measure", nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("variants", schema=None) as batch_op:
        batch_op.drop_column("unit_of_measure")
