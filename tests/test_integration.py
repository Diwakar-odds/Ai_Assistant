import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_assistant.agents.loader import AgentLoader
from ai_assistant.core.multi_agent_coordinator import MultiAgentCoordinator
from ai_assistant.agents.models import Task

async def main():
    print("--- Starting Full Integration Test ---")
    
    # 1. Load System
    print("Loading Agents...")
    registry = AgentLoader.load_all_agents()
    coordinator = MultiAgentCoordinator(registry)
    
    agents = registry.get_all_agents()
    print(f"Loaded {len(agents)} agents: {[a.name for a in agents]}")
    
    # 2. Sequential Task Execution
    
    # Task A: Research
    print("\n[Mock User]: 'Research AI Agents'")
    task_research = Task(
        description="Research AI Agents history", 
        params={"query": "history of AI agents", "num_results": 1}
    )
    res_research = await coordinator.execute_task(task_research)
    print(f"Research Result: {'✅' if res_research.success else '❌'}")
    
    # Task B: Write
    print("\n[Mock User]: 'Write a summary'")
    task_write = Task(
        description="Write a summary about AI Agents",
        params={"topic": "AI Agents History", "type": "article", "filename": "history.md"}
    )
    res_write = await coordinator.execute_task(task_write)
    print(f"Writer Result: {'✅' if res_write.success else '❌'}")
    
    # Task C: Productivity
    print("\n[Mock User]: 'Create a presentation'")
    task_ppt = Task(
        description="Create a PPT about AI",
        params={
            "title": "AI History",
            "slides": [{"title": "Intro", "content": "AI is old."}],
            "filename": "history.pptx"
        }
    )
    res_ppt = await coordinator.execute_task(task_ppt)
    print(f"Productivity Result: {'✅' if res_ppt.success else '❌'}")
    
    print("\n--- Integration Test Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
