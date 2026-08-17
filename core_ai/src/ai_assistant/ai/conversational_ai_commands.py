# Command execution methods for Conversational AI
"""
This module contains all command execution methods that will be merged
into the AdvancedConversationalAI class.
"""

def _try_execute_command(self, query: str, query_lower: str):
    """Try to execute actionable commands and return result."""
    try:
        # Open applications
        if 'open' in query_lower:
            return self._execute_open_command(query, query_lower)
        
        # Close applications
        elif 'close' in query_lower:
            return self._execute_close_command(query, query_lower)
        
        # Google search
        elif 'google' in query_lower or 'search for' in query_lower:
            return self._execute_search_command(query, query_lower)
        
        # Play music
        elif 'play' in query_lower and any(word in query_lower for word in ['music', 'song', 'spotify', 'youtube']):
            return self._execute_play_command(query, query_lower)
        
        # Create documents
        elif any(word in query_lower for word in ['create', 'make', 'generate']) and any(doc in query_lower for doc in ['ppt', 'powerpoint', 'pdf', 'document', 'presentation']):
            return self._execute_create_document(query, query_lower)
        
        # Volume control
        elif 'volume' in query_lower:
            return self._execute_volume_command(query, query_lower)
        
        # System settings
        elif 'settings' in query_lower or 'control panel' in query_lower:
            return self._execute_settings_command(query, query_lower)
        
        return None
        
    except Exception as e:
        return f"❌ Error executing command: {str(e)}"

def _execute_open_command(self, query: str, query_lower: str) -> str:
    """Execute open application commands."""
    import webbrowser
    import subprocess
    
    # Extract app name
    app_name = query_lower.replace('open', '').replace('launch', '').replace('start', '').strip()
    
    if not app_name:
        return "Which application would you like me to open?"
    
    # CRITICAL FIX: Use Intent Recognizer to normalize app name
    # This handles variations like "whats app" -> "whatsapp"
    original_app_name = app_name
    try:
        from ai_assistant.ai.intent_recognizer import IntentRecognizer
        recognizer = IntentRecognizer()
        app_name = recognizer.normalize_app_name(app_name)
        if app_name != original_app_name:
            print(f"[Intent Recognizer] Normalized '{original_app_name}' -> '{app_name}'")
    except Exception as e:
        print(f"[Intent Recognizer] Not available: {e}")
    
    # Check for website URLs directly in app name
    if any(word in app_name for word in ['website', '.com', '.org', '.net', 'http']):
        url = app_name.replace('website', '').strip()
        if not url.startswith('http'):
            url = 'https://' + url
        try:
            import webbrowser
            webbrowser.open(url)
            return f"✅ Opening {url} in your browser"
        except Exception as e:
            return f"❌ Could not open website: {str(e)}"
            
    if not app_name:
        return "Which application would you like me to open?"

    # Try to use automation callback if available
    if self.automation_callback:
        try:
            result = self.automation_callback('open_application', app_name)
            if result:
                return f"✅ {result}"
        except:
            pass

    # Direct fallback to centralized engine
    from ai_assistant.automation.app_discovery import smart_open_application
    return smart_open_application(app_name)

def _execute_close_command(self, query: str, query_lower: str) -> str:
    """Execute close application commands."""
    app_name = query_lower.replace('close', '').replace('stop', '').replace('quit', '').strip()
    
    if not app_name:
        return "Which application would you like me to close?"
    
    if self.automation_callback:
        try:
            result = self.automation_callback('close_application', app_name)
            return f"✅ {result}" if result else f"Attempting to close {app_name}"
        except:
            pass
    
    # Direct fallback to centralized engine
    from ai_assistant.automation.app_automation import AppAutomation
    automator = AppAutomation()
    if automator.close_app(app_name):
        return f"✅ Closed {app_name}"
    return f"❌ Could not close '{app_name}'"

def _execute_search_command(self, query: str, query_lower: str) -> str:
    """Execute Google search commands."""
    # Extract search query
    search_query = query_lower
    for word in ['google', 'search for', 'search', 'look up', 'find']:
        search_query = search_query.replace(word, '')
    search_query = search_query.strip()
    
    if not search_query:
        return "What would you like me to search for?"
    
    if self.automation_callback:
        try:
            result = self.automation_callback('search_google', search_query)
            if result:
                return f"✅ {result}"
        except:
            pass
    
    # Direct fallback
    from ai_assistant.automation.app_automation import AppAutomation
    automator = AppAutomation()
    if automator.search_web(search_query):
        return f"🔍 Searching web for: {search_query}"
    return f"❌ Search failed"

def _execute_play_command(self, query: str, query_lower: str) -> str:
    """Execute play music commands."""
    # Extract song/artist name
    song = query_lower
    for word in ['play', 'music', 'song', 'on spotify', 'on youtube']:
        song = song.replace(word, '')
    song = song.strip()
    
    if not song:
        return "What would you like me to play?"
    
    if self.automation_callback:
        try:
            result = self.automation_callback('play_music', song)
            if result:
                return f"🎵 {result}"
        except:
            pass
    
    # Direct fallback
    from ai_assistant.automation.app_automation import AppAutomation
    automator = AppAutomation()
    if automator.play_media(song):
        return f"🎵 Playing: {song}"
    return f"❌ Could not play media"

def _execute_create_document(self, query: str, query_lower: str) -> str:
    """Execute document creation commands."""
    from ai_assistant.automation.app_discovery import smart_open_application
    
    if 'ppt' in query_lower or 'powerpoint' in query_lower or 'presentation' in query_lower:
        smart_open_application('powerpoint')
        return f"📊 Opening PowerPoint to create your presentation"
    
    elif 'pdf' in query_lower:
        return "📄 To create a PDF, please use Word, PowerPoint, or a PDF editor and save as PDF."
    
    elif 'document' in query_lower:
        smart_open_application('word')
        return "📝 Opening Word to create your document"
    
    return "What type of document would you like to create? (PPT, PDF, Document)"

def _execute_volume_command(self, query: str, query_lower: str) -> str:
    """Execute volume control commands."""
    if self.automation_callback:
        try:
            # Extract volume level
            words = query_lower.split()
            for word in words:
                if word.isdigit():
                    level = int(word)
                    result = self.automation_callback('set_volume', level)
                    return f"🔊 {result}" if result else f"Volume set to {level}%"
            
            # Check for up/down
            if 'up' in query_lower or 'increase' in query_lower or 'raise' in query_lower:
                result = self.automation_callback('volume_up', None)
                return f"🔊 Volume increased"
            elif 'down' in query_lower or 'decrease' in query_lower or 'lower' in query_lower:
                result = self.automation_callback('volume_down', None)
                return f"🔊 Volume decreased"
            elif 'mute' in query_lower:
                result = self.automation_callback('mute', None)
                return f"🔇 Volume muted"
        except:
            pass
    
    return "Please specify: 'volume up', 'volume down', 'volume mute', or 'volume [0-100]'"

def _execute_settings_command(self, query: str, query_lower: str) -> str:
    """Execute system settings commands."""
    import os
    import subprocess
    
    try:
        if 'wifi' in query_lower or 'network' in query_lower:
            uri = 'ms-settings:network'
            msg = "⚙️ Opening Network Settings"
        elif 'bluetooth' in query_lower:
            uri = 'ms-settings:bluetooth'
            msg = "⚙️ Opening Bluetooth Settings"
        elif 'display' in query_lower or 'screen' in query_lower:
            uri = 'ms-settings:display'
            msg = "⚙️ Opening Display Settings"
        elif 'sound' in query_lower or 'audio' in query_lower:
            uri = 'ms-settings:sound'
            msg = "⚙️ Opening Sound Settings"
        elif 'system' in query_lower:
            uri = 'ms-settings:about'
            msg = "⚙️ Opening System Settings"
        elif 'account' in query_lower:
            uri = 'ms-settings:emailandaccounts'
            msg = "⚙️ Opening Accounts Settings"
        else:
            uri = 'ms-settings:'
            msg = "⚙️ Opening Windows Settings"
            
        if os.name == 'nt':
            os.startfile(uri)
        else:
            subprocess.Popen(['xdg-open', uri])
            
        return msg
    except Exception as e:
        return f"❌ Could not open settings: {str(e)}"
