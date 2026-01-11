"""Простое применение миграции для добавления колонки feedback."""
import sys
import os
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

database_url = os.getenv("DATABASE_URL")
if not database_url:
    print("❌ DATABASE_URL не установлен в .env")
    sys.exit(1)

# Заменяем postgresql:// на postgresql+psycopg:// для использования psycopg3
if database_url.startswith("postgresql://") and "+psycopg" not in database_url:
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

print("Подключаюсь к базе данных...")
engine = create_engine(database_url)

try:
    with engine.connect() as conn:
        # Проверяем, существует ли колонка feedback
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='feedback'
        """)
        result = conn.execute(check_query)
        exists = result.fetchone() is not None
        
        if exists:
            print("✓ Колонка 'feedback' уже существует в таблице 'users'")
        else:
            print("Добавляю колонку 'feedback' в таблицу 'users'...")
            # Добавляем колонку
            add_column_query = text("""
                ALTER TABLE users 
                ADD COLUMN feedback TEXT
            """)
            conn.execute(add_column_query)
            conn.commit()
            print("✓ Колонка 'feedback' успешно добавлена!")
    
    print("\n✓ Миграция применена успешно!")
    
except ProgrammingError as e:
    print(f"❌ Ошибка SQL: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

