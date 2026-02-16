@echo off
REM Start the application minimized (runs in background)
title LAN File Share - Background Mode

REM Navigate to script directory
cd /d "%~dp0"

REM Start minimized
if not DEFINED IS_MINIMIZED set IS_MINIMIZED=1 && start "" /min "%~dpnx0" %* && exit

REM Run the application
python main.py

REM Keep window open on error
if errorlevel 1 (
    echo Application error occurred
    pause
)
