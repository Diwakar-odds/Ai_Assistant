#!/usr/bin/env python3
"""
Quick launch script for AI Assistant Windows Desktop App (for development)
Use this to test the app before building the executable.
"""

import subprocess
import sys

if __name__ == '__main__':
    print("=" * 60)
    print("AI Assistant - Windows Desktop App (Dev Mode)")
    print("=" * 60)
    print()
    
    try:
        # First, ensure dependencies are installed
        print("Checking dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pywebview'], 
                      check=False, capture_output=True)
        
        # Run the Windows app
        subprocess.run([sys.executable, 'windows_app.py'])
        
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
