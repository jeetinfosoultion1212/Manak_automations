@echo off
echo MANAK Automation - Distribution Package Creator
echo ===============================================
echo.

echo Creating distribution package...
echo.

REM Create distribution directory
if not exist "MANAK_Automation_Distribution" mkdir "MANAK_Automation_Distribution"
if not exist "MANAK_Automation_Distribution\MANAK_Automation" mkdir "MANAK_Automation_Distribution\MANAK_Automation"

REM Copy executable and dependencies
echo Copying executable files...
if exist "dist\MANAK_Automation" (
    xcopy "dist\MANAK_Automation\*" "MANAK_Automation_Distribution\MANAK_Automation\" /E /I /Y
    echo ✓ Executable files copied
) else (
    echo ERROR: Executable not found. Please run build_exe.py first.
    pause
    exit /b 1
)

REM Copy Chrome driver
echo Copying Chrome driver...
if exist "chromedriver.exe" (
    copy "chromedriver.exe" "MANAK_Automation_Distribution\MANAK_Automation\" >nul
    echo ✓ Chrome driver copied
) else (
    echo WARNING: Chrome driver not found
)

REM Create launcher script for distribution
echo Creating launcher script...
(
echo @echo off
echo echo MANAK Automation Desktop Application
echo echo ====================================
echo echo.
echo echo Starting application...
echo echo.
echo.
echo cd /d "%%~dp0"
echo if exist "MANAK_Automation.exe" ^(
echo     start "" "MANAK_Automation.exe"
echo ^) else ^(
echo     echo Error: Executable not found!
echo     pause
echo ^)
) > "MANAK_Automation_Distribution\Run_MANAK_Automation.bat"

echo ✓ Launcher script created

REM Create README for distribution
echo Creating README...
(
echo # MANAK Automation - Desktop Application
echo.
echo ## Quick Start
echo 1. Double-click: Run_MANAK_Automation.bat
echo 2. Or run: MANAK_Automation.exe directly
echo.
echo ## System Requirements
echo - Windows 10/11
echo - Chrome browser installed
echo - Internet connection
echo - 4GB RAM minimum
echo.
echo ## Features
echo - Automated browser login
echo - Weight entry automation
echo - Request acknowledgment
echo - Order generation
echo - Auto-fill capabilities
echo.
echo ## Troubleshooting
echo 1. If Chrome doesn't open, ensure Chrome browser is installed
echo 2. If login fails, check internet connection
echo 3. If API calls fail, verify API endpoints in Settings
echo.
echo ## Support
echo For technical support, contact the development team.
) > "MANAK_Automation_Distribution\README.txt"

echo ✓ README created

REM Create ZIP file
echo Creating ZIP package...
powershell -command "Compress-Archive -Path 'MANAK_Automation_Distribution\*' -DestinationPath 'MANAK_Automation_Package.zip' -Force"
if errorlevel 1 (
    echo WARNING: Could not create ZIP file. Manual distribution required.
) else (
    echo ✓ ZIP package created: MANAK_Automation_Package.zip
)

echo.
echo ===============================================
echo ✓ DISTRIBUTION PACKAGE CREATED!
echo ===============================================
echo.
echo Distribution folder: MANAK_Automation_Distribution\
echo ZIP package: MANAK_Automation_Package.zip
echo.
echo To distribute to other computers:
echo 1. Copy the MANAK_Automation_Distribution folder
echo 2. Or share the MANAK_Automation_Package.zip file
echo 3. On target computer, run Run_MANAK_Automation.bat
echo.
pause 