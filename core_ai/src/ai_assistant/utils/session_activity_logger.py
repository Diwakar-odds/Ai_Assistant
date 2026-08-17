"""
Session Activity Logger - Import Redirect
=========================================

This module redirects to the main session_activity_logger in utils/
to prevent duplicate instances.

DO NOT MODIFY - import from utils.session_activity_logger directly instead.
"""

import sys
import importlib.util
from pathlib import Path

# Dynamically load the main utils.session_activity_logger bypassing sys.path collisions
main_module = Path(__file__).resolve().parent.parent.parent / "utils" / "session_activity_logger.py"
spec = importlib.util.spec_from_file_location("main_utils_session_activity_logger", str(main_module))
main_utils = importlib.util.module_from_spec(spec)
sys.modules["main_utils_session_activity_logger"] = main_utils
spec.loader.exec_module(main_utils)

from main_utils_session_activity_logger import (
    SessionActivityLogger,
    session_activity_logger,
    get_session_activity_logger,
    log_voice_command,
    log_file_operation,
    log_system_command,
    log_api_request,
    log_user_interaction,
    log_music_control,
    log_email_operation,
    log_calendar_operation,
    log_web_scraping,
    log_multimodal_ai,
    log_automation,
    end_current_session as end_session
)

__all__ = [
    'SessionActivityLogger',
    'session_activity_logger',
    'get_session_activity_logger',
    'log_voice_command',
    'log_file_operation',
    'log_system_command',
    'log_api_request',
    'log_user_interaction',
    'log_music_control',
    'log_email_operation',
    'log_calendar_operation',
    'log_web_scraping',
    'log_multimodal_ai',
    'log_automation',
    'end_session'
]
