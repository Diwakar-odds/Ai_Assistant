"""
Logging Configuration - Import Redirect
=======================================

This module redirects to the main logging_config in utils/
to prevent duplicate instances and session conflicts.

DO NOT MODIFY - import from utils.logging_config directly instead.
"""

import sys
import importlib.util
from pathlib import Path

# Dynamically load the main utils.logging_config bypassing sys.path collisions
main_logging_config = Path(__file__).resolve().parent.parent.parent / "utils" / "logging_config.py"
spec = importlib.util.spec_from_file_location("main_utils_logging_config", str(main_logging_config))
main_utils = importlib.util.module_from_spec(spec)
sys.modules["main_utils_logging_config"] = main_utils
spec.loader.exec_module(main_utils)

from main_utils_logging_config import *

__all__ = [
    'SessionManager',
    'LoggingConfig', 
    'get_logger',
    'get_api_logger'
]
