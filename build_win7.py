#!/usr/bin/env python3
"""
Windows 7 Compatible Build Script for MANAK Automation Desktop Application
Creates a standalone executable file optimized for Windows 7
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def create_win7_spec_file():
    """Create PyInstaller spec file optimized for Windows 7"""
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
        ('ui_tabs', 'ui_tabs'),
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
        'sqlite3',
        'psutil'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='manak_desktop_app_win7',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disable UPX for Windows 7 compatibility
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
    
    with open('manak_desktop_app_win7.spec', 'w') as f:
        f.write(spec_content)
    print("✓ Windows 7 spec file created")

def build_win7_executable():
    """Build the executable optimized for Windows 7"""
    print("Building Windows 7 compatible executable...")
    try:
        # Clean previous builds
        if os.path.exists('build'):
            shutil.rmtree('build')
        if os.path.exists('dist'):
            shutil.rmtree('dist')
        
        # Build using spec file
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller", 
            "--clean", 
            "manak_desktop_app_win7.spec"
        ])
        
        print("✓ Windows 7 executable built successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error building executable: {e}")
        return False

def create_win7_readme():
    """Create Windows 7 specific README"""
    readme_content = '''# MANAK Automation Desktop Application - Windows 7 Version

## Windows 7 Compatibility Notes

### System Requirements:
- Windows 7 Service Pack 1 (SP1)
- Minimum 2GB RAM (4GB recommended)
- DirectX 9.0c compatible graphics card
- Chrome browser version 109 or earlier (for Windows 7)

### Installation:
1. Extract all files to a folder
2. Run `manak_desktop_app_win7.exe`
3. If Chrome doesn't work, install Chrome version 109 or earlier

### Troubleshooting Windows 7:
1. **Chrome Issues**: Install Chrome version 109 or earlier
2. **Missing DLLs**: Install Visual C++ Redistributable 2015-2022
3. **Slow Performance**: Close other applications to free up RAM
4. **Security Warnings**: Right-click exe → Properties → Unblock

### Alternative Browsers:
If Chrome doesn't work, the application can be modified to use Firefox WebDriver.

---
Built with Python 3.12 and PyInstaller for Windows 7 compatibility
'''
    
    with open('README_Windows7.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print("✓ Windows 7 README created")

def main():
    """Main Windows 7 build process"""
    print("MANAK Automation - Windows 7 Build Script")
    print("=" * 50)
    
    # Create Windows 7 spec file
    create_win7_spec_file()
    
    # Build executable
    if build_win7_executable():
        # Create README
        create_win7_readme()
        
        print("\n" + "=" * 50)
        print("✅ WINDOWS 7 BUILD COMPLETE!")
        print("=" * 50)
        print("\nExecutable created: dist/manak_desktop_app_win7.exe")
        print("Size: ~30MB")
        print("\nWindows 7 Compatibility Features:")
        print("- Disabled UPX compression")
        print("- Included all dependencies")
        print("- Optimized for Windows 7 SP1")
        print("\nTo run on Windows 7:")
        print("1. Copy the entire dist folder")
        print("2. Run manak_desktop_app_win7.exe")
        print("3. Ensure Chrome version 109 or earlier is installed")
    else:
        print("\n❌ Windows 7 build failed.")

if __name__ == "__main__":
    main()
