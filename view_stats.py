"""View daily statistics."""
import sys
import os
import logging
from datetime import datetime, timedelta

# Add the current directory and src to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'src'))

from src.db.repository import get_daily_stats, get_daily_stats_summary

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """View daily statistics."""
    try:
        print("\n" + "="*80)
        print("СТАТИСТИКА ПО ДНЯМ")
        print("="*80 + "\n")
        
        # Получаем статистику за последние 30 дней
        stats = get_daily_stats(limit=30)
        
        if not stats:
            print("Нет данных статистики.\n")
            return 0
        
        # Заголовок таблицы
        print(f"{'Дата':<12} | {'Сказки':>8} | {'Новые':>8} | {'/start':>8} | {'Анкеты':>8}")
        print(f"{'':12} | {'':>8} | {'польз.':>8} | {'команд':>8} | {'заполн':>8}")
        print("-" * 80)
        
        # Выводим каждый день
        for stat in stats:
            date_str = stat['date']
            stories = stat['stories_count']
            new_users = stat['new_users_count']
            starts = stat['start_command_count']
            profiles = stat['profile_completed_count']
            
            print(f"{date_str:<12} | {stories:>8} | {new_users:>8} | {starts:>8} | {profiles:>8}")
        
        print("-" * 80)
        
        # Получаем общую сводку
        summary = get_daily_stats_summary()
        
        print("\n" + "="*80)
        print("ОБЩАЯ СТАТИСТИКА")
        print("="*80 + "\n")
        
        print(f"Всего дней с данными:        {summary['days_count']}")
        print(f"Всего создано сказок:        {summary['total_stories']}")
        print(f"Всего новых пользователей:   {summary['total_new_users']}")
        print(f"Всего команд /start:         {summary['total_start_commands']}")
        print(f"Всего заполнено анкет:       {summary['total_profiles_completed']}")
        
        if summary['days_count'] > 0:
            print(f"\nСредняя активность в день:")
            print(f"  - Сказок:                  {summary['total_stories'] / summary['days_count']:.1f}")
            print(f"  - Новых пользователей:     {summary['total_new_users'] / summary['days_count']:.1f}")
            print(f"  - Команд /start:           {summary['total_start_commands'] / summary['days_count']:.1f}")
            print(f"  - Заполненных анкет:       {summary['total_profiles_completed'] / summary['days_count']:.1f}")
        
        print("\n" + "="*80 + "\n")
        
        return 0
        
    except Exception as e:
        logger.error(f"Ошибка при просмотре статистики: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

