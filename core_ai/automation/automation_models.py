"""
Automation Models & Dataclasses
Enums and dataclasses defining workflows, tasks, triggers, and execution results.
Extracted from automation_engine.py.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
import uuid
from datetime import datetime


class WorkflowStatus(Enum):
    """Workflow execution status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(Enum):
    """Types of tasks in workflows."""
    ACTION = "action"          # Execute a function/command
    CONDITION = "condition"    # If/then logic
    DELAY = "delay"           # Wait for specified time
    LOOP = "loop"             # Repeat operations
    PARALLEL = "parallel"     # Execute tasks simultaneously
    SEQUENCE = "sequence"     # Execute tasks in order
    TRIGGER = "trigger"       # Event-based activation
    WEBHOOK = "webhook"       # External API calls
    FILE_OPERATION = "file_op" # File system operations


class TriggerType(Enum):
    """Types of workflow triggers."""
    MANUAL = "manual"         # User initiated
    SCHEDULED = "scheduled"   # Time-based
    EVENT = "event"          # System event
    PATTERN = "pattern"      # Behavioral pattern
    CONDITION = "condition"  # State-based
    WEBHOOK = "webhook"      # External trigger


@dataclass
class WorkflowTask:
    """Individual task within a workflow."""
    id: str
    name: str
    type: TaskType
    function: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 30
    enabled: bool = True
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['type'] = self.type.value if hasattr(self.type, 'value') else self.type
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create from dictionary."""
        data_copy = data.copy()
        if isinstance(data_copy.get('type'), str):
            data_copy['type'] = TaskType(data_copy['type'])
        return cls(**data_copy)


@dataclass
class WorkflowTrigger:
    """Workflow trigger configuration."""
    type: TriggerType
    schedule: Optional[str] = None
    event_pattern: Optional[str] = None
    condition: Optional[str] = None
    enabled: bool = True
    
    def to_dict(self):
        result = asdict(self)
        result['type'] = self.type.value if hasattr(self.type, 'value') else self.type
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        data_copy = data.copy()
        if isinstance(data_copy.get('type'), str):
            data_copy['type'] = TriggerType(data_copy['type'])
        return cls(**data_copy)


@dataclass
class WorkflowResult:
    """Result of workflow execution."""
    workflow_id: str
    execution_id: str
    status: WorkflowStatus
    start_time: str
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    task_results: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    output_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        result = asdict(self)
        result['status'] = self.status.value if hasattr(self.status, 'value') else self.status
        return result


@dataclass
class Workflow:
    """Complete workflow definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "New Workflow"
    description: str = ""
    tasks: List[WorkflowTask] = field(default_factory=list)
    triggers: List[WorkflowTrigger] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.IDLE
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'tasks': [t.to_dict() for t in self.tasks],
            'triggers': [tr.to_dict() for tr in self.triggers],
            'status': self.status.value if hasattr(self.status, 'value') else self.status,
            'enabled': self.enabled,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        tasks = [WorkflowTask.from_dict(t) for t in data.get('tasks', [])]
        triggers = [WorkflowTrigger.from_dict(tr) for tr in data.get('triggers', [])]
        status = WorkflowStatus(data.get('status', 'idle')) if isinstance(data.get('status'), str) else data.get('status', WorkflowStatus.IDLE)
        
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            description=data.get('description', ''),
            tasks=tasks,
            triggers=triggers,
            status=status,
            enabled=data.get('enabled', True),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            tags=data.get('tags', [])
        )
