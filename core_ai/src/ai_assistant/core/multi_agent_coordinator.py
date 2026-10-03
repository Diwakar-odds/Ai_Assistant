import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..agents.registry import AgentRegistry
from ..agents.models import Task, TaskResult, AgentStatus
from ..agents.base_agent import BaseAgent
from .memory_manager import MemoryManager
from .interaction import InteractionManager
from ai_assistant.ai.gguf_model_manager import GGUFModelManager

class MultiAgentCoordinator:
    """
    Central coordinator for the Multi-Agent System.
    Uses the local GGUF model to orchestrate and route tasks to the 12 sub-agents.
    """
    
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.memory = MemoryManager()
        self.interaction = InteractionManager()
        self.active_tasks: Dict[str, Task] = {}
        self.task_results: Dict[str, TaskResult] = {}
        self.model_manager = GGUFModelManager()
        
    async def process_command(self, command_text: str) -> Dict[str, Any]:
        """
        Process a user command using the local LLM to break it down 
        and orchestrate it to the correct agent among the 12.
        """
        try:
            print(f"[Orchestrator] 🤔 Analyzing command: '{command_text}'...")
            llm = self.model_manager.get_model()
            
            # Gather all 12 agents' capabilities
            metadata = self.registry.get_all_metadata()
            agents_info = []
            for meta in metadata:
                agents_info.append(f"- ID: {meta.agent_id} | Name: {meta.name} | Capabilities: {', '.join(meta.capabilities)}")
            
            agents_text = "\n".join(agents_info)
            
            prompt = f"<|start_header_id|>system<|end_header_id|>\nYou are the Master Orchestrator Agent. Your job is to route user commands to the most appropriate sub-agent from the 12 available agents.\n\nAvailable Agents:\n{agents_text}\n\nAnalyze the user's command and reply with ONLY a valid JSON object in this exact format:\n{{\n  \"selected_agent_id\": \"the_agent_id\",\n  \"reasoning\": \"why you chose this agent\",\n  \"extracted_task\": \"the specific task instruction\"\n}}\nIf no agent matches, set selected_agent_id to null.<|eot_id|><|start_header_id|>user<|end_header_id|>\n{command_text}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
            
            # Call local LLM
            response = llm(prompt, max_tokens=300, stop=['<|eot_id|>'], echo=False)
            output = response['choices'][0]['text'].strip()
            
            # Parse JSON
            if "```json" in output:
                output = output.split("```json")[1].split("```")[0].strip()
            elif "```" in output:
                output = output.split("```")[1].split("```")[0].strip()
                
            decision = json.loads(output)
            
            agent_id = decision.get("selected_agent_id")
            if not agent_id:
                return {
                    "status": "rejected",
                    "message": f"Orchestrator decision: No suitable agent found. Reasoning: {decision.get('reasoning')}"
                }
                
            print(f"[Orchestrator] 🚀 Routing to Agent '{agent_id}' (Reason: {decision.get('reasoning')})")
            
            # Create Task
            task = Task(
                task_id=str(uuid.uuid4()),
                description=decision.get("extracted_task", command_text),
                params={"original_command": command_text}
            )
            
            # Force execute on the LLM-selected agent
            agent = self.registry.get_agent(agent_id)
            if not agent:
                return {"status": "error", "message": f"Agent {agent_id} could not be loaded."}
                
            self.active_tasks[task.task_id] = task
            agent.status = AgentStatus.WORKING
            agent.current_task = task
            
            # Execute Task
            start_time = datetime.now()
            result = await agent.execute(task)
            end_time = datetime.now()
            
            result.execution_time = (end_time - start_time).total_seconds()
            self.task_results[task.task_id] = result
            
            agent.status = AgentStatus.IDLE
            agent.current_task = None
            
            return {
                "status": "completed" if result.success else "failed",
                "agent_used": agent.name,
                "result": result.data if result.success else result.error
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": f"Orchestration error: {str(e)}"
            }
        
    async def assign_task(self, task: Task) -> Optional[str]:
        """
        Legacy/Direct assignment without LLM orchestration.
        """
        agent = await self.registry.find_best_agent(task)
        if not agent:
            return None
            
        self.active_tasks[task.task_id] = task
        agent.status = AgentStatus.WORKING
        agent.current_task = task
        return agent.agent_id

    async def execute_task(self, task: Task) -> TaskResult:
        """
        Legacy/Direct execution without LLM orchestration.
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
            return TaskResult(success=False, error=str(e))
        finally:
            if agent:
                agent.status = AgentStatus.IDLE
                agent.current_task = None