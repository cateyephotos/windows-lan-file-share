@echo off
title Create Desktop Shortcut
color 0B

echo ========================================
echo   Create Desktop Shortcut
echo ========================================
echo.

REM Get current directory
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Create VBS script to generate shortcut
echo Set oWS = WScript.CreateObject("WScript.Shell") > "%TEMP%\CreateShortcut.vbs"
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\LAN File Share.lnk" >> "%TEMP%\CreateShortcut.vbs"
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> "%TEMP%\CreateShortcut.vbs"
echo oLink.TargetPath = "%SCRIPT_DIR%\start.bat" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.WorkingDirectory = "%SCRIPT_DIR%" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Description = "Windows LAN File Share Utility" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.IconLocation = "shell32.dll,13" >> "%TEMP%\CreateShortcut.vbs"
echo oLink.Save >> "%TEMP%\CreateShortcut.vbs"

REM Execute VBS script
cscript //nologo "%TEMP%\CreateShortcut.vbs"

REM Clean up
del "%TEMP%\CreateShortcut.vbs"

if exist "%USERPROFILE%\Desktop\LAN File Share.lnk" (
    color 0A
    echo.
    echo [SUCCESS] Desktop shortcut created!
    echo.
    echo You can now launch the application from your desktop.
) else (
    color 0C
    echo.
    echo [ERROR] Failed to create shortcut
)

echo.
echo Press any key to continue...
pause >nul
