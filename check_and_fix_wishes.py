"""Проверка и исправление колонки wishes в БД."""
import sys
import os
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

try:
    from db.session import engine
    from sqlalchemy import text, inspect
    
    print("Проверяю структуру таблицы users...")
    
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('users')]
    print(f"Колонки в таблице users: {columns}")
    
    if 'wishes' in columns:
        print("✓ Колонка 'wishes' уже существует!")
    else:
        print("⚠ Колонка 'wishes' отсутствует. Добавляю...")
        with engine.connect() as conn:
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN wishes TEXT"))
                conn.commit()
                print("✓ Колонка 'wishes' успешно добавлена!")
            except Exception as e:
                print(f"❌ Ошибка при добавлении колонки: {e}")
                conn.rollback()
                sys.exit(1)
    
    # Проверяем еще раз
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns('users')]
    if 'wishes' in columns:
        print("\n✓ Все готово! Колонка 'wishes' присутствует в таблице.")
    else:
        print("\n❌ Не удалось добавить колонку 'wishes'")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

