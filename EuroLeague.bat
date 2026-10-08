@echo off
chcp 65001 >nul
title EuroLeague
cd /d "%~dp0"

echo ============================================================
echo   EuroLeague App
echo ============================================================
echo.

start "" cmd /c "timeout /t 3 >nul && start http://127.0.0.1:5000/"

py app\server.py

echo.
echo O server stamatise.
pause