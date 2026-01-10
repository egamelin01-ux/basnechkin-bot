"""Add wishes column

Revision ID: 002_add_wishes
Revises: 001_initial
Create Date: 2025-01-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_wishes'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('wishes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'wishes')

