@echo off
echo ========================================
echo MANAK Automation - Starting...
echo ========================================
echo.

python run.py

if errorlevel 1 (
    echo.
    echo ========================================
   echo ERROR: Application failed to start!
    echo ========================================
    echo.
    pause
)
