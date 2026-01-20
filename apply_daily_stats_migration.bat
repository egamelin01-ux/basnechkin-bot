@echo off
echo Применение миграции daily_stats...
call venv\Scripts\activate.bat
python apply_daily_stats_migration.py
pause

