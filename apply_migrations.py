"""Применение миграций Alembic."""
import sys
import os
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

try:
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import create_engine
    
    # Загружаем DATABASE_URL
    from dotenv import load_dotenv
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не установлен в .env")
        sys.exit(1)
    
    # Заменяем postgresql:// на postgresql+psycopg:// для использования psycopg3
    if database_url.startswith("postgresql://") and "+psycopg" not in database_url:
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    
    print("Подключаюсь к базе данных...")
    engine = create_engine(database_url)
    
    # Создаем конфигурацию Alembic
    alembic_cfg = Config('alembic.ini')
    
    print("Применяю миграции...")
    command.upgrade(alembic_cfg, "head")
    print("✓ Миграции применены успешно!")
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("\nУбедитесь, что зависимости установлены:")
    print("  py -m pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

