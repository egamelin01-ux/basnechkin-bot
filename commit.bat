@echo off
chcp 65001 >nul
git add .
git commit -m "Обновление файлов: agent_router.py, bot.py, config.py и добавление ЗАПУСК_КОНТЕЙНЕРА.md"
git push

