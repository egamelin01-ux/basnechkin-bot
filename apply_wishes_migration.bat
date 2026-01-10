@echo off
chcp 65001 >nul
echo Применение миграции для добавления колонки wishes...
python apply_wishes_migration.py
pause

