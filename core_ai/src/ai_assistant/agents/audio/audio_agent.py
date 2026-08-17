import asyncio
import os
from typing import Dict, Any, List

from ...models import Task, TaskResult
from ..base_agent import BaseAgent

class AudioAgent(BaseAgent):
    """
    Handles specific audio tasks (Music, SFX, Audio Processing).
    Distinct from CreativeAgent (Speech) and VideoAgent (Editing).
    """
    
    def __init__(self, agent_id: str = "audio_01", config: Dict[str, Any] = None):
        super().__init__(agent_id, config or {})
        self.name = "Audio Agent"
        self.description = "Generates music and processes audio."
        self.capabilities = ["generate_music", "generate_sfx", "clean_audio"]
        
    async def can_handle(self, task: Task) -> bool:
        """Check if task involves audio/music"""
        keywords = ["music", "song", "sound effect", "sfx", "clean audio", "remove noise", "audio track"]
        return any(kw in task.description.lower() for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        """Execute audio tasks"""
        description = task.description.lower()
        
        if "music" in description or "song" in description:
            return await self._generate_music(task)
        elif "sfx" in description or "sound" in description:
            return await self._generate_sfx(task)
        elif "clean" in description or "noise" in description:
            return await self._clean_audio(task)
            
        return TaskResult(success=False, error="Unknown audio task intent")

    async def _generate_music(self, task: Task) -> TaskResult:
        """Generate background music"""
        genre = task.params.get("genre", "lofi")
        duration = task.params.get("duration", 30)
        
        print(f"[{self.name}] 🎵 Generating {genre} music ({duration}s)...")
        # Mock: In reality, call MusicGen or Suno API
        await asyncio.sleep(2)
        
        output_path = os.path.abspath(os.path.join("workspace", "assets", "audio", f"music_{task.task_id}.mp3"))
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Create dummy file
        with open(output_path, 'w') as f:
            f.write("mock audio data")
            
        return TaskResult(
            success=True,
            data={"path": output_path, "message": f"Generated {genre} track"}
        )

    async def _generate_sfx(self, task: Task) -> TaskResult:
        """Generate sound effect"""
        sfx_type = task.params.get("type", "explosion")
        print(f"[{self.name}] 🔊 Generating SFX: {sfx_type}...")
        return TaskResult(success=True, data={"message": "SFX generated"})

    async def _clean_audio(self, task: Task) -> TaskResult:
        """Clean audio file"""
        path = task.params.get("path")
        print(f"[{self.name}] 🎚️ Cleaning noise from: {path}...")
        return TaskResult(success=True, data={"message": "Audio cleaned"})
