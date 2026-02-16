@echo off
title Windows LAN File Share - Server Mode
color 0B

echo ========================================
echo   LAN File Share - SERVER MODE
echo ========================================
echo.
echo This will start the application in server mode
echo You can share files with other computers on your network
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
echo Starting server...
echo.
python main.py

if errorlevel 1 (
    color 0C
    echo.
    echo [ERROR] Application failed to start
    pause
)
