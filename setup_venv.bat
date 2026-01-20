@echo off
chcp 65001 >nul
echo ========================================
echo  Создание виртуального окружения
echo ========================================
echo.

REM Проверка существования venv
if exist "venv\" (
    echo [INFO] Виртуальное окружение уже существует.
    echo [INFO] Удаляю старое окружение...
    rmdir /s /q venv
)

echo [1/4] Создание виртуального окружения...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Не удалось создать venv через python, пробую через py...
    py -m venv venv
    if errorlevel 1 (
        echo [ERROR] Не удалось создать виртуальное окружение!
        pause
        exit /b 1
    )
)
echo [OK] Виртуальное окружение создано
echo.

echo [2/4] Активация виртуального окружения...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Не удалось активировать виртуальное окружение!
    pause
    exit /b 1
)
echo [OK] Виртуальное окружение активировано
echo.

echo [3/4] Обновление pip...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo [WARNING] Не удалось обновить pip, продолжаю...
)
echo.

echo [4/4] Установка зависимостей...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Не удалось установить зависимости!
    pause
    exit /b 1
)
echo [OK] Зависимости установлены
echo.

echo ========================================
echo  Виртуальное окружение готово!
echo ========================================
echo.
echo Для активации в будущем выполните:
echo   venv\Scripts\activate.bat
echo.
echo Или запустите run_local.bat (автоматически активирует venv)
echo.
pause






