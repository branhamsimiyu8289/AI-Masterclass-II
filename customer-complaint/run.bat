@echo off
setlocal
cd /d "%~dp0"
title Customer Complaint Reply Drafter

echo.
echo ================================================================
echo   Starting Customer Complaint Reply Drafter...
echo ================================================================
echo.

REM 1. Create config.env from template on first run if missing
if not exist "config.env" (
    if exist "config.env.example" (
        copy "config.env.example" "config.env" >nul
        echo Created config.env with default settings.
        echo You can edit config.env in Notepad anytime to update your business name or email.
        echo.
    )
)

REM 2. Locate Python (prefer local .venv if already set up)
set "PY_CMD="
if exist ".venv\Scripts\python.exe" (
    set "PY_CMD=.venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        set "PY_CMD=python"
    ) else (
        where py >nul 2>&1
        if %errorlevel%==0 (
            set "PY_CMD=py -3"
        )
    )
)

if "%PY_CMD%"=="" (
    echo [ERROR] Python is not installed on this computer.
    echo.
    echo Please install Python 3.10 or newer from https://www.python.org/downloads/
    echo Important: Tick "Add Python to PATH" during installation, then double-click run.bat again.
    echo.
    pause
    exit /b 1
)

REM 3. Ensure required packages are installed (automatic on first run)
%PY_CMD% -c "import flask, httpx" >nul 2>&1
if not %errorlevel%==0 (
    echo Setting up required components for first-time use. Please wait...
    if not exist ".venv\Scripts\python.exe" (
        %PY_CMD% -m venv .venv >nul 2>&1
        if exist ".venv\Scripts\python.exe" (
            set "PY_CMD=.venv\Scripts\python.exe"
        )
    )
    %PY_CMD% -m pip install --disable-pip-version-check -q -r requirements.txt
    if not %errorlevel%==0 (
        echo.
        echo [ERROR] Could not install required components.
        echo Check your internet connection and double-click run.bat again.
        echo.
        pause
        exit /b 1
    )
    echo Setup complete!
    echo.
)

REM 4. Start the tool (app.py validates config.env and opens your browser)
%PY_CMD% app.py
if not %errorlevel%==0 (
    echo.
    pause
    exit /b %errorlevel%
)

endlocal
