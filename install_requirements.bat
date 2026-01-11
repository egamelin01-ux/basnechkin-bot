@echo off
chcp 65001 >nul
echo Установка зависимостей Python...

REM Проверка виртуального окружения
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Виртуальное окружение найдено, активирую...
    call venv\Scripts\activate.bat
)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Зависимости установлены!
pause

