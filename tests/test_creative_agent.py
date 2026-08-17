import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(r"c:\users\hp\appdata\roaming\python\python39\site-packages")

from ai_assistant.agents.loader import AgentLoader
from ai_assistant.agents.models import Task

async def main():
    print("Testing Creative Agent Integration...")
    
    # 1. Load Registry
    registry = AgentLoader.load_all_agents()
    print("Agents Loaded:", [a.name for a in registry.get_all_agents()])
    
    # 2. Find Agent
    creative = registry.get_agent("creative") # Assuming ID is set via name usually, let's check capabilities
    # Wait, BaseAgent usually generates ID from name or similar. 
    # Let's find by capability.
    
    # Actually, let's just use find_best_agent
    task_img = Task(description="Generate an image of a futuristic city")
    agent_img = await registry.find_best_agent(task_img)
    
    if agent_img and "Creative" in agent_img.name:
         print(f"\n✅ Found qualified agent for Image: {agent_img.name}")
         res = await agent_img.execute(task_img)
         if res.success:
             print(f"✅ Image Task Success: {res.data['message']}")
         else:
             print(f"❌ Image Task Failed: {res.error}")
    else:
         print(f"❌ Could not find Creative Agent for image task. Found: {agent_img}")

    # 3. Test Audio
    task_audio = Task(description="Generate voiceover for this script")
    agent_audio = await registry.find_best_agent(task_audio)
    
    if agent_audio and "Creative" in agent_audio.name:
         print(f"\n✅ Found qualified agent for Audio: {agent_audio.name}")
         res = await agent_audio.execute(task_audio)
         if res.success:
             print(f"✅ Audio Task Success: {res.data['message']}")
         else:
             print(f"❌ Audio Task Failed: {res.error}")
    else:
         print(f"❌ Could not find Creative Agent for audio task.")

if __name__ == "__main__":
    asyncio.run(main())
