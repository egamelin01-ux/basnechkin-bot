"""Отладка загрузки .env файла."""
import os
from pathlib import Path

print("Проверка .env файла...")
print("="*60)

# Проверяем текущую директорию
current_dir = Path.cwd()
print(f"Текущая директория: {current_dir}")

# Ищем .env файл
env_file = current_dir / ".env"
env_example = current_dir / ".env.example"

print(f"\nФайл .env существует: {env_file.exists()}")
print(f"Путь к .env: {env_file}")

if env_file.exists():
    print(f"Размер файла: {env_file.stat().st_size} байт")
    print("\nПервые 500 символов файла .env:")
    print("-"*60)
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read(500)
        # Скрываем пароли
        lines = content.split('\n')
        for line in lines:
            if 'DATABASE_URL' in line or 'PASSWORD' in line or 'PASS' in line:
                if '=' in line:
                    key, value = line.split('=', 1)
                    if '@' in value and '://' in value:
                        # Скрываем пароль в URL
                        parts = value.split('@')
                        if len(parts) == 2:
                            user_pass = parts[0].split('://')[-1]
                            if ':' in user_pass:
                                user = user_pass.split(':')[0]
                                safe_value = value.split(':')[0] + '://' + user + ':***@' + parts[1]
                                print(f"{key}={safe_value}")
                            else:
                                print(f"{key}=***")
                        else:
                            print(f"{key}=***")
                    else:
                        print(f"{key}=***")
                else:
                    print(line)
            else:
                print(line)
        print("-"*60)

# Пробуем загрузить через dotenv
print("\nПопытка загрузки через dotenv...")
try:
    from dotenv import load_dotenv
    result = load_dotenv(env_file)
    print(f"load_dotenv вернул: {result}")
    
    # Проверяем переменные
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Скрываем пароль
        if '@' in database_url:
            parts = database_url.split('@')
            if '://' in parts[0]:
                protocol_user = parts[0].split('://')
                if len(protocol_user) == 2 and ':' in protocol_user[1]:
                    user = protocol_user[1].split(':')[0]
                    safe_url = f"{protocol_user[0]}://{user}:***@{parts[1]}"
                    print(f"✓ DATABASE_URL найден: {safe_url}")
                else:
                    print(f"✓ DATABASE_URL найден: {database_url}")
            else:
                print(f"✓ DATABASE_URL найден: {database_url}")
        else:
            print(f"✓ DATABASE_URL найден: {database_url}")
    else:
        print("❌ DATABASE_URL не найден после load_dotenv")
        
        # Показываем все переменные, которые начинаются с DATABASE
        print("\nВсе переменные, содержащие 'DATABASE':")
        for key, value in os.environ.items():
            if 'DATABASE' in key.upper():
                print(f"  {key} = {value}")
                
except Exception as e:
    print(f"❌ Ошибка при загрузке dotenv: {e}")
    import traceback
    traceback.print_exc()

