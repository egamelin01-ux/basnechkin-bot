"""Быстрая проверка базы данных и миграций."""
import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, 'src')

print("="*60)
print("Проверка подключения и миграций")
print("="*60)

try:
    # 1. Проверка DATABASE_URL
    # Пробуем явно указать путь к .env
    from pathlib import Path
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(env_path)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не найден в .env")
        print(f"\nПроверка файла .env:")
        print(f"  Файл существует: {env_path.exists()}")
        if env_path.exists():
            print(f"  Размер: {env_path.stat().st_size} байт")
            # Показываем первые строки
            with open(env_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()[:5]
                print(f"  Первые строки:")
                for line in lines:
                    if 'DATABASE_URL' in line or 'PASSWORD' not in line:
                        print(f"    {line.strip()}")
        sys.exit(1)
    
    # Скрываем пароль
    if '@' in database_url:
        parts = database_url.split('@')
        if '://' in parts[0]:
            protocol_user = parts[0].split('://')
            if len(protocol_user) == 2 and ':' in protocol_user[1]:
                user = protocol_user[1].split(':')[0]
                safe_url = f"{protocol_user[0]}://{user}:***@{parts[1]}"
                print(f"✓ DATABASE_URL: {safe_url}")
    else:
        print(f"✓ DATABASE_URL: {database_url}")
    
    # 2. Проверка подключения
    print("\n1. Проверка подключения...")
    from db.session import engine
    from sqlalchemy import text, inspect
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 as test"))
        row = result.fetchone()
        print(f"✓ Подключение успешно (результат теста: {row[0]})")
    
    # 3. Проверка таблиц
    print("\n2. Проверка таблиц...")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Найдено таблиц: {len(tables)}")
    
    expected = ['users', 'stories', 'contexts']
    missing = [t for t in expected if t not in tables]
    
    if missing:
        print(f"❌ Отсутствуют таблицы: {missing}")
        print("\n⚠ Нужно применить миграции:")
        print("   py apply_migrations.py")
        print("   или")
        print("   py -m alembic upgrade head")
        sys.exit(1)
    else:
        print(f"✓ Все таблицы присутствуют: {tables}")
    
    # 4. Проверка структуры таблицы users
    print("\n3. Проверка структуры таблицы users...")
    columns = [col['name'] for col in inspector.get_columns('users')]
    print(f"Колонки в users: {', '.join(columns)}")
    
    print("\n" + "="*60)
    print("✅ Всё готово! База данных настроена правильно.")
    print("="*60)
    print("\nТеперь можно запускать бота:")
    print("   py main.py")
    
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("\nУбедитесь, что зависимости установлены:")
    print("   py -m pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

