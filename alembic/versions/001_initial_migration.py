"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('telegram_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('child_names', sa.Text(), nullable=True),
        sa.Column('age', sa.String(length=50), nullable=True),
        sa.Column('traits', sa.Text(), nullable=True),
        sa.Column('context_active', sa.Text(), nullable=True),
        sa.Column('story_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('telegram_id')
    )
    op.create_index('ix_users_telegram_id', 'users', ['telegram_id'], unique=True)

    # Create stories table
    op.create_table(
        'stories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('model', sa.String(length=50), nullable=False, server_default='deepseek'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.telegram_id'], ondelete='CASCADE')
    )
    op.create_index('ix_stories_user_id', 'stories', ['user_id'], unique=False)
    op.create_index('ix_stories_created_at', 'stories', ['created_at'], unique=False)
    op.create_index('ix_stories_user_created', 'stories', ['user_id', 'created_at'], unique=False)

    # Create contexts table
    op.create_table(
        'contexts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.telegram_id'], ondelete='CASCADE')
    )
    op.create_index('ix_contexts_user_id', 'contexts', ['user_id'], unique=False)
    op.create_index('ix_contexts_kind', 'contexts', ['kind'], unique=False)
    op.create_index('ix_contexts_created_at', 'contexts', ['created_at'], unique=False)
    op.create_index('ix_contexts_user_kind_created', 'contexts', ['user_id', 'kind', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_contexts_user_kind_created', table_name='contexts')
    op.drop_index('ix_contexts_created_at', table_name='contexts')
    op.drop_index('ix_contexts_kind', table_name='contexts')
    op.drop_index('ix_contexts_user_id', table_name='contexts')
    op.drop_table('contexts')
    
    op.drop_index('ix_stories_user_created', table_name='stories')
    op.drop_index('ix_stories_created_at', table_name='stories')
    op.drop_index('ix_stories_user_id', table_name='stories')
    op.drop_table('stories')
    
    op.drop_index('ix_users_telegram_id', table_name='users')
    op.drop_table('users')

