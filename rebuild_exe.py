#!/usr/bin/env python3
"""
Quick rebuild script for MANAK Automation Desktop Application
Rebuilds the executable with updated dependencies
"""

import os
import sys
import subprocess
import shutil

def clean_build():
    """Clean previous build artifacts"""
    print("🧹 Cleaning previous build...")
    
    folders_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['*.pyc', '*.pyo']
    
    for folder in folders_to_clean:
        if os.path.exists(folder):
            try:
                shutil.rmtree(folder)
                print(f"✓ Removed {folder}")
            except PermissionError:
                print(f"⚠️ Could not remove {folder} (in use)")
    
    # Clean .pyc files
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith(('.pyc', '.pyo')):
                try:
                    os.remove(os.path.join(root, file))
                except:
                    pass

def build_executable():
    """Build the executable using PyInstaller"""
    print("🔨 Building executable...")
    
    try:
        # Use the updated spec file
        cmd = [
            sys.executable, "-m", "PyInstaller", 
            "--clean", 
            "--noconfirm",
            "MANAK_Automation.spec"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Build successful!")
            return True
        else:
            print("❌ Build failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error during build: {e}")
        return False

def check_executable():
    """Check if executable was created successfully"""
    exe_path = "dist/manak_desktop_app/manak_desktop_app.exe"
    
    if os.path.exists(exe_path):
        size = os.path.getsize(exe_path)
        print(f"✅ Executable created: {exe_path}")
        print(f"📦 Size: {size / (1024*1024):.1f} MB")
        return True
    else:
        print(f"❌ Executable not found: {exe_path}")
        return False

def main():
    """Main rebuild process"""
    print("MANAK Automation - Quick Rebuild")
    print("=" * 40)
    
    # Clean previous build
    clean_build()
    
    # Build executable
    if build_executable():
        if check_executable():
            print("\n" + "=" * 40)
            print("🎉 REBUILD COMPLETE!")
            print("=" * 40)
            print("\nExecutable location: dist/manak_desktop_app/manak_desktop_app.exe")
            print("\nThe executable now includes:")
            print("✓ Job Cards Processor module")
            print("✓ Multiple Jobs Processor module") 
            print("✓ HUID Data Processor module")
            print("✓ All required dependencies")
            print("✓ Enhanced error handling")
            print("\nTry running the executable now - the job data loading should work!")
        else:
            print("\n❌ Executable creation failed")
    else:
        print("\n❌ Build process failed")

if __name__ == "__main__":
    main()
