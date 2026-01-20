@echo off
echo Экспорт статистики в CSV...
call venv\Scripts\activate.bat
python export_stats_csv.py
pause

