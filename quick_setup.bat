@echo off
echo MANAK Automation - Quick Setup
echo ==============================
echo.

echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo ✓ Python found
echo.

echo Installing requirements...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
)

echo ✓ Requirements installed
echo.

echo Building executable...
python build_exe.py
if errorlevel 1 (
    echo ERROR: Failed to build executable
    pause
    exit /b 1
)

echo.
echo ==============================
echo ✓ SETUP COMPLETE!
echo ==============================
echo.
echo The application is now ready to use!
echo.
echo To run the application:
echo 1. Double-click: run_manak_automation.bat
echo 2. Or navigate to: dist\MANAK_Automation\MANAK_Automation.exe
echo.
echo To distribute to other computers:
echo 1. Copy the entire folder to the target computer
echo 2. Run run_manak_automation.bat on the target computer
echo.
pause 