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
    # Make idempotent for environments where column was added manually
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS wishes TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS wishes")

