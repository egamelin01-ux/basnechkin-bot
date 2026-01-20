"""Change telegram_id to BIGINT

Revision ID: 004_bigint_telegram_id
Revises: 003_add_feedback
Create Date: 2026-01-19 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '004_bigint_telegram_id'
down_revision = '003_add_feedback'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    view_def = None
    try:
        view_def = conn.execute(
            text("SELECT pg_get_viewdef('user_overview'::regclass, true)")
        ).scalar()
    except Exception:
        view_def = None

    if view_def:
        op.execute("DROP VIEW IF EXISTS user_overview CASCADE")

    # Drop FKs safely in case names differ from defaults
    op.execute("ALTER TABLE stories DROP CONSTRAINT IF EXISTS stories_user_id_fkey")
    op.execute("ALTER TABLE contexts DROP CONSTRAINT IF EXISTS contexts_user_id_fkey")

    # Change column types to BIGINT
    op.alter_column('users', 'telegram_id', existing_type=sa.Integer(), type_=sa.BigInteger())
    op.alter_column('stories', 'user_id', existing_type=sa.Integer(), type_=sa.BigInteger())
    op.alter_column('contexts', 'user_id', existing_type=sa.Integer(), type_=sa.BigInteger())

    # Recreate FKs
    op.create_foreign_key(
        'stories_user_id_fkey',
        'stories',
        'users',
        ['user_id'],
        ['telegram_id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'contexts_user_id_fkey',
        'contexts',
        'users',
        ['user_id'],
        ['telegram_id'],
        ondelete='CASCADE'
    )

    if view_def:
        cleaned_def = str(view_def).strip().rstrip(";")
        op.execute(f"CREATE VIEW user_overview AS {cleaned_def}")


def downgrade() -> None:
    conn = op.get_bind()
    view_def = None
    try:
        view_def = conn.execute(
            text("SELECT pg_get_viewdef('user_overview'::regclass, true)")
        ).scalar()
    except Exception:
        view_def = None

    if view_def:
        op.execute("DROP VIEW IF EXISTS user_overview CASCADE")

    op.execute("ALTER TABLE stories DROP CONSTRAINT IF EXISTS stories_user_id_fkey")
    op.execute("ALTER TABLE contexts DROP CONSTRAINT IF EXISTS contexts_user_id_fkey")

    op.alter_column('contexts', 'user_id', existing_type=sa.BigInteger(), type_=sa.Integer())
    op.alter_column('stories', 'user_id', existing_type=sa.BigInteger(), type_=sa.Integer())
    op.alter_column('users', 'telegram_id', existing_type=sa.BigInteger(), type_=sa.Integer())

    op.create_foreign_key(
        'stories_user_id_fkey',
        'stories',
        'users',
        ['user_id'],
        ['telegram_id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'contexts_user_id_fkey',
        'contexts',
        'users',
        ['user_id'],
        ['telegram_id'],
        ondelete='CASCADE'
    )

    if view_def:
        cleaned_def = str(view_def).strip().rstrip(";")
        op.execute(f"CREATE VIEW user_overview AS {cleaned_def}")

