@echo off
echo Остановка и удаление старого контейнера...
docker-compose -f docker-compose.yml down

echo.
echo Пересборка образа с новым кодом...
docker-compose -f docker-compose.yml build --no-cache

echo.
echo Запуск контейнера...
docker-compose -f docker-compose.yml up -d

echo.
echo Контейнер пересобран и запущен!
echo Для просмотра логов: docker-compose -f docker-compose.yml logs -f basnechkin-bot

