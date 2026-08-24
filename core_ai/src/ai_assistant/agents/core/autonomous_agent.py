import os
from typing import Dict, Any, List

from ..base_agent import BaseAgent
from ..models import Task, TaskResult
from ...auto_learning_router import LearningDataRouter

class AutonomousAgent(BaseAgent):
    """
    Replicates the 'hermes-agent' autonomous learning loop:
    1. Observes conversations
    2. Routes them to the LearningDataRouter for persistence
    3. Proposes new skills/knowledge based on history
    """
    
    def __init__(self, agent_id: str = "autonomous-001", config: Dict[str, Any] = None):
        super().__init__(agent_id, config or {})
        self.name = "Autonomous Learning Agent"
        self.category = "core"
        self.capabilities = [
            "memory_persistence",
            "behavior_learning",
            "skill_generation"
        ]
        
        # Initialize the learning router
        self.router = LearningDataRouter()
        
    async def can_handle(self, task: Task) -> bool:
        """
        Check if task involves memory, learning, or reflection.
        Also acts as a passive listener for general commands if hooked up correctly.
        """
        keywords = ["remember", "learn", "reflect", "what did i say", "my preferences", "save this"]
        return any(kw in task.description.lower() for kw in keywords)
    
    async def execute(self, task: Task) -> TaskResult:
        """Execute the memory/learning task"""
        try:
            print(f"[{self.name}] Processing learning task: {task.description}")
            
            # Extract intent
            desc = task.description.lower()
            
            if "remember" in desc or "save this" in desc:
                # Force route as high-importance knowledge
                self.router.route_conversation(
                    speaker="user",
                    content=task.description,
                    category="command",
                    importance=5, # High importance for explicit memory
                    success=True
                )
                return TaskResult(
                    success=True,
                    data={"message": "Memory explicitly saved to Personal Knowledge Graph."}
                )
                
            elif "reflect" in desc or "what did i say" in desc:
                # Retrieve from knowledge graph or conversation clusterer
                stats = self.router.get_routing_stats()
                # If we had a direct query method on knowledge_graph, we'd call it here.
                # For now, we return stats to prove the router is active.
                return TaskResult(
                    success=True,
                    data={
                        "message": "Reflection complete.",
                        "learning_stats": stats
                    }
                )
                
            else:
                # Default passive observation
                self.router.route_conversation(
                    speaker="user",
                    content=task.description,
                    category="general",
                    importance=3,
                    success=True
                )
                return TaskResult(
                    success=True,
                    data={"message": "Observation logged to Learning Loop."}
                )
            
        except Exception as e:
            return TaskResult(success=False, error=str(e))
            
    def passive_observe(self, speaker: str, content: str, category: str = "general"):
        """
        Can be called by the main chat loop to constantly feed data 
        into the agent without explicitly treating it as a task.
        """
        self.router.route_conversation(
            speaker=speaker,
            content=content,
            category=category,
            importance=3,
            success=True
        )