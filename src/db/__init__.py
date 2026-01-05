"""Database package for PostgreSQL storage."""
from .session import engine, SessionLocal, Base
from .repository import (
    get_user,
    upsert_user_profile,
    update_user_fields,
    increment_story_total,
    save_story,
    get_last_stories,
    add_context,
    get_active_context,
    delete_user_profile,
)

__all__ = [
    'engine',
    'SessionLocal',
    'Base',
    'get_user',
    'upsert_user_profile',
    'update_user_fields',
    'increment_story_total',
    'save_story',
    'get_last_stories',
    'add_context',
    'get_active_context',
    'delete_user_profile',
]

