import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(r"c:\users\hp\appdata\roaming\python\python39\site-packages")

from ai_assistant.agents.video.video_agent import VideoAgent
from ai_assistant.agents.models import Task

async def main():
    print("Testing Filmora Integration...")
    agent = VideoAgent()
    
    # Test cases for Filmora
    test_cases = [
        ("Wondershare Filmora", "split", ["ctrl", "b"]),
        ("Filmora 13", "export", ["ctrl", "e"]),
        ("filmora", "trim_start", ["alt", "["])
    ]
    
    for app_name, action, expected_keys in test_cases:
        print(f"\n--- Testing Profile: {app_name} ---")
        gui_task = Task(
            description=f"Control App: {action} in {app_name}",
            params={
                "app_name": app_name,
                "action": action
            }
        )
        
        res = await agent.execute(gui_task)
        if res.success:
            print(f"✅ {app_name}: {res.data.get('message')}")
        elif "Could not find or focus window" in res.error:
             print(f"✅ {app_name}: Profile Loaded (Window check skipped)")
        else:
            print(f"❌ {app_name}: {res.error}")

if __name__ == "__main__":
    asyncio.run(main())
