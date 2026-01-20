"""Database repository functions."""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from .session import SessionLocal
from .models import User, Story, Context, DailyStats

logger = logging.getLogger(__name__)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    """
    Get user by telegram_id.
    Returns user dict or None if not found.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            return user.to_dict()
        return None
    except Exception as e:
        logger.error(f"Ошибка получения пользователя {telegram_id}: {e}")
        return None
    finally:
        db.close()


def upsert_user_profile(
    telegram_id: int,
    username: str,
    child_names: str,
    age: str,
    traits: str,
    context_active: Optional[str] = None
) -> bool:
    """
    Create or update user profile.
    Returns True on success, False on error.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if user:
            # Update existing user
            user.username = username or user.username
            user.child_names = child_names
            user.age = age
            user.traits = traits
            if context_active is not None:
                user.context_active = context_active
            user.updated_at = datetime.utcnow()
        else:
            # Create new user
            user = User(
                telegram_id=telegram_id,
                username=username,
                child_names=child_names,
                age=age,
                traits=traits,
                context_active=context_active or '',
                story_total=0
            )
            db.add(user)
        
        db.commit()
        logger.info(f"Профиль пользователя {telegram_id} сохранен")
        return True
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        logger.error(f"Ошибка сохранения профиля пользователя {telegram_id}: {e}", exc_info=True)
        # Проверяем, не связана ли ошибка с отсутствующей колонкой wishes
        if "wishes" in error_msg.lower() or "column" in error_msg.lower():
            logger.error(f"ВНИМАНИЕ: Возможно, колонка 'wishes' отсутствует в БД. Примените миграцию: python apply_wishes_migration.py")
        return False
    finally:
        db.close()


def update_user_fields(telegram_id: int, **fields) -> bool:
    """
    Update user fields dynamically.
    fields can contain: username, child_names, age, traits, context_active, etc.
    Returns True on success, False on error.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            logger.warning(f"Пользователь {telegram_id} не найден для обновления")
            return False
        
        for key, value in fields.items():
            if hasattr(user, key):
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        db.commit()
        logger.info(f"Поля пользователя {telegram_id} обновлены: {list(fields.keys())}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка обновления полей пользователя {telegram_id}: {e}")
        return False
    finally:
        db.close()


def increment_story_total(telegram_id: int) -> int:
    """
    Increment story_total for user and return new total.
    Returns 0 if user not found.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            logger.warning(f"Пользователь {telegram_id} не найден для increment_story_total")
            return 0
        
        user.story_total += 1
        db.commit()
        new_total = user.story_total
        logger.info(f"story_total для пользователя {telegram_id} увеличен до {new_total}")
        return new_total
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка increment_story_total для {telegram_id}: {e}")
        return 0
    finally:
        db.close()


def save_story(telegram_id: int, story_text: str, model: str = 'deepseek') -> bool:
    """
    Save story, increment story_total, and trim to last 5 stories.
    Returns True on success, False on error.
    """
    db = SessionLocal()
    try:
        # Create story
        story = Story(
            user_id=telegram_id,
            text=story_text,
            model=model
        )
        db.add(story)
        
        # Increment story_total
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.story_total += 1
        else:
            logger.warning(f"Пользователь {telegram_id} не найден при сохранении сказки")
            db.rollback()
            return False
        
        # Flush to get story ID, then trim
        db.flush()
        
        # Trim to last 5 stories (before commit)
        _trim_stories(db, telegram_id, limit=5)
        
        db.commit()
        logger.info(f"Сказка сохранена для пользователя {telegram_id}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка сохранения сказки для пользователя {telegram_id}: {e}")
        return False
    finally:
        db.close()


def _trim_stories(db: Session, telegram_id: int, limit: int = 5):
    """
    Keep only last N stories for user, delete older ones.
    Note: does not commit, should be called within a transaction.
    """
    try:
        # Get all stories for user, ordered by created_at DESC
        stories = db.query(Story).filter(
            Story.user_id == telegram_id
        ).order_by(desc(Story.created_at)).all()
        
        if len(stories) > limit:
            # Delete oldest stories (keep last N)
            stories_to_delete = stories[limit:]
            for story in stories_to_delete:
                db.delete(story)
            logger.info(f"Помечено к удалению {len(stories_to_delete)} старых сказок для пользователя {telegram_id}")
    except Exception as e:
        logger.error(f"Ошибка trim сказок для пользователя {telegram_id}: {e}")
        raise


def get_last_stories(telegram_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get last N stories for user.
    Returns list of story dicts.
    """
    db = SessionLocal()
    try:
        stories = db.query(Story).filter(
            Story.user_id == telegram_id
        ).order_by(desc(Story.created_at)).limit(limit).all()
        
        return [
            {
                'id': story.id,
                'user_id': story.user_id,
                'text': story.text,
                'model': story.model,
                'created_at': story.created_at.isoformat() if story.created_at else '',
            }
            for story in stories
        ]
    except Exception as e:
        logger.error(f"Ошибка получения сказок для пользователя {telegram_id}: {e}")
        return []
    finally:
        db.close()


def add_context(telegram_id: int, kind: str, content: str) -> bool:
    """
    Add context (active or archived).
    For archived contexts, trim to last 5.
    Returns True on success, False on error.
    """
    db = SessionLocal()
    try:
        context = Context(
            user_id=telegram_id,
            kind=kind,
            content=content
        )
        db.add(context)
        
        # If archived, trim to last 5
        if kind == 'archived':
            _trim_contexts(db, telegram_id, kind='archived', limit=5)
        
        db.commit()
        logger.info(f"Контекст добавлен для пользователя {telegram_id}, kind={kind}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка добавления контекста для пользователя {telegram_id}: {e}")
        return False
    finally:
        db.close()


def _trim_contexts(db: Session, telegram_id: int, kind: str, limit: int = 5):
    """
    Keep only last N contexts of given kind for user.
    Note: does not commit, should be called within a transaction.
    """
    try:
        contexts = db.query(Context).filter(
            Context.user_id == telegram_id,
            Context.kind == kind
        ).order_by(desc(Context.created_at)).all()
        
        if len(contexts) > limit:
            contexts_to_delete = contexts[limit:]
            for context in contexts_to_delete:
                db.delete(context)
            logger.info(f"Помечено к удалению {len(contexts_to_delete)} старых контекстов для пользователя {telegram_id}")
    except Exception as e:
        logger.error(f"Ошибка trim контекстов для пользователя {telegram_id}: {e}")
        raise


def get_active_context(telegram_id: int) -> Optional[str]:
    """
    Get active context for user.
    Returns context content or None.
    """
    db = SessionLocal()
    try:
        context = db.query(Context).filter(
            Context.user_id == telegram_id,
            Context.kind == 'active'
        ).order_by(desc(Context.created_at)).first()
        
        if context:
            return context.content
        return None
    except Exception as e:
        logger.error(f"Ошибка получения активного контекста для пользователя {telegram_id}: {e}")
        return None
    finally:
        db.close()


def delete_user_profile(telegram_id: int) -> bool:
    """
    Delete user profile and all related stories and contexts.
    Returns True on success, False on error.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            logger.warning(f"Пользователь {telegram_id} не найден для удаления")
            return False
        
        db.delete(user)  # Cascade will delete stories and contexts
        db.commit()
        logger.info(f"Профиль пользователя {telegram_id} и все связанные данные удалены")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка удаления профиля пользователя {telegram_id}: {e}")
        return False
    finally:
        db.close()


# ==================== Daily Statistics ====================

def increment_daily_stat(stat_type: str, increment: int = 1, target_date: Optional[date] = None) -> bool:
    """
    Increment daily statistic counter.
    stat_type can be: 'stories', 'new_users', 'start_command', 'profile_completed'
    Returns True on success, False on error.
    """
    if target_date is None:
        target_date = datetime.utcnow().date()
    
    db = SessionLocal()
    try:
        # Get or create daily stats
        stats = db.query(DailyStats).filter(DailyStats.date == target_date).first()
        
        if not stats:
            stats = DailyStats(
                date=target_date,
                stories_count=0,
                new_users_count=0,
                start_command_count=0,
                profile_completed_count=0
            )
            db.add(stats)
        
        # Increment the appropriate counter
        if stat_type == 'stories':
            stats.stories_count += increment
        elif stat_type == 'new_users':
            stats.new_users_count += increment
        elif stat_type == 'start_command':
            stats.start_command_count += increment
        elif stat_type == 'profile_completed':
            stats.profile_completed_count += increment
        else:
            logger.warning(f"Неизвестный тип статистики: {stat_type}")
            db.rollback()
            return False
        
        stats.updated_at = datetime.utcnow()
        db.commit()
        logger.info(f"Статистика обновлена: {stat_type} +{increment} для {target_date}")
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка обновления статистики {stat_type}: {e}")
        return False
    finally:
        db.close()


def get_daily_stats(start_date: Optional[date] = None, end_date: Optional[date] = None, limit: int = 30) -> List[Dict[str, Any]]:
    """
    Get daily statistics for date range.
    If dates not provided, returns last N days.
    Returns list of stats dicts ordered by date DESC.
    """
    db = SessionLocal()
    try:
        query = db.query(DailyStats)
        
        if start_date:
            query = query.filter(DailyStats.date >= start_date)
        if end_date:
            query = query.filter(DailyStats.date <= end_date)
        
        stats = query.order_by(desc(DailyStats.date)).limit(limit).all()
        
        return [stat.to_dict() for stat in stats]
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        return []
    finally:
        db.close()


def get_daily_stats_summary() -> Dict[str, Any]:
    """
    Get summary statistics across all days.
    Returns dict with total counts.
    """
    db = SessionLocal()
    try:
        result = db.query(
            func.sum(DailyStats.stories_count).label('total_stories'),
            func.sum(DailyStats.new_users_count).label('total_new_users'),
            func.sum(DailyStats.start_command_count).label('total_start_commands'),
            func.sum(DailyStats.profile_completed_count).label('total_profiles_completed'),
            func.count(DailyStats.date).label('days_count')
        ).first()
        
        return {
            'total_stories': result.total_stories or 0,
            'total_new_users': result.total_new_users or 0,
            'total_start_commands': result.total_start_commands or 0,
            'total_profiles_completed': result.total_profiles_completed or 0,
            'days_count': result.days_count or 0,
        }
    except Exception as e:
        logger.error(f"Ошибка получения сводной статистики: {e}")
        return {
            'total_stories': 0,
            'total_new_users': 0,
            'total_start_commands': 0,
            'total_profiles_completed': 0,
            'days_count': 0,
        }
    finally:
        db.close()

