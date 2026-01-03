#!/usr/bin/env python3
"""
Desktop Application Launcher
Launch the MANAK Portal Desktop Application
"""

import sys
import os

def check_requirements():
    """Check if required packages are available"""
    try:
        import tkinter
        print("✓ Tkinter available")
    except ImportError:
        print("✗ Tkinter not available - GUI not supported in this environment")
        return False
    
    try:
        import selenium
        print("✓ Selenium available")
    except ImportError:
        print("✗ Selenium not available")
        return False
        
    return True

def main():
    print("MANAK Portal Desktop Application Launcher")
    print("=" * 50)
    
    if not check_requirements():
        print("\nCannot launch desktop application - missing requirements")
        print("This environment may not support GUI applications")
        print("\nAs an alternative, you can:")
        print("1. Use the web-based version that's currently running")
        print("2. Download and run this script on a local computer with desktop support")
        return
    
    print("\nLaunching desktop application...")
    
    try:
        from desktop_manak_app import ManakDesktopApp
        
        print("✓ Desktop application starting...")
        print("A GUI window should open shortly")
        
        app = ManakDesktopApp()
        app.run()
        
    except Exception as e:
        print(f"✗ Error launching application: {e}")
        print("\nThis cloud environment may not support desktop GUI applications.")
        print("Please use the web-based version instead.")

if __name__ == "__main__":
    main()