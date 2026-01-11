"""Add feedback column

Revision ID: 003_add_feedback
Revises: 002_add_wishes
Create Date: 2025-01-03 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_feedback'
down_revision = '002_add_wishes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('feedback', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'feedback')

