"""Проверка наличия колонки feedback в таблице users."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

load_dotenv()

from sqlalchemy import create_engine, text

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
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='feedback'
        """)
        result = conn.execute(check_query)
        row = result.fetchone()
        
        if row:
            print(f"✓ Колонка 'feedback' существует в таблице 'users'")
            print(f"  Тип данных: {row[1]}")
        else:
            print("❌ Колонка 'feedback' НЕ найдена в таблице 'users'")
            print("\nДля добавления колонки запустите:")
            print("  python apply_feedback_migration.py")
            
        # Показываем все колонки таблицы users для справки
        print("\nВсе колонки таблицы 'users':")
        all_columns_query = text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name='users'
            ORDER BY ordinal_position
        """)
        all_result = conn.execute(all_columns_query)
        for col_row in all_result:
            print(f"  - {col_row[0]} ({col_row[1]})")
            
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)






