@echo off
chcp 65001 >nul
echo ========================================
echo  Тестирование зависимостей
echo ========================================
echo.

echo [1/5] Проверка Python...
python --version
if errorlevel 1 (
    echo ОШИБКА: Python не найден!
    pause
    exit /b 1
)
echo.

echo [2/5] Проверка основных модулей...
python test_import.py
if errorlevel 1 (
    echo.
    echo ОШИБКА: Некоторые зависимости не установлены!
    echo Установите: python -m pip install -r requirements.txt
    pause
    exit /b 1
)
echo.

echo [3/5] Проверка конфигурации...
python -c "from src.config import TELEGRAM_BOT_TOKEN, DATABASE_URL; print('OK - конфигурация загружена')" 2>&1
if errorlevel 1 (
    echo ОШИБКА: Проблема с конфигурацией!
    echo Проверьте файл .env
    pause
    exit /b 1
)
echo.

echo [4/5] Попытка запуска бота (5 секунд)...
timeout /t 1 >nul
start /B python main.py
timeout /t 5 >nul
taskkill /F /IM python.exe >nul 2>&1
echo.

echo ========================================
echo  Все проверки пройдены!
echo ========================================
pause

