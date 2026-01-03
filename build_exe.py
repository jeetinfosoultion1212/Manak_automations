#!/usr/bin/env python3
"""
Build Script for MANAK Automation Desktop Application
Creates a standalone executable file
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_pyinstaller():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        print("PyInstaller is available")
        return True
    except ImportError:
        print("PyInstaller not found. Installing...")
        return False

def install_requirements():
    """Install required packages"""
    print("Installing requirements...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Requirements installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing requirements: {e}")
        return False

def create_spec_file():
    """Create PyInstaller spec file for the application"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['manak_desktop_app.py'],
    pathex=[],
    binaries=[
        ('chromedriver.exe', '.'),
    ],
    datas=[
        ('config', 'config'),
        ('device_license.py', '.'),
        ('multiple_jobs_processor.py', '.'),
        ('huid_data_processor.py', '.'),
        ('request_generator.py', '.'),
        ('submit_huid_data_api.php', '.'),
    ],
    hiddenimports=[
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.common.by',
        'selenium.webdriver.support',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.expected_conditions',
        'selenium.common.exceptions',
        'requests',
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'threading',
        'time',
        'random',
        'json',
        'os',
        'sys',
        'device_license',
        'multiple_jobs_processor',
        'huid_data_processor',
        'request_generator',
        'mysql.connector',
        'mysql.connector.locales',
        'mysql.connector.locales.eng',
        'mysql.connector.plugins',
        'mysql.connector.plugins.mysql_native_password',
        'mysql.connector.plugins.caching_sha2_password',
        'mysql.connector.cursor',
        'mysql.connector.pooling',
        'mysql.connector.errors',
        'job_cards_processor',
        'delivery_voucher_processor',
        'weight_capture_processor',
    ],
    hookspath=['.'],  # Use hooks from current directory
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='manak_desktop_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disable UPX for better Windows 7 compatibility
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
    
    with open('manak_desktop_app.spec', 'w') as f:
        f.write(spec_content)
    print("Spec file created")

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable...")
    try:
        # Clean previous builds
        if os.path.exists('build'):
            try:
                shutil.rmtree('build')
            except PermissionError:
                print("⚠️ Could not remove build folder (in use), continuing...")
        if os.path.exists('dist'):
            try:
                shutil.rmtree('dist')
            except PermissionError:
                print("⚠️ Could not remove dist folder (in use), continuing...")
        
        # Build using spec file with Windows 7 compatibility
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller", 
            "--clean", 
            "manak_desktop_app.spec"
        ])
        
        print("Executable built successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error building executable: {e}")
        return False

def create_launcher_script():
    """Create a simple launcher script"""
    launcher_content = '''@echo off
echo MANAK Automation Desktop Application
echo ====================================
echo.
echo Starting application...
echo.

cd /d "%~dp0"
if exist "dist\\manak_desktop_app\\manak_desktop_app.exe" (
    start "" "dist\\manak_desktop_app\\manak_desktop_app.exe"
) else (
    echo Error: Executable not found!
    echo Please run build_exe.py first to create the executable.
    pause
)
'''
    
    with open('run_manak_automation.bat', 'w') as f:
        f.write(launcher_content)
    print("Launcher script created")

def create_readme():
    """Create a README file with instructions"""
    readme_content = '''# MANAK Automation Desktop Application

## Overview
This is a desktop automation application for the MANAK portal that helps with weight entry and request management.

## Features
- 🔐 Automated browser login
- ⚖️ Weight entry automation
- 📋 Request acknowledgment
- 🔄 Order generation
- 🎯 Auto-fill capabilities

## Installation & Usage

### Option 1: Run from Source
1. Install Python 3.8 or higher
2. Install requirements: `pip install -r requirements.txt`
3. Run: `python desktop_manak_app.py`

### Option 2: Use Executable (Recommended)
1. Run: `python build_exe.py`
2. Wait for build to complete
3. Run: `run_manak_automation.bat`

### Option 3: Direct Executable
1. Navigate to `dist/MANAK_Automation/`
2. Run `MANAK_Automation.exe`

## System Requirements
- Windows 10/11
- Chrome browser installed
- Internet connection
- 4GB RAM minimum

## Configuration
- Username and password are pre-configured
- API endpoints can be modified in Settings tab
- Chrome driver is included in the package

## Troubleshooting
1. If Chrome doesn't open, ensure Chrome browser is installed
2. If login fails, check internet connection
3. If API calls fail, verify API endpoints in Settings

## Support
For technical support, contact the development team.

---
Built with Python, Selenium, and Tkinter
'''
    
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print("README file created")

def main():
    """Main build process"""
    print("MANAK Automation - Build Script")
    print("=" * 40)
    
    # Check and install requirements
    if not check_pyinstaller():
        if not install_requirements():
            print("Failed to install requirements. Exiting.")
            return
    
    # Create spec file
    create_spec_file()
    
    # Build executable
    if build_executable():
        # Create launcher script
        create_launcher_script()
        
        # Create README
        create_readme()
        
        print("\n" + "=" * 40)
        print("BUILD COMPLETE!")
        print("=" * 40)
        print("\nExecutable created in: dist/manak_desktop_app/")
        print("Launcher script: run_manak_automation.bat")
        print("\nTo run the application:")
        print("1. Double-click run_manak_automation.bat")
        print("2. Or navigate to dist/manak_desktop_app/ and run manak_desktop_app.exe")
        print("\nThe executable is now ready to distribute to other computers!")
    else:
        print("\n❌ Build failed. Please check the error messages above.")

if __name__ == "__main__":
    main() 