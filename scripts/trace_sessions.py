import sys
import traceback

# Monkey-patch to trace session creation
orig_start_new_session = None

def trace_session_start(cls):
    print('\n===== SESSION CREATION TRACEBACK =====')
    traceback.print_stack(limit=20)
    print('======================================\n')
    return orig_start_new_session(cls)

# Patch SessionManager BEFORE it's imported
print('Patching SessionManager...')
from utils.logging_config import SessionManager
orig_start_new_session = SessionManager.start_new_session
SessionManager.start_new_session = classmethod(trace_session_start)

# Now import modern_web_backend
print('\nAbout to import modern_web_backend...\n')
import ai_assistant.services.modern_web_backend
print('\n Done importing modern_web_backend\n')
