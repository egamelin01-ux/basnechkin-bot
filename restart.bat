@echo off
echo Перезапуск контейнера basnechkin-bot...
docker-compose -f docker-compose.dev.yml restart basnechkin-bot
echo.
echo Контейнер перезапущен! Показываю последние логи:
echo.
docker-compose -f docker-compose.dev.yml logs --tail=20 basnechkin-bot
echo.
echo Для просмотра логов в реальном времени: docker-compose -f docker-compose.dev.yml logs -f basnechkin-bot

