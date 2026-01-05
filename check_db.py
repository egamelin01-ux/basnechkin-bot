"""Проверка подключения к БД."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, 'src')

try:
    from db.session import engine
    from sqlalchemy import text, inspect
    
    print("Проверяю подключение...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        print(f"✓ Подключение успешно! Результат теста: {row[0]}")
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nТаблицы в базе данных: {tables}")
    
    expected = ['users', 'stories', 'contexts']
    missing = [t for t in expected if t not in tables]
    
    if missing:
        print(f"\n⚠ Отсутствуют таблицы: {missing}")
        print("Запустите: alembic upgrade head")
    else:
        print("\n✓ Все таблицы присутствуют!")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()

