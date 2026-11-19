@echo off
setlocal
echo ========================================================
echo   Zawadi Sales Reporter - 1-Click Automated Setup
echo ========================================================
echo Scheduling daily report to run automatically at 6:00 PM...
echo.
cd /d "%~dp0"
python setup_scheduler.py --install
echo.
echo ========================================================
echo Current Schedule Status:
python setup_scheduler.py --status
echo ========================================================
echo.
echo Setup completed successfully!
echo You can now close this window.
pause
