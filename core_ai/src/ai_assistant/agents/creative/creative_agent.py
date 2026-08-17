import os
import time
import asyncio
from typing import Dict, Any, Optional

from ..models import Task, TaskResult
from ..base_agent import BaseAgent

class CreativeAgent(BaseAgent):
    """
    Agent responsible for generating creative assets:
    - Images (Thumbnails, B-Roll, Art)
    - Audio (Voiceovers, Sound Effects)
    """
    
    def __init__(self, agent_id: str = "creative_01", config: Dict[str, Any] = None):
        super().__init__(agent_id, config or {})
        self.name = "CreativeWorker"
        self.description = "Generates images and audio assets."
        
    async def can_handle(self, task: Task) -> bool:
        """Check if task involves creative generation"""
        keywords = [
            "image", "generate", "create", "art", "picture", "thumbnail", 
            "photo", "voice", "speech", "audio", "narrate", "tts", "sound"
        ]
        return any(kw in task.description.lower() for kw in keywords) and \
               ("video" not in task.description.lower() or "generate" in task.description.lower())

    async def execute(self, task: Task) -> TaskResult:
        """Execute the creative task"""
        description = task.description.lower()
        
        # Detect Intent
        if any(kw in description for kw in ["image", "art", "picture", "thumbnail", "photo"]):
            return await self._handle_image_generation(task)
        elif any(kw in description for kw in ["voice", "speech", "narrate", "tts"]):
            return await self._handle_audio_generation(task)
            
        return TaskResult(success=False, error="Unknown creative request type")

    async def _handle_image_generation(self, task: Task) -> TaskResult:
        """Generate an image (Mock/Simulation for now)"""
        prompt = task.params.get("prompt") or task.description
        size = task.params.get("size", "1024x1024")
        
        print(f"[{self.name}] Generating Image for: '{prompt}' ({size})...")
        
        # Simulation delay
        await asyncio.sleep(2)
        
        # Create a placeholder file to verify output
        output_dir = os.path.abspath(os.path.join("workspace", "assets", "images"))
        os.makedirs(output_dir, exist_ok=True)
        filename = f"generated_image_{int(time.time())}.png"
        output_path = os.path.join(output_dir, filename)
        
        # Create a dummy file
        with open(output_path, "w") as f:
            f.write(f"Fake Image Content for: {prompt}")
            
        return TaskResult(
            success=True, 
            data={
                "message": f"Image generated successfully: {filename}", 
                "path": output_path,
                "preview": "[Image Content Placeholder]"
            }
        )

    async def _handle_audio_generation(self, task: Task) -> TaskResult:
        """Generate audio (Mock/Simulation for now)"""
        text = task.params.get("text") or task.params.get("content") or task.description
        voice = task.params.get("voice", "default_female")
        
        print(f"[{self.name}] Generating Speech: '{text[:20]}...' using {voice}...")
        
        await asyncio.sleep(2)
        
        output_dir = os.path.abspath(os.path.join("workspace", "assets", "audio"))
        os.makedirs(output_dir, exist_ok=True)
        filename = f"generated_audio_{int(time.time())}.mp3"
        output_path = os.path.join(output_dir, filename)
        
        with open(output_path, "w") as f:
            f.write(f"Fake Audio Content: {text}")
            
        return TaskResult(
            success=True, 
            data={
                "message": f"Audio generated successfully: {filename}",
                "path": output_path
            }
        )
