@echo off
title MANAK Automation Desktop Application
echo.
echo ========================================
echo  MANAK Automation Desktop Application
echo ========================================
echo.
echo Starting application...
echo.

cd /d "%~dp0"

if exist "dist\manak_desktop_app.exe" (
    echo Found executable, starting...
    start "" "dist\manak_desktop_app.exe"
) else (
    echo Error: Executable not found!
    echo Please run rebuild_comprehensive.py first.
    echo.
    pause
)
