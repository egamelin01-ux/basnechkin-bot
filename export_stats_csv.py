"""Export daily statistics to CSV file."""
import sys
import os
import logging
import csv
from datetime import datetime

# Add the current directory and src to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'src'))

from src.db.repository import get_daily_stats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Export daily statistics to CSV."""
    try:
        # Генерируем имя файла с текущей датой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stats_export_{timestamp}.csv"
        
        logger.info(f"Экспорт статистики в файл {filename}...")
        
        # Получаем статистику за все дни
        stats = get_daily_stats(limit=1000)
        
        if not stats:
            print("Нет данных для экспорта.\n")
            return 0
        
        # Записываем в CSV
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = [
                'Дата',
                'Сказки',
                'Новые пользователи',
                'Команд /start',
                'Заполнено анкет'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for stat in reversed(stats):  # Reverse to get oldest first
                writer.writerow({
                    'Дата': stat['date'],
                    'Сказки': stat['stories_count'],
                    'Новые пользователи': stat['new_users_count'],
                    'Команд /start': stat['start_command_count'],
                    'Заполнено анкет': stat['profile_completed_count']
                })
        
        print(f"✓ Статистика успешно экспортирована в файл: {filename}")
        print(f"  Записей: {len(stats)}\n")
        
        return 0
        
    except Exception as e:
        logger.error(f"Ошибка при экспорте статистики: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

