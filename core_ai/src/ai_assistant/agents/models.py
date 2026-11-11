from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, Field


class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    BUSY = "busy"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"
    OFFLINE = "offline"


class VerificationResult(BaseModel):
    is_valid: bool
    score: float = 0.0
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class ProofreadResult(BaseModel):
    errors: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    quality_score: float = 1.0


class Task(BaseModel):
    description: str
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    params: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    priority: int = 1
    target_agent_id: Optional[str] = None
    required_capabilities: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    chain_id: Optional[str] = None
    timeout: float = 120.0
    max_retries: int = 1
    requires_confirmation: bool = False


class TaskResult(BaseModel):
    success: bool
    output_path: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    verification: Optional[VerificationResult] = None
    artifacts: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
