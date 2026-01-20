"""Точка входа для запуска бота Сказочник."""
import sys
from pathlib import Path

# Добавляем директорию src в путь для импортов
sys.path.insert(0, str(Path(__file__).parent / "src"))

from bot import main

if __name__ == "__main__":
    main()

