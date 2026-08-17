from typing import Dict, List, Optional, Type, Callable, Any
from dataclasses import dataclass
from .base_agent import BaseAgent
from .models import Task

@dataclass
class AgentMetadata:
    """Metadata for a lazy-loaded agent"""
    agent_id: str
    name: str
    description: str
    capabilities: List[str]
    status: str = "standby"  # standby, active, error

class AgentRegistry:
    """
    Manages all available agents and their capabilities with lazy loading support
    """
    
    def __init__(self):
        self._active_agents: Dict[str, BaseAgent] = {}
        self._definitions: Dict[str, AgentMetadata] = {}
        self._factories: Dict[str, Callable[[], BaseAgent]] = {}
        self._capabilities: Dict[str, List[str]] = {}  # capability -> agent_ids
        
    def register_agent(self, agent: BaseAgent):
        """Register an already instantiated agent (legacy support)"""
        # Create metadata from instance
        metadata = AgentMetadata(
            agent_id=agent.agent_id,
            name=agent.name,
            description=agent.description,
            capabilities=agent.capabilities,
            status="active"
        )
        self._definitions[agent.agent_id] = metadata
        self._active_agents[agent.agent_id] = agent
        self._register_capabilities(agent.agent_id, agent.capabilities)
        print(f"Registered active agent: {agent.name} ({agent.agent_id})")

    def register_agent_definition(self, metadata: AgentMetadata, factory: Callable[[], BaseAgent]):
        """Register an agent definition for lazy loading"""
        self._definitions[metadata.agent_id] = metadata
        self._factories[metadata.agent_id] = factory
        self._register_capabilities(metadata.agent_id, metadata.capabilities)
        print(f"Registered agent definition: {metadata.name} ({metadata.agent_id})")

    def _register_capabilities(self, agent_id: str, capabilities: List[str]):
        """Helper to map capabilities"""
        for cap in capabilities:
            if cap not in self._capabilities:
                self._capabilities[cap] = []
            if agent_id not in self._capabilities[cap]:
                self._capabilities[cap].append(agent_id)

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID, instantiating if necessary"""
        # Return existing if active
        if agent_id in self._active_agents:
            return self._active_agents[agent_id]
            
        # Instantiate if defined
        if agent_id in self._factories:
            try:
                print(f"🚀 Lazy loading agent: {agent_id}...")
                factory = self._factories[agent_id]
                agent = factory()
                
                # Update status
                self._active_agents[agent_id] = agent
                if agent_id in self._definitions:
                    self._definitions[agent_id].status = "active"
                
                print(f"✅ Agent {agent_id} loaded successfully")
                return agent
            except Exception as e:
                print(f"❌ Failed to lazy load agent {agent_id}: {e}")
                if agent_id in self._definitions:
                    self._definitions[agent_id].status = "error"
                return None
                
        return None
        
    def get_all_agents(self) -> List[BaseAgent]:
        """Get all currently ACTIVE agents"""
        return list(self._active_agents.values())
        
    def get_all_metadata(self) -> List[AgentMetadata]:
        """Get metadata for ALL agents (active and standby)"""
        return list(self._definitions.values())
        
    def find_agents_by_capability(self, capability: str) -> List[str]:
        """Find agent IDs that have a specific capability"""
        return self._capabilities.get(capability, [])
        
    async def find_best_agent(self, task: Task) -> Optional[BaseAgent]:
        """Find the best agent for a given task (may trigger load)"""
        # This is a complex logic that might need to inspect metadata first
        # For now, we search definitions
        candidates = []
        for agent_id, meta in self._definitions.items():
            # Simple keyword matching on capabilities for now
            # In a real system, we might need to load them to ask if they can handle it,
            # OR rely on metadata descriptions.
            # Lazy approach: Check capabilities metadata
            if any(cap in task.description.lower() for cap in meta.capabilities):
                candidates.append(agent_id)
                
        if not candidates:
            # Fallback to checking all active agents
            for agent in self._active_agents.values():
                if await agent.can_handle(task):
                     return agent
            return None
            
        # Load the best candidate
        # For now, pick first
        return self.get_agent(candidates[0])
