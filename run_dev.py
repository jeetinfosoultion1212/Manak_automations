#!/usr/bin/env python3
"""
Development Launcher for MANAK Automation
Bypasses license verification for testing purposes
"""

import os
import sys
import subprocess

def run_in_dev_mode():
    """Run the application in development mode"""
    print("🔧 Starting MANAK Automation in Development Mode")
    print("License verification will be bypassed for testing")
    print("-" * 50)
    
    # Set development mode environment variable
    env = os.environ.copy()
    env['MANAK_DEV_MODE'] = '1'
    
    try:
        # Run the main application
        result = subprocess.run([sys.executable, 'desktop_manak_app.py'], 
                              env=env, 
                              cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            print("\n✅ Application closed successfully")
        else:
            print(f"\n❌ Application exited with code {result.returncode}")
            
    except KeyboardInterrupt:
        print("\n⚠️ Application interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running application: {e}")

if __name__ == "__main__":
    run_in_dev_mode() 