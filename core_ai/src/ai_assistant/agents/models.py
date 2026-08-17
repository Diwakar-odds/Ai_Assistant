from __future__ import annotations
from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"

class Task(BaseModel):
    description: str
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    params: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    priority: int = 1

class TaskResult(BaseModel):
    success: bool
    output_path: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0

class VerificationResult(BaseModel):
    is_valid: bool
    score: float = 0.0
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)

class ProofreadResult(BaseModel):
    errors: List[str]
    suggestions: List[str]
    quality_score: float
