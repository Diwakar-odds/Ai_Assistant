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
    PENDING = "pending"           # Created, not started
    PLANNING = "planning"         # Decomposing into actions
    EXECUTING = "executing"       # Running actions
    VERIFYING = "verifying"       # Checking results
    COMPLETED = "completed"       # Successfully finished
    FAILED = "failed"            # Error occurred
    CANCELLED = "cancelled"       # User cancelled


class ActionType(Enum):
    """Types of actions in a chain"""
    BROWSER = "browser"
    APP = "app"
    FILE = "file"
    SYSTEM = "system"
    API = "api"
    DATABASE = "database"
    CUSTOM = "custom"


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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "description": self.description,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "status": self.status,
            "progress": self.progress,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "verified": self.verified,
            "verification_result": self.verification_result
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
    
    # Error handling
    errors: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    
    @property
    def total_actions(self) -> int:
        """Total number of actions"""
        return len(self.actions)
    
    @property
    def progress_percentage(self) -> float:
        """Overall progress percentage"""
        if self.total_actions == 0:
            return 0.0
        return (self.actions_completed / self.total_actions) * 100
    
    @property
    def duration_seconds(self) -> float:
        """Total execution duration"""
        if not self.started_at:
            return 0.0
        end_time = self.completed_at or datetime.now()
        return (end_time - self.started_at).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "command": self.command,
            "actions": [a.to_dict() for a in self.actions],
            "status": self.status.value,
            "current_action_index": self.current_action_index,
            "actions_completed": self.actions_completed,
            "actions_failed": self.actions_failed,
            "total_actions": self.total_actions,
            "progress_percentage": self.progress_percentage,
            "results": self.results,
            "verification_results": self.verification_results,
            "final_output": self.final_output,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors,
            "retry_count": self.retry_count
        }


@dataclass
class ExecutionReport:
    """Report of chain execution"""
    chain_id: str
    success: bool
    
    # Statistics
    total_actions: int
    completed_actions: int
    failed_actions: int
    skipped_actions: int
    
    # Timing
    duration_seconds: float
    average_action_time: float
    
    # Results
    outputs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    # Verification
    verification_passed: bool = False
    verification_score: float = 0.0
    
    # Details
    action_results: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "chain_id": self.chain_id,
            "success": self.success,
            "total_actions": self.total_actions,
            "completed_actions": self.completed_actions,
            "failed_actions": self.failed_actions,
            "skipped_actions": self.skipped_actions,
            "duration_seconds": self.duration_seconds,
            "average_action_time": self.average_action_time,
            "outputs": self.outputs,
            "errors": self.errors,
            "verification_passed": self.verification_passed,
            "verification_score": self.verification_score,
            "action_results": self.action_results
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
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "chain_id": self.chain_id,
            "status": self.status,
            "progress_percentage": self.progress_percentage,
            "current_action": self.current_action,
            "current_action_progress": self.current_action_progress,
            "completed_actions": self.completed_actions,
            "total_actions": self.total_actions,
            "elapsed_seconds": self.elapsed_seconds,
            "estimated_remaining_seconds": self.estimated_remaining_seconds
        }


def generate_chain_id() -> str:
    """Generate unique chain ID"""
    return f"chain_{uuid.uuid4().hex[:12]}"


def generate_action_id() -> str:
    """Generate unique action ID"""
    return f"action_{uuid.uuid4().hex[:8]}"
