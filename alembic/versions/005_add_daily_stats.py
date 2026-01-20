"""add daily stats table

Revision ID: 005_add_daily_stats
Revises: 004_bigint_telegram_id
Create Date: 2026-01-20

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '005_add_daily_stats'
down_revision = '004_bigint_telegram_id'
branch_labels = None
depends_on = None


def upgrade():
    """Create daily_stats table."""
    op.create_table(
        'daily_stats',
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('stories_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('new_users_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('start_command_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('profile_completed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('date')
    )
    op.create_index(op.f('ix_daily_stats_date'), 'daily_stats', ['date'], unique=True)


def downgrade():
    """Drop daily_stats table."""
    op.drop_index(op.f('ix_daily_stats_date'), table_name='daily_stats')
    op.drop_table('daily_stats')

