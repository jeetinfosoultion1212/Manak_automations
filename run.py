#!/usr/bin/env python3
"""
MANAK Automation - Quick Start
Double-click this file or run: python run.py
"""

import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

if __name__ == '__main__':
    print("=" * 60)
    print("Starting MANAK Automation...")
    print("=" * 60)
    
    try:
        # Import the app
        from manak_desktop_app import ManakDesktopApp
        
        # Create and run app
        app = ManakDesktopApp()
        app.run()
        
    except Exception as e:
        print(f"\nError starting application: {e}")
        print("\nPress Enter to exit...")
        input()
