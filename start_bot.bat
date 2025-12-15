@echo off
title TikTok Embed Fixer Bot
:: Change directory to the script's location
cd /d "%~dp0"

echo Starting TikTok Fixer Bot...
echo Path: %~dp0
echo.

:: Check if python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in your PATH.
    pause
    exit /b
)

:: Run the bot
python main.py

:: If the bot crashes or is stopped, keep window open to see error
echo.
echo ---------------------------------------
echo Bot has stopped. See error message above.
echo ---------------------------------------
pause
