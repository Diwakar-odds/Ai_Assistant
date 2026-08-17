
import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

try:
    from ai_assistant.services import modern_web_backend
    print("Successfully imported modern_web_backend")
except ImportError as e:
    print(f"Failed to import modern_web_backend: {e}")

try:
    from ai_assistant import automation_tools_new
    print("Successfully imported automation_tools_new")
except ImportError as e:
    print(f"Failed to import automation_tools_new: {e}")
