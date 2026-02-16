@echo off
title Windows LAN File Share - Launcher
color 0A

echo ========================================
echo   Windows LAN File Share Utility
echo ========================================
echo.

REM Check if Python is installed
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo [ERROR] Python is not installed or not in PATH
    echo.
    echo Please install Python 3.6+ from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    echo.
    pause
    exit /b 1
)

REM Display Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo [OK] Python %PYVER% detected
echo.

REM Check if main.py exists
echo [2/3] Checking application files...
if not exist "main.py" (
    color 0C
    echo [ERROR] main.py not found in current directory
    echo Please ensure you are running this from the project folder
    echo.
    pause
    exit /b 1
)
echo [OK] Application files found
echo.

REM Start the application
echo [3/3] Starting the application...
echo.
echo ========================================
echo   Application is now running
echo   Close this window to exit
echo ========================================
echo.

python main.py

REM Keep window open if there was an error
if errorlevel 1 (
    color 0C
    echo.
    echo ========================================
    echo   Application exited with an error
    echo ========================================
    echo.
    pause
)
