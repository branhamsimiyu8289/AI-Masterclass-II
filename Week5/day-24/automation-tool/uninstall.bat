@echo off
setlocal
echo ========================================================
echo   Zawadi Sales Reporter - Uninstall Schedule
echo ========================================================
cd /d "%~dp0"
python setup_scheduler.py --uninstall
echo.
pause
