import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(r"c:\users\hp\appdata\roaming\python\python39\site-packages")

from ai_assistant.agents.video.video_agent import VideoAgent
from ai_assistant.agents.models import Task

async def main():
    print("Testing Video Agent Training Mode...")
    agent = VideoAgent()
    
    # 1. Start Training
    print("\n--- Starting Session ---")
    res_start = await agent.execute(Task(
        description="Start training mode",
        params={"mode": "start", "profile": "test_workflow"}
    ))
    print(f"Start: {res_start.success} - {res_start.data.get('message')}")
    
    # 2. Add Action
    print("\n--- Adding Action ---")
    res_add = await agent.execute(Task(
        description="Add training action",
        params={"mode": "add", "action_type": "hotkey", "params": {"keys": ["ctrl", "c"]}}
    ))
    print(f"Add: {res_add.success} - {res_add.data.get('message')}")

    # 3. Save Workflow
    print("\n--- Saving Workflow ---")
    res_save = await agent.execute(Task(
        description="Save training workflow",
        params={"mode": "save"}
    ))
    if res_save.success:
        print(f"✅ Save Successful: {res_save.data.get('message')}")
    else:
        print(f"❌ Save Failed: {res_save.error}")

if __name__ == "__main__":
    asyncio.run(main())
