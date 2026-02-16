@echo off
REM Install as Windows service (requires admin privileges)
title LAN File Share - Service Installer
color 0B

echo ========================================
echo   Install as Windows Service
echo ========================================
echo.
echo This will install LAN File Share as a Windows service
echo that starts automatically when Windows boots.
echo.
echo NOTE: This requires Administrator privileges
echo.
echo ========================================
echo.

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% neq 0 (
    color 0C
    echo [ERROR] This script requires Administrator privileges
    echo.
    echo Right-click this file and select "Run as administrator"
    echo.
    pause
    exit /b 1
)

echo [INFO] Administrator privileges confirmed
echo.
echo [WARNING] Service installation requires additional setup
echo This feature is for advanced users only.
echo.
echo To install as a service, you'll need:
echo   1. Install NSSM (Non-Sucking Service Manager)
echo   2. Or use Python packages like pywin32
echo.
echo For now, use Task Scheduler to run at startup:
echo   1. Open Task Scheduler
echo   2. Create Basic Task
echo   3. Set trigger to "At startup"
echo   4. Set action to run: %~dp0start-minimized.bat
echo.
pause
