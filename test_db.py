"""Test database connection and basic operations."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add src to path
sys.path.insert(0, 'src')

def test_connection():
    """Test database connection."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL не установлен в .env")
        return False
    
    # Hide password in output
    safe_url = database_url
    if '@' in database_url:
        parts = database_url.split('@')
        if '://' in parts[0]:
            protocol_user = parts[0].split('://')
            if len(protocol_user) == 2:
                protocol = protocol_user[0]
                user_part = protocol_user[1]
                if ':' in user_part:
                    user = user_part.split(':')[0]
                    safe_url = f"{protocol}://{user}:***@{parts[1]}"
    
    print(f"✓ DATABASE_URL найден: {safe_url}")
    
    try:
        from db.session import engine
        from db.models import Base
        
        # Test connection
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        print("✓ Подключение к базе данных успешно")
        
        # Test tables existence
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = ['users', 'stories', 'contexts']
        missing_tables = [t for t in expected_tables if t not in tables]
        
        if missing_tables:
            print(f"⚠ Таблицы отсутствуют: {missing_tables}")
            print("  Запустите: alembic upgrade head")
            return False
        else:
            print(f"✓ Все таблицы присутствуют: {tables}")
        
        # Test basic operations
        from db.repository import get_user, upsert_user_profile, save_story, delete_user_profile
        
        test_user_id = 999999999
        test_username = "test_user"
        
        # Create user
        print(f"\nТестирую создание пользователя {test_user_id}...")
        success = upsert_user_profile(
            telegram_id=test_user_id,
            username=test_username,
            child_names="Test Child",
            age="5",
            traits="test traits"
        )
        if success:
            print("✓ Пользователь создан")
        else:
            print("❌ Ошибка создания пользователя")
            return False
        
        # Get user
        user = get_user(test_user_id)
        if user and user.get('username') == test_username:
            print("✓ Пользователь получен")
        else:
            print("❌ Ошибка получения пользователя")
            return False
        
        # Save story
        print("\nТестирую сохранение сказки...")
        success = save_story(test_user_id, "Test story text", model='test')
        if success:
            print("✓ Сказка сохранена")
        else:
            print("❌ Ошибка сохранения сказки")
            return False
        
        # Cleanup test user
        delete_user_profile(test_user_id)
        print(f"✓ Тестовый пользователь {test_user_id} удален")
        
        print("\n✅ Все тесты пройдены успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

