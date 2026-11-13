"""
Command Models for Executive Brain
Data models for the brain-based command routing system.
"""

import threading
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

from ai_assistant.core.action_chain_models import ChainStatus, ActionChain


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
    pause_event: threading.Event = field(default_factory=threading.Event)
    source: CommandSource = CommandSource.CHAT
    created_at: float = 0.0
    app_context: Optional[str] = None      # e.g. "chrome", "whatsapp"
    intent_context: Optional[str] = None   # e.g. "browser_task", "messaging"

    # Synchronized execution & UI state (compatible with modern_web_backend & #12 DTO)
    status: ChainStatus = ChainStatus.PENDING
    total_actions: int = 0
    actions_completed: int = 0
    actions_failed: int = 0
    current_action_index: int = 0
    current_action: Optional[str] = None
    current_agent: Optional[str] = None
    requires_confirmation: bool = False
    safety_level: str = "safe"
    results: Dict[str, Any] = field(default_factory=dict)
    verification_results: List[Dict[str, Any]] = field(default_factory=list)
    final_output: Optional[Any] = None
    errors: List[str] = field(default_factory=list)
    retry_count: int = 0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    action_chain: Optional[ActionChain] = None

    @property
    def id(self) -> str:
        return self.chain_id

    @property
    def progress_percentage(self) -> float:
        if self.action_chain is not None:
            return self.action_chain.progress_percentage
        if self.status == ChainStatus.COMPLETED:
            return 100.0
        if self.total_actions <= 0:
            return 0.0
        return round((self.actions_completed / self.total_actions) * 100.0, 2)

    @property
    def duration_seconds(self) -> float:
        if self.action_chain is not None and self.action_chain.started_at:
            return self.action_chain.duration_seconds
        if not self.started_at:
            return 0.0
        import time
        end_ts = self.completed_at or time.time()
        return max(0.0, end_ts - self.started_at)

    @property
    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set() or self.status == ChainStatus.CANCELLED

    @property
    def is_paused(self) -> bool:
        return self.pause_event.is_set() or self.status == ChainStatus.PAUSED

    def pause(self):
        """Signal this chain to pause"""
        self.pause_event.set()
        if self.status not in (ChainStatus.CANCELLED, ChainStatus.COMPLETED, ChainStatus.FAILED):
            self.status = ChainStatus.PAUSED
        if self.action_chain is not None and self.action_chain.status not in (
            ChainStatus.CANCELLED, ChainStatus.COMPLETED, ChainStatus.FAILED
        ):
            self.action_chain.status = ChainStatus.PAUSED

    def resume(self):
        """Signal this chain to resume"""
        self.pause_event.clear()
        if self.status == ChainStatus.PAUSED:
            self.status = ChainStatus.EXECUTING
        if self.action_chain is not None and self.action_chain.status in (
            ChainStatus.PAUSED, ChainStatus.WAITING_CONFIRMATION
        ):
            self.action_chain.status = ChainStatus.EXECUTING

    def cancel(self):
        """Signal this chain to stop"""
        self.cancel_event.set()
        self.pause_event.clear()
        self.status = ChainStatus.CANCELLED
        if self.action_chain is not None:
            self.action_chain.status = ChainStatus.CANCELLED

    def sync_from_action_chain(self, chain: ActionChain):
        """Synchronize tracked metrics from live ActionChain instance."""
        if chain is None:
            return
        self.action_chain = chain
        self.status = chain.status if isinstance(chain.status, ChainStatus) else ChainStatus.EXECUTING
        self.total_actions = chain.total_actions
        self.actions_completed = chain.actions_completed
        self.actions_failed = chain.actions_failed
        self.current_action_index = chain.current_action_index
        self.current_agent = chain.current_agent or self.current_agent
        self.requires_confirmation = chain.requires_confirmation
        self.safety_level = chain.safety_level
        self.results = dict(chain.results)
        self.verification_results = list(chain.verification_results)
        self.final_output = chain.final_output if chain.final_output is not None else self.final_output
        self.errors = list(chain.errors)
        self.retry_count = chain.retry_count
        if chain.actions and 0 <= chain.current_action_index < len(chain.actions):
            act = chain.actions[chain.current_action_index]
            self.current_action = act.description
            if act.agent_id:
                self.current_agent = act.agent_id

    def to_dict(self) -> Dict[str, Any]:
        if self.action_chain is not None:
            dto = self.action_chain.to_dict()
            dto["source"] = self.source.value if isinstance(self.source, Enum) else str(self.source)
            dto["app_context"] = dto.get("app_context") or self.app_context
            dto["current_action"] = self.current_action
            dto["is_cancelled"] = self.is_cancelled
            dto["is_paused"] = self.is_paused
            dto["is_alive"] = self.thread.is_alive() if self.thread else False
            return dto

        status_val = self.status.value if isinstance(self.status, Enum) else str(self.status)
        created_iso = (
            datetime.fromtimestamp(self.created_at).isoformat()
            if self.created_at else None
        )
        started_iso = (
            datetime.fromtimestamp(self.started_at).isoformat()
            if self.started_at else None
        )
        completed_iso = (
            datetime.fromtimestamp(self.completed_at).isoformat()
            if self.completed_at else None
        )
        return {
            "chain_id": self.chain_id,
            "id": self.chain_id,
            "command": self.command,
            "source": self.source.value if isinstance(self.source, Enum) else str(self.source),
            "status": status_val,
            "progress_percentage": self.progress_percentage,
            "current_action_index": self.current_action_index,
            "total_actions": self.total_actions,
            "actions_completed": self.actions_completed,
            "actions_failed": self.actions_failed,
            "current_action": self.current_action,
            "app_context": self.app_context,
            "current_agent": self.current_agent,
            "requires_confirmation": self.requires_confirmation,
            "safety_level": self.safety_level,
            "actions": [],
            "results": self.results,
            "verification_results": self.verification_results,
            "final_output": self.final_output,
            "created_at": created_iso,
            "started_at": started_iso,
            "completed_at": completed_iso,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
            "is_cancelled": self.is_cancelled,
            "is_paused": self.is_paused,
            "is_alive": self.thread.is_alive() if self.thread else False,
        }


@dataclass
class BrainResponse:
    """Response from the executive brain after processing a command"""
    action_taken: str   # 'executing', 'merged', 'parallel', 'cancelled', 'paused', 'resumed', 'chatting', 'completed'
    message: str
    chain_id: Optional[str] = None
    active_chains: List[str] = field(default_factory=list)
    success: bool = True
    chain: Optional[Dict[str, Any]] = None
    results: List[Dict[str, Any]] = field(default_factory=list)
    final_output: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_taken": self.action_taken,
            "message": self.message,
            "chain_id": self.chain_id,
            "active_chains": self.active_chains,
            "success": self.success,
            "chain": self.chain,
            "results": self.results,
            "final_output": self.final_output,
        }


# ===== Executive Command Keywords =====

# Strong unambiguous stop commands (trigger stop even when idle to halt any lingering/speech/OS tasks)
STRONG_EXECUTIVE_STOP_KEYWORDS = [
    'emergency stop', 'stop all', 'stop everything', 'cancel all', 'cancel everything',
    'abort all', 'halt all', 'stop execution', 'cancel chain', 'stop chain',
    'band karo', 'rokdo', 'rok do', 'band kar', 'rok lo',
    'mat karo', 'ruko',
    'रुको', 'बंद करो', 'रोक दो', 'मत करो', 'सब बंद करो', 'सब रोको',
]

# Full stop keywords (includes single-token bare words valid standalone or while active)
EXECUTIVE_STOP_KEYWORDS = [
    'stop', 'cancel', 'halt', 'abort', 'quit',
    'ruko', 'band karo', 'rokdo', 'rok do', 'band kar', 'rok lo',
    'nahi', 'mat karo', 'hatao', 'chhodo',
    'रुको', 'बंद करो', 'रोक दो', 'नहीं', 'मत करो',
]

EXECUTIVE_PAUSE_KEYWORDS = [
    'pause', 'pause execution', 'pause chain', 'hold', 'hold on',
    'ruko zara', 'ek second', 'ek minute', 'thehro', 'pause karo',
    'रुको ज़रा', 'एक सेकंड', 'ठहरो', 'पॉज़ करो',
]

EXECUTIVE_RESUME_KEYWORDS = [
    'resume', 'continue', 'go ahead', 'proceed', 'carry on',
    'resume execution', 'resume chain', 'continue chain',
    'chalu karo', 'aage badho', 'jari rakho', 'phir se chalu',
    'चालू करो', 'आगे बढ़ो', 'जारी रखो',
]

SEQUENTIAL_KEYWORDS = [
    'then', 'and then', 'after that', 'next', 'also', 'followed by',
    'phir', 'aur phir', 'fir', 'aur fir', 'uske baad', 'iske baad',
    'फिर', 'और फिर', 'उसके बाद', 'इसके बाद', 'तथा', 'एवं',
]

PARALLEL_KEYWORDS = [
    'simultaneously', 'at the same time', 'in parallel', 'concurrently',
    'meanwhile', 'alongside', 'ek saath', 'saath mein', 'ek sath', 'sath mein',
    'एक साथ', 'साथ में',
]

# Notice: bare 'nahi'/'नहीं' is intentionally excluded so it does not shadow EXECUTIVE_STOP_KEYWORDS.
MODIFICATION_KEYWORDS = [
    'no wait', 'actually', 'instead', 'change to', 'not that',
    'nahi ruko', 'nahi actually', 'wo nahi', 'iske jagah', 'isko badlo',
    'नहीं रुको', 'वो नहीं', 'इसकी जगह', 'बदल के',
]
