@echo off
title Windows LAN File Share - Quick Start
color 0D

:menu
cls
echo ========================================
echo   Windows LAN File Share - Quick Start
echo ========================================
echo.
echo Select an option:
echo.
echo   1. Start Application (Full GUI)
echo   2. Start as Server (Share Files)
echo   3. Start as Client (Download Files)
echo   4. Run Setup
echo   5. Create Desktop Shortcut
echo   6. Exit
echo.
echo ========================================
echo.

set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto start_full
if "%choice%"=="2" goto start_server
if "%choice%"=="3" goto start_client
if "%choice%"=="4" goto run_setup
if "%choice%"=="5" goto create_shortcut
if "%choice%"=="6" goto exit

echo Invalid choice. Please try again.
timeout /t 2 >nul
goto menu

:start_full
cls
echo Starting full application...
call start.bat
goto end

:start_server
cls
echo Starting server mode...
call start-server.bat
goto end

:start_client
cls
echo Starting client mode...
call start-client.bat
goto end

:run_setup
cls
echo Running setup...
python setup.py
pause
goto menu

:create_shortcut
cls
call create-shortcut.bat
pause
goto menu

:exit
echo Goodbye!
timeout /t 1 >nul
exit

:end
