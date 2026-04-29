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

if not exist ".venv\Scripts\python.exe" (
    echo Creating local virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo Error: Could not create .venv.
        pause
        exit /b
    )
)

echo Installing/updating dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error: Could not install dependencies.
    pause
    exit /b
)

if not exist ".env" (
    echo DISCORD_BOT_TOKEN=put-your-discord-bot-token-here> .env
    echo Created .env. Open it and replace put-your-discord-bot-token-here with your real Discord bot token.
    echo Then run start_bot.bat again.
    pause
    exit /b
)

findstr /C:"put-your-discord-bot-token-here" ".env" >nul 2>&1
if %errorlevel% equ 0 (
    echo .env still contains the placeholder token.
    echo Open .env and replace put-your-discord-bot-token-here with your real Discord bot token.
    pause
    exit /b
)

:: Run the bot
".venv\Scripts\python.exe" main.py

:: If the bot crashes or is stopped, keep window open to see error
echo.
echo ---------------------------------------
echo Bot has stopped. See error message above.
echo ---------------------------------------
pause
