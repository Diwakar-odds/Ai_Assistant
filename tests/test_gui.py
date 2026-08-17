import asyncio
import os
import sys
import subprocess
import time

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(r"c:\users\hp\appdata\roaming\python\python39\site-packages")

from ai_assistant.agents.video.video_agent import VideoAgent
from ai_assistant.agents.models import Task

async def main():
    print("Testing Video Agent GUI Automation...")
    
    # 1. Launch Notepad
    print("Launching Notepad...")
    try:
        notepad = subprocess.Popen("notepad.exe")
        time.sleep(2) # Wait for launch
    except Exception as e:
        print(f"Failed to launch notepad: {e}")
        return

    agent = VideoAgent()
    
    # 2. Control Notepad
    print("\n--- Testing App Control (data entry) ---")
    gui_task = Task(
        description="Control App: Type Hello World in Notepad",
        params={
            "app_name": "Notepad", # Window title usually contains this
            "text": "Hello User! This is the Video Agent using GUI Automation.\n",
            "action": None 
        }
    )
    
    res_gui = await agent.execute(gui_task)
    
    if res_gui.success:
        print(f"✅ GUI Task Successful: {res_gui.data.get('message')}")
    else:
        print(f"❌ GUI Task Failed: {res_gui.error}")
        
    print("\n--- Closing Notepad (Manual Step for User) ---")
    # notepad.terminate() # Don't terminate, let user see result

if __name__ == "__main__":
    asyncio.run(main())
