import logging
import psutil

logger = logging.getLogger(__name__)

class SituationAwareness:
    """Monitors the active state of the user's system to build context."""
    
    def __init__(self):
        self._last_context = None
        
    def get_system_load(self) -> str:
        """Returns a string describing current system load."""
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory().percent
            if cpu > 80 or mem > 85:
                return "Heavy system load"
            elif cpu > 50 or mem > 60:
                return "Moderate system load"
            return "Light system load"
        except Exception:
            return "Unknown system load"
            
    def get_active_context(self) -> str:
        """
        Mock for cross-platform active window detection.
        In a real scenario, this would use pywinauto (Windows) or AppKit (macOS).
        """
        # We can look at top processes by CPU or memory to guess the activity
        try:
            processes = sorted(
                psutil.process_iter(['name', 'cpu_percent']),
                key=lambda p: p.info['cpu_percent'] if p.info['cpu_percent'] else 0,
                reverse=True
            )
            top_process = processes[0].info['name'].lower() if processes else ""
            
            if "code" in top_process or "idea" in top_process or "pycharm" in top_process:
                return "Coding/Development"
            if "chrome" in top_process or "firefox" in top_process or "msedge" in top_process:
                return "Web Browsing"
            if "discord" in top_process or "slack" in top_process or "teams" in top_process:
                return "Communicating"
            return "General Desktop Use"
            return "General Desktop Use"
        except Exception:
            return "General Desktop Use"

    def detect_context_switch(self) -> tuple[bool, str, str]:
        """
        Detects if the user has switched contexts since the last check.
        Returns (has_switched, old_context, new_context)
        """
        current = self.get_active_context()
        if self._last_context is None:
            self._last_context = current
            return False, "", current
            
        if current != self._last_context:
            old = self._last_context
            self._last_context = current
            return True, old, current
            
        return False, self._last_context, current
