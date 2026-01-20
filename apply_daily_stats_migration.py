"""Apply daily stats migration."""
import sys
import os
import logging
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

# Add the current directory and src to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'src'))

from src.db.session import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_daily_stats_table():
    """Check if daily_stats table exists."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    return 'daily_stats' in tables


def main():
    """Apply daily stats migration."""
    try:
        logger.info("Проверка таблицы daily_stats...")
        
        if check_daily_stats_table():
            logger.info("✓ Таблица daily_stats уже существует")
            return 0
        
        logger.info("Таблица daily_stats не найдена. Применяем миграцию...")
        
        # Apply migration
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "005_add_daily_stats")
        
        logger.info("✓ Миграция успешно применена")
        
        # Verify
        if check_daily_stats_table():
            logger.info("✓ Таблица daily_stats создана успешно")
            return 0
        else:
            logger.error("✗ Таблица daily_stats не была создана")
            return 1
            
    except Exception as e:
        logger.error(f"✗ Ошибка при применении миграции: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

