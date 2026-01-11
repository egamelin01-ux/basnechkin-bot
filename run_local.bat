@echo off
chcp 65001 >nul
echo ========================================
echo  Локальный запуск бота
echo ========================================
echo.

REM Проверка существования venv
if not exist "venv\" (
    echo [ERROR] Виртуальное окружение не найдено!
    echo [INFO] Создайте его: setup_venv.bat
    pause
    exit /b 1
)

echo [INFO] Активация виртуального окружения...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Не удалось активировать виртуальное окружение!
    pause
    exit /b 1
)

echo [OK] Виртуальное окружение активировано
echo.
echo ========================================
echo  Запуск бота...
echo ========================================
echo.

python main.py

pause


