@echo off
chcp 65001 >nul
echo Проверка и исправление колонки wishes в БД...
python check_and_fix_wishes.py
pause

