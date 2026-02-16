@echo off
title Windows LAN File Share - Client Mode
color 0E

echo ========================================
echo   LAN File Share - CLIENT MODE
echo ========================================
echo.
echo This will start the application in client mode
echo You can browse and download files from other computers
echo.
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo [ERROR] Python not found!
    pause
    exit /b 1
)

REM Navigate to script directory
cd /d "%~dp0"

REM Start application
echo Starting client...
echo.
python main.py

if errorlevel 1 (
    color 0C
    echo.
    echo [ERROR] Application failed to start
    pause
)
