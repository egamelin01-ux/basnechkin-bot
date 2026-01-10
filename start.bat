@echo off
echo Запуск контейнера basnechkin-bot...
docker-compose -f docker-compose.dev.yml up -d

echo.
echo Проверка статуса...
docker-compose -f docker-compose.dev.yml ps

echo.
echo Просмотр логов (последние 30 строк)...
docker-compose -f docker-compose.dev.yml logs --tail=30 basnechkin-bot

