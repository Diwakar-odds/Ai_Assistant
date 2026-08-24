# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

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
from ai_assistant.vision.gemini_vision_provider import GeminiVisionProvider
try:
    from ai_assistant.workflow.intent_router import IntentRouter
except ImportError:
    IntentRouter = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None


# =============================================================================
# TOKEN MANAGEMENT (consolidated from advanced_chat_system.py)
# =============================================================================

class TokenCounter:
    """Token counter for various models."""
    
    MODEL_TOKEN_LIMITS = {
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "gpt-3.5-turbo": 4096,
        "gemini-pro": 32768,
        "gemini-2.5-flash": 1000000,
        "gemini-1.5-pro": 1000000,
        "llama-2-7b": 4096,
        "llama-2-70b": 4096,
    }
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        self.model = model
        self.token_limit = self.MODEL_TOKEN_LIMITS.get(model, 4096)
        
        # Try to use tiktoken for accurate counting
        try:
            import tiktoken
            self.encoder = tiktoken.encoding_for_model(model.split("-")[0])
            self.use_tiktoken = True
        except:
            self.encoder = None
            self.use_tiktoken = False
    
    def count(self, text: str) -> int:
        """Count tokens in text."""
        if self.use_tiktoken and self.encoder:
            try:
                return len(self.encoder.encode(text))
            except:
                pass
        # Fallback: rough estimation (1 token â‰ˆ 4 characters)
        return len(text) // 4
    
    def count_messages(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in a message list."""
        total = 0
        for msg in messages:
            total += self.count(json.dumps(msg))
        return total
    
    def fits_in_context(self, messages: List[Dict[str, str]], new_message: str) -> bool:
        """Check if message list + new message fits in context window."""
        current_tokens = self.count_messages(messages)
        new_tokens = self.count(new_message)
        return (current_tokens + new_tokens) < (self.token_limit * 0.9)
    
    def trim_history(self, messages: List[Dict[str, str]], max_tokens: int = None) -> List[Dict[str, str]]:
        """Trim message history to fit within token limit."""
        if max_tokens is None:
            max_tokens = self.token_limit - 1000
        
        if not messages:
            return []
        
        trimmed = []
        total_tokens = 0
        
        # Always keep system message
        if messages and messages[0].get("role") == "system":
            trimmed.append(messages[0])
            total_tokens = self.count(json.dumps(messages[0]))
        
        # Add messages from end (most recent) backwards
        for msg in reversed(messages[1:]):
            msg_tokens = self.count(json.dumps(msg))
            if total_tokens + msg_tokens > max_tokens:
                break
            trimmed.insert(1 if trimmed else 0, msg)
            total_tokens += msg_tokens
        
        return trimmed


# =============================================================================
# CONVERSATION STATE & CONTEXT
# =============================================================================

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
    
    def __init__(self, db_path: str = "data/core/conversation_ai.db", automation_callback: Optional[Callable] = None):
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
        
        # Initialize LLM provider for real-time responses
        self.llm_provider = None
        self._init_llm_provider()
        
        # Initialize feedback learning system
        self.feedback_system = None
        self._init_feedback_system()
        
        # Initialize database
        self._init_database()
        self._load_contexts()
        
        # Background thread for proactive suggestions
        self.proactive_thread = None
        self.running = True
        self._start_proactive_monitoring()
        
        # Initialize VLM Provider
        try:
            self.vision_provider = GeminiVisionProvider(model_name="gemini-2.5-flash")
            print("âœ… Vision Provider initialized (Gemini)")
        except Exception as e:
            print(f"âš ï¸ Vision Provider init failed: {e}")
            self.vision_provider = None

        # Initialize Semantic Intent Router
        try:
            if IntentRouter:
                self.intent_router = IntentRouter()
                print("âœ… Semantic Intent Router initialized")
            else:
                self.intent_router = None
                print("âš ï¸ IntentRouter module not found")
        except Exception as e:
            print(f"âš ï¸ Intent Router init failed: {e}")
            self.intent_router = None

        # Initialize MCP Enhancer
        try:
            import asyncio
            from ai_assistant.integrations.mcp_conversational import enhance_with_mcp
            
            def _apply_mcp_enhancement():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(enhance_with_mcp(self))
                    loop.close()
                except Exception as e:
                    print(f"âš ï¸ Failed to apply MCP enhancement: {e}")
            
            # Run in background to not block initialization
            threading.Thread(target=_apply_mcp_enhancement, daemon=True).start()
        except Exception as e:
            print(f"âš ï¸ MCP loading error: {e}")

    def _init_llm_provider(self):
        """Initialize the LLM provider for generating real-time AI responses."""
        try:
            # Ensure environment variables are loaded
            import os
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except:
                pass  # dotenv not available, use system env vars
            
            from ai_assistant.ai.llm_provider import UnifiedChatInterface, LLMFactory
            
            # Try to create a unified chat interface with automatic provider detection
            self.llm_provider = UnifiedChatInterface(
                provider=None,
                model=None,
                use_fallback=True
            )
            
            # Add a system prompt for the assistant
            system_prompt = (
                "You are Pulsar, a smart, helpful, and concise AI assistant created by Divakar. "
                "You MUST NEVER identify as a large language model trained by Google or any other company. "
                "You MUST NEVER mention Gemma, OpenAI, Google, or any base models. "
                "Keep your answers brief and directly address the user. "
                "You are capable of controlling the system, managing files, and executing complex chains of action. "
                "Navigate the system freely. If asked to do something, simply confirm it shall be done."
            )

            # Try to load user profile to personalize the prompt
            try:
                from ai_assistant.core.database_config import get_db_path
                db_path = str(get_db_path('personal_knowledge'))
                
                if os.path.exists(db_path):
                    # Use a new connection for profile check
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    try:
                        # Check table existence first
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_nodes'")
                        if cursor.fetchone():
                            cursor.execute("SELECT content, metadata FROM knowledge_nodes WHERE node_type='person'")
                            rows = cursor.fetchall()
                            user_name = None
                            user_role = None
                            user_interests = []
                            user_style = None
                            user_skills = []
                            user_goals = []
                            user_location = None
                            
                            for content, metadata_json in rows:
                                try:
                                    metadata = json.loads(metadata_json) if metadata_json else {}
                                    if metadata.get('is_primary_user'):
                                        user_name = content
                                        user_role = metadata.get('role', 'User')
                                        user_interests = metadata.get('interests', [])
                                        user_style = metadata.get('communication_style')
                                        user_skills = metadata.get('skills', [])
                                        user_goals = metadata.get('goals', [])
                                        user_location = metadata.get('location')
                                        break
                                except:
                                    pass
                            
                            # Fallback to first person if no primary user found
                            if not user_name and rows:
                                user_name = rows[0][0]
                            
                            if user_name:
                                print(f"âœ… Loaded detailed user profile for: {user_name}")
                                system_prompt += f"\n\n### USER PROFILE ###\n"
                                system_prompt += f"You are assisting {user_name}"
                                if user_role:
                                    system_prompt += f", who is the {user_role} of this system."
                                
                                if user_location:
                                    system_prompt += f"\nLocation: {user_location}"
                                
                                if user_style:
                                    system_prompt += f"\n\nCOMMUNICATION PREFERENCE:\nThe user prefers {user_style} responses. Adjust your tone and detail level accordingly."
                                
                                if user_interests:
                                    system_prompt += f"\n\nINTERESTS:\n{', '.join(user_interests)}"
                                
                                if user_skills:
                                    system_prompt += f"\n\nTECHNICAL SKILLS:\n{', '.join(user_skills)}\n(You can assume technical competence in these areas)"
                                
                                if user_goals:
                                    system_prompt += f"\n\nUSER GOALS:\n{', '.join(user_goals)}\n(Help the user achieve these goals)"
                                    
                                system_prompt += "\n\nAddress the user by name occasionally when appropriate to build rapport."
                    except Exception as db_err:
                        print(f"âš ï¸  Note: Could not read user profile: {db_err}")
                    finally:
                        conn.close()

                    # Inject usage patterns dynamically
                    try:
                        from ai_assistant.ai.usage_pattern_analyzer import UsagePatternAnalyzer
                        analyzer = UsagePatternAnalyzer()
                        summary = analyzer.get_pattern_summary()
                        if summary:
                            system_prompt += f"\n\nCURRENT CONTEXT & HABITS:\n"
                            system_prompt += f"- Peak Activity: {summary.get('peak_activity')}\n"
                            system_prompt += f"- Top Apps: {', '.join(summary.get('top_apps', []))}\n"
                            system_prompt += f"- Frequent Topics: {', '.join(summary.get('frequent_topics', []))}\n"
                    except Exception as pattern_err:
                        print(f"âš ï¸  Note: Could not inject usage patterns: {pattern_err}")

                    # Inject User DNA (Living Profile)
                    try:
                        from ai_assistant.ai.user_dna import UserDNA
                        dna_system = UserDNA()
                        dna_profile = dna_system.get_full_profile()
                        if dna_profile:
                            system_prompt += f"\n\nEVOLVING USER DNA (DEEP PREFERENCES):\n"
                            for key, value in dna_profile.items():
                                system_prompt += f"- {key.capitalize()}: {value}\n"
                    except Exception as dna_err:
                        print(f"âš ï¸  Note: Could not inject User DNA: {dna_err}")

            except Exception as e:
                print(f"âš ï¸  Error loading user profile: {e}")

            self.llm_provider.add_system_message(system_prompt)
            print("âœ… LLM provider initialized for real-time AI responses")
        except Exception as e:
            print(f"âš ï¸ LLM provider initialization failed: {e}")
            print("   Falling back to rule-based responses. Set OPENAI_API_KEY or GEMINI_API_KEY for AI responses.")
            self.llm_provider = None
    
    def _init_feedback_system(self):
        """Initialize feedback learning system for training data collection."""
        try:
            from ai_assistant.ai.advanced_feedback_learning import AdaptiveLearningEngine
            self.feedback_system = AdaptiveLearningEngine()
            print("âœ… Training data feedback loop initialized")
        except Exception as e:
            print(f"âš ï¸ Feedback system initialization failed: {e}")
            self.feedback_system = None
        
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
            
            # Emit mood change to UI
            try:
                from ai_assistant.services.modern_web_backend import socketio
                if socketio:
                    socketio.emit('mood_update', {'mood': new_mood.value})
            except ImportError:
                pass
    
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
    
    def save_interaction_feedback(self, prompt: str, response: str, feedback_type: str = "implicit", rating: float = 0.8):
        """Save interaction to training data with optional feedback."""
        if self.feedback_system:
            try:
                # Update User DNA implicitly
                try:
                    from ai_assistant.ai.user_dna import UserDNA
                    dna_system = UserDNA()
                    if feedback_type == "thumbs_up":
                        dna_system.update_trait("latest_successful_topic", getattr(self.contexts.get(self.active_context_id), 'topic', "unknown"))
                except Exception as dna_err:
                    pass

                self.feedback_system.record_interaction(
                    prompt, 
                    response, 
                    context={'mood': self.user_mood.value, 'active_context': self.active_context_id}
                )
                # Add implicit positive feedback for successful interactions
                if feedback_type == "implicit" and rating > 0.7:
                    self.feedback_system.process_thumbs_feedback(
                        prompt=prompt,
                        response=response,
                        is_positive=True,
                        context={'mood': self.user_mood.value}
                    )
                elif feedback_type == "thumbs_up":
                    self.feedback_system.process_thumbs_feedback(
                        prompt=prompt,
                        response=response,
                        is_positive=True,
                        context={'mood': self.user_mood.value}
                    )
            except Exception as e:
                logger.warning(f"⚠️ Failed to save training data: {e}")
    
    def process_message(self, message: str, role: str = "user", provider: str = None, model: str = None) -> str:
        """Process a message and generate an intelligent response with REAL execution."""
        try:
            # Add message to conversation
            self.add_message(role, message)
            
            message_lower = message.lower()

            
            # Detect mood from user messages
            if role == "user":
                self.detect_mood(message)
            
            # Check for context switch
            is_switch, switch_msg, new_ctx_id = self.handle_context_switch_request(message)
            if is_switch:
                # Save to training data
                if self.feedback_system and role == "user":
                    self.feedback_system.record_interaction(message, switch_msg, context={'type': 'context_switch'})
                return switch_msg
            
            # Intercept compound media commands to maintain context before splitting
            media_compound_patterns = [
                r'open ([\w\s]+) and play (.+)',
                r'([\w\s]+) khol aur (.+) baja',
                r'([\w\s]+) khol aur play (.+)',
                r'open ([\w\s]+) aur play (.+)',
            ]
            for pattern in media_compound_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    app_name = match.group(1).strip()
                    song = match.group(2).strip()
                    # Pass the context-rich string to _execute_play_command
                    cmd_res = self._execute_play_command(message_lower, f"play {song} on {app_name}")
                    if cmd_res:
                        return cmd_res
            # Chain of Action: Split by separators (and, then, aur, ,)
            # Use regex to split but keep delimiters to reconstruct if needed, or just split.
            # Handles: "open chrome and search google", "youtube khol aur song baja"
            chain_separators = r'\s+(?:and|then|aur|&)\s+|,\s*'
            
            # Simple heuristic: If multiple parts found, process sequentially
            parts = re.split(chain_separators, message_lower)
            if len(parts) > 1:
                results = []
                for part in parts:
                    part = part.strip()
                    if not part: continue
                    
                    # Try to execute each part as a command
                    # We recurse to self.process_message but avoid infinite recursion by checking strictly for command execution
                    # Actually, using _try_execute_command is safer to avoid looping conversationally
                    
                    cmd_res = self._try_execute_command(part, part)
                    if cmd_res:
                        results.append(cmd_res)
                    else:
                        # If a part is not a command. e.g. "open chrome and hello"
                        # "hello" is not a command. We typically ignore or handle as chat.
                        # For now, let's treat it as a secondary query if needed, or just skip?
                        # User wants Action triggers. If "hello" is passed, we might get "Hello!" response.
                        
                        # Fallback for chat parts? 
                        # Only if it looks like a question or greeting?
                        # Let's try to generate response for non-command parts too.
                        # But prevent "I can help you with..." generic responses for fragments.
                        
                        # Safe fallback:
                        chat_res = self._generate_contextual_response(part, provider=provider, model=model)
                        if chat_res:
                             results.append(chat_res)

                if results:
                    return " \n".join(results)

            # Process different types of queries
            # message_lower is already defined above

            
            # TRY TO EXECUTE COMMAND FIRST - This is the main change!
            command_result = self._try_execute_command(message, message_lower)
            if command_result:
                # Save successful command execution to training data
                if self.feedback_system and role == "user":
                    self.feedback_system.record_interaction(message, command_result, context={'type': 'command'})
                return command_result
            
            # Math queries (if not a command)
            if (any(word in message_lower for word in ['calculate', 'times', 'plus', 'minus', 'divided', 'multiply']) and 'what is' in message_lower) or ('pie' in message_lower or 'pi' in message_lower):
                math_result = self._process_math_query(message)
                # Save to training data
                if self.feedback_system and role == "user":
                    self.feedback_system.record_interaction(message, math_result, context={'type': 'math'})
                return math_result
            
            # Information queries (if not a command)
            if any(word in message_lower for word in ['time', 'date', 'day']) and ('what' in message_lower or 'tell' in message_lower):
                info_result = self._process_info_query(message)
                # Save to training data
                if self.feedback_system and role == "user":
                    self.feedback_system.record_interaction(message, info_result, context={'type': 'info'})
                return info_result
            
            # If nothing else matched, try as a general command with automation callback
            if self.automation_callback:
                # Last resort: check if it's asking to do something
                action_words = ['open', 'close', 'start', 'stop', 'launch', 'run', 'play', 'search', 'find', 
                               'create', 'make', 'set', 'change', 'show', 'get', 'check',
                               'khol', 'band', 'chala', 'baja', 'sun', 'dikha', 'bhejo', 'dhund', 'khoj']
                if any(word in message_lower for word in action_words):
                    return "ðŸ¤” I can sense you want me to do something! Could you be more specific? Here are some examples:\n\nðŸ“± 'open chrome' - Opens Google Chrome\nðŸŽµ 'play music' - Plays music on YouTube\nðŸ” 'search for python' - Searches Google\nðŸ“ 'create a document' - Opens Word\n\nWhat exactly would you like me to do?"
            
            # Default: Generate contextual response with LLM
            response = self._generate_contextual_response(message, provider, model)
            
            # Save all conversational responses to training data
            if self.feedback_system and role == "user":
                self.feedback_system.record_interaction(message, response, context={
                    'type': 'conversation',
                    'mood': self.user_mood.value,
                    'context_id': self.active_context_id
                })
            
            return response
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Error in process_message: {error_trace}")
            
            # More user-friendly error messages based on the error type
            if "automation" in str(e).lower():
                return "ðŸ”§ I'm having trouble connecting to some system features right now. Please try again, or try a different command."
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                return "ðŸŒ There seems to be a network issue. Please check your connection and try again."
            else:
                return "ðŸ˜… I encountered a small hiccup while processing that. Could you try rephrasing your request or try a different command?"
    
    def process_query(self, query: str) -> str:
        """
        Alias for process_message to enforce compatibility with voice handlers.
        """
        return self.process_message(query, role="user")
    
    def _process_math_query(self, query: str) -> str:
        """Process mathematical queries and return calculated results."""
        try:
            import re
            query_lower = query.lower()
            
            # Extract numbers and operations
            if 'pie' in query_lower or 'pi' in query_lower:
                return "The value of Ï€ (pi) is approximately 3.14159265359. It's the ratio of a circle's circumference to its diameter."
            
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
                    import ast
                    import operator
                    safe_operators = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.USub: operator.neg, ast.UAdd: operator.pos}
                    def evaluate_math(node):
                        if isinstance(node, ast.Expression): return evaluate_math(node.body)
                        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return node.value
                        elif isinstance(node, ast.BinOp): return safe_operators[type(node.op)](evaluate_math(node.left), evaluate_math(node.right))
                        elif isinstance(node, ast.UnaryOp): return safe_operators[type(node.op)](evaluate_math(node.operand))
                        raise ValueError("Unsupported")
                    
                    result = evaluate_math(ast.parse(expr, mode='eval'))
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
            # Clean query to remove emojis and extra symbols for better matching
            # This handles cases like "ðŸš€ Open Chrome" -> "open chrome"
            clean_query = re.sub(r'[^\w\s\d\.\-\?\!]', '', query_lower).strip()
            
            # Heuristic: Check first few words for command verbs to avoid false positives
            # e.g. "I can see you didn't open chrome" should NOT trigger "open chrome"
            words = clean_query.split()
            first_few_words = words[:4] if len(words) > 4 else words
            
            # --- SEMANTIC ROUTING LAYER ---
            if self.intent_router:
                route, score = self.intent_router.determine_intent(query)
                if route:
                    print(f"ðŸ§  Semantic Route: {route} (Confidence: {score})")
                    if route == 'vision':
                        return self._execute_vision_command(query, clean_query)
                    elif route == 'open':
                         return self._execute_open_command(query, clean_query)
                    elif route == 'close':
                        return self._execute_close_command(query, clean_query)
                    elif route == 'search':
                        return self._execute_search_command(query, clean_query)
                    elif route == 'play':
                         return self._execute_play_command(query, clean_query)
            # ------------------------------

            
            # PRIORITY 1: System/Settings commands (more specific than generic open)
            if ('settings' in clean_query or 'control panel' in clean_query or \
               any(word in clean_query for word in ['wifi', 'bluetooth', 'display', 'network', 'sound'])) and \
               any(word in first_few_words for word in ['open', 'start', 'show', 'launch']):
                return self._execute_settings_command(query, clean_query)
            
            # PRIORITY 2: Opening apps/websites - Most common command
            if any(word in first_few_words for word in ['open', 'launch', 'start', 'run', 'khol', 'chalo', 'chalu']):
                return self._execute_open_command(query, clean_query)
            
            # PRIORITY 3: Closing apps
            if any(word in first_few_words for word in ['close', 'quit', 'exit', 'kill', 'stop', 'band', 'hata']):
                return self._execute_close_command(query, clean_query)
            
            # PRIORITY 3.5: YouTube Search / Watch
            if 'youtube' in clean_query:
                # If command is explicitly 'search', 'find', 'watch', 'play', 'show' + youtube
                if any(word in first_few_words for word in ['search', 'find', 'look', 'watch', 'play', 'show', 'dikha', 'chala']):
                     return self._execute_play_command(query, clean_query)
            
            # PRIORITY 3.8: Vision / Screen Analysis
            # "Look at this", "Screen dekho", "What is on screen", "Take screenshot", "see it in taskbar"
            if any(word in clean_query for word in ['look', 'see', 'screen', 'dekho', 'kya hai', 'scan', 'screenshot', 'capture', 'taskbar']) and \
               any(word in clean_query for word in ['at', 'my', 'screen', 'dekho', 'this', 'ye', 'take', 'check', 'of', 'it', 'is', 'in']):
                 logger.debug(f"DEBUG: Vision Intent Detected for {clean_query}")
                 return self._execute_vision_command(query, clean_query)


            
            # PRIORITY 4: Searching - Google, web search
            if any(word in first_few_words for word in ['google', 'search', 'find', 'lookup', 'dhund', 'khoj', 'pata']) and 'download' not in clean_query:
                return self._execute_search_command(query, clean_query)
            
            # PRIORITY 4.5: Downloading (YouTube/Media)
            if any(word in first_few_words for word in ['download', 'get']) and 'audio' in clean_query:
                return self._execute_download_command(query, clean_query)
            
            # PRIORITY 5: Playing music
            if any(word in first_few_words for word in ['play', 'baja', 'laga', 'sun']):
                return self._execute_play_command(query, clean_query)
            
            # PRIORITY 6: Creating documents
            if any(word in first_few_words for word in ['create', 'make', 'generate', 'new']) and \
               any(doc in clean_query for doc in ['ppt', 'powerpoint', 'presentation', 'pdf', 'document', 'doc', 'word']):
                return self._execute_create_document(query, clean_query)
            
            # PRIORITY 7: Volume control
            if 'volume' in clean_query or 'sound' in clean_query or 'mute' in clean_query:
                return self._execute_volume_command(query, clean_query)
            
            # PRIORITY 8: System commands (shutdown, restart, etc.)
            if any(word in first_few_words for word in ['shutdown', 'restart', 'sleep', 'lock']):
                return self._execute_system_command(query, clean_query)
            
            return None
            
        except Exception as e:
            import traceback
            print(f"Command execution error: {traceback.format_exc()}")
            return f"âŒ Error executing command: {str(e)}"
    
    def _execute_download_command(self, query: str, query_lower: str) -> str:
        """Execute download commands (YouTube audio)."""
        # Extract search term
        search_term = query_lower
        for word in ['download', 'get', 'audio', 'song', 'music', 'mp3', 'from', 'youtube', 'the', 'please', 'can', 'you']:
            search_term = search_term.replace(word, '')
        search_term = search_term.strip()
        
        if not search_term:
            return "What song or video would you like me to download?"
            
        return f"â¬‡ï¸ Downloading '{search_term}'... This might take a moment.\n\n" + \
               self._perform_download_task(search_term)

    def _perform_download_task(self, search_term: str) -> str:
        """Helper to run download in a way that returns a string result."""
        # In a real async system, this should be a background task.
        # For now, we'll do it synchronously but warn the user.
        try:
            result = youtube_downloader.search_and_download_audio(search_term)
            if result['status'] == 'success':
                return f"âœ… Success! Downloaded: {result['title']}\nSaved to: {result['file_path']}"
            else:
                return f"âŒ Download failed: {result['message']}"
        except Exception as e:
            return f"âŒ Error: {str(e)}"

    def _verify_execution_visually(self, command_text: str, expected_app_name: str) -> str:
        """Uses Gemini Vision to verify if a command actually succeeded on screen."""
        if not self.vision_provider:
            return "âš ï¸ (Visual verification skipped: Vision Provider not initialized. Set GEMINI_API_KEY)"
    
        print(f"ðŸ‘€ Verifying execution of: {expected_app_name}...")
        
        # 1. Wait a moment for the application/UI to load
        time.sleep(3.0) 
        
        try:
            # 2. Capture the current screen
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            
            # 3. Create a strict, binary validation prompt for the VLM
            verification_prompt = (
                f"I just commanded the computer to '{command_text}'. "
                f"You are a strict validation system. Look at this current screenshot of the desktop. "
                f"Can you clearly see that '{expected_app_name}' is open or the action was successful? "
                f"Reply with EXACTLY ONE WORD: 'SUCCESS' if you see it, or 'FAILURE' if you do not."
            )
            
            # 4. Ask Gemini Vision to analyze it
            result = self.vision_provider.analyze_image(image=screenshot, prompt=verification_prompt)
            text_result = result.get("text", "").strip().upper()
            
            if "SUCCESS" in text_result:
                return "âœ… (Visually Verified by AI)"
            else:
                return "âŒ (Warning: App did not appear on screen. It might be loading slowly or failed.)"
                
        except Exception as e:
            return f"âš ï¸ (Visual verification error: {str(e)})"

    def _execute_open_command(self, query: str, query_lower: str) -> str:
        """Execute open application commands."""
        # Extract app name - remove command words
        app_name = query_lower
        for word in ['open', 'launch', 'start', 'run', 'the', 'app', 'application', 'program', 'khol', 'chalu', 'karo']:
            app_name = app_name.replace(word, '')
        app_name = app_name.strip()
        
        if not app_name:
            return "Which application would you like me to open?"
        
        # 🚀 CRITICAL FIX: Use Intent Recognizer to normalize app name
        original_app_name = app_name
        try:
            from ai_assistant.ai.intent_recognizer import IntentRecognizer
            recognizer = IntentRecognizer()
            app_name = recognizer.normalize_app_name(app_name)
            if app_name != original_app_name:
                print(f"[Intent Recognizer] Normalized '{original_app_name}' -> '{app_name}'")
        except Exception as e:
            print(f"[Intent Recognizer] Not available: {e}")
            
        # Check if it's a URL or website directly
        if any(indicator in app_name for indicator in ['.com', '.org', '.net', '.io', '.app', '.dev', 'http', 'www.']):
            url = app_name
            if not url.startswith('http'):
                url = 'https://' + url.replace('www.', '')
            try:
                import webbrowser
                webbrowser.open(url)
                return self._format_success(f"✅ Opening {url} in your browser", f"open {url}")
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
        
        # Direct fallback to centralized engine
        try:
            from ai_assistant.automation.app_discovery import smart_open_application
            result = smart_open_application(app_name)
            return self._format_success(f"✅ {result}", f"open {app_name}")
        except Exception as e:
            return f"❌ Could not find application '{app_name}'. Try being more specific or check if it's installed."

    def _execute_close_command(self, query: str, query_lower: str) -> str:
        """Execute close application commands."""
        # Extract app name - remove command words
        app_name = query_lower
        words_to_remove = ['close', 'stop', 'quit', 'exit', 'kill', 'end', 'terminate', 'the', 'app', 'application', 'band', 'hata', 'karo']
        pattern = r'\b(?:' + '|'.join(words_to_remove) + r')\b'
        app_name = re.sub(pattern, '', app_name, flags=re.IGNORECASE)
        app_name = re.sub(r'\s+', ' ', app_name).strip()
        
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
        
        from ai_assistant.automation.app_automation import AppAutomation
        automator = AppAutomation()
        if automator.close_app(app_name):
            return f"✅ Closed {app_name.title()}"
        return f"❌ Could not close '{app_name}'"

    def _execute_search_command(self, query: str, query_lower: str) -> str:
        """Execute Google search commands."""
        # Extract search query - remove command words
        search_query = query_lower
        words_to_remove = ['google', 'search for', 'search', 'look up', 'look for', 'find', 'about', 'on', 'the', 'dhund', 'khoj', 'karo', 'ke baare mein']
        words_to_remove.sort(key=len, reverse=True)
        pattern = r'\b(?:' + '|'.join(re.escape(w) for w in words_to_remove) + r')\b'
        search_query = re.sub(pattern, '', search_query, flags=re.IGNORECASE)
        search_query = re.sub(r'\s+', ' ', search_query).strip()
        
        if not search_query or len(search_query) < 2:
            return "What would you like me to search for?"
            
        # 🌟 CONTEXT AWARENESS: Check Active Window
        # ONLY if user didn't explicitly ask for Google
        if 'google' not in query_lower:
            try:
                active_window = self._get_active_window_title().lower()
                logger.debug(f"DEBUG: Active Window: {active_window}")
                
                if 'youtube' in active_window:
                    # Redirect to YouTube search
                    return self._execute_play_command(f"{search_query}", f"{search_query}")
                    
                elif 'spotify' in active_window:
                    # Redirect to Spotify search (if supported, else standard play)
                    return self._execute_play_command(f"play {search_query} on spotify", f"play {search_query} on spotify")
                    
            except Exception as e:
                print(f"Context check failed: {e}")

        # Try automation callback first
        if self.automation_callback:
            try:
                result = self.automation_callback('search_google', search_query)
                if result and 'error' not in str(result).lower():
                    return f"🔍 {result}"
            except Exception as e:
                print(f"Automation search error: {e}")
        
        # Fallback to direct automation engine
        from ai_assistant.automation.app_automation import AppAutomation
        automator = AppAutomation()
        if automator.search_web(search_query):
            return f"🔍 Searching Google for: '{search_query}'"
        return f"❌ Search failed"

    def _execute_play_command(self, query: str, query_lower: str) -> str:
        """Execute play music commands."""
        import re
        song = query_lower
        
        # Extract platform to preserve it from stop-word stripping
        platform_suffix = ""
        platform_match = re.search(r'\b(on|pe)\s+(youtube music|youtubemusic|spotify|youtube|apple music|soundcloud|jiosaavn)\b', song)
        if platform_match:
            platform_suffix = " " + platform_match.group(0)
            song = song[:platform_match.start()].strip()
            
        # Handle "by artist" patterns specially
        if ' by ' in song:
            song = re.sub(r'\bplay\b', '', song, flags=re.IGNORECASE).strip()
            words_to_remove = ['music', 'song', 'the', 'some', 'something', 'search', 'find', 'watch', 'look for', 'baja', 'laga', 'sun', 'dikha']
            words_to_remove.sort(key=len, reverse=True)
            pattern = r'\b(?:' + '|'.join(re.escape(w) for w in words_to_remove) + r')\b'
            song = re.sub(pattern, '', song, flags=re.IGNORECASE)
        else:
            words_to_remove = ['play', 'music', 'song', 'the', 'some', 'search', 'find', 'watch', 'look for', 'baja', 'laga', 'sun', 'dikha']
            words_to_remove.sort(key=len, reverse=True)
            pattern = r'\b(?:' + '|'.join(re.escape(w) for w in words_to_remove) + r')\b'
            song = re.sub(pattern, '', song, flags=re.IGNORECASE)
            
        song = re.sub(r'\s+', ' ', song).strip()
        
        # Re-attach platform
        song = song + platform_suffix
        
        if not song or len(song) < 2 or song in ['music', 'something', 'anything']:
            if self.automation_callback:
                try:
                    result = self.automation_callback('play_music', 'popular music')
                    if result and 'error' not in str(result).lower():
                        return f"🎵 {result}"
                except Exception as e:
                    print(f"Automation play error: {e}")
            return "🎵 I'd love to play music for you! Please tell me what song or artist you'd like to hear."
        
        if self.automation_callback:
            try:
                result = self.automation_callback('play_music', song)
                if result and 'error' not in str(result).lower():
                    return f"🎵 {result}"
            except Exception as e:
                print(f"Automation play error: {e}")
        
        # Fallback to direct automation engine
        from ai_assistant.automation.app_automation import AppAutomation
        automator = AppAutomation()
        if automator.play_media(song):
            return f"🎵 Playing: '{song}'"
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
                        return f"ðŸ”Š {result}" if result else f"Volume set to {level}%"
                
                # Check for up/down
                if 'up' in query_lower or 'increase' in query_lower or 'raise' in query_lower:
                    result = self.automation_callback('volume_up', None)
                    return f"ðŸ”Š Volume increased"
                elif 'down' in query_lower or 'decrease' in query_lower or 'lower' in query_lower:
                    result = self.automation_callback('volume_down', None)
                    return f"ðŸ”Š Volume decreased"
                elif 'mute' in query_lower:
                    result = self.automation_callback('mute', None)
                    return f"ðŸ”‡ Volume muted"
            except:
                pass
        
        return "Please specify: 'volume up', 'volume down', 'volume mute', or 'volume [0-100]'"
    
    def _execute_settings_command(self, query: str, query_lower: str) -> str:
        """Execute system settings commands."""
        try:
            if 'wifi' in query_lower or 'network' in query_lower:
                subprocess.Popen('ms-settings:network', shell=True)
                return "âš™ï¸ Opening Network Settings"
            elif 'bluetooth' in query_lower:
                subprocess.Popen('ms-settings:bluetooth', shell=True)
                return "âš™ï¸ Opening Bluetooth Settings"
            elif 'display' in query_lower or 'screen' in query_lower:
                subprocess.Popen('ms-settings:display', shell=True)
                return "âš™ï¸ Opening Display Settings"
            elif 'sound' in query_lower or 'audio' in query_lower:
                subprocess.Popen('ms-settings:sound', shell=True)
                return "âš™ï¸ Opening Sound Settings"
            elif 'system' in query_lower:
                subprocess.Popen('ms-settings:about', shell=True)
                return "âš™ï¸ Opening System Settings"
            else:
                subprocess.Popen('ms-settings:', shell=True)
                return "âš™ï¸ Opening Windows Settings"
        except Exception as e:
            return f"âŒ Could not open settings: {str(e)}"
    
    def _execute_system_command(self, query: str, query_lower: str) -> str:
        """Execute system commands like shutdown, restart, etc."""
        try:
            if 'shutdown' in query_lower:
                # Don't actually shutdown without confirmation!
                return "âš ï¸ To shutdown your computer, please use the Start menu or confirm this action."
            elif 'restart' in query_lower:
                return "âš ï¸ To restart your computer, please use the Start menu or confirm this action."
            elif 'lock' in query_lower:
                subprocess.Popen('rundll32.exe user32.dll,LockWorkStation', shell=True)
                return "ðŸ”’ Locking your computer..."
            elif 'sleep' in query_lower:
                subprocess.Popen('rundll32.exe powrprof.dll,SetSuspendState 0,1,0', shell=True)
                return "ðŸ˜´ Putting computer to sleep..."
            else:
                return "I can help with: lock, sleep. For shutdown/restart, please use the Start menu for safety."
        except Exception as e:
            return f"âŒ Could not execute system command: {str(e)}"

    def _get_active_window_title(self) -> str:
        """Get the title of the currently active window."""
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
        except Exception:
            return ""

    def _execute_vision_command(self, query: str, query_lower: str) -> str:
        """Execute vision/VLM commands by analyzing the screen."""
        if not self.vision_provider:
             return "âš ï¸ Vision features are not initialized. Please check GEMINI_API_KEY."
        
        if not ImageGrab:
             return "âš ï¸ PIL ImageGrab is not available. Cannot capture screen."

        try:
            # 1. Capture Screen
            screenshot = ImageGrab.grab()
            
            # 2. Refine Prompt
            prompt = query_lower
            for word in ['look', 'at', 'this', 'screen', 'dekho', 'scan', 'check', 'my', 'what', 'is', 'on', 'the', 'kya', 'hai', 'ye', 'take', 'screenshot', 'capture', 'taskbar']:
                 prompt = prompt.replace(word, '')
            prompt = prompt.strip()
            
            # If prompt is too short, assume general description
            if len(prompt) < 3:
                full_prompt = "Describe what is currently visible on my screen in detail."
            else:
                full_prompt = f"Analyze this screen and answer: {query}"
            
            # 3. Analyze
            return f"ðŸ‘€ Looking at screen...\n" + self.vision_provider.analyze_image(screenshot, full_prompt).text
            
        except Exception as e:
            return f"âŒ Vision verification failed: {str(e)}"

    def _verify_task_completion(self, original_command: str) -> str:
        """Wait and verify task completion using VLM."""
        if not self.vision_provider or not ImageGrab: return ""
        
        target_app = original_command.split(' ', 1)[1] if ' ' in original_command else original_command
        if len(target_app) < 2: return ""

        try:
            # 1. Wait for action (2s)
            time.sleep(2) 
            
            # 2. Capture
            screenshot = ImageGrab.grab()
            
            # 3. Ask VLM
            prompt = f"I just executed command: '{original_command}'. Check if '{target_app}' is visible/open/active on the screen. Reply with 'âœ… Verified' or 'âŒ Issue' and a very short reason."
            
            res = self.vision_provider.analyze_image(screenshot, prompt)
            return f"\n\n[Vision Audit]: {res.text}"
        except:
             return ""

    def _format_success(self, message: str, command: str) -> str:
        """Helper to append verification to success message."""
        verify = self._verify_task_completion(command)
        return f"{message}{verify}"


    
    def _process_command_query(self, query: str) -> str:
        """Process command-based queries."""
        query_lower = query.lower()
        
        if 'open' in query_lower:
            return "I understand you want to open an application. Which app would you like me to open?"
        
        return f"I can help execute that command. You asked: '{query}'"
    
    def _generate_contextual_response(self, message: str, provider: str = None, model: str = None) -> str:
        """Generate a contextual response using LLM or fallback to rule-based."""
        message_lower = message.lower().strip()
        
        # Determine which provider to use
        active_provider = self.llm_provider
        
        # Dynamic Switching if requested
        if provider and active_provider:
             # If requested provider is different from current
             current_name = active_provider.provider_name.lower() if hasattr(active_provider, 'provider_name') else ''
             if provider.lower() not in current_name:
                  try:
                       print(f"ðŸ”„ Temporarily switching LLM: {current_name} -> {provider}")
                       from ai_assistant.ai.llm_provider import UnifiedChatInterface
                       # Create temp provider
                       active_provider = UnifiedChatInterface(provider=provider, model=model, use_fallback=True)
                       
                       # Add Identity System Message
                       if 'openai' in provider.lower():
                            active_provider.add_system_message("You are an AI assistant powered by OpenAI.")
                       elif 'gemini' in provider.lower():
                            active_provider.add_system_message("You are Pulsar, powered by Google Gemini.")
                            
                  except Exception as e:
                       print(f"âš ï¸ Failed to switch provider: {e}")
                       active_provider = self.llm_provider # Fallback to default

        # FIRST: Try to use the LLM provider for real-time AI responses
        if active_provider:
            try:
                # Build conversation context for the LLM
                conversation_context = ""
                if self.active_context_id and self.active_context_id in self.contexts:
                    context = self.contexts[self.active_context_id]
                    # Include recent messages for context
                    recent_msgs = context.messages[-5:] if context.messages else []
                    for msg in recent_msgs:
                        role = msg.get('role', 'user')
                        content = msg.get('content', '')
                        if content:
                            conversation_context += f"{role.capitalize()}: {content}\n"
                
                # Generate response using LLM
                print(f"ðŸ¤– Generating AI response for: {message[:50]}...")
                response = active_provider.chat(message, stream=False)
                
                logger.debug(f"DEBUG: LLM response type: {type(response)}, length: {len(str(response)) if response else 0}")
                logger.debug(f"DEBUG: Response content: {str(response)[:100]}")
                
                if response and "Error" not in str(response) and len(str(response)) > 5:
                    print(f"âœ… AI response generated successfully")
                    return response
                else:
                    print(f"âš ï¸ LLM returned empty or error response, using fallback")
                    print(f"   Response was: {response}")
            except Exception as e:
                print(f"âš ï¸ LLM response generation failed: {e}, using rule-based fallback")
        
        # FALLBACK: Rule-based responses for common queries (when LLM unavailable)
        # Handle greetings
        greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        if any(greeting in message_lower for greeting in greetings):
            return "ðŸ‘‹ Hello! I'm your assistant. I can help you open apps, search the web, play music, create documents, and much more. What would you like me to do?"
        
        # Handle "how are you" type questions
        if any(phrase in message_lower for phrase in ['how are you', 'how r u', 'how do you feel']):
            return "I'm doing great, thank you for asking! ðŸ˜Š I'm ready to help you with any tasks. What can I do for you today?"
        
        # Handle capability questions
        if any(phrase in message_lower for phrase in ['what can you do', 'what are you capable of', 'help me', 'what features']):
            return "ðŸš€ I can help you with many things:\n\nðŸ“± Open applications (chrome, notepad, calculator, etc.)\nðŸ” Search Google for anything\nðŸŽµ Play music on YouTube/Spotify\nðŸ“ Create documents and presentations\nðŸ”§ Control system settings (volume, WiFi, etc.)\nðŸ“Š Perform calculations\nâ° Tell you time and date\n\nJust ask me naturally! For example: 'open chrome', 'play some music', or 'search for python tutorials'."
        
        # Handle thank you messages
        if any(phrase in message_lower for phrase in ['thank you', 'thanks', 'appreciate']):
            return "You're very welcome! ðŸ˜Š I'm always here to help. Is there anything else you need?"
        
        # Handle questions about assistant
        if any(phrase in message_lower for phrase in ['who are you', 'what are you', 'tell me about yourself']):
            return "I'm Pulsar Assistant! ðŸ¤– I'm an AI assistant designed to help you with daily tasks like opening applications, searching the web, playing music, managing files, and much more. Think of me as your personal digital helper!"
        
        # Handle unclear requests
        if any(phrase in message_lower for phrase in ['do something', 'help', 'assist', 'i need']):
            return "I'd be happy to help! ðŸ’ª Here are some things I can do for you:\n\nâ€¢ Open applications: 'open chrome'\nâ€¢ Search: 'google python tutorial'\nâ€¢ Play music: 'play believer'\nâ€¢ Create files: 'create a document'\nâ€¢ System control: 'volume up'\n\nWhat would you like me to help with?"
        
        # Return context-aware response for ongoing conversations
        if self.active_context_id:
            context = self.contexts[self.active_context_id]
            if len(context.messages) > 3:
                return f"I'm following our conversation about {context.topic}. What else can I help you with? ðŸš€"
        
        # For general knowledge questions without LLM - indicate limitation
        question_words = ['what', 'why', 'how', 'when', 'where', 'who', 'which', 'explain', 'tell me about']
        if any(word in message_lower for word in question_words):
            return (
                "ðŸ¤” That's a great question! However, I'm currently running in offline mode without access to AI. "
                "To get intelligent answers to your questions, please configure an API key:\n\n"
                "â€¢ Set OPENAI_API_KEY for GPT models, or\n"
                "â€¢ Set GEMINI_API_KEY for Google Gemini\n\n"
                "In the meantime, I can still help you with:\n"
                "â€¢ Opening apps: 'open chrome'\n"
                "â€¢ Playing music: 'play [song name]'\n"
                "â€¢ Searching: 'search for [query]'\n"
                "â€¢ Basic calculations: 'what is 10 times 5'"
            )
        
        # Random thoughtful responses for variety
        import random
        thoughtful_responses = [
            "That's interesting! I'd love to help you with that. For intelligent responses, please set up an AI API key (OPENAI_API_KEY or GEMINI_API_KEY). ðŸ’¡",
            "I hear you! For detailed AI-powered responses, please configure your API keys. Meanwhile, try commands like 'open chrome' or 'play music'! ðŸ˜Š",
            "Got it! To unlock my full potential, please set OPENAI_API_KEY or GEMINI_API_KEY. I can still help with app control and searches! ðŸŽ¯"
        ]
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
            logger.error(f"Error loading contexts: {e}")
    
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
