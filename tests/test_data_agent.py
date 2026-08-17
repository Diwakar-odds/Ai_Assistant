import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ai_assistant.agents.loader import AgentLoader
from ai_assistant.agents.models import Task

async def main():
    print("Testing Data Analyst Agent...")
    
    registry = AgentLoader.load_all_agents()
    
    # Test Chart Generation
    task_chart = Task(
        description="Create a bar chart of sales data",
        params={
            "type": "bar", 
            "title": "Q1 Sales",
            "data": [
                {"Month": "Jan", "Sales": 100},
                {"Month": "Feb", "Sales": 150},
                {"Month": "Mar", "Sales": 120}
            ]
        }
    )
    
    agent = await registry.find_best_agent(task_chart)
    if agent and "Data" in agent.name:
        print(f"✅ Found Data Agent: {agent.name}")
        res = await agent.execute(task_chart)
        if res.success:
            print(f"✅ Chart Task Success: {res.data['message']}")
        else:
            print(f"❌ Chart Task Failed: {res.error}")
    else:
        print(f"❌ Could not find Data Agent. Found: {agent}")

if __name__ == "__main__":
    asyncio.run(main())
