# MANAK Automation Desktop Application

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
