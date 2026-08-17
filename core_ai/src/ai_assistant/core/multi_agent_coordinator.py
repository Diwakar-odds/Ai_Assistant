import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..agents.registry import AgentRegistry
from ..agents.models import Task, TaskResult, AgentStatus
from ..agents.base_agent import BaseAgent
from .memory_manager import MemoryManager
from .interaction import InteractionManager

class MultiAgentCoordinator:
    """
    Central coordinator for the Multi-Agent System.
    Handles task routing, agent assignment, and progress tracking.
    """
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.memory = MemoryManager()
        self.interaction = InteractionManager()
        self.active_tasks: Dict[str, Task] = {}
        self.task_results: Dict[str, TaskResult] = {}
        
    async def process_command(self, command_text: str) -> Dict[str, Any]:
        """
        Process a user command (placeholder for now)
        In the future, this will use LLM to break down the command.
        """
        # For Phase 1, we just return a simple acknowledgment
        return {
            "status": "processing",
            "message": f"Received command: {command_text} (Decomposition not implemented yet)"
        }
        
    async def assign_task(self, task: Task) -> Optional[str]:
        """
        Assign a task to the best available agent and start execution.
        Returns the agent ID if assigned, None otherwise.
        """
        agent = await self.registry.find_best_agent(task)
        
        if not agent:
            print(f"No suitable agent found for task: {task.description}")
            return None
            
        print(f"Assigning task '{task.description}' to agent {agent.name} ({agent.agent_id})")
        
        # Track task
        self.active_tasks[task.task_id] = task
        agent.status = AgentStatus.WORKING
        agent.current_task = task
        
        return agent.agent_id

    async def execute_task(self, task: Task) -> TaskResult:
        """
        Finds an agent and executes the task immediately (for testing).
        """
        agent_id = await self.assign_task(task)
        if not agent_id:
            return TaskResult(success=False, error="No agent found")
            
        agent = self.registry.get_agent(agent_id)
        
        try:
            start_time = datetime.now()
            result = await agent.execute(task)
            end_time = datetime.now()
            
            result.execution_time = (end_time - start_time).total_seconds()
            self.task_results[task.task_id] = result
            
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            return TaskResult(success=False, error=str(e))
        finally:
            if agent:
                agent.status = AgentStatus.IDLE
                agent.current_task = None
