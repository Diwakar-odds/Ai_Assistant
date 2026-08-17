from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import time

from .models import Task, TaskResult, AgentStatus, VerificationResult, ProofreadResult

class BaseAgent(ABC):
    """Base class for all AI agents"""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        self.agent_id = agent_id
        self.name = ""
        self.category = ""
        self.capabilities: List[str] = []
        self.status = AgentStatus.IDLE
        self.config = config
        
        # Tracking
        self.current_task: Optional[Task] = None
        self.task_history: List[Task] = []
        
        # VLM and LLM (to be initialized by subclasses or passed in config)
        self.vlm = None
        self.llm = None
        
    @abstractmethod
    async def can_handle(self, task: Task) -> bool:
        """Check if agent can handle this task"""
        pass
    
    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """Execute the assigned task"""
        pass
    
    async def verify(self, result: TaskResult) -> VerificationResult:
        """Verify task completion using VLM - default implementation"""
        # Default implementation returns success if result was successful
        # Subclasses should override with actual VLM verification
        return VerificationResult(is_valid=result.success, score=1.0 if result.success else 0.0)
    
    async def proofread(self, output_path: str) -> ProofreadResult:
        """VLM-based proofreading - default no-op"""
        return ProofreadResult(errors=[], suggestions=[], quality_score=1.0)
