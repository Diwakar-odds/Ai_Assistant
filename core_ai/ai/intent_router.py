# Setup centralized logging
try:
    from ai_assistant.utils.logging_config import get_logger
    logger = get_logger(__name__, log_category="app")
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

"""
Intelligent Intent Router for Pulsar AI Assistant

Three-tier architecture:
  Tier 1: Fast local pattern matching (~0ms) for obvious & agent commands
  Tier 2: Local ML Semantic matching (SentenceTransformers)
  Tier 3: LLM function calling / structured JSON routing (Gemini + UnifiedChatInterface)
"""

import re
import json
import time
import threading
from typing import Dict, List, Optional, Any, Tuple, NamedTuple
from dataclasses import dataclass, field
from pathlib import Path
import numpy as np

from ai_assistant.core.local_command_normalizer import normalize_hinglish_devanagari
from ai_assistant.ai.shared_embedder import encode_text


# =============================================================================
# CANONICAL AGENT INTENT METADATA (Single Source of Truth)
# =============================================================================

AGENT_INTENT_METADATA: Dict[str, Tuple[str, str]] = {
    "agent_productivity": ("productivity-001", "create_word_document"),
    "agent_research": ("research-001", "research_topic"),
    "agent_deep_research": ("deep-research-001", "deep_research"),
    "agent_writer": ("writer-001", "write_article"),
    "agent_video": ("video-001", "create_video"),
    "agent_creative": ("creative-001", "generate_image"),
    "agent_data": ("data-001", "analyze_data"),
    "agent_database": ("database-001", "query_database"),
    "agent_communication": ("comm-001", "send_email"),
    "agent_web": ("web-001", "browse_web"),
    "agent_student": ("student-001", "learn_topic"),
    "agent_file": ("file-001", "organize_files"),
    "agent_audio": ("audio-001", "transcribe_audio"),
    "agent_autonomous": ("autonomous-001", "behavior_learning"),
}


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
    tier: int  # 1, 2, or 3 (which tier resolved it)
    raw_query: str


# =============================================================================
# INTENT ROUTER
# =============================================================================

_intent_router_instance = None


class IntentRouter:
    """
    Intelligent intent routing using a multi-tier system:

    Tier 1: Fast regex/keyword matching for unambiguous local & agent commands
    Tier 2: Local ML Semantic matching (SentenceTransformers)
    Tier 3: LLM routing (Gemini function calling or active UnifiedChatInterface provider)
    """

    def __new__(cls, *args, **kwargs):
        global _intent_router_instance
        if _intent_router_instance is None:
            _intent_router_instance = super().__new__(cls)
            _intent_router_instance._initialized = False
        return _intent_router_instance

    def __init__(self, llm_provider=None):
        """
        Args:
            llm_provider: UnifiedChatInterface instance for Tier 3 routing.
                          If None, Gemini / active settings provider will be checked lazily.
        """
        if getattr(self, '_initialized', False):
            if llm_provider is not None:
                self.llm_provider = llm_provider
            return

        self.llm_provider = llm_provider
        self.intents: Dict[str, IntentDefinition] = {}

        # Dedicated LLM for routing (separate from conversation history)
        self._router_llm = None
        self._local_classifier = None
        self._tls = threading.local()
        self._init_router_llm()

        # Register all default intents
        self._register_all_intents()
        self._initialized = True

        logger.info(
            f"✅ IntentRouter initialized with {len(self.intents)} intents "
            f"(Tier 3 Gemini {'enabled' if self._router_llm else 'standby'})"
        )

    def _get_active_gemini_config(self) -> Tuple[bool, str, Optional[str]]:
        """Dynamically check active provider/model/key from unified settings_manager and per-request overrides."""
        import os
        import sys
        from pathlib import Path

        tls = getattr(self, '_tls', None)
        if tls is not None:
            if getattr(tls, 'offline_mode', None):
                return False, "gemini-2.5-flash", None
            req_prov = getattr(tls, 'provider_override', None)
            if req_prov and str(req_prov).strip().lower() not in ("gemini", "google"):
                return False, "gemini-2.5-flash", None

        provider = "gemini"
        model_name = "gemini-2.5-flash"
        api_key = None
        try:
            backend_dir = str(Path(__file__).resolve().parents[4] / 'backend')
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            from settings_manager import get_provider, get_model, get_api_key
            provider = (get_provider() or "gemini").lower()
            sm_model = get_model() or model_name
            if "gemini" in sm_model.lower():
                model_name = sm_model
            api_key = get_api_key("gemini")
        except Exception:
            api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY")

        enabled = (provider == "gemini") and bool(api_key)
        return enabled, model_name, api_key

    def _get_active_provider_name(self) -> str:
        tls = getattr(self, '_tls', None)
        if tls is not None:
            if getattr(tls, 'offline_mode', None):
                return "offline"
            req_prov = getattr(tls, 'provider_override', None)
            if req_prov:
                return str(req_prov).strip().lower()
        try:
            import sys
            from pathlib import Path
            backend_dir = str(Path(__file__).resolve().parents[4] / 'backend')
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            from settings_manager import get_provider
            return (get_provider() or "gemini").lower()
        except Exception:
            return "gemini"

    def _init_router_llm(self):
        """Initialize local IntentClassifier state and optional Gemini Tier 3 router."""
        self._router_llm = None
        self._local_classifier = None
        # Lazy-load _local_classifier in _semantic_route to save startup time
        try:
            enabled, model_name, api_key = self._get_active_gemini_config()
            if enabled and api_key:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self._router_llm = genai.GenerativeModel(model_name)
                logger.info(f"✅ IntentRouter Tier 3: Gemini ({model_name}) function calling available")
            else:
                logger.info("ℹ️ IntentRouter Tier 3 Gemini standby (provider fallback available via UnifiedChatInterface)")
        except Exception as e:
            logger.warning(f"⚠️ IntentRouter Gemini init failed: {e}")

    # =========================================================================
    # INTENT REGISTRATION
    # =========================================================================

    def register_intent(self, intent: IntentDefinition):
        """Register an intent definition."""
        self.intents[intent.name] = intent

    def _register_all_intents(self):
        """Register all built-in local, executive, and specialized agent intents in deterministic priority order."""

        # 0. Executive Control Intents (strict standalone anchors so app names like "stop spotify" never collide)
        self.register_intent(IntentDefinition(
            name="executive_stop",
            description="Immediately stop or cancel running task chains or execution",
            parameters={"action": {"type": "string", "description": "Action", "required": True}},
            tier1_patterns=[
                r'^\s*(?:emergency\s+stop|stop\s+(?:all|everything|execution|tasks?|chains?|now)|cancel\s+(?:all|everything|current\s+(?:task|chain)|execution)|abort(?:\s+all)?|halt(?:\s+all)?)\s*$',
                r'^\s*(?:band\s+karo|rok\s*do|rok\s+lo|mat\s+karo|sab\s+band\s+karo|sab\s+roko|रुको|बंद\s+करो|रोक\s+दो|मत\s+करो)\s*$',
                r'^\s*(?P<action>stop|cancel|ruko)\s*$',
            ],
            examples=["stop", "stop all", "emergency stop", "band karo", "rok do"]
        ))

        self.register_intent(IntentDefinition(
            name="executive_pause",
            description="Pause currently running task chain execution",
            parameters={"action": {"type": "string", "description": "Action", "required": True}},
            tier1_patterns=[
                r'^\s*(?:pause\s+(?:all|execution|chain|task|karo)|hold\s+on|ruko\s+zara|ek\s+second|ek\s+minute|thehro|पॉज़\s+करो|ठहरो)\s*$',
                r'^\s*(?P<action>pause)\s*$',
            ],
            examples=["pause", "pause execution", "hold on", "thehro"]
        ))

        self.register_intent(IntentDefinition(
            name="executive_resume",
            description="Resume paused task chain execution",
            parameters={"action": {"type": "string", "description": "Action", "required": True}},
            tier1_patterns=[
                r'^\s*(?:resume(?:\s+(?:all|execution|chain|task|karo))?|continue(?:\s+(?:execution|chain|task))?|carry\s+on|proceed(?:\s+now)?|go\s+ahead|aage\s+badho|jari\s+rakho|जारी\s+रखो|आगे\s+बढ़ो)\s*$',
                r'^\s*(?P<action>resume)\s*$',
            ],
            examples=["resume", "resume execution", "continue", "aage badho"]
        ))

        # 1. Wait / Delay (chain timing step)
        self.register_intent(IntentDefinition(
            name="wait",
            description="Wait or sleep for a given number of seconds inside a workflow",
            parameters={
                "seconds": {"type": "number", "description": "Seconds to wait", "required": True}
            },
            tier1_patterns=[
                r'^\s*(?:wait|sleep|delay|pause\s+for)\s+(?:for\s+)?(?P<seconds>\d+(?:\.\d+)?)\s*(?:seconds?|secs?|s)\b.*',
                r'^\s*(?P<seconds>\d+(?:\.\d+)?)\s*(?:seconds?|secs?|सेकंड)\s+(?:wait|ruko|इंतज़ार)\b.*',
            ],
            examples=["wait 2 seconds", "sleep 5s", "wait for 1.5 seconds"]
        ))

        # 2. Say / Speak / Notify step
        self.register_intent(IntentDefinition(
            name="say",
            description="Speak or output a short notification phrase",
            parameters={
                "text": {"type": "string", "description": "Text to output or speak", "required": True}
            },
            tier1_patterns=[
                r'^\s*(?:say|speak\s+aloud|announce|notify\s+user)\s+(?P<text>.+)$',
            ],
            examples=["say task completed", "announce hello world"]
        ))

        # 3. YouTube History (before open_app & youtube_search)
        self.register_intent(IntentDefinition(
            name="youtube_history",
            description="Open YouTube watch history or view history",
            parameters={},
            tier1_patterns=[
                r'^\s*(?:show\s+|open\s+|view\s+|check\s+)?(?:youtube\s+)?(?:watch\s+)?history\s*$',
                r'^\s*youtube\s+(?:ki\s+)?history\b.*',
            ],
            examples=["show youtube history", "youtube history", "open watch history"]
        ))

        # 4. YouTube Search (before search_web & open_app)
        self.register_intent(IntentDefinition(
            name="youtube_search",
            description="Search videos on YouTube",
            parameters={
                "query": {"type": "string", "description": "The search query on YouTube", "required": True}
            },
            tier1_patterns=[
                r'^\s*(?:youtube\s+search|search\s+(?:on\s+)?youtube)\s+(?:for\s+)?(?P<query>.+)',
                r'^\s*search\s+(?:for\s+)?(?P<query>.+?)\s+on\s+youtube\s*$',
                r'^\s*(?:youtube\s+pe|youtube\s+par)\s+(?:search\s+karo|dhundo)\s+(?P<query>.+)',
                r'^\s*(?P<query>.+?)\s+(?:on\s+youtube|in\s+youtube|youtube\s+pe|youtube\s+par)\s*$',
            ],
            examples=["youtube search lofi hip hop", "search on youtube relax music", "cat videos on youtube"]
        ))

        # 5. Open Settings (before open_app & wifi/bluetooth toggles)
        self.register_intent(IntentDefinition(
            name="open_settings",
            description="Open Windows system settings, Control Panel, or a specific settings page",
            parameters={
                "setting": {"type": "string", "description": "Specific setting or page to open", "required": False}
            },
            tier1_patterns=[
                r'^\s*(?:open|show|launch|khol|kholo)\s+(?:the\s+|windows\s+)?(?P<setting>wifi|wi-fi|wi\s+fi|bluetooth|display|screen|network|sound|audio|hotspot|mobile\s+hotspot|airplane(?:\s+mode)?|flight\s+mode|night\s+light|battery|power|personalization|theme|privacy|security|windows\s+update|update|storage)\s+(?:ki\s+)?settings(?:\s+page)?\b.*',
                r'^\s*(?P<setting>wifi|wi-fi|wi\s+fi|bluetooth|display|screen|network|sound|audio|hotspot|mobile\s+hotspot|airplane(?:\s+mode)?|flight\s+mode|night\s+light|battery|power|personalization|theme|privacy|security|windows\s+update|update|storage)\s+(?:ki\s+)?settings(?:\s+page)?\s+(?:khol\s+do|khol\s+de|kholo|khol|open\s+karo|open|dikhao)\b.*',
                r'^\s*(?:open|show|launch|khol|kholo)\s+(?:the\s+|windows\s+)?(?P<setting>control\s+panel)\b.*',
                r'^\s*(?P<setting>control\s+panel)\s+(?:khol\s+do|khol\s+de|kholo|khol|open\s+karo|open|dikhao)\b.*',
                r'^\s*(?:open|show|launch|khol|kholo)\s+(?:the\s+)?(?:windows\s+)?settings(?:\s+app|\s+page)?\s*$',
                r'^\s*(?:windows\s+)?settings(?:\s+app|\s+page)?\s+(?:khol\s+do|khol\s+de|kholo|khol|open\s+karo|open)\s*$',
            ],
            examples=["open settings", "wifi settings khol do", "show display settings", "open control panel"]
        ))

        # 6. Volume Control
        self.register_intent(IntentDefinition(
            name="volume_control",
            description="Control or check the system volume (up, down, mute, unmute, set, status)",
            parameters={
                "action": {"type": "string", "description": "Volume action", "enum": ["up", "down", "mute", "unmute", "set", "status"], "required": True},
                "level": {"type": "integer", "description": "Volume level 0-100 (when action is 'set')", "required": False}
            },
            tier1_patterns=[
                r'(?:set\s+)?(?:the\s+)?(?:system\s+)?(?:volume|sound|awaaz|awaz|audio|आवाज़|आवाज|वॉल्यूम)\s+(?:(?:ko|to|at|on|set\s+(?:to)?)\s+)*(\d{1,3})\b',
                r'\b(full|max|maximum|min|minimum)\s+(?:the\s+)?(?:volume|sound|awaaz|awaz|audio|आवाज़|आवाज|वॉल्यूम)\b',
                r'(?:volume|sound|awaaz|awaz|audio|आवाज़|आवाज|वॉल्यूम)\s+(?:(?:ko|to)\s+)?(full|max|maximum|min|minimum)\b',
                r'\b(?:what\s+is\s+(?:the\s+)?|check\s+|get\s+|current\s+|show\s+)(?:system\s+)?(?:volume|sound\s+level)\b',
                r'^\s*(?:volume|sound|awaaz|awaz|आवाज़|आवाज|वॉल्यूम)\s+(?:kitna|kitni|kya|status|कितना|कितनी|क्या)\b.*',
                r'\b(increase|decrease|raise|lower|turn\s+up|turn\s+down|mute|unmute|badhao|badha|tez|kam|dhima|बढ़ाओ|बढ़ा|तेज़|तेज|कम|धीमा|धीमी|म्यूट|बंद)\s+(?:the\s+)?(?:system\s+)?(?:volume|sound|awaaz|awaz|audio|आवाज़|आवाज|वॉल्यूम)\b',
                r'\b(?:turn|raise|lower)\s+(?:the\s+)?(?:volume|sound|awaaz|awaz|audio|आवाज़|आवाज|वॉल्यूम)\s+(up|down|high|low)\b',
                r'\b(?:volume|sound|awaaz|awaz|audio|आवाज़|आवाज|वॉल्यूम)\s+(?:ko\s+)?(up|down|mute|unmute|band|kam|zyada|jyada|badha|badhao|tez|dhima|dhimi|increase|decrease|high|low|off|on|बढ़ाओ|बढ़ा|कम|धीमा|धीमी|तेज़|तेज|म्यूट|बंद|ज्यादा)\b',
                r'^\s*(unmute|mute|म्यूट|अनम्यूट)\b(?!\s+(?:voice|tts|mic\b|microphone))(?:\s+(?:the\s+)?(?:system\s+)?(?:volume|sound|awaaz|awaz|audio|आवाज़|आवाज|वॉल्यूम))?(?:\s+(?:karo|kardo|kar\s+do|kar|do|de|please|plz|करो|कर\s+दो|कर\s+दे))?\s*$',
            ],
            examples=["volume up", "volume mute कर दो", "unmute", "increase volume", "awaaz kam karo", "volume set 50", "आवाज़ बढ़ाओ", "वॉल्यूम कम करो"]
        ))

        # 7. Bluetooth Toggle
        self.register_intent(IntentDefinition(
            name="bluetooth_toggle",
            description="Turn bluetooth on or off",
            parameters={
                "enable": {"type": "boolean", "description": "True to turn on, False to turn off", "required": True}
            },
            tier1_patterns=[
                r'\b(?:bluetooth|ब्लूटूथ|ब्लूटुथ)\s+(?:ko\s+)?(on|off|chalu|chalao|band|start|stop|enable|disable|activate|deactivate|चालू|बंद|ऑन|ऑफ|ऑफ़)\b',
                r'\b(on|off|chalu|chalao|band|start|stop|enable|disable|activate|deactivate|चालू|बंद|ऑन|ऑफ|ऑफ़)\s+(?:the\s+)?(?:bluetooth|ब्लूटूथ|ब्लूटुथ)\b',
                r'\b(?:turn|switch)\s+(on|off|chalu|band|of|चालू|बंद)\s+(?:the\s+)?(?:bluetooth|ब्लूटूथ|ब्लूटुथ)\b',
            ],
            examples=["bluetooth on karo", "turn off bluetooth", "bluetooth chalu karo", "ब्लूटूथ चालू करो", "ब्लूटूथ बंद करो"]
        ))

        # 8. WiFi Toggle
        self.register_intent(IntentDefinition(
            name="wifi_toggle",
            description="Turn wifi on or off",
            parameters={
                "enable": {"type": "boolean", "description": "True to turn on, False to turn off", "required": True}
            },
            tier1_patterns=[
                r'\b(?:wifi|wi-fi|wi\s+fi|वाईफाई|वाई-फाई|वाइफाई|वाइ\s*फाई)\s+(?:ko\s+)?(on|off|chalu|chalao|band|start|stop|enable|disable|activate|deactivate|चालू|बंद|ऑन|ऑफ|ऑफ़)\b',
                r'\b(on|off|chalu|chalao|band|start|stop|enable|disable|activate|deactivate|चालू|बंद|ऑन|ऑफ|ऑफ़)\s+(?:the\s+)?(?:wifi|wi-fi|wi\s+fi|वाईफाई|वाई-फाई|वाइफाई|वाइ\s*फाई)\b',
                r'\b(?:turn|switch)\s+(on|off|chalu|band|of|चालू|बंद)\s+(?:the\s+)?(?:wifi|wi-fi|wi\s+fi|वाईफाई|वाई-फाई|वाइफाई|वाइ\s*फाई)\b',
            ],
            examples=["wifi on karo", "Wi-Fi on कर दो", "turn off wifi", "wifi band karo", "वाईफाई चालू करो", "वाईफाई बंद करो"]
        ))

        # 9. Screen Brightness Control
        self.register_intent(IntentDefinition(
            name="set_brightness",
            description="Check or adjust screen brightness (set 0-100, up, down, status)",
            parameters={
                "action": {"type": "string", "description": "Brightness action", "enum": ["set", "up", "down", "status"], "required": True},
                "level": {"type": "integer", "description": "Brightness percentage 0-100 (when action is 'set')", "required": False}
            },
            tier1_patterns=[
                r'\b(?:what\s+is\s+(?:the\s+)?|check\s+|get\s+|current\s+)brightness\b',
                r'\bbrightness\s+(?:kitni|kitna|kya|status)\b.*',
                r'(?:set\s+)?(?:the\s+)?(?:screen\s+)?brightness\s+(?:(?:ko|to|at|on|set\s+(?:to)?)\s+)*(\d{1,3})\b',
                r'\bbrightness\s+(?:(?:ko|to)\s+)?(full|max|maximum|min|minimum)\b',
                r'\b(increase|decrease|raise|lower|turn\s+up|turn\s+down|dim|badhao|badha|tez|kam)\s+(?:the\s+)?(?:screen\s+)?brightness\b',
                r'\bbrightness\s+(?:ko\s+)?(up|down|high|low|kam|zyada|jyada|badha|badhao|tez|dhima|dhimi|increase|decrease)\b',
            ],
            examples=["brightness बढ़ा दो", "brightness kam karo", "set brightness to 70", "check brightness"]
        ))

        # 10. Dark / Light Mode Toggle
        self.register_intent(IntentDefinition(
            name="dark_mode_toggle",
            description="Enable or disable Windows Dark Mode / Light Mode",
            parameters={
                "enable": {"type": "boolean", "description": "True to enable Dark Mode, False for Light Mode", "required": True}
            },
            tier1_patterns=[
                r'\b(dark|light)\s+(?:mode|theme)\b',
            ],
            examples=["dark mode on karo", "turn off dark mode", "light mode on karo"]
        ))

        # 11. Battery Status
        self.register_intent(IntentDefinition(
            name="battery_status",
            description="Check the battery level, charging status, or power information",
            parameters={},
            tier1_patterns=[
                r'\b(?:battery|betri|charging|charge\s+kitna|charge\s+kitni|battery\s+charge)\b',
            ],
            examples=["battery kitni hai", "check battery", "charge kitna hai"]
        ))

        # 12. List Running Apps & Taskbar Check (before open_app)
        self.register_intent(IntentDefinition(
            name="list_running_apps",
            description="List all currently running applications, open programs, or active windows",
            parameters={},
            tier1_patterns=[
                r'\b(?:running\s+apps?|open\s+apps(?:\s|$)|active\s+apps?|chal\s+rahe|khule\s+hain|kaun\s+se\s+apps?)\b',
                r'\b(?:which|what|kaun|kitne|tell\s+me\s+which)\s+(?:apps?|programs?|windows?)\s+(?:are\s+)?(?:currently\s+)?(?:running|open|active|chal|khule)\b',
                r'\b(?:apps?|programs?|windows?)\s+(?:are\s+)?(?:currently\s+)?(?:running|open|active|chal\s+rahe|khule\s+hain)\b',
            ],
            examples=["which apps are running", "kaun se apps chal rahe hain", "running apps dikhao"]
        ))

        self.register_intent(IntentDefinition(
            name="check_taskbar",
            description="Check if a specific app is running on the taskbar or inspect open desktop windows",
            parameters={
                "app_name": {"type": "string", "description": "Optional app name to check", "required": False}
            },
            tier1_patterns=[
                r'^\s*check\s+(?:the\s+)?taskbar(?:\s+for\s+(?P<app_name>.+))?\s*$',
                r'^\s*is\s+(?P<app_name>[a-zA-Z0-9_\s-]+?)\s+(?:running|open)(?:\s+on\s+taskbar)?\s*\??\s*$',
            ],
            examples=["check taskbar", "is notepad running"]
        ))

        # 13. System Control
        self.register_intent(IntentDefinition(
            name="system_control",
            description="System power commands: shutdown, restart, sleep, or lock the computer",
            parameters={
                "action": {"type": "string", "description": "System action", "enum": ["shutdown", "restart", "sleep", "lock"], "required": True}
            },
            tier1_patterns=[
                r'^\s*(shutdown|restart|sleep|lock)\s*(?:the\s+)?(?:computer|system|pc|laptop|screen)?\s*$',
                r'^\s*(?:computer|system|pc|laptop|screen)\s+(shutdown|restart|sleep|lock)(?:\s+karo|\s+kar\s+do)?\s*$',
                r'^\s*(lock|shutdown|restart|sleep)\s+(?:karo|kar\s+do|kar|do)\s*$',
            ],
            examples=["shutdown", "restart the computer", "lock karo", "system sleep"]
        ))

        # 14. Create Document (Word / PPT / PDF)
        self.register_intent(IntentDefinition(
            name="create_document",
            description="Create a new document, presentation, or file (Word, PPT, PDF)",
            parameters={
                "doc_type": {"type": "string", "description": "Type of document", "enum": ["document", "presentation", "pdf", "word", "ppt", "powerpoint", "docx", "pptx"], "required": True},
                "title": {"type": "string", "description": "Title or topic for the document", "required": False},
                "content": {"type": "string", "description": "Optional document body or output placeholder", "required": False},
                "output_path": {"type": "string", "description": "Optional destination path", "required": False},
            },
            tier1_patterns=[
                r'^\s*(?:create|make|generate|save|write|banao|bana)\s+(?:a\s+|this\s+|that\s+)?(?:new\s+)?(?P<doc_type>ppt|pptx|powerpoint|presentation|pdf|document|docx?|word(?:\s+doc(?:ument)?)?)(?:\s+(?:file|deck|report))?(?:\s+(?:on|about|titled|named|for|of|with)\s+(?P<title>.+))?$',
                r'^\s*(?:save|export)\s+(?:it|this|that|the\s+summary|\{.+?\})\s+(?:as|to|into)\s+(?:a\s+)?(?P<doc_type>ppt|pptx|presentation|pdf|word|doc|docx|document)(?:\s+(?:file|named|at|called)\s+(?P<title>.+))?$',
            ],
            examples=["create a ppt", "make presentation on AI", "create a word document on robotics", "save it to a word document"]
        ))

        # 15. File Operations (Create Folder, Find File, Open Folder, Move File, Send File)
        self.register_intent(IntentDefinition(
            name="create_folder",
            description="Create a new folder or directory on the filesystem",
            parameters={
                "name": {"type": "string", "description": "Name of the folder to create", "required": True},
                "path": {"type": "string", "description": "Parent path where to create the folder", "required": False}
            },
            tier1_patterns=[
                r'(?:create|make|banao|bana)\s+(?:a\s+)?(?:new\s+)?(?:folder|directory)\s+(?:named?\s+|called\s+)?(?P<name>[^\s]+)(?:\s+(?:in|at|on|under)\s+(?P<path>.+))?$',
                r'(?:create|make|banao|bana)\s+(?:a\s+)?(?:new\s+)?(?:folder|directory)\s+(?:named?\s+)?(?P<name>.+)',
            ],
            examples=["create folder test", "make a new folder named projects", "folder banao homework"]
        ))

        self.register_intent(IntentDefinition(
            name="find_file",
            description="Find or locate a file by name on the local system",
            parameters={
                "file_name": {"type": "string", "description": "Name or pattern of file to find", "required": True},
                "location": {"type": "string", "description": "Optional directory to search in", "required": False}
            },
            tier1_patterns=[
                r'^\s*(?:find|locate|search\s+for)\s+(?:the\s+)?file\s+(?P<file_name>.+?)(?:\s+(?:in|inside|under)\s+(?P<location>.+))?\s*$',
                r'^\s*(?:find|locate)\s+(?P<file_name>[^\s]+\.[a-zA-Z0-9]{1,5})(?:\s+(?:in|inside|under)\s+(?P<location>.+))?\s*$',
            ],
            examples=["find file report.pdf", "locate resume.docx", "search for file notes.txt in Documents"]
        ))

        self.register_intent(IntentDefinition(
            name="open_folder",
            description="Open a local folder or directory in File Explorer",
            parameters={
                "folder": {"type": "string", "description": "Folder name or path", "required": True},
            },
            tier1_patterns=[
                r'^\s*(?:open|show|browse)\s+(?:the\s+)?(?P<folder>downloads|documents|desktop|pictures|music|videos)\s+(?:folder|directory)\s*$',
                r'^\s*(?:open|show|browse)\s+(?:the\s+)?(?:folder|directory)\s+(?P<folder>.+)\s*$',
                r'^\s*(?:locate\s+to|locate|navigate\s+to|go\s+to)\s+(?:the\s+)?(?P<folder>.+?)\s*(?:folder|directory)?\s*$',
                r'^\s*(?P<folder>.+?)\s+(?:naam\s+ka\s+folder\s+dhundo|folder\s+dhundo|folder\s+locate\s+karo|folder\s+kholo|folder\s+open\s+karo)\s*$',
                r'^\s*(?:open|kholo|show|browse)\s+(?P<folder>(?:[a-zA-Z]:|\/|\\\\|disk\s+[a-zA-Z]|drive\s+[a-zA-Z]).*)\s*$',
                r'^\s*(?:find|locate|search\s+for|dhundo)\s+(?:the\s+)?(?:folder|directory)\s+(?P<folder>.+)\s*$',
            ],
            examples=["open downloads folder", "open folder D:/Projects", "locate to resume folder in disk d", "resume naam ka folder dhundo"]
        ))

        self.register_intent(IntentDefinition(
            name="setup_project",
            description="Setup, prepare or open a project workspace in Antigravity or VS Code",
            parameters={
                "project_name": {"type": "string", "description": "Project name or folder to open", "required": True},
                "ide": {"type": "string", "description": "Optional IDE choice (antigravity, vscode, both)", "required": False},
            },
            tier1_patterns=[
                r'^\s*(?:open|setup|load|start)\s+(?:the\s+)?project\s+(?P<project_name>[a-zA-Z0-9_\s-]+?)(?:\s+(?:in|with|on)\s+(?P<ide>vscode|vs\s*code|antigravity|both|dono))?\s*$',
                r'^\s*(?P<project_name>[a-zA-Z0-9_\s-]+?)\s+(?:pe|par|pr)\s+kaam\s+(?:karna|krna)\s+(?:hai|h)(?:\s+(?:aaj|abhi))?\s*$',
                r'^\s*aaj\s+(?P<project_name>[a-zA-Z0-9_\s-]+?)\s+(?:pe|par|pr)\s+kaam\s+(?:karna|krna)\s+(?:hai|h)\s*$',
                r'^\s*(?:setup|kholo|khol\s*do)\s+(?:project\s+)?(?P<project_name>[a-zA-Z0-9_\s-]+?)(?:\s+ko)?(?:\s+(?:in|me|mein)\s+(?P<ide>vscode|vs\s*code|antigravity|dono))?\s*$',
                r'^\s*(?P<ide>antigravity|vscode|vs\s*code)\s+(?:me|mein)\s+(?P<project_name>[a-zA-Z0-9_\s-]+?)\s+(?:kholo|setup\s*karo|khol\s*do|setup\s*krdo)\s*$',
                r'^\s*(?:project|workspace)\s+(?P<project_name>[a-zA-Z0-9_\s-]+?)\s+(?:setup|start|open)\s+(?:karo|krdo)\s*$',
                r'^\s*(?P<ide>antigravity|vscode|vs\s*code|both|dono)\s*(?:me|mein|kholo|open|khol\s*do)?\s*$',
            ],
            examples=["ai assitant pr kaam krna hai", "aaj antimatter pr kaam krna hai", "antigravity me chatflow kholo", "open project Ai_Assistant in vscode"]
        ))

        self.register_intent(IntentDefinition(
            name="meeting_recorder",
            description="Start or stop silent background meeting recording and generate MoM in Hindi",
            parameters={
                "action": {"type": "string", "description": "start or stop", "required": True},
            },
            tier1_patterns=[
                r'^\s*(?:start|record|listen\s+to|silent)\s+meeting(?:\s+suno|\s+shuru\s+karo|\s+start\s+karo|\s+record\s+karo)?\s*$',
                r'^\s*(?:silent\s+)?meeting\s+(?:suno|start\s+karo|shuru\s+karo|record\s+karo|shuru|note\s+karo|सुनो|शुरू\s+करो)\s*$',
                r'^\s*(?:meri\s+)?meeting\s+hai(?:\s+silent\s+raho|\s+suno|\s+sunna)?\s*$',
                r'^\s*(?:stop|end|finish)\s+meeting\s*$',
                r'^\s*meeting\s+(?:khatam|khatam\s+ho\s+gayi|stop|band|roko|end|over|खत्म|खत्म\s+हो\s+गई|रोको|बंद\s+करो)(?:\s+(?:karo|kar\s+do|ho\s+gayi))?\s*$',
                r'^\s*(?:meeting\s+ka\s+)?mom\s+(?:do|banao|dikhau|de\s+do|bana\s+do|generate\s+karo)\s*$',
            ],
            examples=["meeting suno", "silent meeting shuru karo", "meeting khatam ho gayi", "meeting ka mom do"]
        ))

        self.register_intent(IntentDefinition(
            name="read_email",
            description="Read and summarize unread emails or open Gmail",
            parameters={
                "unread_only": {"type": "boolean", "description": "Read unread only", "required": False},
            },
            tier1_patterns=[
                r'^\s*(?:read|check|summarize|get)\s+(?:my\s+)?(?:gmail|emails?|mails?|inbox)\s*$',
                r'^\s*(?:gmail|email|mail|inbox)\s+(?:padho|padh\s+ke\s+batao|padh\s+kar\s+batao|check\s+karo|batao|kholo|पढ़ो|बताओ)\s*$',
                r'^\s*(?:kiska|koi)\s+(?:mail|email)\s+(?:aaya\s+hai|aaya)\s*$',
            ],
            examples=["gmail padh kar bata de", "check my emails", "koi mail aaya hai"]
        ))

        self.register_intent(IntentDefinition(
            name="move_file",
            description="Move a file from source path to destination folder/path",
            parameters={
                "source": {"type": "string", "description": "Source file path or name", "required": True},
                "destination": {"type": "string", "description": "Destination folder or path", "required": True},
            },
            tier1_patterns=[
                r'^\s*move\s+(?:the\s+)?(?:file\s+)?(?P<source>.+?)\s+(?:to|into)\s+(?P<destination>.+)\s*$',
            ],
            examples=["move report.pdf to Archive", "move it to Documents"]
        ))

        self.register_intent(IntentDefinition(
            name="send_file",
            description="Send a file attachment to a contact via messaging app",
            parameters={
                "file": {"type": "string", "description": "File path or name to send", "required": True},
                "contact": {"type": "string", "description": "Recipient contact name", "required": True},
                "app": {"type": "string", "description": "App to send via (whatsapp, email, etc.)", "required": False},
            },
            tier1_patterns=[
                r'^\s*send\s+(?:the\s+)?file\s+(?P<file>.+?)\s+to\s+(?P<contact>[^\s]+(?:\s+[^\s]+)?)(?:\s+(?:on|via)\s+(?P<app>\w+))?\s*$',
                r'^\s*send\s+(?P<file>\{prev\.[^}]+\}|[^\s]+\.[a-zA-Z0-9]{1,5})\s+to\s+(?P<contact>[^\s]+)(?:\s+(?:on|via)\s+(?P<app>\w+))?\s*$',
            ],
            examples=["send file report.pdf to Rahul on whatsapp", "send resume.docx to John"]
        ))

        # 16. Analyze Screen
        self.register_intent(IntentDefinition(
            name="analyze_screen",
            description="Look at the screen, take a screenshot, or analyze what is visible on the desktop",
            parameters={
                "question": {"type": "string", "description": "Specific question about what's on screen", "required": False}
            },
            tier1_patterns=[
                r'(?:look\s+at|see|scan|check|analyze|analyse)\s+(?:my\s+)?(?:screen|desktop|display|this)',
                r'(?:screen|desktop|स्क्रीन)\s+(?:dekho|check|scan|dikhao|देखो|दिखाओ|चेक\s+करो|स्कैन\s+करो|पढ़ो)',
                r'(?:take|capture)\s+(?:a\s+)?screenshot',
                r'^\s*(?:screenshot|स्क्रीनशॉट)\s*(?:lo|le\s+lo|kheencho|kheecho|karo|lena|लो|ले\s*लो|खींचो|करो)?\s*$',
                r'(?:what(?:\'?s)?|kya|क्या)\s+(?:is\s+)?(?:on\s+)?(?:my\s+)?(?:screen|desktop|स्क्रीन)(?:\s+(?:पर|में)\s+क्या\s+है)?',
                r'^\s*(?:स्क्रीन\s*(?:पर|में)?\s*(?:क्या\s*है|क्या\s*चल\s*रहा\s*है))\s*$',
            ],
            examples=["look at my screen", "screen dekho", "what's on screen", "take screenshot", "स्क्रीन देखो", "स्क्रीनशॉट लो"]
        ))

        # 17. Download Media
        self.register_intent(IntentDefinition(
            name="download_media",
            description="Download audio, song, or video from YouTube or the internet",
            parameters={
                "query": {"type": "string", "description": "Name or URL of song/video to download", "required": True}
            },
            tier1_patterns=[
                r'^\s*(?:download)\s+(?:audio|song|music|video)?\s*(?P<query>.+)',
            ],
            examples=["download audio believer", "download this song", "download video from youtube"]
        ))

        # 18. Send Message (guarded so "whatsapp kholo" never matches and multi-step "X aur Y" splits cleanly)
        self.register_intent(IntentDefinition(
            name="send_message",
            description="Send a message to a contact via WhatsApp, SMS, or messaging platform",
            parameters={
                "contact": {"type": "string", "description": "Name of the contact to send message to", "required": True},
                "message": {"type": "string", "description": "Content of the message to send", "required": True}
            },
            tier1_patterns=[
                r'^\s*(?:send\s+(?:a\s+)?message\s+to\s+(?P<contact>[^\s:,]+(?:\s+[^\s:,]+)?)\s+(?:saying|that|:)\s*(?P<message>.+))$',
                r'^\s*(?:msg|message)\s+(?P<contact>[^\s:,]+)\s+(?:saying|that|:)\s*(?P<message>.+)$',
                r'^\s*(?:send\s+(?:a\s+)?message\s+|msg\s+|text\s+|send\s+)(?P<message>.+?)\s+to\s+(?P<contact>[^\s:,]+(?:\s+[^\s:,]+)?)(?:\s+(?:on|via)\s+whatsapp)?\s*$',
                r'^\s*(?:send\s+(?:a\s+)?message\s+to|text\s+to|whatsapp\s+to)\s+(?P<contact>[^\s:,]+(?:\s+[^\s:,]+)?)(?:\s+on\s+whatsapp|\s+via\s+whatsapp)?(?:\s+(?:saying|that|with|:)\s*(?P<message>.*))?$',
                r'^\s*(?:text|whatsapp)\s+(?!kholo\b|khol\b|kholna\b|open\b|band\b|close\b|quit\b|exit\b|launch\b|start\b|chalu\b)(?P<contact>[^\s:,]+(?:\s+[^\s:,]+)?)(?:\s+on\s+whatsapp|\s+via\s+whatsapp)?\s+(?:saying|that|with|:)\s*(?P<message>.*)$',
                r'^\s*(?:(?:whatsapp|whtsp|whtsap)\s+(?:pe|par|pr|me|mein)\s+)?(?P<contact>[^\s:,]+(?:\s+[^\s:,]+)?)\s+ko\s+(?P<message>.+?)\s+(?:likh\s+(?:ke|kar|kr)\s+)?(?:bhejo|bhej\s+do|send\s+karo|send\s+kar\s+do)(?:\s+(?:whatsapp|whtsp|whtsap)\s+(?:pe|par|pr|me|mein))?\s*$',
                r'^\s*(?:(?:whatsapp|whtsp|whtsap)\s+(?:pe|par|pr|me|mein)\s+)?(?P<contact>[^\s:,]+(?:\s+[^\s:,]+)?)\s+ko\s+(?:message|msg|text)\s*(?:bhejo|karo|kar\s+do|भेजो|करो)?(?:\s+(?:ki|कि|saying|that|:)\s*(?P<message>.*))?$',
                r'^\s*(?P<contact>[^\s:,]+)\s+ko\s+(?:bol\s+do|bat\s+karo|बोल\s+दो)\s*(?:ki|कि|that)?\s*(?P<message>.*)$',
                r'^\s*(?P<contact>[^\s:,]+)\s+message\s+karo\s+(?:saying|ki|:)\s*(?P<message>.+)$',
                r'^\s*(?P<message>.+?)\s+(?:likh\s+(?:ke|kar|kr)\s+)?(?:bhejo|bhej\s+do|send\s+karo|send\s+kar\s+do)(?:\s+(?:whatsapp|whtsp|whtsap)\s+(?:pe|par|pr|me|mein))?\s*$',
            ],
            examples=["send message to John saying hello", "msg Jane: how are you", "John ko message karo ki namaste", "मॉम को message करो"]
        ))

        # 19. Media Time Skip & Video Play
        self.register_intent(IntentDefinition(
            name="skip_time",
            description="Skip or fast-forward a given number of minutes in media playback",
            parameters={
                "minutes": {"type": "integer", "description": "Minutes to skip", "required": True}
            },
            tier1_patterns=[
                r'^\s*(?P<minutes>\d+)\s+(?:minutes?|mins?|मिनट)\s+(?:skip|forward|आगे\s+बढ़ाओ)\b.*',
                r'^\s*(?:skip|forward|आगे\s+बढ़ाओ)\s+(?P<minutes>\d+)\s+(?:minutes?|mins?|मिनट)\b.*',
            ],
            examples=["20 minutes skip karo", "skip 5 mins"]
        ))

        self.register_intent(IntentDefinition(
            name="play_video",
            description="Play or resume a video",
            parameters={
                "query": {"type": "string", "description": "Optional video title/query", "required": False}
            },
            tier1_patterns=[
                r'^\s*(?:play|चलाओ|chalao)\s+(?:the\s+)?video(?:\s+(?P<query>.+))?\s*$',
                r'^\s*video\s+(?:play|चलाओ|chalao)(?:\s+(?P<query>.+))?\s*$',
            ],
            examples=["play video", "video play करो", "play video python tutorial"]
        ))

        # 19b. Media Control (playback navigation: next/prev/pause/resume/play_pause)
        self.register_intent(IntentDefinition(
            name="media_control",
            description="Control media playback: next track, previous track, pause song, resume music",
            parameters={
                "action": {"type": "string", "description": "Action (next, previous, pause, resume, play_pause)", "required": True}
            },
            tier1_patterns=[
                # Next track patterns
                r'^\s*(?:play\s+)?(?P<action>next)(?:\s+(?:song|track|music|audio|item))?\s*$',
                r'^\s*(?:skip|forward)(?:\s+(?:this|the)?\s*(?:song|track|music|audio))?\s*$',
                r'^\s*(?:अगला\s+गाना|agla\s+gaana|अगला\s+ट्रैक|नेक्स्ट\s+(?:सॉन्ग|सांग|गाना|ट्रैक))\s*$',
                r'^\s*(?:gaana|gana|गाना|music|song)\s+(?P<action>बदलो|badlo|skip\s*karo|next\s*karo|skip|next)\s*$',

                # Previous track patterns
                r'^\s*(?:play\s+)?(?P<action>previous|prev)(?:\s+(?:song|track|music|audio|item))?\s*$',
                r'^\s*(?:last\s+song|last\s+track|पिछला\s+गाना|pichla\s+gaana|pichhla\s+gaana|पिछला\s+ट्रैक)\s*$',
                r'^\s*(?:gaana|gana|गाना|music|song)\s+(?P<action>pichhe\s*karo|previous\s*karo|previous|prev)\s*$',

                # Pause patterns
                r'^\s*(?P<action>pause)\s+(?:the\s+)?(?:song|music|playback|audio|video|track|media)\s*$',
                r'^\s*(?:pause\s+the\s+song|pause\s+song|pause\s+music|pause\s+video|pause\s+playback|pause\s+audio)\s*$',
                r'^\s*(?P<action>stop)\s+(?:the\s+)?(?:music|song|playback|audio)\s*$',
                r'^\s*(?:gaana|gana|गाना|music|song)\s+(?P<action>pause|rok\s*do|roko|band\s*karo)(?:\s+karo|\s+kar\s+do)?\s*$',
                r'^\s*(?:म्यूजिक|गाना)\s+(?:रोक\s*दो|बंद\s*करो|पॉज़\s*करो|पॉज\s*करो)\s*$',

                # Resume patterns
                r'^\s*(?P<action>resume)\s+(?:the\s+)?(?:song|music|playback|audio|video|track|media)\s*$',
                r'^\s*(?:resume\s+the\s+song|resume\s+song|resume\s+music|resume\s+playback)\s*$',
                r'^\s*(?:gaana|gana|गाना|music|song)\s+(?P<action>resume|chalao|chalu\s*karo)(?:\s+karo|\s+kar\s+do)?\s*$',
                r'^\s*(?:म्यूजिक|गाना)\s+(?:चालू\s*करो|चलाओ|शुरू\s*करो)\s*$',

                # Play/Pause toggle
                r'^\s*(?:play\s+song|play\s+music)\s*$',
                r'^\s*(?:toggle\s+(?:playback|media|music|song)|play\s+pause)\s*$',
            ],
            examples=["play next song", "next song", "previous song", "pause song", "resume music", "अगला गाना", "पिछला गाना", "pause the song"]
        ))

        # 20. Play Media (music / audio)
        self.register_intent(IntentDefinition(
            name="play_media",
            description="Play music, a song, or media content",
            parameters={
                "query": {"type": "string", "description": "Name of song, artist, or media to play", "required": True},
                "platform": {"type": "string", "description": "Platform to play on (youtube, spotify, etc.)", "required": False}
            },
            tier1_patterns=[
                # Verb prefix: play saiyaara, bajao kesariya, chalao believer, चलाओ सैयारा
                r'^\s*(?:play|baja|bajao|bjao|bjado|bja\s+do|baja\s+do|laga|lagao|lagado|laga\s+do|sun|suno|chalao|chalado|chala\s+do|चलाओ|चला\s+दो|बजाओ|बजा\s+दो|लगाओ|लगा\s+दो|सुनाओ|प्ले\s+करो|प्ले\s+कर\s+दो)\s+(?:(?:a\s+)?(?:song|track|music|gaana|gana|गाना|सॉन्ग|सांग|गीत)\s+)?(?P<query>.+)',
                # Compound verb prefix: gaana chalao saiyaara, gana bajao believer
                r'^\s*(?:play\s+(?:a\s+)?(?:song|track|music)|gaana\s+(?:chalao|bajao|lagao)|gana\s+(?:chalao|bajao|lagao)|गाना\s+(?:चलाओ|बजाओ|लगाओ|सुनाओ)|song\s+(?:baja|bajao|bjao|chalao)|म्यूजिक\s+(?:चलाओ|बजाओ))\s+(?P<query>.+)',
                # Query prefix: saiyaara gaana chalao, saiyaara chala do, सैयारा गाना चलाओ, सैयारा चलाओ, सैयारा बजा दो
                r'^\s*(?P<query>.+?)\s+(?:(?:ka\s+)?(?:gaana|gana|गाना|song|track|music|गीत|सॉन्ग|सांग)\s+)?(?:play\s*(?:karo|krdo|kro|kar\s*do)?|chalao|chalado|chala\s+do|bajao|bjado|bjao|bja\s+do|lagao|lagado|laga\s+do|suno|sunao|चलाओ|चला\s+दो|बजाओ|बजा\s+दो|लगाओ|लगा\s+दो|सुनाओ|प्ले\s+करो|प्ले\s+कर\s+दो)\s*$',
                # Platform specific: play believer on spotify
                r'^\s*play\s+(?P<query>.+?)\s+on\s+(?P<platform>spotify|youtube(?:\s+music)?|yt\s+music)\s*$',
            ],
            examples=["play believer", "baja do arijit singh", "play music on spotify", "gaana laga do", "behja song bjao", "सैयारा गाना चलाओ", "सैयारा चलाओ"]
        ))

        # 21. Type Text (before writer agent so literal "type hello" works without swallowing "write an essay")
        self.register_intent(IntentDefinition(
            name="type_text",
            description="Type literal text into the active window or specified application",
            parameters={
                "text": {"type": "string", "description": "Literal text to type", "required": True},
                "app_name": {"type": "string", "description": "Optional target app", "required": False},
            },
            tier1_patterns=[
                r'^\s*(?:type|likho|लिखो)\s+(?P<text>.+?)(?:\s+in\s+(?P<app_name>notepad|word|vscode|chrome|editor))?\s*$',
                r'^\s*(?P<text>.+?)\s+(?:type\s+karo|likho|लिखो)\s*$',
                r'^\s*write\s+(?!an?\s+(?:essay|article|blog|story|poem|report|email|summary)\b)(?:the\s+text\s+)?["\'](?P<text>.+?)["\'](?:\s+in\s+(?P<app_name>\w+))?\s*$',
                r'^\s*write\s+(?P<text>.+?)\s+in\s+(?P<app_name>notepad|word|vscode|editor)\s*$',
            ],
            examples=["type hello world", "likho good morning", "write 'hello' in notepad"]
        ))

        # =====================================================================
        # SPECIALIZED AGENT CAPABILITY INTENTS (14 Agents)
        # =====================================================================

        # 22. Deep Research Agent
        self.register_intent(IntentDefinition(
            name="agent_deep_research",
            description="Perform deep multi-source research and synthesis via Deep Research Agent",
            parameters={
                "topic": {"type": "string", "description": "Topic for deep research", "required": True},
                "capability": {"type": "string", "description": "Agent capability", "required": False},
            },
            tier1_patterns=[
                r'^\s*(?:do\s+|perform\s+|run\s+|conduct\s+)?deep\s+research\s+(?:on|about|for|into)?\s*(?P<topic>.+)$',
                r'^\s*(?:investigate\s+(?:trends|deeply)|multi-?source\s+research)\s+(?:on|about|for)?\s*(?P<topic>.+)$',
            ],
            examples=["deep research on AI agents 2026", "do deep research about quantum computing"]
        ))

        # 23. Research Agent
        self.register_intent(IntentDefinition(
            name="agent_research",
            description="Research topics, gather information, Wikipedia summaries, or scrape URLs via Research Agent",
            parameters={
                "topic": {"type": "string", "description": "Research topic or URL", "required": True},
                "capability": {"type": "string", "description": "Agent capability", "required": False},
            },
            tier1_patterns=[
                r'^\s*(?:do\s+|perform\s+|run\s+)?research\s+(?:on|about|for)\s+(?P<topic>.+)$',
                r'^\s*(?:gather|collect)\s+(?:information|info|research)\s+(?:on|about)\s+(?P<topic>.+)$',
                r'^\s*wikipedia\s+(?:summary\s+(?:for|of|on)\s+)?(?P<topic>.+)$',
                r'^\s*scrape\s+(?:the\s+)?(?:url|page|website)?\s*(?P<topic>.+)$',
            ],
            examples=["research on renewable energy", "wikipedia summary for Albert Einstein", "scrape https://example.com"]
        ))

        # 24. Writer Agent
        self.register_intent(IntentDefinition(
            name="agent_writer",
            description="Write articles, essays, emails, creative pieces, summarize or proofread text via Writer Agent",
            parameters={
                "topic": {"type": "string", "description": "Topic, text, or prompt to write/summarize", "required": True},
                "capability": {"type": "string", "description": "Specific writing capability", "required": False},
            },
            tier1_patterns=[
                r'^\s*(?:write|compose|draft|author|generate)\s+(?:a\s+|an\s+)?(?:detailed\s+|short\s+|long\s+)?(?:article|essay|blog(?:\s+post)?|story|report|poem|summary|script)\s+(?:about|on|for|regarding)?\s*(?P<topic>.+)$',
                r'^\s*draft\s+(?:a\s+|an\s+)?email\s+(?P<topic>.+)$',
                r'^\s*(?:summarize|summarise|proofread|rewrite|paraphrase)\s+(?P<topic>.+)$',
            ],
            examples=["write an article on AI ethics", "write an essay about space exploration", "summarize {prev.output}", "draft an email to boss about leave"]
        ))

        # 25. Productivity Agent (Excel, Word editing, conversion; PPT/Word creation also routed through ProductivityAgent in executor)
        self.register_intent(IntentDefinition(
            name="agent_productivity",
            description="Create Excel spreadsheets, edit Office documents, or convert document formats via Productivity Agent",
            parameters={
                "task": {"type": "string", "description": "Document or spreadsheet task description", "required": True},
            },
            tier1_patterns=[
                r'^\s*(?:create|make|build|generate)\s+(?:an?\s+)?(?:excel|spreadsheet|xlsx|workbook)(?:\s+(?:for|on|about|called|named)\s+(?P<task>.+))?$',
                r'^\s*(?:edit|format|update)\s+(?:the\s+)?(?:word\s+|excel\s+|ppt\s+|powerpoint\s+)?(?:document|spreadsheet|presentation|file)\s+(?P<task>.+)$',
                r'^\s*convert\s+(?P<task>.+\s+to\s+(?:pdf|docx?|xlsx?|pptx?|markdown|md|txt))$',
            ],
            examples=["create an excel spreadsheet for monthly budget", "convert report.docx to pdf"]
        ))

        # 26. Creative Agent
        self.register_intent(IntentDefinition(
            name="agent_creative",
            description="Generate images, art, illustrations, logos, or creative layouts via Creative Agent",
            parameters={
                "prompt": {"type": "string", "description": "Visual or creative prompt", "required": True},
            },
            tier1_patterns=[
                r'^\s*(?:generate|create|draw|design|render|make)\s+(?:an?\s+)?(?:ai\s+)?(?:image|picture|artwork|art|illustration|logo|poster|banner|thumbnail|diagram)\s+(?:of|for|about|showing)?\s*(?P<prompt>.+)$',
            ],
            examples=["generate an image of a cyberpunk city", "create a logo for Pulsar AI"]
        ))

        # 27. Data Analyst Agent
        self.register_intent(IntentDefinition(
            name="agent_data",
            description="Analyze datasets, compute statistics, or generate charts via Data Analyst Agent",
            parameters={
                "task": {"type": "string", "description": "Data analysis or charting instruction", "required": True},
            },
            tier1_patterns=[
                r'^\s*(?:analyze|analyse|inspect|profile)\s+(?:the\s+)?(?:dataset|data|csv|metrics|sales|logs)\s*(?P<task>.*)$',
                r'^\s*(?:create|plot|generate|make)\s+(?:a\s+)?(?:chart|graph|plot|bar\s+chart|line\s+chart|pie\s+chart|histogram|visualization)\s+(?:of|for|from)?\s*(?P<task>.+)$',
                r'^\s*(?:run|perform)\s+statistical\s+analysis\s+(?:on|of)?\s*(?P<task>.+)$',
            ],
            examples=["analyze the sales csv data", "create a bar chart of revenue by quarter"]
        ))

        # 28. Database Agent
        self.register_intent(IntentDefinition(
            name="agent_database",
            description="Query SQL/NoSQL databases, inspect schemas, or optimize queries via Database Agent",
            parameters={
                "query": {"type": "string", "description": "Database task or SQL query", "required": True},
            },
            tier1_patterns=[
                r'^\s*(?:query|inspect|check|migrate|optimize)\s+(?:the\s+)?(?:database|db|sql\s+table|schema)\s*(?P<query>.*)$',
                r'^\s*(?:run|execute)\s+(?:a\s+)?(?:sql\s+)?query\s+(?P<query>.+)$',
            ],
            examples=["query the database for active users", "optimize sql query on orders table"]
        ))

        # 29. Communication Agent (Email & Calendar/Meetings)
        self.register_intent(IntentDefinition(
            name="agent_communication",
            description="Send emails, schedule meetings, or manage calendar via Communication Agent",
            parameters={
                "task": {"type": "string", "description": "Email or scheduling instruction", "required": True},
            },
            tier1_patterns=[
                r'^\s*(?:send|write)\s+(?:an?\s+)?email\s+(?:to\s+)?(?P<task>.+)$',
                r'^\s*(?:schedule|book|set\s+up|create)\s+(?:a\s+)?(?:meeting|call|calendar\s+event|appointment)\s*(?P<task>.*)$',
                r'^\s*(?:check|show)\s+(?:my\s+)?(?:calendar|schedule|inbox|unread\s+emails)\b.*$',
            ],
            examples=["send an email to Alice about project update", "schedule a meeting with team tomorrow at 10am"]
        ))

        # 30. Web Agent
        self.register_intent(IntentDefinition(
            name="agent_web",
            description="Automate web pages, fill forms, or monitor websites via Web Agent",
            parameters={
                "task": {"type": "string", "description": "Web automation task", "required": True},
            },
            tier1_patterns=[
                r'^\s*(?:automate\s+(?:website|web\s+page|browser)|fill\s+(?:the\s+)?form\s+on|monitor\s+(?:the\s+)?(?:website|site))\s+(?P<task>.+)$',
            ],
            examples=["monitor website https://example.com for changes", "fill the form on signup page"]
        ))

        # 31. File Manager Agent (high-level organization / backup; single find/move/open_folder handled locally above)
        self.register_intent(IntentDefinition(
            name="agent_file",
            description="Organize folders, clean up directories, or backup files via File Manager Agent",
            parameters={
                "task": {"type": "string", "description": "File organization or backup task", "required": True},
            },
            tier1_patterns=[
                r'^\s*(?:organize|sort|clean\s*up|declutter|backup|back\s+up)\s+(?:my\s+|the\s+)?(?:files|downloads|desktop|documents|folder|directory)\b(?:\s*(?P<task>.*))?$',
            ],
            examples=["organize my downloads folder", "backup project files"]
        ))

        # 32. Audio Agent
        self.register_intent(IntentDefinition(
            name="agent_audio",
            description="Transcribe audio files, process audio, or synthesize speech via Audio Agent",
            parameters={
                "task": {"type": "string", "description": "Audio task or file path", "required": True},
            },
            tier1_patterns=[
                r'^\s*(?:transcribe|convert\s+speech|extract\s+audio|process\s+audio|synthesize\s+speech)\s*(?P<task>.*)$',
            ],
            examples=["transcribe audio recording.mp3", "synthesize speech for intro script"]
        ))

        # 33. Video Agent
        self.register_intent(IntentDefinition(
            name="agent_video",
            description="Create, edit, trim, or add subtitles to videos via Video Agent",
            parameters={
                "task": {"type": "string", "description": "Video creation or editing task", "required": True},
            },
            tier1_patterns=[
                r'^\s*(?:create|generate|make|edit|render|trim)\s+(?:a\s+)?video\s+(?:about|from|of|for|with)?\s*(?P<task>.+)$',
                r'^\s*add\s+subtitles\s+to\s+(?P<task>.+)$',
            ],
            examples=["create a video about space exploration", "add subtitles to demo.mp4"]
        ))

        # 34. Student Agent
        self.register_intent(IntentDefinition(
            name="agent_student",
            description="Create study notes, flashcards, or structured learning plans via Student Agent",
            parameters={
                "topic": {"type": "string", "description": "Subject or topic to study", "required": True},
            },
            tier1_patterns=[
                r'^\s*(?:create|make|generate)\s+(?:study\s+)?(?:flashcards|study\s+notes|quiz)\s+(?:on|for|about)\s+(?P<topic>.+)$',
                r'^\s*(?:quiz\s+me\s+on|help\s+me\s+learn|teach\s+me)\s+(?P<topic>.+)$',
            ],
            examples=["create flashcards for operating systems", "study notes on neural networks"]
        ))

        # 35. Open App (after specific app/settings/youtube/agent intents; before search_web)
        self.register_intent(IntentDefinition(
            name="open_app",
            description="Open an application, website, or program on the computer",
            parameters={
                "target": {"type": "string", "description": "Name of the app, website, or program to open", "required": True}
            },
            tier1_patterns=[
                r'^\s*(?:open|launch|start|run|खोलो|खोल\s+दो|खोल\s+दे|खोलिये|खोलिए|खोल|ओपन\s+करो|ओपन\s+कर\s+दो|ओपन|प्वलो|पोलो)\s+(?!writing\b|working\b|analyzing\b|researching\b|creating\b|generating\b|typing\b|a\s+query\b|sql\b)(?!(?:.*?)\b(?:and\s+then|aur\s+phir|and\s+(?:search|play|type|write|open|close|send|check|read)|aur\s+(?:chalao|likho|khojo|bhejo))\b)(?P<target>.+?)\s*$',
                r'^\s*(?:khol|kholo|kholna|chalo|chalu\s+kar|chalu\s+karo)\s+(?!(?:.*?)\b(?:and\s+then|aur\s+phir|aur\s+fir|and\s+(?:search|play|type|write|open|close|send|check|read))\b)(?P<target>.+?)\s*$',
                r'^\s*(?!(?:which|what|tell\s+me)\b)(?P<target>.+?)\s+(?:khol\s+do|khol\s+de|kholo|kholna|khol|open\s+karo|open\s+kar\s+do|open|launch\s+karo|launch|start\s+karo|start|chalu\s+karo|chalu\s+kar|खोलो|खोल\s+दो|खोल\s+दे|खोलिये|खोलिए|खोलना|खोल|ओपन\s+करो|ओपन\s+कर\s+दो|ओपन|चालू\s+करो|चालू\s+कर\s+दो|प्वलो|पोलो|कलो)\s*$',
            ],
            examples=["open chrome", "open youtube music", "youtube music khol do", "chrome khol do", "start notepad"]
        ))

        # 36. Close App (after wifi/bluetooth toggles and executive_stop)
        self.register_intent(IntentDefinition(
            name="close_app",
            description="Close, quit, or kill an application or program",
            parameters={
                "target": {"type": "string", "description": "Name of the app or program to close", "required": True}
            },
            tier1_patterns=[
                r'^\s*(?:close|quit|exit|kill|stop|बंद\s+करो|बंद\s+कर\s+दो|बंद|क्लोज\s+करो|क्लोज)\s+(?!all\b|everything\b|execution\b|chain\b|tasks?\b|speaking\b|talking\b)(?P<target>.+)',
                r'^\s*(?:band\s+kar|band\s+karo|band\s+kro|bnd\s+kro|bnd\s+karo|hata|hatao)\s+(?P<target>.+)',
                r'^\s*(?P<target>.+?)\s+(?:band\s+karo|band\s+kro|bnd\s+kro|bnd\s+karo|band\s+kar\s+do|bnd\s+kar\s+do|bnd\s+krdo|band\s+kar|close\s+karo|close\s+kro|close\s+kar|close|hatao|बंद\s+करो|बंद\s+कर\s+दो|बंद\s+कर|बंद|क्लोज\s+करो|क्लोज\s+कर\s+दो|हटाओ)\s*$',
            ],
            examples=["close notepad", "quit chrome", "stop spotify", "notepad band karo"]
        ))

        # 37. Search Web (last catch-all, after youtube_search, find_file, agent_research, and open_app)
        self.register_intent(IntentDefinition(
            name="search_web",
            description="Search the web or Google for information",
            parameters={
                "query": {"type": "string", "description": "The search query", "required": True}
            },
            tier1_patterns=[
                r'^\s*(?:google\s+karo|google\s+(?!chrome\b|maps\b|drive\b|docs\b|sheets\b|meet\b|photos\b|earth\b|calendar\b)|search\s+(?:for\s+)?(?!file\b)|lookup\s+|find\s+(?!out\b|file\b))(?P<query>.+)',
                r'^\s*(?:dhund|dhundo|khoj|pata\s+karo|search\s+karo|search\s+kar\s+do)\s+(?P<query>.+)',
                r'^\s*(?P<query>.+?)\s+(?:google\s+(?:pe|par)\s+)?(?:search\s+karo|search\s+kar\s+do|dhundo|khojo)\s*$',
                r'^\s*(?:web|net|internet)\s+(?:pr|pe|par)\s+(?:check\s+kro|check\s+karo|dekho|search\s+kro|search\s+karo)\b(?:\s*,\s*)?(?P<query>.*)$',
                r'^\s*(?:check\s+(?:on|in)\s+(?:the\s+)?(?:web|internet))\s+(?:for\s+)?(?P<query>.+)$',
                r'^\s*(?P<query>(?:gold|silver|petrol|diesel|bitcoin|dollar|crude\s+oil)\s+(?:price|rate).*)',
                r'^\s*(?P<query>.*\b(?:gold|silver|petrol|diesel|bitcoin)\b.*(?:price|rate|bhav|daam|kitna\s+hai).*)',
            ],
            examples=["search python tutorial", "google karo AI news", "dhund do machine learning"]
        ))

    # =========================================================================
    # TIER 1: FAST LOCAL MATCHING
    # =========================================================================

    @staticmethod
    def _clean_for_tier1(text: str) -> str:
        """Lowercase and strip symbols/punctuation while preserving Devanagari combining marks, placeholders, and URL/path delimiters."""
        import unicodedata
        if not text:
            return ""
        keep = {'.', '-', '_', ':', '/', '{', '}', '"', "'"}
        cleaned = "".join(
            " " if (unicodedata.category(ch)[0] in ("P", "S", "Z", "C") and ch not in keep) else ch
            for ch in text.lower().strip()
        )
        return re.sub(r'\s+', ' ', cleaned).strip()

    @staticmethod
    def _strip_trailing_fillers(val: str) -> str:
        trailing_fillers = ('please', 'karo', 'kar', 'do', 'de', 'karna', 'the', 'a', 'bro', 'bhai', 'yaar', 'plz', 'pls', 'na', 'ji')
        param_val = val.strip()
        prev = None
        while prev != param_val:
            prev = param_val
            for filler in trailing_fillers:
                param_val = re.sub(rf'\s+{re.escape(filler)}\s*$', '', param_val, flags=re.IGNORECASE).strip()
        param_val = re.sub(r'^(?:for|of)\s+', '', param_val, flags=re.IGNORECASE).strip()
        return param_val

    def _fast_match(self, message: str) -> Optional[IntentResult]:
        """
        Tier 1: Fast regex-based pattern matching.
        Returns IntentResult if a clear match is found, None otherwise.
        """
        if not message or not message.strip():
            return None

        # Never hijack informational/tutorial questions as OS actions
        if re.match(r'^\s*(?:how\s+(?:to|do\s+i|can\s+i)|what\s+is\s+(?:a|an)\s+|explain\s+|define\s+)\b', message, re.IGNORECASE):
            return None

        from ai_assistant.core.local_command_normalizer import normalize_hinglish_devanagari

        candidates: List[str] = []
        raw_clean = self._clean_for_tier1(message)
        if raw_clean:
            candidates.append(raw_clean)
        norm_msg = normalize_hinglish_devanagari(message)
        norm_clean = self._clean_for_tier1(norm_msg)
        if norm_clean and norm_clean not in candidates:
            candidates.append(norm_clean)

        for intent_name, intent_def in self.intents.items():
            for pattern in intent_def.tier1_patterns:
                for candidate in candidates:
                    match = re.search(pattern, candidate, re.IGNORECASE | re.UNICODE)
                    if match:
                        params: Dict[str, Any] = {}
                        groupdict = match.groupdict()
                        groups = match.groups()

                        if groupdict:
                            for k, v in groupdict.items():
                                if v is not None and str(v).strip():
                                    params[k] = self._strip_trailing_fillers(str(v))
                        else:
                            param_names = list(intent_def.parameters.keys())
                            for i, group_val in enumerate(groups):
                                if i < len(param_names) and group_val:
                                    params[param_names[i]] = self._strip_trailing_fillers(str(group_val))

                        # Post-processing by intent type
                        if intent_name in ("executive_stop", "executive_pause", "executive_resume"):
                            action_map = {
                                "executive_stop": "stop",
                                "executive_pause": "pause",
                                "executive_resume": "resume",
                            }
                            params["action"] = action_map[intent_name]

                        elif intent_name == "media_control":
                            act = str(params.get("action") or "").lower().strip()
                            c_lower = candidate.lower()
                            if act in ("prev", "previous") or any(w in c_lower for w in ("pichla", "पिछला", "previous", "prev", "last song")):
                                params["action"] = "previous"
                            elif act in ("next", "skip", "forward", "badlo", "बदलो") or any(w in c_lower for w in ("agla", "अगला", "next", "skip", "badlo", "बदलो")):
                                params["action"] = "next"
                            elif act in ("pause", "stop") or any(w in c_lower for w in ("pause", "rok", "रोक", "बंद", "stop music", "stop song", "stop the music")):
                                params["action"] = "pause"
                            elif act == "resume" or any(w in c_lower for w in ("resume", "chalu", "चालू", "chalao")):
                                params["action"] = "resume"
                            elif any(w in c_lower for w in ("play song", "play music", "play_pause", "toggle")):
                                params["action"] = "play_pause"
                            else:
                                params["action"] = "play_pause"

                        elif intent_name == "wait":
                            try:
                                params["seconds"] = float(params.get("seconds", 1.0))
                            except (TypeError, ValueError):
                                params["seconds"] = 1.0

                        elif intent_name == "skip_time":
                            try:
                                params["minutes"] = int(params.get("minutes", 1))
                            except (TypeError, ValueError):
                                params["minutes"] = 1

                        elif intent_name in ("bluetooth_toggle", "wifi_toggle"):
                            raw = (groups[0] if groups else "").lower().strip()
                            params["enable"] = raw in ("on", "chalu", "chalao", "start", "enable", "activate")

                        elif intent_name == "dark_mode_toggle":
                            raw = (groups[0] if groups else "dark").lower().strip()
                            is_dark = (raw == "dark")
                            tokens = set((norm_clean or candidate).lower().split())
                            if tokens & {"off", "band", "disable", "deactivate"}:
                                is_dark = not is_dark
                            params["enable"] = is_dark

                        elif intent_name == "volume_control":
                            raw = re.sub(r'\s+', ' ', (groups[0] if groups else "")).lower().strip()
                            if raw in ("full", "max", "maximum"):
                                params["action"] = "set"
                                params["level"] = 100
                            elif raw in ("min", "minimum"):
                                params["action"] = "set"
                                params["level"] = 0
                            elif raw.isdigit():
                                params["action"] = "set"
                                params["level"] = max(0, min(100, int(raw)))
                            elif not raw:
                                params["action"] = "status"
                            else:
                                action_map = {
                                    "up": "up", "increase": "up", "raise": "up", "turn up": "up", "high": "up",
                                    "zyada": "up", "jyada": "up", "badha": "up", "badhao": "up", "badha do": "up", "tez": "up",
                                    "बढ़ाओ": "up", "बढ़ा": "up", "तेज़": "up", "तेज": "up", "ज्यादा": "up",
                                    "down": "down", "decrease": "down", "lower": "down", "turn down": "down", "low": "down",
                                    "kam": "down", "kam karo": "down", "dhima": "down", "dhimi": "down",
                                    "कम": "down", "धीमा": "down", "धीमी": "down", "घटाओ": "down",
                                    "mute": "mute", "band": "mute", "off": "mute", "म्यूट": "mute", "बंद": "mute",
                                    "unmute": "unmute", "on": "unmute", "अनम्यूट": "unmute", "चालू": "unmute",
                                }
                                params["action"] = action_map.get(raw, raw)

                        elif intent_name == "set_brightness":
                            raw = re.sub(r'\s+', ' ', (groups[0] if groups else "")).lower().strip()
                            if raw in ("full", "max", "maximum"):
                                params["action"] = "set"
                                params["level"] = 100
                            elif raw in ("min", "minimum"):
                                params["action"] = "set"
                                params["level"] = 10
                            elif raw.isdigit():
                                params["action"] = "set"
                                params["level"] = max(0, min(100, int(raw)))
                            elif not raw:
                                params["action"] = "status"
                            else:
                                b_map = {
                                    "up": "up", "increase": "up", "raise": "up", "turn up": "up", "high": "up",
                                    "zyada": "up", "jyada": "up", "badha": "up", "badhao": "up", "tez": "up",
                                    "down": "down", "decrease": "down", "lower": "down", "turn down": "down", "dim": "down", "low": "down",
                                    "kam": "down", "dhima": "down", "dhimi": "down",
                                }
                                params["action"] = b_map.get(raw, "status")

                        elif intent_name in AGENT_INTENT_METADATA:
                            agent_id, cap = AGENT_INTENT_METADATA[intent_name]
                            params.setdefault("agent_id", agent_id)
                            params.setdefault("capability", cap)
                            params.setdefault("execution_target", "agent")
                            params.setdefault("description", message.strip())

                        elif intent_name == "create_document":
                            params.setdefault("execution_target", "agent")
                            params.setdefault("agent_id", "productivity-001")
                            doc_type = str(params.get("doc_type") or "document").lower()
                            if doc_type in ("ppt", "pptx", "powerpoint", "presentation"):
                                params.setdefault("capability", "create_powerpoint")
                            else:
                                params.setdefault("capability", "create_word_document")

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
    # TIER 2 & 3: SEMANTIC + MULTI-PROVIDER LLM ROUTING
    # =========================================================================

    def _build_gemini_tools(self) -> list:
        """Build Gemini function declarations from registered intents."""
        try:
            from google.generativeai.types import FunctionDeclaration, Tool

            func_declarations = []
            for intent_name, intent_def in self.intents.items():
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

    def _semantic_route(self, message: str) -> Optional[IntentResult]:
        """Tier 2: Use local SentenceTransformers ML to determine intent."""
        try:
            if self._local_classifier is None:
                from ai_assistant.ai.intent_classification import IntentClassifier
                from ai_assistant.core.database_config import get_db_path
                self._local_classifier = IntentClassifier(db_path=str(get_db_path("intent_classifier")))

            from ai_assistant.core.local_command_normalizer import normalize_hinglish_devanagari
            query_for_ml = normalize_hinglish_devanagari(message) or message

            start_time = time.time()
            result = self._local_classifier.classify(query_for_ml)
            elapsed = time.time() - start_time

            intent_name = result.intent_name
            confidence = result.confidence

            name_map = {
                'open_application': 'open_app',
                'close_application': 'close_app',
                'information_query': 'info_query',
            }
            intent_name = name_map.get(intent_name, intent_name)

            if intent_name in self.intents and confidence > 0.40:
                logger.info(f"Tier 2 matched: {intent_name} (conf: {confidence:.2f}) ({elapsed:.2f}s)")
                params = result.entities if hasattr(result, 'entities') else {}
                if 'application' in params and 'target' not in params and params['application']:
                    params['target'] = params['application'][0]
                return IntentResult(
                    intent_name=intent_name,
                    parameters=params,
                    confidence=confidence,
                    tier=2,
                    raw_query=message
                )

            return None
        except Exception as e:
            logger.warning(f"Tier 2 Semantic routing failed: {e}")
            return None

    def _llm_route(self, message: str) -> Optional[IntentResult]:
        """
        Tier 3: Use LLM routing (Gemini function calling OR active UnifiedChatInterface provider).
        Returns IntentResult if the LLM identifies an actionable intent, None for pure conversation.
        """
        tls = getattr(self, '_tls', None)
        if tls is not None and getattr(tls, 'offline_mode', None):
            # In offline mode, still allow injected self.llm_provider (e.g., unit test mock)
            if self.llm_provider is None:
                return None

        enabled, model_name, api_key = self._get_active_gemini_config()
        if enabled and api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)

                tools = self._build_gemini_tools()
                if tools:
                    router_instruction = (
                        "You are an intent classifier for Pulsar AI assistant (English, Hindi, Hinglish). "
                        "If the user message is a COMMAND or specialized agent request, call the matching function. "
                        "If it is pure CONVERSATION (greetings, questions, chat, opinions), respond with 'CONVERSATION'."
                    )
                    router_model = genai.GenerativeModel(
                        model_name=model_name,
                        tools=tools,
                        system_instruction=router_instruction,
                    )
                    start_time = time.time()
                    response = router_model.generate_content(
                        message,
                        generation_config={"temperature": 0.1, "max_output_tokens": 120}
                    )
                    elapsed = time.time() - start_time
                    if response.candidates:
                        candidate = response.candidates[0]
                        if candidate.content and candidate.content.parts:
                            for part in candidate.content.parts:
                                if hasattr(part, 'function_call') and part.function_call:
                                    fc = part.function_call
                                    intent_name = fc.name
                                    params = {}
                                    if fc.args:
                                        for key, value in fc.args.items():
                                            params[key] = value
                                    if intent_name in AGENT_INTENT_METADATA:
                                        aid, cap = AGENT_INTENT_METADATA[intent_name]
                                        params.setdefault("agent_id", aid)
                                        params.setdefault("capability", cap)
                                        params.setdefault("execution_target", "agent")
                                    logger.info(f"Tier 3 Gemini matched: {intent_name} ({elapsed:.2f}s)")
                                    return IntentResult(
                                        intent_name=intent_name,
                                        parameters=params,
                                        confidence=0.85,
                                        tier=3,
                                        raw_query=message
                                    )
                    return None
            except Exception as e:
                logger.warning(f"Tier 3 Gemini routing failed: {e}")

        # Provider-agnostic fallback via self.llm_provider (or explicit provider override)
        provider_obj = self.llm_provider
        if provider_obj is None:
            active_prov = self._get_active_provider_name()
            if active_prov and active_prov not in ("gemini", "offline"):
                try:
                    from ai_assistant.ai.llm_provider import UnifiedChatInterface
                    provider_obj = UnifiedChatInterface(provider=active_prov, use_fallback=False)
                except Exception:
                    provider_obj = None

        if provider_obj is not None:
            try:
                intent_summaries = "\n".join(
                    f"- {name}: {defn.description}"
                    for name, defn in self.intents.items()
                )
                prompt = (
                    "Classify the following message into one of these intents or return CONVERSATION.\n"
                    f"Intents:\n{intent_summaries}\n\n"
                    f"Message: {message}\n"
                    'Reply ONLY with JSON: {"intent": "<name_or_CONVERSATION>", "parameters": {}}'
                )
                raw = provider_obj.chat(prompt, stream=False) if hasattr(provider_obj, "chat") else ""
                if isinstance(raw, str) and raw.strip():
                    cleaned = raw.strip()
                    if "```json" in cleaned:
                        cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0].strip()
                    elif "```" in cleaned:
                        cleaned = cleaned.split("```", 1)[1].split("```", 1)[0].strip()
                    data = json.loads(cleaned)
                    intent_name = data.get("intent")
                    if intent_name and intent_name != "CONVERSATION" and intent_name in self.intents:
                        params = data.get("parameters") or {}
                        if not isinstance(params, dict):
                            params = {}
                        if intent_name in AGENT_INTENT_METADATA:
                            aid, cap = AGENT_INTENT_METADATA[intent_name]
                            params.setdefault("agent_id", aid)
                            params.setdefault("capability", cap)
                            params.setdefault("execution_target", "agent")
                        return IntentResult(
                            intent_name=intent_name,
                            parameters=params,
                            confidence=0.80,
                            tier=3,
                            raw_query=message
                        )
            except Exception as e:
                logger.debug(f"Tier 3 UnifiedChatInterface routing skipped: {e}")

        return None

    # =========================================================================
    # PUBLIC API
    # =========================================================================

    def route(
        self,
        message: str,
        provider_override: Optional[str] = None,
        offline_mode: Optional[bool] = None,
    ) -> Optional[IntentResult]:
        """
        Route a user message to an intent.

        Returns:
            IntentResult if a command intent is detected
            None if the message is pure conversation
        """
        if not message or not message.strip():
            return None

        if not hasattr(self, '_tls') or self._tls is None:
            self._tls = threading.local()
        prev_prov = getattr(self._tls, 'provider_override', None)
        prev_off = getattr(self._tls, 'offline_mode', None)
        if provider_override is not None:
            self._tls.provider_override = provider_override
        if offline_mode is not None:
            self._tls.offline_mode = offline_mode
        try:
            return self._route_inner(message)
        finally:
            self._tls.provider_override = prev_prov
            self._tls.offline_mode = prev_off

    def _route_inner(self, message: str) -> Optional[IntentResult]:
        from ai_assistant.core.local_command_normalizer import normalize_hinglish_devanagari
        msg_clean = message.strip().lower()
        norm_clean = normalize_hinglish_devanagari(message).strip().lower()

        # Tier 1: Fast local match (Regex) on raw query or normalized query
        result = self._fast_match(message)
        if not result and norm_clean != msg_clean:
            result = self._fast_match(norm_clean)
        if result:
            logger.info(f"🎯 Intent routed (Tier 1): {result.intent_name} → {result.parameters}")
            return result

        # Fast Conversational Bypass: Skip heavy SentenceTransformer embeddings for obvious chat / questions
        conversational_patterns = [
            r'^(?:hi|hello|hey|namaste|aur|bhai|dost|bro|yaar|suno)\b',
            r'^(?:kaisa|kaise|kya|kyun|kab|kahan|kaun)\b',
            r'^(?:how|what|who|why|when|where|which|can you|tell me|explain)\b',
            r'^(?:thanks|thank you|shukriya|dhanyawad)\b',
            r'^(?:ok|okay|theek|achha|haan|nahi|no|yes)\b',
            r'(?:kaise ho|kya haal|how are you|who are you|what is your name)',
        ]
        if any(
            re.search(pat, candidate, re.IGNORECASE)
            for candidate in (msg_clean, norm_clean)
            if candidate
            for pat in conversational_patterns
        ):
            logger.debug(f"💬 Conversational fast-path matched: '{message}' (bypassing Tier 2 ML)")
            return None

        # Tier 1.5: Precomputed Vector Matching (<15ms, zero LLM, high precision)
        try:
            vm = IntentVectorMatcher()
            if vm.is_available():
                v_res = vm.match(message)
                if v_res and v_res.intent_name in self.intents:
                    logger.info(
                        f"🎯 Intent routed (Tier 1.5 Vector): {v_res.intent_name} "
                        f"(conf: {v_res.confidence:.2f}, phrase: '{v_res.matched_phrase}') → {v_res.parameters}"
                    )
                    return IntentResult(
                        intent_name=v_res.intent_name,
                        parameters=v_res.parameters,
                        confidence=v_res.confidence,
                        tier=1,
                        raw_query=message,
                    )
        except Exception as vm_err:
            logger.debug(f"Tier 1.5 vector match warning: {vm_err}")

        # Tier 2: Local ML Semantic matching (SentenceTransformers)
        result = self._semantic_route(message)
        if result:
            logger.info(f"🧠 Intent routed (Tier 2): {result.intent_name} → {result.parameters}")
            return result

        # Tier 3: LLM function calling / provider JSON routing
        result = self._llm_route(message)
        if result:
            logger.info(f"☁️ Intent routed (Tier 3): {result.intent_name} → {result.parameters}")
            return result

        # No intent detected — this is conversation
        return None

    def get_status(self) -> Dict[str, Any]:
        """Get router status for debugging."""
        enabled, model_name, _ = self._get_active_gemini_config()
        active_prov = self._get_active_provider_name()
        tier3_provider = "gemini" if enabled else (active_prov if self.llm_provider or active_prov not in ("offline", "none") else "none")
        return {
            "total_intents": len(self.intents),
            "intent_names": list(self.intents.keys()),
            "tier1_enabled": True,
            "tier2_local_ml_loaded": self._local_classifier is not None,
            "tier2_enabled": enabled,  # Backwards compatibility key
            "tier2_provider": tier3_provider,
            "tier3_enabled": enabled or (self.llm_provider is not None),
            "tier3_provider": tier3_provider,
            "tier3_model": model_name if enabled else None,
        }


# =============================================================================
# Tier 1.5 Semantic Vector Matcher
# (Consolidated from intent_vector_matcher)
# =============================================================================

class VectorMatchResult(NamedTuple):
    intent_name: str
    confidence: float
    matched_phrase: str
    margin: float
    parameters: Dict[str, Any]


class IntentVectorMatcher:
    """
    Tier 1.5 Semantic Vector Command Matcher
    Performs ultra-fast (<15ms) cosine similarity matching against precomputed intent vectors
    stored in data/core/intent_embeddings.npz.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, npz_path: Optional[str] = None):
        if self._initialized:
            return

        if npz_path is None:
            try:
                from core_ai.config.paths import DATA_DIR
                npz_candidate = DATA_DIR / "core" / "intent_embeddings.npz"
                if npz_candidate.exists():
                    npz_path = str(npz_candidate)
            except Exception:
                pass
            if npz_path is None:
                for p in [Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[3], Path(__file__).resolve().parents[4]]:
                    candidate = p / "data" / "core" / "intent_embeddings.npz"
                    if candidate.exists():
                        npz_path = str(candidate)
                        break

        self.npz_path = npz_path
        self.matrix: Optional[np.ndarray] = None
        self.intent_names: Optional[np.ndarray] = None
        self.phrases: Optional[np.ndarray] = None
        self._load_matrix()
        self._initialized = True

    def _load_matrix(self):
        """Loads precomputed embedding matrix from disk in <2ms."""
        if not self.npz_path or not Path(self.npz_path).exists():
            logger.warning(f"Vector matrix file not found: {self.npz_path}. Tier 1.5 disabled.")
            return

        try:
            data = np.load(self.npz_path, allow_pickle=True)
            self.matrix = data["matrix"].astype(np.float32)
            self.intent_names = data["intent_names"]
            self.phrases = data["phrases"]
            logger.info(
                f"✅ Tier 1.5 Vector Matcher loaded: {len(self.phrases)} phrases, "
                f"{len(set(self.intent_names))} intents (matrix shape: {self.matrix.shape})"
            )
        except Exception as e:
            logger.warning(f"Failed to load vector matrix {self.npz_path}: {e}")
            self.matrix = None

    def is_available(self) -> bool:
        return self.matrix is not None and len(self.matrix) > 0

    def match(
        self,
        query: str,
        threshold: float = 0.72,
        margin: float = 0.10
    ) -> Optional[VectorMatchResult]:
        """
        Match a user query against the vector matrix using normalized cosine similarity.
        Returns VectorMatchResult if confidence is high, None otherwise.
        """
        if not self.is_available():
            return None

        clean_query = query.strip()
        if not clean_query:
            return None

        norm_query = normalize_hinglish_devanagari(clean_query).strip() or clean_query
        q_vec = encode_text(norm_query, normalize=True)
        if q_vec is None:
            return None

        scores = np.dot(self.matrix, q_vec)
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        best_intent = str(self.intent_names[best_idx])
        best_phrase = str(self.phrases[best_idx])

        other_scores = [
            scores[i]
            for i in range(len(scores))
            if self.intent_names[i] != best_intent
        ]
        second_best = float(max(other_scores)) if other_scores else 0.0
        score_margin = best_score - second_best

        is_confident = (
            best_score >= 0.85 or
            (best_score >= threshold and score_margin >= margin)
        )

        if not is_confident:
            logger.debug(
                f"Tier 1.5 vector match rejected: '{clean_query}' -> {best_intent} "
                f"(score: {best_score:.3f}, margin: {score_margin:.3f}, threshold: {threshold})"
            )
            return None

        params = self._extract_parameters(best_intent, clean_query, norm_query)
        logger.info(
            f"🎯 Tier 1.5 Vector Matched: '{clean_query}' -> {best_intent} "
            f"(score: {best_score:.3f}, phrase: '{best_phrase}')"
        )
        return VectorMatchResult(
            intent_name=best_intent,
            confidence=best_score,
            matched_phrase=best_phrase,
            margin=score_margin,
            parameters=params,
        )

    def _extract_parameters(self, intent_name: str, raw_query: str, norm_query: str) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        q = norm_query.lower()

        if intent_name == "volume_control":
            if any(w in q for w in ["mute", "silent", "awaaz band"]):
                params["action"] = "mute"
            elif any(w in q for w in ["unmute", "awaaz kholo"]):
                params["action"] = "unmute"
            elif any(w in q for w in ["badhao", "badha", "increase", "up", "raise", "tez"]):
                params["action"] = "up"
            elif any(w in q for w in ["kam", "ghatao", "decrease", "down", "lower", "dheema"]):
                params["action"] = "down"
            m = re.search(r'\b(\d{1,3})\b', q)
            if m:
                lvl = int(m.group(1))
                if 0 <= lvl <= 100:
                    params["action"] = "set"
                    params["level"] = lvl

        elif intent_name in ("wifi_toggle", "bluetooth_toggle"):
            if any(w in q for w in ["on", "chalu", "start", "enable", "activate"]):
                params["enable"] = True
            elif any(w in q for w in ["off", "band", "stop", "disable", "deactivate"]):
                params["enable"] = False

        elif intent_name == "open_app":
            clean = re.sub(r'^(?:kholo|open|launch|run|start|chalao)\s+', '', q)
            clean = re.sub(r'\s+(?:kholo|open|karo|chalao|start|launch)$', '', clean).strip()
            if clean:
                params["target"] = clean
                params["app_name"] = clean

        elif intent_name == "close_app":
            clean = re.sub(r'^(?:band\s+karo|close|quit|exit|kill|shutdown)\s+', '', q)
            clean = re.sub(r'\s+(?:band\s+karo|close|kar\s+do|quit)$', '', clean).strip()
            if clean:
                params["target"] = clean
                params["app_name"] = clean

        elif intent_name == "media_control":
            if any(w in q for w in ["next", "agla", "skip"]):
                params["action"] = "next"
            elif any(w in q for w in ["prev", "previous", "pichla"]):
                params["action"] = "previous"
            elif any(w in q for w in ["pause", "roko", "ruk"]):
                params["action"] = "pause"
            elif any(w in q for w in ["play", "resume", "chalao"]):
                params["action"] = "resume"

        elif intent_name == "send_message":
            params["platform"] = "whatsapp"
            m = re.search(r'^(?P<contact>[a-zA-Z\u0900-\u097F]+)\s+ko\s+(?P<message>.+?)\s+(?:whatsapp|whtsp|msg|bhejo)', q)
            if m:
                params["contact"] = m.group("contact").strip()
                params["message"] = m.group("message").strip()

        elif intent_name == "search_web":
            clean = re.sub(r'^(?:search|google|search\s+for|dhoondo|check|pata\s+karo)\s+', '', q)
            clean = re.sub(r'\s+(?:search\s+karo|google\s+karo|dhoondo|pata\s+karo|check\s+kro)$', '', clean).strip()
            params["query"] = clean or raw_query

        return params

