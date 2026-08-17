
import runpy
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.getcwd())

print(f"sys.path: {sys.path}")

try:
    # Try to import the module directly to see the error
    from ai_assistant.services import modern_web_backend
    print("Import successful")
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
