@echo off
echo Starting Windows LAN File Share Utility...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Check if main.py exists
if not exist "main.py" (
    echo Error: main.py not found in current directory
    echo Please ensure you are running this from the project folder
    pause
    exit /b 1
)

REM Start the application
echo Starting the application...
python main.py

REM Keep window open if there was an error
if errorlevel 1 (
    echo.
    echo Application exited with an error. Press any key to close...
    pause >nul
)
