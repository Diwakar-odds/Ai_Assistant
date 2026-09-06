# Setup centralized logging
try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__, log_category="app")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

"""
Intelligent Intent Router for Pulsar AI Assistant

Two-tier architecture:
  Tier 1: Fast local pattern matching (~0ms) for obvious commands
  Tier 2: LLM function calling (~300-800ms) for ambiguous/Hinglish queries

Replaces the hardcoded if/else keyword chain in _try_execute_command.
"""

import re
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class IntentDefinition:
    """Definition of a single intent (command type)."""
    name: str
    description: str  # Human-readable, used in LLM function description
    parameters: Dict[str, Dict[str, Any]]  # param_name -> {type, description, enum?, required?}
    tier1_patterns: List[str] = field(default_factory=list)  # Regex patterns for fast matching
    examples: List[str] = field(default_factory=list)  # Example phrases (for documentation)


@dataclass
class IntentResult:
    """Result of intent routing."""
    intent_name: Optional[str]  # None = no command detected (pure conversation)
    parameters: Dict[str, Any]
    confidence: float  # 0.0-1.0
    tier: int  # 1 or 2 (which tier resolved it)
    raw_query: str


# =============================================================================
# INTENT ROUTER
# =============================================================================

class IntentRouter:
    """
    Intelligent intent routing using a two-tier system:
    
    Tier 1: Fast regex/keyword matching for unambiguous commands
    Tier 2: LLM function calling (Gemini) for ambiguous or Hinglish queries
    """

    def __init__(self, llm_provider=None):
        """
        Args:
            llm_provider: UnifiedChatInterface instance for Tier 2 routing.
                          If None, only Tier 1 will be available.
        """
        self.llm_provider = llm_provider
        self.intents: Dict[str, IntentDefinition] = {}
        
        # Dedicated LLM for routing (separate from conversation history)
        self._router_llm = None
        self._init_router_llm()
        
        # Register all default intents
        self._register_all_intents()
        
        logger.info(f"✅ IntentRouter initialized with {len(self.intents)} intents "
                     f"(Tier 2 {'enabled' if self._router_llm else 'disabled'})")

    def _init_router_llm(self):
        """Initialize a dedicated LLM instance for intent routing (doesn't pollute conversation history)."""
        try:
            import os
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self._router_llm = genai.GenerativeModel("gemini-2.5-flash")
                logger.info("✅ IntentRouter Tier 2: Gemini function calling ready")
                return
            
            # Fallback: try OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                # We'll use the llm_provider passed in for OpenAI
                if self.llm_provider and not getattr(self.llm_provider, 'offline_mode', True):
                    self._router_llm = "openai_fallback"
                    logger.info("✅ IntentRouter Tier 2: OpenAI fallback ready")
                    return
            
            logger.warning("⚠️ IntentRouter Tier 2 disabled: No API key found (GEMINI_API_KEY or OPENAI_API_KEY)")
        except Exception as e:
            logger.warning(f"⚠️ IntentRouter Tier 2 init failed: {e}")

    # =========================================================================
    # INTENT REGISTRATION
    # =========================================================================

    def register_intent(self, intent: IntentDefinition):
        """Register an intent definition."""
        self.intents[intent.name] = intent

    def _register_all_intents(self):
        """Register all 14 built-in intents."""

        # 1. Open App
        self.register_intent(IntentDefinition(
            name="open_app",
            description="Open an application, website, or program on the computer",
            parameters={
                "target": {"type": "string", "description": "Name of the app, website, or program to open", "required": True}
            },
            tier1_patterns=[
                r'^\s*(?:open|launch|start|run)\s+(.+)',
                r'^\s*(?:khol|kholo|chalo|chalu\s+kar|chalu\s+karo)\s+(.+)',
            ],
            examples=["open chrome", "chrome khol do", "start notepad", "launch spotify"]
        ))

        # 2. Close App
        self.register_intent(IntentDefinition(
            name="close_app",
            description="Close, quit, or kill an application or program",
            parameters={
                "target": {"type": "string", "description": "Name of the app or program to close", "required": True}
            },
            tier1_patterns=[
                r'^\s*(?:close|quit|exit|kill|stop)\s+(.+)',
                r'^\s*(?:band\s+kar|band\s+karo|hata|hatao)\s+(.+)',
            ],
            examples=["close notepad", "quit chrome", "notepad band karo"]
        ))

        # 3. Search Web
        self.register_intent(IntentDefinition(
            name="search_web",
            description="Search the web or Google for information",
            parameters={
                "query": {"type": "string", "description": "The search query", "required": True}
            },
            tier1_patterns=[
                r'^\s*(?:google|search|search\s+for|lookup|find)\s+(.+)',
                r'^\s*(?:dhund|khoj|pata\s+karo|search\s+karo)\s+(.+)',
            ],
            examples=["search python tutorial", "google karo AI news", "dhund do machine learning"]
        ))

        # 4. Play Media
        self.register_intent(IntentDefinition(
            name="play_media",
            description="Play music, a song, a video, or media content",
            parameters={
                "query": {"type": "string", "description": "Name of song, artist, video, or media to play", "required": True},
                "platform": {"type": "string", "description": "Platform to play on (youtube, spotify, etc.)", "required": False}
            },
            tier1_patterns=[
                r'^\s*(?:play|baja|bajao|laga|lagao|sun|suno)\s+(.+)',
            ],
            examples=["play believer", "baja do arijit singh", "play music on spotify", "gaana laga do"]
        ))

        # 5. Volume Control
        self.register_intent(IntentDefinition(
            name="volume_control",
            description="Control the system volume (up, down, mute, unmute, or set to specific level)",
            parameters={
                "action": {"type": "string", "description": "Volume action", "enum": ["up", "down", "mute", "unmute", "set"], "required": True},
                "level": {"type": "integer", "description": "Volume level 0-100 (only when action is 'set')", "required": False}
            },
            tier1_patterns=[
                r'(?:volume|sound|awaaz|awaz)\s+(up|down|mute|unmute|kam|zyada|badha|badhao|kam\s+karo|badha\s+do)',
                r'(mute|unmute)\s+(?:sound|volume|awaaz)?',
                r'(?:awaaz|awaz|volume)\s+(kam|zyada|badha|badhao)\s*(?:karo|kar|do)?',
            ],
            examples=["volume up", "mute", "awaaz kam karo", "volume set 50"]
        ))

        # 6. System Control
        self.register_intent(IntentDefinition(
            name="system_control",
            description="System power commands: shutdown, restart, sleep, or lock the computer",
            parameters={
                "action": {"type": "string", "description": "System action", "enum": ["shutdown", "restart", "sleep", "lock"], "required": True}
            },
            tier1_patterns=[
                r'^\s*(shutdown|restart|sleep|lock)\s*(?:the\s+)?(?:computer|system|pc)?',
                r'^\s*(?:computer|system|pc)\s+(shutdown|restart|sleep|lock)',
            ],
            examples=["shutdown", "restart the computer", "lock karo", "system sleep"]
        ))

        # 7. Battery Status
        self.register_intent(IntentDefinition(
            name="battery_status",
            description="Check the battery level, charging status, or power information",
            parameters={},
            tier1_patterns=[
                r'(?:battery|charge|betri|charging)',
            ],
            examples=["battery kitni hai", "check battery", "charge kitna hai", "is it charging"]
        ))

        # 8. List Running Apps
        self.register_intent(IntentDefinition(
            name="list_running_apps",
            description="List all currently running applications, open programs, or active windows",
            parameters={},
            tier1_patterns=[
                r'(?:running\s+app|open\s+app|active\s+app|chal\s+rahe|khule\s+hain|kaun\s+se\s+app)',
                r'(?:which|what|kaun|kitne)\s+(?:apps?|programs?|windows?)\s+(?:are\s+)?(?:running|open|active|chal|khule)',
            ],
            examples=["which apps are running", "kaun se apps chal rahe hain", "running apps dikhao", "open apps"]
        ))

        # 9. Bluetooth Toggle
        self.register_intent(IntentDefinition(
            name="bluetooth_toggle",
            description="Turn bluetooth on or off",
            parameters={
                "enable": {"type": "boolean", "description": "True to turn on, False to turn off", "required": True}
            },
            tier1_patterns=[
                r'bluetooth\s+(on|off|chalu|band|start|stop)',
                r'(on|off|chalu|band|start|stop)\s+bluetooth',
            ],
            examples=["bluetooth on karo", "turn off bluetooth", "bluetooth chalu karo"]
        ))

        # 10. Create Document
        self.register_intent(IntentDefinition(
            name="create_document",
            description="Create a new document, presentation, or file (Word, PPT, PDF)",
            parameters={
                "doc_type": {"type": "string", "description": "Type of document", "enum": ["document", "presentation", "pdf", "word", "ppt", "powerpoint"], "required": True},
                "title": {"type": "string", "description": "Title or topic for the document", "required": False}
            },
            tier1_patterns=[
                r'^\s*(?:create|make|generate|new|banao|bana)\s+(?:a\s+)?(?:new\s+)?(ppt|powerpoint|presentation|pdf|document|doc|word)',
            ],
            examples=["create a ppt", "make presentation on AI", "document bana do", "new word file"]
        ))

        # 11. Create Folder
        self.register_intent(IntentDefinition(
            name="create_folder",
            description="Create a new folder or directory on the filesystem",
            parameters={
                "name": {"type": "string", "description": "Name of the folder to create", "required": True},
                "path": {"type": "string", "description": "Path where to create the folder", "required": False}
            },
            tier1_patterns=[
                r'(?:create|make|banao|bana)\s+(?:a\s+)?(?:new\s+)?(?:folder|directory)\s+(?:named?\s+)?(.+)',
            ],
            examples=["create folder test", "make a new folder named projects", "folder banao homework"]
        ))

        # 12. Open Settings
        self.register_intent(IntentDefinition(
            name="open_settings",
            description="Open system settings, control panel, or a specific settings page (WiFi, display, sound, network, bluetooth)",
            parameters={
                "setting": {"type": "string", "description": "Specific setting to open (wifi, bluetooth, display, network, sound)", "required": False}
            },
            tier1_patterns=[
                r'(?:open|show|launch)\s+(?:the\s+)?(?:settings|control\s+panel)',
                r'(?:open|show|launch)\s+(?:the\s+)?(wifi|bluetooth|display|network|sound)\s+settings',
            ],
            examples=["open settings", "wifi settings khol do", "show display settings"]
        ))

        # 13. Analyze Screen
        self.register_intent(IntentDefinition(
            name="analyze_screen",
            description="Look at the screen, take a screenshot, analyze what's visible on the desktop, or describe screen content",
            parameters={
                "question": {"type": "string", "description": "Specific question about what's on screen", "required": False}
            },
            tier1_patterns=[
                r'(?:look\s+at|see|scan|check)\s+(?:my\s+)?(?:screen|desktop|display|this)',
                r'(?:screen|desktop)\s+(?:dekho|check|scan|dikhao)',
                r'(?:take|capture)\s+(?:a\s+)?screenshot',
                r'(?:what(?:\'?s)?|kya)\s+(?:is\s+)?(?:on\s+)?(?:my\s+)?(?:screen|desktop)',
            ],
            examples=["look at my screen", "screen dekho", "what's on screen", "take screenshot"]
        ))

        # 14. Download Media
        self.register_intent(IntentDefinition(
            name="download_media",
            description="Download audio, song, or video from YouTube or the internet",
            parameters={
                "query": {"type": "string", "description": "Name of the song, video, or content to download", "required": True}
            },
            tier1_patterns=[
                r'^\s*(?:download)\s+(?:audio|song|music|video)?\s*(.+)',
            ],
            examples=["download audio believer", "download this song", "download video from youtube"]
        ))

    # =========================================================================
    # TIER 1: FAST LOCAL MATCHING
    # =========================================================================

    def _fast_match(self, message: str) -> Optional[IntentResult]:
        """
        Tier 1: Fast regex-based pattern matching.
        Returns IntentResult if a clear match is found, None otherwise.
        """
        message_clean = message.lower().strip()
        # Remove emojis and special chars for matching
        message_clean = re.sub(r'[^\w\s\d\.\-\?\!]', '', message_clean).strip()

        for intent_name, intent_def in self.intents.items():
            for pattern in intent_def.tier1_patterns:
                match = re.search(pattern, message_clean, re.IGNORECASE)
                if match:
                    # Extract parameters from capture groups
                    params = {}
                    groups = match.groups()
                    
                    # Map captured groups to parameter names
                    param_names = [p for p in intent_def.parameters.keys()]
                    for i, group_val in enumerate(groups):
                        if i < len(param_names) and group_val:
                            param_val = group_val.strip()
                            # Clean trailing filler words
                            for filler in ['please', 'karo', 'kar', 'do', 'de', 'karna', 'the', 'a', 'bro', 'bhai', 'yaar']:
                                param_val = re.sub(rf'\s+{filler}\s*$', '', param_val).strip()
                            params[param_names[i]] = param_val
                    
                    # Special handling for boolean params (bluetooth enable)
                    if intent_name == "bluetooth_toggle":
                        raw = (groups[0] if groups else "").lower()
                        params["enable"] = raw in ("on", "chalu", "start")
                    
                    # Special handling for volume action mapping
                    if intent_name == "volume_control":
                        raw = (groups[0] if groups else "").lower()
                        action_map = {
                            "up": "up", "zyada": "up", "badha": "up", "badhao": "up", "badha do": "up",
                            "down": "down", "kam": "down", "kam karo": "down",
                            "mute": "mute", "unmute": "unmute"
                        }
                        params["action"] = action_map.get(raw, raw)

                    logger.debug(f"Tier 1 matched: {intent_name} with params {params}")
                    return IntentResult(
                        intent_name=intent_name,
                        parameters=params,
                        confidence=0.95,
                        tier=1,
                        raw_query=message
                    )

        return None

    # =========================================================================
    # TIER 2: LLM FUNCTION CALLING
    # =========================================================================

    def _build_gemini_tools(self) -> list:
        """Build Gemini function declarations from registered intents."""
        try:
            from google.generativeai.types import FunctionDeclaration, Tool
            
            func_declarations = []
            for intent_name, intent_def in self.intents.items():
                # Build parameter schema
                properties = {}
                required = []
                for param_name, param_info in intent_def.parameters.items():
                    prop = {
                        "type": param_info.get("type", "string").upper(),
                        "description": param_info.get("description", "")
                    }
                    if "enum" in param_info:
                        prop["enum"] = param_info["enum"]
                    properties[param_name] = prop
                    if param_info.get("required", False):
                        required.append(param_name)

                # Build function declaration
                params_schema = None
                if properties:
                    params_schema = {
                        "type": "OBJECT",
                        "properties": properties,
                    }
                    if required:
                        params_schema["required"] = required

                func_declarations.append(
                    FunctionDeclaration(
                        name=intent_name,
                        description=intent_def.description,
                        parameters=params_schema
                    )
                )

            return [Tool(function_declarations=func_declarations)]
        except Exception as e:
            logger.error(f"Failed to build Gemini tools: {e}")
            return []

    def _llm_route(self, message: str) -> Optional[IntentResult]:
        """
        Tier 2: Use LLM function calling to determine intent.
        Returns IntentResult if the LLM calls a function, None if it's just conversation.
        """
        if not self._router_llm:
            return None
        
        try:
            import google.generativeai as genai
            
            tools = self._build_gemini_tools()
            if not tools:
                return None

            # System instruction for the router
            router_instruction = (
                "You are an intent classifier for a voice assistant called Pulsar. "
                "The user speaks in English, Hindi, or Hinglish (a mix of both). "
                "Your ONLY job is to determine if the user's message is a COMMAND that should trigger an action, "
                "or if it's just casual CONVERSATION. "
                "If it IS a command, call the appropriate function with the correct parameters. "
                "If it is NOT a command (greetings, questions, chat, opinions), do NOT call any function — "
                "just respond with the single word 'CONVERSATION'. "
                "Examples of NON-commands: 'hi', 'how are you', 'what is AI', 'tell me a joke', 'don't tell me', "
                "'nahi bro', 'thanks', 'who are you'. "
                "Examples of COMMANDS: 'chrome khol do', 'play believer', 'battery kitni hai', "
                "'kaun se apps chal rahe hain', 'volume kam karo', 'bluetooth on karo'."
            )
            
            # Use a fresh model instance with tools for routing
            router_model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                tools=tools,
                system_instruction=router_instruction,
            )

            start_time = time.time()
            response = router_model.generate_content(
                message,
                generation_config={"temperature": 0.1, "max_output_tokens": 100}
            )
            elapsed = time.time() - start_time
            logger.debug(f"Tier 2 LLM routing took {elapsed:.2f}s")

            # Check if the model called a function
            if response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            fc = part.function_call
                            intent_name = fc.name
                            # Extract parameters
                            params = {}
                            if fc.args:
                                for key, value in fc.args.items():
                                    params[key] = value

                            logger.info(f"Tier 2 matched: {intent_name} with params {params} ({elapsed:.2f}s)")
                            return IntentResult(
                                intent_name=intent_name,
                                parameters=params,
                                confidence=0.85,
                                tier=2,
                                raw_query=message
                            )

            # No function call = conversation
            logger.debug(f"Tier 2: No intent detected (conversation)")
            return None

        except Exception as e:
            logger.warning(f"Tier 2 LLM routing failed: {e}")
            return None

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def route(self, message: str) -> Optional[IntentResult]:
        """
        Route a user message to an intent.
        
        Returns:
            IntentResult if a command intent is detected
            None if the message is pure conversation
        """
        if not message or not message.strip():
            return None

        # Tier 1: Fast local match
        result = self._fast_match(message)
        if result:
            logger.info(f"🎯 Intent routed (Tier 1): {result.intent_name} → {result.parameters}")
            return result

        # Tier 2: LLM function calling
        result = self._llm_route(message)
        if result:
            logger.info(f"🧠 Intent routed (Tier 2): {result.intent_name} → {result.parameters}")
            return result

        # No intent detected — this is conversation
        return None

    def get_status(self) -> Dict[str, Any]:
        """Get router status for debugging."""
        return {
            "total_intents": len(self.intents),
            "intent_names": list(self.intents.keys()),
            "tier2_enabled": self._router_llm is not None,
            "tier2_provider": "gemini" if self._router_llm and self._router_llm != "openai_fallback" else ("openai" if self._router_llm else "none"),
        }
