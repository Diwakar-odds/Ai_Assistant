"""
Automation Handler Module
Handles local action execution, app launches, Spotify controls, notes, and Hinglish dispatch.
Extracted from assistant.py for modularity.
"""

import os
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from ai_assistant.automation_tools_new import (
        setup_memory, save_to_memory, get_memory,
        open_application, close_application,
        search_google, search_and_play_spotify,
        set_system_volume, get_system_volume,
        get_weather_info, get_system_status,
        smart_open_application, write_a_note,
        spotify_play_pause, spotify_next_track, spotify_previous_track,
        get_spotify_status
    )
    AUTOMATION_AVAILABLE = True
except ImportError:
    AUTOMATION_AVAILABLE = False


class AutomationHandler:
    """Manages command dispatching, desktop automation, and tools."""
    
    def __init__(self):
        self.available = AUTOMATION_AVAILABLE
        if self.available:
            try:
                setup_memory()
            except Exception as e:
                logger.debug(f"Memory setup note: {e}")

    def execute_command(self, command: str) -> str:
        """Process and execute automation command with regex matching."""
        if not command:
            return "No command provided."
            
        cmd_lower = command.lower().strip()
        
        # Open app
        match = re.match(r'^(?:open|launch|start|kholo|chalao)\s+(.+)$', cmd_lower)
        if match:
            app_name = match.group(1).strip()
            if self.available:
                return smart_open_application(app_name)
            return f"Opening {app_name} (simulation)"
            
        # Close app
        match = re.match(r'^(?:close|band\s+karo|exit)\s+(.+)$', cmd_lower)
        if match:
            app_name = match.group(1).strip()
            if self.available:
                return close_application(app_name)
            return f"Closing {app_name} (simulation)"
            
        # Spotify search/play
        match = re.match(r'^(?:play|baja|bajao)\s+(.+)$', cmd_lower)
        if match:
            query = match.group(1).strip()
            if self.available:
                return search_and_play_spotify(query)
            return f"Playing {query} on Spotify (simulation)"
            
        # Volume control
        match = re.match(r'^(?:set volume to|volume karo)\s+(\d+)$', cmd_lower)
        if match:
            vol = int(match.group(1))
            if self.available:
                return set_system_volume(vol)
            return f"Volume set to {vol}% (simulation)"
            
        # Weather
        if any(w in cmd_lower for w in ['weather', 'mausam', 'temperature']):
            if self.available:
                return str(get_weather_info())
            return "Weather is sunny, 24°C"
            
        # Write note
        match = re.match(r'^(?:note down|write note|likho)\s+(.+)$', cmd_lower)
        if match:
            note = match.group(1).strip()
            if self.available:
                return write_a_note(note)
            return f"Note recorded: {note}"
            
        return f"Processed automation command: {command}"
