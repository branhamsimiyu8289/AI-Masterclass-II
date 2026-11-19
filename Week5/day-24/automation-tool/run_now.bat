@echo off
setlocal
echo ========================================================
echo   Zawadi Sales Reporter - Run On Demand
echo ========================================================
cd /d "%~dp0"
python sales_reporter.py
echo.
echo Check run_log.txt for execution log.
pause
