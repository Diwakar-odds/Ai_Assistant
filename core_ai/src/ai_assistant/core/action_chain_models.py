"""
Action Chain Models
Data models for chain-of-actions execution system
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid


class ChainStatus(Enum):
    """Status of action chain execution"""
    PENDING = "pending"                         # Created, not started
    PLANNING = "planning"                       # Decomposing into actions
    EXECUTING = "executing"                     # Running actions
    VERIFYING = "verifying"                     # Checking results
    PAUSED = "paused"                           # Paused by user or system
    WAITING_CONFIRMATION = "waiting_confirmation"  # Waiting for user confirmation
    COMPLETED = "completed"                     # Successfully finished
    FAILED = "failed"                           # Error occurred
    CANCELLED = "cancelled"                     # User cancelled


class ActionType(Enum):
    """Types of actions in a chain"""
    BROWSER = "browser"
    APP = "app"
    FILE = "file"
    SYSTEM = "system"
    API = "api"
    DATABASE = "database"
    AGENT = "agent"
    RESEARCH = "research"
    COMMUNICATION = "communication"
    MEDIA = "media"
    WAIT = "wait"
    CUSTOM = "custom"


def _normalize_status_value(status: Any) -> str:
    """Safely convert a ChainStatus or raw string into canonical lowercase string."""
    if isinstance(status, Enum):
        return str(status.value).lower()
    if status is None:
        return ChainStatus.PENDING.value
    return str(status).strip().lower()


@dataclass
class Action:
    """Single action in a chain"""
    id: str
    type: ActionType
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)

    # Execution state
    status: str = "pending"
    progress: int = 0  # 0-100
    result: Any = None
    error: Optional[str] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0

    # Verification
    verified: bool = False
    verification_result: Optional[Dict[str, Any]] = None

    # Orchestration & multi-agent metadata
    step: int = 0
    intent: str = ""
    agent_id: Optional[str] = None
    capability: Optional[str] = None
    parallel_group: Optional[str] = None
    requires_confirmation: bool = False
    output_key: Optional[str] = None
    condition: Optional[str] = None
    on_failure: str = "abort"  # abort | continue | fallback | skip
    fallback_action_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to canonical dictionary DTO"""
        action_type_val = self.type.value if isinstance(self.type, Enum) else str(self.type)
        return {
            "id": self.id,
            "step": self.step,
            "intent": self.intent,
            "type": action_type_val,
            "description": self.description,
            "parameters": self.parameters,
            "dependencies": list(self.dependencies or []),
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "verified": self.verified,
            "verification_result": self.verification_result,
            "agent_id": self.agent_id,
            "capability": self.capability,
            "parallel_group": self.parallel_group,
            "requires_confirmation": self.requires_confirmation,
            "output_key": self.output_key,
            "condition": self.condition,
            "on_failure": self.on_failure,
            "fallback_action_id": self.fallback_action_id,
        }


@dataclass
class ActionChain:
    """Complete chain of actions"""
    id: str
    command: str
    actions: List[Action] = field(default_factory=list)

    # Status tracking
    status: ChainStatus = ChainStatus.PENDING
    current_action_index: int = 0
    actions_completed: int = 0
    actions_failed: int = 0

    # Results
    results: Dict[str, Any] = field(default_factory=dict)
    verification_results: List[Dict[str, Any]] = field(default_factory=list)
    final_output: Optional[Any] = None

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    requires_confirmation: bool = False
    safety_level: str = "safe"
    source: str = "chat"
    app_context: Optional[str] = None
    current_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    context_vars: Dict[str, Any] = field(default_factory=dict)

    # Error handling
    errors: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3

    @property
    def chain_id(self) -> str:
        """Canonical alias for id"""
        return self.id

    @property
    def total_actions(self) -> int:
        """Total number of actions"""
        return len(self.actions)

    @property
    def progress_percentage(self) -> float:
        """Overall progress percentage"""
        status_val = _normalize_status_value(self.status)
        if status_val == ChainStatus.COMPLETED.value:
            return 100.0
        if self.total_actions == 0:
            return 0.0
        return round((self.actions_completed / self.total_actions) * 100.0, 2)

    @property
    def duration_seconds(self) -> float:
        """Total execution duration"""
        if not self.started_at:
            return 0.0
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to canonical Chain DTO dictionary"""
        status_val = _normalize_status_value(self.status)
        return {
            "chain_id": self.id,
            "id": self.id,
            "command": self.command,
            "source": self.source,
            "status": status_val,
            "progress_percentage": self.progress_percentage,
            "current_action_index": self.current_action_index,
            "total_actions": self.total_actions,
            "actions_completed": self.actions_completed,
            "actions_failed": self.actions_failed,
            "app_context": self.app_context,
            "current_agent": self.current_agent,
            "requires_confirmation": self.requires_confirmation,
            "safety_level": self.safety_level,
            "actions": [a.to_dict() for a in self.actions],
            "results": self.results,
            "verification_results": self.verification_results,
            "final_output": self.final_output,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }


@dataclass
class ExecutionReport:
    """Report of chain execution"""
    chain_id: str
    success: bool = True

    # Statistics
    total_actions: int = 0
    completed_actions: int = 0
    failed_actions: int = 0
    skipped_actions: int = 0

    # Timing
    duration_seconds: float = 0.0
    average_action_time: float = 0.0

    # Results
    outputs: List[Any] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    # Verification
    verification_passed: bool = False
    verification_score: float = 0.0

    # Details
    action_results: List[Dict[str, Any]] = field(default_factory=list)

    # Status & summary metadata
    status: ChainStatus = ChainStatus.COMPLETED
    message: str = ""
    final_output: Optional[Any] = None

    # Compatibility aliases (used by legacy callers)
    actions_completed: Optional[int] = None
    actions_failed: Optional[int] = None

    def __post_init__(self):
        if self.actions_completed is not None and self.completed_actions == 0:
            self.completed_actions = self.actions_completed
        if self.actions_failed is not None and self.failed_actions == 0:
            self.failed_actions = self.actions_failed

        if isinstance(self.status, str):
            try:
                self.status = ChainStatus(self.status.lower())
            except ValueError:
                self.status = ChainStatus.COMPLETED if self.success else ChainStatus.FAILED

        # Keep success and status aligned on terminal failures/cancellations
        if self.status in (ChainStatus.FAILED, ChainStatus.CANCELLED):
            self.success = False
        elif not self.success and self.status == ChainStatus.COMPLETED:
            self.status = ChainStatus.FAILED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        status_val = _normalize_status_value(self.status)
        return {
            "chain_id": self.chain_id,
            "success": self.success,
            "status": status_val,
            "message": self.message,
            "total_actions": self.total_actions,
            "completed_actions": self.completed_actions,
            "failed_actions": self.failed_actions,
            "skipped_actions": self.skipped_actions,
            "duration_seconds": self.duration_seconds,
            "average_action_time": self.average_action_time,
            "outputs": self.outputs,
            "final_output": self.final_output,
            "errors": self.errors,
            "verification_passed": self.verification_passed,
            "verification_score": self.verification_score,
            "action_results": self.action_results,
        }


@dataclass
class ProgressReport:
    """Real-time progress report"""
    chain_id: str
    status: str
    progress_percentage: float
    current_action: Optional[str] = None
    current_action_progress: int = 0
    completed_actions: int = 0
    total_actions: int = 0
    elapsed_seconds: float = 0.0
    estimated_remaining_seconds: float = 0.0
    current_agent: Optional[str] = None
    event_type: str = "chain_progress"
    step_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    actions: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            "chain_id": self.chain_id,
            "event_type": self.event_type,
            "status": _normalize_status_value(self.status),
            "progress_percentage": self.progress_percentage,
            "current_action": self.current_action,
            "current_action_progress": self.current_action_progress,
            "completed_actions": self.completed_actions,
            "total_actions": self.total_actions,
            "elapsed_seconds": self.elapsed_seconds,
            "estimated_remaining_seconds": self.estimated_remaining_seconds,
            "current_agent": self.current_agent,
            "step_id": self.step_id,
            "message": self.message,
            "error": self.error,
        }
        if self.actions is not None:
            data["actions"] = self.actions
        return data


def generate_chain_id() -> str:
    """Generate unique chain ID"""
    return f"chain_{uuid.uuid4().hex[:12]}"


def generate_action_id() -> str:
    """Generate unique action ID"""
    return f"action_{uuid.uuid4().hex[:8]}"
