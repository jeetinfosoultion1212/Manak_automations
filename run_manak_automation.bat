@echo off
echo MANAK Automation Desktop Application
echo ====================================
echo.
echo Starting application...
echo.

cd /d "%~dp0"
if exist "dist\manak_desktop_app\manak_desktop_app.exe" (
    start "" "dist\manak_desktop_app\manak_desktop_app.exe"
) else (
    echo Error: Executable not found!
    echo Please run build_exe.py first to create the executable.
    pause
)
