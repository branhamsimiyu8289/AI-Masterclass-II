@echo off
setlocal
title Invoice Reminder Automation Service

echo ==============================================================================
echo        INVOICE REMINDER AUTOMATION SERVICE - CLIENT DISPATCH RUNNER
echo ==============================================================================
echo.

cd /d "%~dp0"

:: Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python was not found in your system PATH.
    echo Please install Python 3.9+ from https://python.org or your app store.
    pause
    exit /b 1
)

:: Run script
python invoice_reminder.py %*

echo.
echo ==============================================================================
echo Process completed. Drafted emails are saved in the Outbox\ folder.
echo ==============================================================================
pause
