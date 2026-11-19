@echo off
setlocal
echo ========================================================
echo   Zawadi Sales Reporter - Schedule Status Check
echo ========================================================
cd /d "%~dp0"
python setup_scheduler.py --status
echo.
pause
