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
    
    # Common application mappings
    app_mappings = {
        'chrome': 'chrome.exe',
        'google chrome': 'chrome.exe',
        'firefox': 'firefox.exe',
        'edge': 'msedge.exe',
        'microsoft edge': 'msedge.exe',
        'notepad': 'notepad.exe',
        'calculator': 'calc.exe',
        'calc': 'calc.exe',
        'paint': 'mspaint.exe',
        'word': 'WINWORD.EXE',
        'excel': 'EXCEL.EXE',
        'powerpoint': 'POWERPNT.EXE',
        'outlook': 'OUTLOOK.EXE',
        'vs code': 'code.cmd',
        'vscode': 'code.cmd',
        'spotify': 'spotify.exe',
        'discord': 'discord.exe',
        'slack': 'slack.exe',
        'teams': 'teams.exe',
    }
    
    # Check for website URLs
    if any(word in app_name for word in ['website', '.com', '.org', '.net', 'http']):
        url = app_name.replace('website', '').strip()
        if not url.startswith('http'):
            url = 'https://' + url
        try:
            webbrowser.open(url)
            return f"✅ Opening {url} in your browser"
        except Exception as e:
            return f"❌ Could not open website: {str(e)}"
    
    # Try to use automation callback if available
    if self.automation_callback:
        try:
            result = self.automation_callback('open_application', app_name)
            if result and 'success' in str(result).lower():
                return f"✅ {result}"
            elif result:
                return str(result)
        except:
            pass
    
    # Try direct execution
    try:
        exe_name = app_mappings.get(app_name, app_name + '.exe')
        subprocess.Popen(exe_name, shell=True)
        return f"✅ Opening {app_name.title()}"
    except Exception as e:
        # Try as command
        try:
            subprocess.Popen(app_name, shell=True)
            return f"✅ Launching {app_name}"
        except:
            return f"❌ Could not open '{app_name}'. Please check the application name."

def _execute_close_command(self, query: str, query_lower: str) -> str:
    """Execute close application commands."""
    import subprocess
    
    app_name = query_lower.replace('close', '').replace('stop', '').replace('quit', '').strip()
    
    if not app_name:
        return "Which application would you like me to close?"
    
    if self.automation_callback:
        try:
            result = self.automation_callback('close_application', app_name)
            return f"✅ {result}" if result else f"Attempting to close {app_name}"
        except:
            pass
    
    try:
        subprocess.run(['taskkill', '/IM', app_name + '.exe', '/F'], 
                     capture_output=True, shell=True, timeout=5)
        return f"✅ Closed {app_name}"
    except:
        return f"❌ Could not close '{app_name}'"

def _execute_search_command(self, query: str, query_lower: str) -> str:
    """Execute Google search commands."""
    import webbrowser
    
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
    
    try:
        url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}"
        webbrowser.open(url)
        return f"🔍 Searching Google for: {search_query}"
    except Exception as e:
        return f"❌ Search failed: {str(e)}"

def _execute_play_command(self, query: str, query_lower: str) -> str:
    """Execute play music commands."""
    import webbrowser
    
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
    
    # Fallback to YouTube
    try:
        url = f"https://www.youtube.com/results?search_query={song.replace(' ', '+')}"
        webbrowser.open(url)
        return f"🎵 Opening YouTube search for: {song}"
    except Exception as e:
        return f"❌ Could not play: {str(e)}"

def _execute_create_document(self, query: str, query_lower: str) -> str:
    """Execute document creation commands."""
    import subprocess
    
    if 'ppt' in query_lower or 'powerpoint' in query_lower or 'presentation' in query_lower:
        doc_type = 'PowerPoint presentation'
        try:
            subprocess.Popen('POWERPNT.EXE', shell=True)
            return f"📊 Opening PowerPoint to create your presentation"
        except:
            return "❌ PowerPoint not found. Please install Microsoft Office."
    
    elif 'pdf' in query_lower:
        return "📄 To create a PDF, please use Word, PowerPoint, or a PDF editor and save as PDF."
    
    elif 'document' in query_lower:
        try:
            subprocess.Popen('WINWORD.EXE', shell=True)
            return "📝 Opening Word to create your document"
        except:
            return "❌ Word not found. Please install Microsoft Office."
    
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
    import subprocess
    
    try:
        if 'wifi' in query_lower or 'network' in query_lower:
            subprocess.Popen('ms-settings:network', shell=True)
            return "⚙️ Opening Network Settings"
        elif 'bluetooth' in query_lower:
            subprocess.Popen('ms-settings:bluetooth', shell=True)
            return "⚙️ Opening Bluetooth Settings"
        elif 'display' in query_lower or 'screen' in query_lower:
            subprocess.Popen('ms-settings:display', shell=True)
            return "⚙️ Opening Display Settings"
        elif 'sound' in query_lower or 'audio' in query_lower:
            subprocess.Popen('ms-settings:sound', shell=True)
            return "⚙️ Opening Sound Settings"
        elif 'system' in query_lower:
            subprocess.Popen('ms-settings:about', shell=True)
            return "⚙️ Opening System Settings"
        else:
            subprocess.Popen('ms-settings:', shell=True)
            return "⚙️ Opening Windows Settings"
    except Exception as e:
        return f"❌ Could not open settings: {str(e)}"
