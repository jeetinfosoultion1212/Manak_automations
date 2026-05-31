#!/usr/bin/env python3
"""
Complete Build Script for MANAK Automation Desktop Application
Creates a standalone executable with ALL features including:
- Embedded Browser
- All Processors
- License Management
- API Integration
- Support for all Windows versions (Win7, Win10, Win11)
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import time

class Colors:
    """Console colors for better output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.END}\n")

def print_step(step, text):
    """Print formatted step"""
    print(f"{Colors.CYAN}[Step {step}]{Colors.END} {Colors.BOLD}{text}{Colors.END}")

def print_success(text):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def check_python_version():
    """Check if Python version is compatible"""
    print_step(1, "Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python 3.8 or higher required. Current: {version.major}.{version.minor}")
        return False
    print_success(f"Python {version.major}.{version.minor}.{version.micro} detected")
    return True

def check_required_files():
    """Check if all required files exist"""
    print_step(2, "Checking required files...")
    
    required_files = [
        'src/manak_desktop_app.py',
        'src/license/device_license.py',
        'src/processors/simple_embedded_browser.py',
        'requirements.txt',
        'manak_desktop_app_complete.spec',
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
            print_error(f"Missing: {file}")
        else:
            print_success(f"Found: {file}")
    
    if missing_files:
        print_error("Some required files are missing!")
        return False
    
    return True

def install_dependencies():
    """Install all required dependencies"""
    print_step(3, "Installing dependencies...")
    
    try:
        print("📦 Installing packages from requirements.txt...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--upgrade"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print_success("All dependencies installed")
        
        # Install PyInstaller if not present
        try:
            import PyInstaller
            print_success("PyInstaller is available")
        except ImportError:
            print("📦 Installing PyInstaller...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "pyinstaller>=6.0"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print_success("PyInstaller installed")
        
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        return False

def clean_build_folders():
    """Clean previous build folders"""
    print_step(4, "Cleaning previous builds...")
    
    folders_to_clean = ['build', 'dist', '__pycache__']
    
    for folder in folders_to_clean:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print_success(f"Removed: {folder}")
            except PermissionError:
                print_warning(f"Could not remove {folder} (in use), continuing...")
            except Exception as e:
                print_warning(f"Error removing {folder}: {e}")
    
    # Clean .pyc files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                try:
                    os.remove(os.path.join(root, file))
                except:
                    pass
    return True

def create_hook_files():
    """Create PyInstaller hook files for better module detection"""
    print_step(5, "Creating PyInstaller hooks...")
    
    os.makedirs('scripts', exist_ok=True)
    
    # Hook for webview
    webview_hook = """
# Hook for pywebview
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('webview')

hiddenimports += [
    'webview',
    'webview.window',
    'webview.guilib',
    'clr',
]
"""
    
    with open('scripts/hook-webview.py', 'w', encoding='utf-8') as f:
        f.write(webview_hook)
    print_success("Created webview hook")
    
    # Hook for mysql.connector
    mysql_hook = """
# Hook for mysql-connector-python
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('mysql.connector')

hiddenimports += [
    'mysql.connector.locales.eng',
    'mysql.connector.plugins.caching_sha2_password',
    'mysql.connector.plugins.mysql_native_password',
]
"""
    
    with open('scripts/hook-mysql.connector.py', 'w', encoding='utf-8') as f:
        f.write(mysql_hook)
    print_success("Created MySQL hook")
    return True

def build_executable():
    """Build the executable using PyInstaller"""
    print_step(6, "Building executable (this may take several minutes)...")
    
    try:
        start_time = time.time()
        
        # Build command
        build_cmd = [
            sys.executable, 
            "-m", 
            "PyInstaller",
            "--clean",
            "--noconfirm",
            "manak_desktop_app_complete.spec"
        ]
        
        print(f"🔨 Running: {' '.join(build_cmd)}")
        
        # Run build process
        process = subprocess.Popen(
            build_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Show progress
        for line in process.stdout:
            if "INFO:" in line:
                print(f"  {line.strip()}")
        
        process.wait()
        
        if process.returncode == 0:
            elapsed = time.time() - start_time
            print_success(f"Build completed in {elapsed:.1f} seconds")
            return True
        else:
            print_error("Build failed")
            return False
            
    except subprocess.CalledProcessError as e:
        print_error(f"Build error: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        return False

def create_distribution_package():
    """Create distribution package with all necessary files"""
    print_step(7, "Creating distribution package...")
    
    # Create distribution folder
    dist_folder = "MANAK_Automation_Distribution"
    if os.path.exists(dist_folder):
        shutil.rmtree(dist_folder)
    os.makedirs(dist_folder)
    
    # Copy executable
    if os.path.exists("dist/MANAK_Automation.exe"):
        shutil.copy2("dist/MANAK_Automation.exe", f"{dist_folder}/MANAK_Automation.exe")
        print_success("Copied executable")
    
    # Copy portable version if exists
    if os.path.exists("dist/MANAK_Automation_Portable"):
        shutil.copytree("dist/MANAK_Automation_Portable", f"{dist_folder}/MANAK_Automation_Portable")
        print_success("Copied portable version")
    
    # Copy config files
    if os.path.exists("config"):
        shutil.copytree("config", f"{dist_folder}/config")
        print_success("Copied config files")
    
    # Copy documentation
    docs_to_copy = [
        'docs/EMBEDDED_BROWSER_GUIDE.md',
        'docs/USER_GUIDE.md',
        'docs/SETUP_GUIDE.md',
        'EMBEDDED_BROWSER_UPDATE.md',
        'README.md'
    ]
    
    os.makedirs(f"{dist_folder}/docs", exist_ok=True)
    for doc in docs_to_copy:
        if os.path.exists(doc):
            shutil.copy2(doc, f"{dist_folder}/docs/{os.path.basename(doc)}")
    print_success("Copied documentation")
    
    # Create launcher script
    launcher_content = """@echo off
title MANAK Automation
echo.
echo ================================================
echo    MANAK Automation Desktop Application
echo ================================================
echo.
echo Starting application...
echo.

REM Run the executable
start "" "MANAK_Automation.exe"

REM Wait a moment
timeout /t 2 /nobreak >nul

echo.
echo Application started!
echo You can close this window.
echo.
"""
    
    with open(f"{dist_folder}/Run_MANAK_Automation.bat", 'w', encoding='utf-8') as f:
        f.write(launcher_content)
    print_success("Created launcher script")
    
    # Create installation guide
    install_guide = """# MANAK Automation - Installation Guide

## Quick Start

1. **First Time Setup:**
   - Double-click `Run_MANAK_Automation.bat`
   - Or run `MANAK_Automation.exe` directly

2. **Install Embedded Browser (Optional but Recommended):**
   - Open application
   - Go to Settings tab
   - Click "Install Embedded Browser"
   - Restart application

3. **Login:**
   - Enter your portal credentials
   - Click Login
   - Start using the application

## Features Included

✅ Embedded Browser (prevents logout issues)
✅ Bulk Jobs Processing
✅ Weight Entry Automation
✅ Job Cards Creation
✅ Delivery Voucher Management
✅ License Management
✅ API Integration

## System Requirements

- Windows 7 / 8 / 10 / 11
- 4GB RAM minimum
- Internet connection
- Chrome browser (for external browser features)

## Troubleshooting

**Application won't start:**
- Make sure you extracted all files
- Run as Administrator
- Check antivirus isn't blocking it

**Embedded Browser not working:**
- Run: `pip install pywebview`
- Or use the installation script in the app

**License issues:**
- Check internet connection
- Verify credentials with administrator
- Check firewall settings

## Support

For help, contact your system administrator.

Read the complete guides in the `docs` folder.
"""
    
    with open(f"{dist_folder}/INSTALLATION_GUIDE.txt", 'w', encoding='utf-8') as f:
        f.write(install_guide)
    print_success("Created installation guide")
    
    print_success(f"Distribution package created: {dist_folder}/")
    return True

def verify_build():
    """Verify that the build was successful"""
    print_step(8, "Verifying build...")
    
    expected_files = [
        'dist/MANAK_Automation.exe',
    ]
    
    all_found = True
    for file in expected_files:
        if os.path.exists(file):
            size_mb = os.path.getsize(file) / (1024 * 1024)
            print_success(f"Found: {file} ({size_mb:.1f} MB)")
        else:
            print_error(f"Missing: {file}")
            all_found = False
    
    return all_found

def print_final_instructions():
    """Print final instructions"""
    print_header("BUILD COMPLETE!")
    
    print(f"{Colors.GREEN}✨ Your executable is ready!{Colors.END}\n")
    
    print(f"{Colors.BOLD}📦 Files created:{Colors.END}")
    print(f"  • dist/MANAK_Automation.exe (single file)")
    print(f"  • MANAK_Automation_Distribution/ (complete package)")
    
    print(f"\n{Colors.BOLD}🚀 To run the application:{Colors.END}")
    print(f"  • Double-click: dist/MANAK_Automation.exe")
    print(f"  • Or use: MANAK_Automation_Distribution/Run_MANAK_Automation.bat")
    
    print(f"\n{Colors.BOLD}📤 To distribute to users:{Colors.END}")
    print(f"  • Zip the MANAK_Automation_Distribution folder")
    print(f"  • Send to users")
    print(f"  • Users extract and run Run_MANAK_Automation.bat")
    
    print(f"\n{Colors.BOLD}✅ What's included:{Colors.END}")
    print(f"  • All processors (Bulk Jobs, Weight Entry, etc.)")
    print(f"  • Embedded Browser (prevents logout)")
    print(f"  • License Management")
    print(f"  • API Integration")
    print(f"  • Complete documentation")
    
    print(f"\n{Colors.BOLD}💡 Compatibility:{Colors.END}")
    print(f"  • Windows 7 ✅")
    print(f"  • Windows 8/8.1 ✅")
    print(f"  • Windows 10 ✅")
    print(f"  • Windows 11 ✅")
    
    print(f"\n{Colors.BOLD}📚 Documentation:{Colors.END}")
    print(f"  • MANAK_Automation_Distribution/docs/EMBEDDED_BROWSER_GUIDE.md")
    print(f"  • MANAK_Automation_Distribution/docs/USER_GUIDE.md")
    print(f"  • MANAK_Automation_Distribution/INSTALLATION_GUIDE.txt")
    
    print(f"\n{Colors.GREEN}{'='*60}{Colors.END}")

def main():
    """Main build process"""
    print_header("MANAK Automation - Complete Build System")
    
    print(f"{Colors.BOLD}This script will:{Colors.END}")
    print("  1. Check Python version")
    print("  2. Verify required files")
    print("  3. Install dependencies")
    print("  4. Clean previous builds")
    print("  5. Create build hooks")
    print("  6. Build executable")
    print("  7. Create distribution package")
    print("  8. Verify build")
    print()
    
    input("Press Enter to start the build process...")
    
    # Execute build steps
    steps = [
        check_python_version,
        check_required_files,
        # install_dependencies,
        clean_build_folders,
        create_hook_files,
        build_executable,
        create_distribution_package,
        verify_build,
    ]
    
    for step_func in steps:
        if not step_func():
            print_error("\n❌ Build failed! Please fix the errors above and try again.")
            input("\nPress Enter to exit...")
            sys.exit(1)
        print()  # Add spacing between steps
    
    print_final_instructions()
    
    input("\n✨ Press Enter to exit...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_error("\n\nBuild cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
