"""Тест импорта модулей"""
try:
    print("Проверка sqlalchemy...")
    import sqlalchemy
    print(f"✓ SQLAlchemy установлен: {sqlalchemy.__version__}")
except ImportError as e:
    print(f"✗ SQLAlchemy НЕ установлен: {e}")
    exit(1)

try:
    print("Проверка telegram...")
    import telegram
    print(f"✓ python-telegram-bot установлен: {telegram.__version__}")
except ImportError as e:
    print(f"✗ python-telegram-bot НЕ установлен: {e}")
    exit(1)

try:
    print("Проверка openai...")
    import openai
    print(f"✓ openai установлен: {openai.__version__}")
except ImportError as e:
    print(f"✗ openai НЕ установлен: {e}")
    exit(1)

try:
    print("Проверка requests...")
    import requests
    print(f"✓ requests установлен: {requests.__version__}")
except ImportError as e:
    print(f"✗ requests НЕ установлен: {e}")
    exit(1)

print("\nВсе зависимости установлены!")

