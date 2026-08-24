import logging
from typing import Optional

logger = logging.getLogger(__name__)

class DesktopAgent:
    """
    Hooks for desktop automation to allow the AI to interact with the OS environment.
    Wraps existing automation_tools_new functions and provides an OOP interface.
    """
    def __init__(self):
        self._available = False
        try:
            from ai_assistant import automation_tools_new
            self.tools = automation_tools_new
            self._available = True
        except ImportError as e:
            logger.warning(f"Desktop automation tools not available: {e}")
            self.tools = None

    def is_available(self) -> bool:
        return self._available

    def open_application(self, app_name: str) -> str:
        if not self.is_available():
            return "Desktop automation is currently disabled."
        try:
            return self.tools.smart_open_application(app_name)
        except Exception as e:
            logger.error(f"Error opening application {app_name}: {e}")
            return f"Failed to open {app_name}: {e}"

    def close_application(self, app_name: str) -> str:
        if not self.is_available():
            return "Desktop automation is currently disabled."
        try:
            return self.tools.close_application(app_name)
        except Exception as e:
            logger.error(f"Error closing application {app_name}: {e}")
            return f"Failed to close {app_name}: {e}"

    def get_system_status(self) -> str:
        if not self.is_available():
            return "System status unavailable."
        try:
            return self.tools.get_system_status()
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return f"Failed to get system status: {e}"

    def play_music(self, query: str) -> str:
        if not self.is_available():
            return "Music integration is currently disabled."
        try:
            return self.tools.search_and_play_spotify(query)
        except Exception as e:
            logger.error(f"Error playing music: {e}")
            return f"Failed to play music: {e}"

desktop_agent = DesktopAgent()
