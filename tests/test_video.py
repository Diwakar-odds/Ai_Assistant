import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# Force add user site packages
sys.path.append(r"c:\users\hp\appdata\roaming\python\python39\site-packages")

from ai_assistant.agents.video.video_agent import VideoAgent
from ai_assistant.agents.models import Task

async def main():
    print("Testing Video Agent...")
    
    # Ensure dummy video exists
    dummy_video = os.path.abspath("dummy_test.mp4")
    if not os.path.exists(dummy_video):
        print("Dummy video not found! Please run create_dummy_video.py first.")
        return

    agent = VideoAgent()
    
    # 1. Test Editing (Trimming)
    print("\n--- Testing Video Editing (Trim) ---")
    trim_task = Task(
        description="Trim video to first 2 seconds",
        params={
            "input_file": dummy_video,
            "start_time": 0,
            "end_time": 2,
            "output_filename": "trimmed_test.mp4"
        }
    )
    res_trim = await agent.execute(trim_task)
    if res_trim.success:
        print(f"✅ Video Trimming Successful")
        print(f"Output: {res_trim.output_path}")
    else:
        print(f"❌ Video Trimming Failed: {res_trim.error}")

    # 2. Test Audio Extraction
    print("\n--- Testing Audio Extraction ---")
    audio_task = Task(
        description="Extract audio from video",
        params={
            "input_file": dummy_video,
            "output_filename": "extracted_audio.mp3"
        }
    )
    res_audio = await agent.execute(audio_task)
    if res_audio.success:
        print(f"✅ Audio Extraction Successful")
        print(f"Output: {res_audio.output_path}")
    else:
        print(f"❌ Audio Extraction Failed: {res_audio.error}")
        
    print("\n--- Testing Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
