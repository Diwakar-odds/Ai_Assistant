# Advanced Conversational AI Module
"""
Advanced conversational AI capabilities including:
- Context switching and multi-task handling
- Proactive assistance and suggestions
- Emotional intelligence and mood detection
- Multi-turn complex task management
- Conversation memory and context persistence
- Real-time command execution
"""

import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import os
import re
import webbrowser
import subprocess

class ConversationState(Enum):
    """Conversation state enumeration."""
    IDLE = "idle"
    ACTIVE = "active"
    WAITING_FOR_INPUT = "waiting_for_input"
    PROCESSING = "processing"
    MULTI_TASK = "multi_task"
    CONTEXT_SWITCH = "context_switch"

class MoodType(Enum):
    """User mood detection types."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    FRUSTRATED = "frustrated"
    FOCUSED = "focused"
    TIRED = "tired"
    URGENT = "urgent"
    CONFUSED = "confused"

@dataclass
class ConversationContext:
    """Context information for conversations."""
    id: str
    name: str
    topic: str
    started_at: datetime
    last_activity: datetime
    state: ConversationState
    messages: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    priority: int = 1
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['started_at'] = self.started_at.isoformat()
        result['last_activity'] = self.last_activity.isoformat()
        result['state'] = self.state.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create from dictionary."""
        data['started_at'] = datetime.fromisoformat(data['started_at'])
        data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        data['state'] = ConversationState(data['state'])
        return cls(**data)

class AdvancedConversationalAI:
    """Advanced conversational AI system with context management."""
    
    def __init__(self, db_path: str = "conversation_ai.db", automation_callback: Optional[Callable] = None):
        """Initialize the conversational AI system."""
        self.db_path = db_path
        self.contexts: Dict[str, ConversationContext] = {}
        self.active_context_id: Optional[str] = None
        self.user_mood: MoodType = MoodType.NEUTRAL
        self.mood_history: List[Tuple[datetime, MoodType]] = []
        self.automation_callback = automation_callback
        
        # Conversation patterns and triggers
        self.proactive_triggers = []
        self.context_switch_patterns = []
        self.mood_indicators = self._init_mood_indicators()
        
        # Initialize database
        self._init_database()
        self._load_contexts()
        
        # Background thread for proactive suggestions
        self.proactive_thread = None
        self.running = True
        self._start_proactive_monitoring()
        
    def _init_database(self):
        """Initialize SQLite database for conversation persistence."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    state TEXT NOT NULL,
                    messages TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    priority INTEGER DEFAULT 1
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mood_history (
                    timestamp TEXT NOT NULL,
                    mood TEXT NOT NULL,
                    context_id TEXT,
                    trigger TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_patterns (
                    pattern_type TEXT NOT NULL,
                    pattern_data TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    last_seen TEXT NOT NULL
                )
            """)
    
    def _init_mood_indicators(self) -> Dict[MoodType, List[str]]:
        """Initialize mood detection patterns."""
        return {
            MoodType.FRUSTRATED: [
                r"\b(frustrated|annoying|stupid|hate|angry|mad)\b",
                r"\b(why won't|doesn't work|not working|broken)\b",
                r"\b(damn|dammit|fuck|shit)\b",
                r"\b(give up|quit|stop)\b"
            ],
            MoodType.HAPPY: [
                r"\b(great|awesome|perfect|excellent|wonderful)\b",
                r"\b(thank you|thanks|appreciate|love)\b",
                r"\b(happy|excited|amazing|fantastic)\b",
                r"\b(yes|yay|woohoo|brilliant)\b"
            ],
            MoodType.URGENT: [
                r"\b(urgent|emergency|asap|immediately|now)\b",
                r"\b(hurry|quick|fast|deadline|late)\b",
                r"\b(important|critical|priority)\b"
            ],
            MoodType.CONFUSED: [
                r"\b(confused|don't understand|what|how|why)\b",
                r"\b(unclear|lost|help|explain)\b",
                r"\b(what do you mean|I don't get it)\b"
            ],
            MoodType.TIRED: [
                r"\b(tired|exhausted|sleepy|worn out)\b",
                r"\b(long day|late night|early morning)\b",
                r"\b(can't focus|distracted)\b"
            ],
            MoodType.FOCUSED: [
                r"\b(working on|focused|concentrate|deep work)\b",
                r"\b(busy|in the zone|productive)\b",
                r"\b(meeting|presentation|deadline)\b"
            ]
        }
    
    def detect_mood(self, text: str, context_clues: Dict[str, Any] = None) -> MoodType:
        """Detect user mood from text and context."""
        text_lower = text.lower()
        detected_moods = []
        
        # Text-based mood detection
        for mood, patterns in self.mood_indicators.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    detected_moods.append(mood)
                    break
        
        # Context-based mood adjustments
        if context_clues:
            # Time-based mood inference
            current_hour = datetime.now().hour
            if current_hour < 8:
                detected_moods.append(MoodType.TIRED)
            elif current_hour > 22:
                detected_moods.append(MoodType.TIRED)
            
            # Task-based mood inference
            if context_clues.get('task_complexity') == 'high':
                detected_moods.append(MoodType.FOCUSED)
            
            # Recent error patterns
            if context_clues.get('recent_errors', 0) > 2:
                detected_moods.append(MoodType.FRUSTRATED)
        
        # Determine primary mood
        if detected_moods:
            # Priority order for conflicting moods
            mood_priority = [
                MoodType.URGENT, MoodType.FRUSTRATED, MoodType.CONFUSED,
                MoodType.TIRED, MoodType.FOCUSED, MoodType.HAPPY
            ]
            
            for mood in mood_priority:
                if mood in detected_moods:
                    self._update_mood(mood, text)
                    return mood
        
        return self.user_mood
    
    def _update_mood(self, new_mood: MoodType, trigger: str = ""):
        """Update user mood and store in history."""
        if new_mood != self.user_mood:
            self.mood_history.append((datetime.now(), new_mood))
            self.user_mood = new_mood
            
            # Store in database
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO mood_history (timestamp, mood, context_id, trigger)
                    VALUES (?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(),
                    new_mood.value,
                    self.active_context_id,
                    trigger[:200]  # Limit trigger length
                ))
    
    def create_context(self, name: str, topic: str, initial_message: str = "") -> str:
        """Create a new conversation context."""
        context_id = f"ctx_{int(time.time())}_{len(self.contexts)}"
        
        context = ConversationContext(
            id=context_id,
            name=name,
            topic=topic,
            started_at=datetime.now(),
            last_activity=datetime.now(),
            state=ConversationState.ACTIVE,
            messages=[],
            metadata={"created_by": "user", "auto_generated": False},
            priority=1
        )
        
        if initial_message:
            context.messages.append({
                "role": "user",
                "content": initial_message,
                "timestamp": datetime.now().isoformat(),
                "mood": self.user_mood.value
            })
        
        self.contexts[context_id] = context
        self.active_context_id = context_id
        self._save_context(context)
        
        return context_id
    
    def switch_context(self, context_id: str = None, context_name: str = None) -> bool:
        """Switch to a different conversation context."""
        target_context = None
        
        if context_id and context_id in self.contexts:
            target_context = self.contexts[context_id]
        elif context_name:
            for ctx in self.contexts.values():
                if ctx.name.lower() == context_name.lower():
                    target_context = ctx
                    break
        
        if target_context:
            # Update current context state
            if self.active_context_id:
                current_ctx = self.contexts[self.active_context_id]
                current_ctx.state = ConversationState.IDLE
                current_ctx.last_activity = datetime.now()
                self._save_context(current_ctx)
            
            # Switch to new context
            target_context.state = ConversationState.ACTIVE
            target_context.last_activity = datetime.now()
            self.active_context_id = target_context.id
            self._save_context(target_context)
            
            return True
        
        return False
    
    def add_message(self, role: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """Add a message to the current conversation context."""
        if not self.active_context_id:
            # Create default context if none exists
            self.create_context("Default", "General Conversation", content if role == "user" else "")
            if role == "user":
                return True  # Message already added in create_context
        
        context = self.contexts[self.active_context_id]
        
        # Detect mood from user messages
        if role == "user":
            self.detect_mood(content, metadata)
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "mood": self.user_mood.value if role == "user" else None,
            "metadata": metadata or {}
        }
        
        context.messages.append(message)
        context.last_activity = datetime.now()
        context.state = ConversationState.ACTIVE
        
        # Update topic if this is a significant message
        if len(context.messages) <= 3 and len(content) > 20:
            context.topic = self._extract_topic(content)
        
        self._save_context(context)
        return True
    
    def get_context_summary(self, context_id: str = None) -> Dict[str, Any]:
        """Get a summary of the conversation context."""
        ctx_id = context_id or self.active_context_id
        if not ctx_id or ctx_id not in self.contexts:
            return {"error": "Context not found"}
        
        context = self.contexts[ctx_id]
        
        return {
            "id": context.id,
            "name": context.name,
            "topic": context.topic,
            "message_count": len(context.messages),
            "duration": str(context.last_activity - context.started_at),
            "state": context.state.value,
            "current_mood": self.user_mood.value,
            "recent_messages": context.messages[-3:] if context.messages else []
        }
    
    def get_conversation_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation history."""
        if not self.active_context_id:
            return []
        
        context = self.contexts[self.active_context_id]
        return context.messages[-limit:] if context.messages else []
    
    def process_message(self, message: str, role: str = "user") -> str:
        """Process a message and generate an intelligent response with REAL execution."""
        try:
            # Add message to conversation
            self.add_message(role, message)
            
            # Detect mood from user messages
            if role == "user":
                self.detect_mood(message)
            
            # Check for context switch
            is_switch, switch_msg, new_ctx_id = self.handle_context_switch_request(message)
            if is_switch:
                return switch_msg
            
            # Process different types of queries
            message_lower = message.lower()
            
            # TRY TO EXECUTE COMMAND FIRST - This is the main change!
            command_result = self._try_execute_command(message, message_lower)
            if command_result:
                return command_result
            
            # Math queries (if not a command)
            if any(word in message_lower for word in ['calculate', 'times', 'plus', 'minus', 'divided', 'multiply']) and 'what is' in message_lower:
                return self._process_math_query(message)
            
            # Information queries (if not a command)
            if any(word in message_lower for word in ['time', 'date', 'day']) and ('what' in message_lower or 'tell' in message_lower):
                return self._process_info_query(message)
            
            # If nothing else matched, try as a general command with automation callback
            if self.automation_callback:
                # Last resort: check if it's asking to do something
                action_words = ['open', 'close', 'start', 'stop', 'launch', 'run', 'play', 'search', 'find', 
                               'create', 'make', 'set', 'change', 'show', 'get', 'check']
                if any(word in message_lower for word in action_words):
                    return "🤔 I can sense you want me to do something! Could you be more specific? Here are some examples:\n\n📱 'open chrome' - Opens Google Chrome\n🎵 'play music' - Plays music on YouTube\n🔍 'search for python' - Searches Google\n📝 'create a document' - Opens Word\n\nWhat exactly would you like me to do?"
            
            # Default: Generate contextual response
            return self._generate_contextual_response(message)
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error in process_message: {error_trace}")
            
            # More user-friendly error messages based on the error type
            if "automation" in str(e).lower():
                return "🔧 I'm having trouble connecting to some system features right now. Please try again, or try a different command."
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                return "🌐 There seems to be a network issue. Please check your connection and try again."
            else:
                return "😅 I encountered a small hiccup while processing that. Could you try rephrasing your request or try a different command?"
    
    def _process_math_query(self, query: str) -> str:
        """Process mathematical queries and return calculated results."""
        try:
            import re
            query_lower = query.lower()
            
            # Extract numbers and operations
            if 'pie' in query_lower or 'pi' in query_lower:
                return "The value of π (pi) is approximately 3.14159265359. It's the ratio of a circle's circumference to its diameter."
            
            # Simple arithmetic patterns
            patterns = [
                (r'(\d+)\s*times\s*(\d+)', lambda m: int(m.group(1)) * int(m.group(2)), 'multiplication'),
                (r'(\d+)\s*\*\s*(\d+)', lambda m: int(m.group(1)) * int(m.group(2)), 'multiplication'),
                (r'(\d+)\s*plus\s*(\d+)', lambda m: int(m.group(1)) + int(m.group(2)), 'addition'),
                (r'(\d+)\s*\+\s*(\d+)', lambda m: int(m.group(1)) + int(m.group(2)), 'addition'),
                (r'(\d+)\s*minus\s*(\d+)', lambda m: int(m.group(1)) - int(m.group(2)), 'subtraction'),
                (r'(\d+)\s*-\s*(\d+)', lambda m: int(m.group(1)) - int(m.group(2)), 'subtraction'),
                (r'(\d+)\s*divided by\s*(\d+)', lambda m: int(m.group(1)) / int(m.group(2)), 'division'),
                (r'(\d+)\s*/\s*(\d+)', lambda m: int(m.group(1)) / int(m.group(2)), 'division'),
            ]
            
            for pattern, calc_func, operation in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    result = calc_func(match)
                    num1, num2 = match.group(1), match.group(2)
                    return f"The answer is {result}. ({num1} {operation.replace('ion', 'ed')} by {num2} = {result})"
            
            # Try to evaluate simple expressions safely
            try:
                # Extract only numbers and basic operators
                expr = re.sub(r'[^0-9+\-*/()\s.]', '', query)
                if expr and any(c.isdigit() for c in expr):
                    result = eval(expr)
                    return f"The answer is {result}."
            except:
                pass
            
            return "I can help you with calculations! Try asking like 'what is 10 times 5' or 'calculate 100 plus 50'."
            
        except Exception as e:
            return "I had trouble with that calculation. Can you rephrase your question?"
    
    def _process_info_query(self, query: str) -> str:
        """Process informational queries."""
        # This is a placeholder - in production, you'd integrate with knowledge bases or APIs
        query_lower = query.lower()
        
        if 'time' in query_lower:
            from datetime import datetime
            current_time = datetime.now().strftime("%I:%M %p")
            return f"The current time is {current_time}."
        
        if 'date' in query_lower:
            from datetime import datetime
            current_date = datetime.now().strftime("%B %d, %Y")
            return f"Today is {current_date}."
        
        if 'day' in query_lower:
            from datetime import datetime
            day = datetime.now().strftime("%A")
            return f"Today is {day}."
        
        return f"That's an interesting question! I'm still learning to answer complex information queries. You asked: '{query}'"
    
    def _try_execute_command(self, query: str, query_lower: str):
        """Try to execute actionable commands and return result."""
        try:
            # PRIORITY 1: System/Settings commands (more specific than generic open)
            if 'settings' in query_lower or 'control panel' in query_lower or \
               any(word in query_lower for word in ['wifi', 'bluetooth', 'display', 'network', 'sound']) and 'open' in query_lower:
                return self._execute_settings_command(query, query_lower)
            
            # PRIORITY 2: Opening apps/websites - Most common command
            if any(word in query_lower for word in ['open', 'launch', 'start', 'run']):
                return self._execute_open_command(query, query_lower)
            
            # PRIORITY 3: Closing apps
            if any(word in query_lower for word in ['close', 'quit', 'exit', 'kill', 'stop']):
                return self._execute_close_command(query, query_lower)
            
            # PRIORITY 4: Searching - Google, web search
            if any(word in query_lower for word in ['google', 'search', 'find', 'look up', 'look for']):
                return self._execute_search_command(query, query_lower)
            
            # PRIORITY 5: Playing music
            if 'play' in query_lower:
                return self._execute_play_command(query, query_lower)
            
            # PRIORITY 6: Creating documents
            if any(word in query_lower for word in ['create', 'make', 'generate', 'new']) and \
               any(doc in query_lower for doc in ['ppt', 'powerpoint', 'presentation', 'pdf', 'document', 'doc', 'word']):
                return self._execute_create_document(query, query_lower)
            
            # PRIORITY 7: Volume control
            if 'volume' in query_lower or 'sound' in query_lower or 'mute' in query_lower:
                return self._execute_volume_command(query, query_lower)
            
            # PRIORITY 8: System commands (shutdown, restart, etc.)
            if any(word in query_lower for word in ['shutdown', 'restart', 'sleep', 'lock']):
                return self._execute_system_command(query, query_lower)
            
            return None
            
        except Exception as e:
            import traceback
            print(f"Command execution error: {traceback.format_exc()}")
            return f"❌ Error executing command: {str(e)}"
    
    def _execute_open_command(self, query: str, query_lower: str) -> str:
        """Execute open application commands."""
        # Extract app name - remove command words
        app_name = query_lower
        for word in ['open', 'launch', 'start', 'run', 'the', 'app', 'application', 'program']:
            app_name = app_name.replace(word, '')
        app_name = app_name.strip()
        
        if not app_name:
            return "Which application would you like me to open?"
        
        # Extensive application mappings
        app_mappings = {
            # Browsers
            'chrome': 'chrome.exe',
            'google chrome': 'chrome.exe',
            'firefox': 'firefox.exe',
            'edge': 'msedge.exe',
            'microsoft edge': 'msedge.exe',
            'brave': 'brave.exe',
            'opera': 'opera.exe',
            
            # Office
            'word': 'WINWORD.EXE',
            'excel': 'EXCEL.EXE',
            'powerpoint': 'POWERPNT.EXE',
            'outlook': 'OUTLOOK.EXE',
            'onenote': 'ONENOTE.EXE',
            'access': 'MSACCESS.EXE',
            
            # System
            'notepad': 'notepad.exe',
            'calculator': 'calc.exe',
            'calc': 'calc.exe',
            'paint': 'mspaint.exe',
            'task manager': 'taskmgr.exe',
            'taskmanager': 'taskmgr.exe',
            'cmd': 'cmd.exe',
            'command prompt': 'cmd.exe',
            'powershell': 'powershell.exe',
            'explorer': 'explorer.exe',
            'file explorer': 'explorer.exe',
            'control panel': 'control.exe',
            
            # Development
            'vs code': 'code.cmd',
            'vscode': 'code.cmd',
            'visual studio code': 'code.cmd',
            'visual studio': 'devenv.exe',
            'sublime': 'sublime_text.exe',
            'atom': 'atom.exe',
            'pycharm': 'pycharm64.exe',
            
            # Communication
            'spotify': 'spotify.exe',
            'discord': 'discord.exe',
            'slack': 'slack.exe',
            'teams': 'teams.exe',
            'zoom': 'zoom.exe',
            'skype': 'skype.exe',
            
            # Media
            'vlc': 'vlc.exe',
            'media player': 'wmplayer.exe',
            'windows media player': 'wmplayer.exe',
            
            # Common websites as keywords
            'youtube': 'https://youtube.com',
            'gmail': 'https://gmail.com',
            'facebook': 'https://facebook.com',
            'twitter': 'https://twitter.com',
            'instagram': 'https://instagram.com',
            'linkedin': 'https://linkedin.com',
            'github': 'https://github.com',
            'stackoverflow': 'https://stackoverflow.com',
            'reddit': 'https://reddit.com',
        }
        
        # Check if it's a URL or website
        if any(indicator in app_name for indicator in ['.com', '.org', '.net', '.io', '.app', '.dev', 'http', 'www.']):
            url = app_name
            if not url.startswith('http'):
                url = 'https://' + url.replace('www.', '')
            try:
                webbrowser.open(url)
                return f"✅ Opening {url} in your browser"
            except Exception as e:
                return f"❌ Could not open website: {str(e)}"
        
        # Try automation callback before direct execution to leverage automation tools
        if self.automation_callback:
            try:
                result = self.automation_callback('open_application', app_name)
                if result and 'error' not in str(result).lower():
                    return f"✅ {result}"
            except Exception as e:
                print(f"Automation callback error: {e}")
        
        # Check if it's a mapped app
        if app_name in app_mappings:
            target = app_mappings[app_name]
            
            # If it's a URL, open in browser
            if target.startswith('http'):
                try:
                    webbrowser.open(target)
                    return f"✅ Opening {app_name.title()}"
                except Exception as e:
                    return f"❌ Could not open: {str(e)}"
            
            # Otherwise it's an executable
            try:
                subprocess.Popen(target, shell=True)
                return f"✅ Opening {app_name.title()}"
            except:
                pass  # Try automation callback below
        # Last resort: try as-is
        try:
            if not app_name.endswith('.exe'):
                app_name_exe = app_name + '.exe'
            else:
                app_name_exe = app_name
            subprocess.Popen(app_name_exe, shell=True)
            return f"✅ Opening {app_name.title()}"
        except:
            return f"❌ Could not find application '{app_name}'. Try being more specific or check if it's installed."
    
    def _execute_close_command(self, query: str, query_lower: str) -> str:
        """Execute close application commands."""
        # Extract app name - remove command words
        app_name = query_lower
        for word in ['close', 'stop', 'quit', 'exit', 'kill', 'end', 'terminate', 'the', 'app', 'application']:
            app_name = app_name.replace(word, '')
        app_name = app_name.strip()
        
        if not app_name:
            return "Which application would you like me to close?"
        
        # Try automation callback first
        if self.automation_callback:
            try:
                result = self.automation_callback('close_application', app_name)
                if result and 'error' not in str(result).lower():
                    return f"✅ {result}"
            except Exception as e:
                print(f"Automation close error: {e}")
        
        # Map common names to process names
        process_mappings = {
            'chrome': 'chrome',
            'google chrome': 'chrome',
            'firefox': 'firefox',
            'edge': 'msedge',
            'notepad': 'notepad',
            'calculator': 'calculator',
            'calc': 'calculator',
            'word': 'WINWORD',
            'excel': 'EXCEL',
            'powerpoint': 'POWERPNT',
            'outlook': 'OUTLOOK',
            'spotify': 'spotify',
            'discord': 'discord',
            'vscode': 'code',
            'vs code': 'code',
        }
        
        process_name = process_mappings.get(app_name, app_name)
        
        # Try to close the application
        try:
            # Try with and without .exe extension
            for name in [process_name + '.exe', process_name]:
                try:
                    result = subprocess.run(
                        ['taskkill', '/IM', name, '/F'],
                        capture_output=True,
                        text=True,
                        shell=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        return f"✅ Closed {app_name.title()}"
                except:
                    continue
            
            return f"❌ Could not close '{app_name}'. It may not be running."
        except Exception as e:
            return f"❌ Error closing application: {str(e)}"
    
    def _execute_search_command(self, query: str, query_lower: str) -> str:
        """Execute Google search commands."""
        # Extract search query - remove command words
        search_query = query_lower
        for word in ['google', 'search for', 'search', 'look up', 'look for', 'find', 'about', 'on', 'the']:
            search_query = search_query.replace(word, '')
        search_query = search_query.strip()
        
        if not search_query or len(search_query) < 2:
            return "What would you like me to search for?"
        
        # Try automation callback first (might have better search integration)
        if self.automation_callback:
            try:
                result = self.automation_callback('search_google', search_query)
                if result and 'error' not in str(result).lower():
                    return f"🔍 {result}"
            except Exception as e:
                print(f"Automation search error: {e}")
        
        # Fallback to direct browser search
        try:
            # Use proper URL encoding
            import urllib.parse
            encoded_query = urllib.parse.quote_plus(search_query)
            url = f"https://www.google.com/search?q={encoded_query}"
            webbrowser.open(url)
            return f"🔍 Searching Google for: '{search_query}'"
        except Exception as e:
            return f"❌ Search failed: {str(e)}"
    
    def _execute_play_command(self, query: str, query_lower: str) -> str:
        """Execute play music commands."""
        # Extract song/artist name - remove command words
        song = query_lower
        
        # Handle "by artist" patterns specially
        if ' by ' in song:
            # Keep everything after 'play' but preserve 'by artist'
            song = song.replace('play', '').strip()
            for word in ['music', 'song', 'on spotify', 'on youtube', 'the', 'some', 'something']:
                song = song.replace(word, '')
        else:
            # Normal processing for direct song names
            for word in ['play', 'music', 'song', 'on spotify', 'on youtube', 'the', 'some']:
                song = song.replace(word, '')
        
        song = song.strip()
        
        # Handle generic music requests
        if not song or len(song) < 2 or song in ['music', 'something', 'anything']:
            # Try automation callback for generic music
            if self.automation_callback:
                try:
                    result = self.automation_callback('play_music', 'popular music')
                    if result and 'error' not in str(result).lower():
                        return f"🎵 {result}"
                except Exception as e:
                    print(f"Automation play error: {e}")
            
            # Fallback response for generic requests
            return "🎵 I'd love to play music for you! Please tell me what song or artist you'd like to hear. For example: 'play believer', 'play coldplay', or 'play some rock music'."
        
        # Try automation callback first (might have Spotify integration)
        if self.automation_callback:
            try:
                result = self.automation_callback('play_music', song)
                if result and 'error' not in str(result).lower():
                    return f"🎵 {result}"
            except Exception as e:
                print(f"Automation play error: {e}")
        
        # Fallback to YouTube search
        try:
            import urllib.parse
            encoded_song = urllib.parse.quote_plus(song + " official")
            url = f"https://www.youtube.com/results?search_query={encoded_song}"
            webbrowser.open(url)
            return f"🎵 Opening YouTube search for: '{song}'"
        except Exception as e:
            return f"❌ Could not play: {str(e)}"
    
    def _execute_create_document(self, query: str, query_lower: str) -> str:
        """Execute document creation commands."""
        if 'ppt' in query_lower or 'powerpoint' in query_lower or 'presentation' in query_lower:
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
    
    def _execute_system_command(self, query: str, query_lower: str) -> str:
        """Execute system commands like shutdown, restart, etc."""
        try:
            if 'shutdown' in query_lower:
                # Don't actually shutdown without confirmation!
                return "⚠️ To shutdown your computer, please use the Start menu or confirm this action."
            elif 'restart' in query_lower:
                return "⚠️ To restart your computer, please use the Start menu or confirm this action."
            elif 'lock' in query_lower:
                subprocess.Popen('rundll32.exe user32.dll,LockWorkStation', shell=True)
                return "🔒 Locking your computer..."
            elif 'sleep' in query_lower:
                subprocess.Popen('rundll32.exe powrprof.dll,SetSuspendState 0,1,0', shell=True)
                return "😴 Putting computer to sleep..."
            else:
                return "I can help with: lock, sleep. For shutdown/restart, please use the Start menu for safety."
        except Exception as e:
            return f"❌ Could not execute system command: {str(e)}"
    
    def _process_command_query(self, query: str) -> str:
        """Process command-based queries."""
        query_lower = query.lower()
        
        if 'open' in query_lower:
            return "I understand you want to open an application. Which app would you like me to open?"
        
        return f"I can help execute that command. You asked: '{query}'"
    
    def _generate_contextual_response(self, message: str) -> str:
        """Generate a contextual response based on conversation history."""
        message_lower = message.lower().strip()
        
        # Handle greetings and common conversational inputs
        greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        if any(greeting in message_lower for greeting in greetings):
            return "👋 Hello! I'm your assistant. I can help you open apps, search the web, play music, create documents, and much more. What would you like me to do?"
        
        # Handle "how are you" type questions
        if any(phrase in message_lower for phrase in ['how are you', 'how r u', 'how do you feel']):
            return "I'm doing great, thank you for asking! 😊 I'm ready to help you with any tasks. What can I do for you today?"
        
        # Handle capability questions
        if any(phrase in message_lower for phrase in ['what can you do', 'what are you capable of', 'help me', 'what features']):
            return "🚀 I can help you with many things:\n\n📱 Open applications (chrome, notepad, calculator, etc.)\n🔍 Search Google for anything\n🎵 Play music on YouTube/Spotify\n📝 Create documents and presentations\n🔧 Control system settings (volume, WiFi, etc.)\n📊 Perform calculations\n⏰ Tell you time and date\n\nJust ask me naturally! For example: 'open chrome', 'play some music', or 'search for python tutorials'."
        
        # Handle thank you messages
        if any(phrase in message_lower for phrase in ['thank you', 'thanks', 'appreciate']):
            return "You're very welcome! 😊 I'm always here to help. Is there anything else you need?"
        
        # Handle questions about assistant
        if any(phrase in message_lower for phrase in ['who are you', 'what are you', 'tell me about yourself']):
            return "I'm YourDaddy Assistant! 🤖 I'm an AI assistant designed to help you with daily tasks like opening applications, searching the web, playing music, managing files, and much more. Think of me as your personal digital helper!"
        
        # Handle unclear requests
        if any(phrase in message_lower for phrase in ['do something', 'help', 'assist', 'i need']):
            return "I'd be happy to help! 💪 Here are some things I can do for you:\n\n• Open applications: 'open chrome'\n• Search: 'google python tutorial'\n• Play music: 'play believer'\n• Create files: 'create a document'\n• System control: 'volume up'\n\nWhat would you like me to help with?"
        
        # Handle general conversation
        thoughtful_responses = [
            "That's interesting! How can I assist you with that? 🤔",
            "I see! What would you like me to help you with? 😊",
            "Got it! Let me know what you need help with. 💡",
            "Understood! What task can I help you complete? 🎯"
        ]
        
        # Return context-aware response for ongoing conversations
        if self.active_context_id:
            context = self.contexts[self.active_context_id]
            if len(context.messages) > 3:
                return f"I'm following our conversation about {context.topic}. What else can I help you with? 🚀"
        
        # Random thoughtful response for variety
        import random
        return random.choice(thoughtful_responses)
    
    def suggest_next_actions(self) -> List[Dict[str, Any]]:
        """Suggest next actions based on conversation context and user mood."""

        suggestions = []
        
        if not self.active_context_id:
            return [{
                "type": "start_conversation",
                "text": "Start a new conversation",
                "action": "create_context",
                "priority": 1
            }]
        
        context = self.contexts[self.active_context_id]
        recent_messages = context.messages[-5:] if context.messages else []
        
        # Mood-based suggestions
        if self.user_mood == MoodType.FRUSTRATED:
            suggestions.extend([
                {
                    "type": "help",
                    "text": "Would you like me to try a different approach?",
                    "action": "offer_alternative",
                    "priority": 1
                },
                {
                    "type": "break",
                    "text": "Maybe take a short break?",
                    "action": "suggest_break",
                    "priority": 2
                }
            ])
        
        elif self.user_mood == MoodType.CONFUSED:
            suggestions.extend([
                {
                    "type": "clarification",
                    "text": "Let me explain that more clearly",
                    "action": "provide_explanation",
                    "priority": 1
                },
                {
                    "type": "step_by_step",
                    "text": "Break this down into steps",
                    "action": "create_tutorial",
                    "priority": 2
                }
            ])
        
        elif self.user_mood == MoodType.FOCUSED:
            suggestions.extend([
                {
                    "type": "productivity",
                    "text": "Keep going! You're in the zone",
                    "action": "minimize_distractions",
                    "priority": 1
                },
                {
                    "type": "efficiency",
                    "text": "Want me to automate some of this?",
                    "action": "suggest_automation",
                    "priority": 2
                }
            ])
        
        # Context-based suggestions
        if context.topic.lower() in ["email", "mail", "message"]:
            suggestions.append({
                "type": "email_action",
                "text": "Check for new emails?",
                "action": "check_email",
                "priority": 3
            })
        
        elif context.topic.lower() in ["file", "document", "folder"]:
            suggestions.append({
                "type": "file_action",
                "text": "Organize your files?",
                "action": "organize_files",
                "priority": 3
            })
        
        # Time-based suggestions
        current_hour = datetime.now().hour
        if current_hour == 9 and datetime.now().weekday() < 5:
            suggestions.append({
                "type": "schedule",
                "text": "Review today's schedule?",
                "action": "show_calendar",
                "priority": 2
            })
        
        # Sort by priority
        suggestions.sort(key=lambda x: x["priority"])
        return suggestions[:5]  # Return top 5 suggestions
    
    def handle_context_switch_request(self, user_input: str) -> Tuple[bool, str, Optional[str]]:
        """Handle requests to switch conversation context."""
        switch_patterns = [
            r"switch to (.*)",
            r"go back to (.*)",
            r"continue (.*)",
            r"work on (.*)",
            r"talk about (.*)"
        ]
        
        for pattern in switch_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                target = match.group(1).strip()
                
                # Try to find matching context
                for context in self.contexts.values():
                    if (target.lower() in context.name.lower() or 
                        target.lower() in context.topic.lower()):
                        
                        if self.switch_context(context.id):
                            return True, f"Switched to conversation about {context.topic}", context.id
                
                # Create new context if not found
                context_id = self.create_context(target.title(), target)
                return True, f"Started new conversation about {target}", context_id
        
        return False, "", None
    
    def get_proactive_suggestions(self) -> List[Dict[str, Any]]:
        """Get proactive suggestions based on patterns and context."""
        suggestions = []
        now = datetime.now()
        
        # Time-based suggestions
        if now.hour == 9 and now.weekday() < 5:  # Weekday morning
            suggestions.append({
                "type": "morning_briefing",
                "message": "Good morning! Would you like your daily briefing?",
                "actions": ["show_calendar", "check_email", "get_weather"],
                "priority": 1
            })
        
        elif now.hour == 17 and now.weekday() < 5:  # Weekday evening
            suggestions.append({
                "type": "end_of_day",
                "message": "End of workday - shall I help you wrap up?",
                "actions": ["backup_files", "summary_report", "tomorrow_prep"],
                "priority": 1
            })
        
        # Pattern-based suggestions
        if self._detect_repetitive_pattern():
            suggestions.append({
                "type": "automation",
                "message": "I notice you do this often. Want me to automate it?",
                "actions": ["create_script", "setup_shortcut"],
                "priority": 2
            })
        
        # Context-based suggestions
        if self.active_context_id:
            context = self.contexts[self.active_context_id]
            idle_time = now - context.last_activity
            
            if idle_time > timedelta(minutes=30):
                suggestions.append({
                    "type": "check_in",
                    "message": f"Still working on {context.topic}? Need any help?",
                    "actions": ["continue_task", "switch_context", "take_break"],
                    "priority": 3
                })
        
        return suggestions
    
    def _detect_repetitive_pattern(self) -> bool:
        """Detect if user is doing repetitive tasks."""
        # Simple pattern detection - can be enhanced
        if not self.active_context_id:
            return False
        
        context = self.contexts[self.active_context_id]
        recent_messages = context.messages[-10:]
        
        if len(recent_messages) < 5:
            return False
        
        # Look for similar commands
        user_messages = [msg["content"] for msg in recent_messages if msg["role"] == "user"]
        
        # Simple similarity check
        similar_count = 0
        for i in range(len(user_messages) - 1):
            for j in range(i + 1, len(user_messages)):
                similarity = self._calculate_similarity(user_messages[i], user_messages[j])
                if similarity > 0.7:  # 70% similarity threshold
                    similar_count += 1
        
        return similar_count >= 2
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    def _extract_topic(self, text: str) -> str:
        """Extract topic from text content."""
        # Simple topic extraction - can be enhanced with NLP
        words = text.lower().split()
        
        # Remove common words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        meaningful_words = [w for w in words if w not in stop_words and len(w) > 3]
        
        if meaningful_words:
            return " ".join(meaningful_words[:3])  # First 3 meaningful words
        
        return "General Discussion"
    
    def _save_context(self, context: ConversationContext):
        """Save conversation context to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO conversations 
                (id, name, topic, started_at, last_activity, state, messages, metadata, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                context.id,
                context.name,
                context.topic,
                context.started_at.isoformat(),
                context.last_activity.isoformat(),
                context.state.value,
                json.dumps(context.messages),
                json.dumps(context.metadata),
                context.priority
            ))
    
    def _load_contexts(self):
        """Load conversation contexts from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT * FROM conversations ORDER BY last_activity DESC")
                for row in cursor:
                    context_data = {
                        'id': row[0],
                        'name': row[1],
                        'topic': row[2],
                        'started_at': row[3],
                        'last_activity': row[4],
                        'state': row[5],
                        'messages': json.loads(row[6]),
                        'metadata': json.loads(row[7]),
                        'priority': row[8]
                    }
                    
                    context = ConversationContext.from_dict(context_data)
                    self.contexts[context.id] = context
                    
                    # Set most recent as active
                    if not self.active_context_id and context.state == ConversationState.ACTIVE.value:
                        self.active_context_id = context.id
        except Exception as e:
            print(f"Error loading contexts: {e}")
    
    def _start_proactive_monitoring(self):
        """Start background thread for proactive suggestions."""
        def monitor():
            while self.running:
                try:
                    suggestions = self.get_proactive_suggestions()
                    if suggestions:
                        # Here you would integrate with the main app to show suggestions
                        pass
                    time.sleep(300)  # Check every 5 minutes
                except Exception as e:
                    print(f"Proactive monitoring error: {e}")
                    time.sleep(60)
        
        self.proactive_thread = threading.Thread(target=monitor, daemon=True)
        self.proactive_thread.start()
    
    def cleanup(self):
        """Cleanup resources."""
        self.running = False
        if self.proactive_thread:
            self.proactive_thread.join(timeout=1)

# Convenience functions for easy integration
def create_conversation_context(name: str, topic: str, initial_message: str = "") -> str:
    """Create a new conversation context."""
    ai = AdvancedConversationalAI()
    return ai.create_context(name, topic, initial_message)

def switch_conversation_context(context_name: str) -> bool:
    """Switch to a different conversation context."""
    ai = AdvancedConversationalAI()
    return ai.switch_context(context_name=context_name)

def add_conversation_message(role: str, content: str) -> bool:
    """Add a message to the current conversation."""
    ai = AdvancedConversationalAI()
    return ai.add_message(role, content)

def get_conversation_suggestions() -> List[Dict[str, Any]]:
    """Get suggestions for next actions."""
    ai = AdvancedConversationalAI()
    return ai.suggest_next_actions()

def detect_user_mood(text: str) -> str:
    """Detect user mood from text."""
    ai = AdvancedConversationalAI()
    mood = ai.detect_mood(text)
    return mood.value

# Export functions
__all__ = [
    'AdvancedConversationalAI',
    'ConversationState',
    'MoodType',
    'ConversationContext',
    'create_conversation_context',
    'switch_conversation_context',
    'add_conversation_message',
    'get_conversation_suggestions',
    'detect_user_mood'
]