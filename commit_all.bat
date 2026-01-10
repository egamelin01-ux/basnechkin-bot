@echo off
chcp 65001 >nul
cd /d "%~dp0"
git add -A
git status
echo.
echo Enter commit message (or press Enter for default):
set /p commit_msg=""
if "%commit_msg%"=="" (
    git commit -m "Update project files"
) else (
    git commit -m "%commit_msg%"
)
pause
