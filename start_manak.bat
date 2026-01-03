@echo off
title MANAK Automation Launcher
echo.
echo ========================================
echo    MANAK Automation - Launcher
echo ========================================
echo.
echo Starting application launcher...
echo.

python start_app.py

if %errorlevel% neq 0 (
    echo.
    echo Error: Failed to start the application
    echo Please make sure Python is installed and in your PATH
    echo.
    pause
) 