"""
Command Models for Executive Brain
Data models for the brain-based command routing system.
"""

import threading
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class CommandSource(Enum):
    """Sources of incoming commands"""
    VOICE = "voice"
    CHAT = "chat"
    API = "api"
    WEBSOCKET = "websocket"
    ORCHESTRATOR = "orchestrator"


class CommandPriority(Enum):
    """Command priority levels — lower number = higher priority"""
    EXECUTIVE = 0   # stop, cancel, pause — always immediate
    VOICE = 1       # voice commands — highest task priority
    CHAT = 2        # chat/text commands
    API = 3         # programmatic API calls


class CommandClassification(Enum):
    """How the brain classifies an incoming command"""
    EXECUTIVE_STOP = "executive_stop"
    EXECUTIVE_PAUSE = "executive_pause"
    EXECUTIVE_RESUME = "executive_resume"
    TASK_NEW = "task_new"
    TASK_RELATED = "task_related"       # Merge with active chain
    TASK_MODIFY = "task_modify"         # "no wait, use Firefox instead"
    CONVERSATIONAL = "conversational"   # Not a task, just chat


class BrainState(Enum):
    """Current state of the executive brain"""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    PAUSED = "paused"


@dataclass
class TimestampedCommand:
    """A command with metadata about when and where it came from"""
    text: str
    timestamp: float
    source: CommandSource
    priority: CommandPriority
    classification: Optional[CommandClassification] = None
    
    @classmethod
    def from_voice(cls, text: str):
        import time
        return cls(
            text=text,
            timestamp=time.time(),
            source=CommandSource.VOICE,
            priority=CommandPriority.VOICE
        )
    
    @classmethod
    def from_chat(cls, text: str):
        import time
        return cls(
            text=text,
            timestamp=time.time(),
            source=CommandSource.CHAT,
            priority=CommandPriority.CHAT
        )
    
    @classmethod
    def from_api(cls, text: str):
        import time
        return cls(
            text=text,
            timestamp=time.time(),
            source=CommandSource.API,
            priority=CommandPriority.API
        )


@dataclass
class ManagedChain:
    """A chain that's being tracked by the brain"""
    chain_id: str
    command: str
    thread: Optional[threading.Thread] = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    source: CommandSource = CommandSource.CHAT
    created_at: float = 0.0
    app_context: Optional[str] = None  # e.g. "chrome", "whatsapp"
    intent_context: Optional[str] = None  # e.g. "browser_task", "messaging"
    
    @property
    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set()
    
    def cancel(self):
        """Signal this chain to stop"""
        self.cancel_event.set()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "command": self.command,
            "source": self.source.value,
            "created_at": self.created_at,
            "app_context": self.app_context,
            "is_cancelled": self.is_cancelled,
            "is_alive": self.thread.is_alive() if self.thread else False
        }


@dataclass
class BrainResponse:
    """Response from the executive brain after processing a command"""
    action_taken: str   # 'executing', 'merged', 'parallel', 'cancelled', 'paused', 'resumed', 'chatting'
    message: str
    chain_id: Optional[str] = None
    active_chains: List[str] = field(default_factory=list)
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_taken": self.action_taken,
            "message": self.message,
            "chain_id": self.chain_id,
            "active_chains": self.active_chains,
            "success": self.success
        }


# ===== Executive Command Keywords =====

EXECUTIVE_STOP_KEYWORDS = [
    'stop', 'cancel', 'halt', 'abort', 'quit',
    'ruko', 'band karo', 'rokdo', 'rok do', 'band kar',
    'nahi', 'mat karo', 'hatao', 'chhodo',
    'रुको', 'बंद करो', 'रोक दो', 'नहीं', 'मत करो',
]

EXECUTIVE_PAUSE_KEYWORDS = [
    'pause', 'wait', 'hold', 'hold on',
    'ruko zara', 'ek second', 'ek minute', 'thehro',
    'रुको ज़रा', 'एक सेकंड', 'ठहरो',
]

EXECUTIVE_RESUME_KEYWORDS = [
    'resume', 'continue', 'go ahead', 'proceed', 'carry on',
    'chalu karo', 'aage badho', 'jari rakho',
    'चालू करो', 'आगे बढ़ो', 'जारी रखो',
]

SEQUENTIAL_KEYWORDS = [
    'then', 'and then', 'after that', 'next', 'also',
    'phir', 'aur phir', 'uske baad', 'fir',
    'फिर', 'और फिर', 'उसके बाद',
]

MODIFICATION_KEYWORDS = [
    'no wait', 'actually', 'instead', 'change to', 'not that',
    'nahi', 'ruko actually', 'wo nahi', 'iske jagah',
    'नहीं', 'रुको', 'वो नहीं', 'इसकी जगह',
]
