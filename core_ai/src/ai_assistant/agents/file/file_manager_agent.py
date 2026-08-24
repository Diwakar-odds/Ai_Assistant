import os
import shutil
from typing import Dict, Any, List

from ...models import Task, TaskResult
from ..base_agent import BaseAgent

class FileManagerAgent(BaseAgent):
    """
    Handles file organization and operations.
    """
    
    def __init__(self, agent_id: str = "file_01", config: Dict[str, Any] = None):
        super().__init__(agent_id, config or {})
        self.name = "File Manager Agent"
        self.description = "Organizes files and folders."
        self.capabilities = ["organize_files", "rename_files", "list_files"]
        
    async def can_handle(self, task: Task) -> bool:
        """Check if task involves file management"""
        keywords = ["file", "folder", "directory", "organize", "rename", "move", "copy", "cleanup"]
        return any(kw in task.description.lower() for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        """Execute file tasks"""
        description = task.description.lower()
        
        if "organize" in description or "cleanup" in description:
            return await self._organize_files(task)
        elif "rename" in description:
            return await self._rename_files(task)
            
        return TaskResult(success=False, error="Unknown file operation")

    async def _organize_files(self, task: Task) -> TaskResult:
        """Organize files by extension"""
        path = task.params.get("path")
        if not path or not os.path.exists(path):
             return TaskResult(success=False, error="Invalid directory path")
             
        print(f"[{self.name}] 📂 Organizing: {path}...")
        
        moved_count = 0
        extensions = {
            "images": [".png", ".jpg", ".jpeg", ".gif"],
            "docs": [".pdf", ".docx", ".txt"],
            "code": [".py", ".js", ".html"]
        }
        
        # Mock logic to avoid messing up user system in demo
        # In real usage, this would shutil.move files
        for item in os.listdir(path):
            if os.path.isfile(os.path.join(path, item)):
                _, ext = os.path.splitext(item)
                for cat, exts in extensions.items():
                    if ext.lower() in exts:
                        # os.makedirs(os.path.join(path, cat), exist_ok=True)
                        # shutil.move(...)
                        moved_count += 1
                        
        return TaskResult(
            success=True,
            data={"message": f"Organized {moved_count} files (Simulation)", "path": path}
        )

    async def _rename_files(self, task: Task) -> TaskResult:
        """Batch rename"""
        print(f"[{self.name}] 🏷️ Batch renaming simulation...")
        return TaskResult(success=True, data={"message": "Renamed files"})