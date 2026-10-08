@echo off
chcp 65001 >nul
title EuroLeague Control Panel
cd /d "%~dp0"

echo ============================================================
echo   EuroLeague Control Panel
echo ============================================================
echo.

start "" cmd /c "timeout /t 3 >nul && start http://127.0.0.1:5001/"

py control\server.py

echo.
echo O server stamatise.
pause