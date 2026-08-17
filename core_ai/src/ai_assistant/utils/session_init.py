"""
Session Initialization Module - Import Redirect
===============================================

DEPRECATED: This file redirects to utils/session_init
DO NOT modify - import from utils.session_init directly instead
"""

import sys
import importlib.util
from pathlib import Path

# Dynamically load the main utils.session_init bypassing sys.path collisions
main_module = Path(__file__).resolve().parent.parent.parent / "utils" / "session_init.py"
spec = importlib.util.spec_from_file_location("main_utils_session_init", str(main_module))
main_utils = importlib.util.module_from_spec(spec)
sys.modules["main_utils_session_init"] = main_utils
spec.loader.exec_module(main_utils)

# Re-export everything from main session_init to maintain compatibility
from main_utils_session_init import *

# Explicitly re-export key items
from main_utils_session_init import (
    session_id,
    SESSION_START_TIME,
    CURRENT_SESSION_ID,
    get_session_info,
    log_module_initialization
)