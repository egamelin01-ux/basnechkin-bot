@echo off
REM Скрипт для сборки и пуша образа в Docker Hub
REM Использование: push_to_dockerhub.bat [username] [tag]
REM Пример: push_to_dockerhub.bat myusername latest

setlocal enabledelayedexpansion

REM Проверка аргументов
if "%~1"=="" (
    echo Ошибка: Не указано имя пользователя Docker Hub
    echo Использование: push_to_dockerhub.bat [username] [tag]
    echo Пример: push_to_dockerhub.bat myusername latest
    exit /b 1
)

set DOCKER_USERNAME=%~1
set IMAGE_TAG=%~2

if "%IMAGE_TAG%"=="" (
    set IMAGE_TAG=latest
)

set IMAGE_NAME=basnechkin-bot
set FULL_IMAGE_NAME=%DOCKER_USERNAME%/%IMAGE_NAME%:%IMAGE_TAG%

echo ========================================
echo Сборка и пуш образа в Docker Hub
echo ========================================
echo.
echo Имя пользователя: %DOCKER_USERNAME%
echo Имя образа: %IMAGE_NAME%
echo Тег: %IMAGE_TAG%
echo Полное имя: %FULL_IMAGE_NAME%
echo.

REM Проверка авторизации в Docker Hub
echo Проверка авторизации в Docker Hub...
docker info >nul 2>&1
if errorlevel 1 (
    echo Ошибка: Docker не запущен или не установлен
    exit /b 1
)

REM Сборка образа
echo.
echo [1/3] Сборка Docker образа...
docker build -t %FULL_IMAGE_NAME% .
if errorlevel 1 (
    echo Ошибка при сборке образа
    exit /b 1
)

REM Создание тега latest (если указан другой тег)
if not "%IMAGE_TAG%"=="latest" (
    echo.
    echo [1.5/3] Создание дополнительного тега latest...
    docker tag %FULL_IMAGE_NAME% %DOCKER_USERNAME%/%IMAGE_NAME%:latest
)

REM Пуш образа
echo.
echo [2/3] Отправка образа в Docker Hub...
docker push %FULL_IMAGE_NAME%
if errorlevel 1 (
    echo Ошибка при отправке образа
    echo Убедитесь, что вы авторизованы: docker login
    exit /b 1
)

REM Пуш тега latest (если был создан)
if not "%IMAGE_TAG%"=="latest" (
    echo.
    echo [2.5/3] Отправка тега latest...
    docker push %DOCKER_USERNAME%/%IMAGE_NAME%:latest
)

echo.
echo [3/3] Готово!
echo.
echo ========================================
echo Образ успешно загружен в Docker Hub
echo ========================================
echo.
echo Полное имя образа: %FULL_IMAGE_NAME%
echo.
echo Для использования образа выполните:
echo   docker pull %FULL_IMAGE_NAME%
echo.
echo Или в docker-compose.yml:
echo   image: %FULL_IMAGE_NAME%
echo.

endlocal

