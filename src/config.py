"""Конфигурация проекта."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен в .env")

# OpenAI (Agent 1)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не установлен в .env")

# DeepSeek
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY не установлен в .env")

DEEPSEEK_API_URL = os.getenv(
    "DEEPSEEK_API_URL", 
    "https://api.deepseek.com/v1/chat/completions"
)

# Google Sheets (deprecated - используем PostgreSQL)
# GOOGLE_SHEETS_CREDENTIALS_PATH = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "credentials.json")
# SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

# PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL не установлен в .env")

# Заменяем postgresql:// на postgresql+psycopg:// для использования psycopg3
if DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# Настройки
ANTIFLOOD_SECONDS = int(os.getenv("ANTIFLOOD_SECONDS", "15"))
PROFILE_CACHE_TTL_MINUTES = int(os.getenv("PROFILE_CACHE_TTL_MINUTES", "5"))

# Пути
BASE_DIR = Path(__file__).parent.parent

