@echo off
chcp 65001 >nul
echo Применение миграции для добавления колонки feedback...
python apply_feedback_migration.py
pause

