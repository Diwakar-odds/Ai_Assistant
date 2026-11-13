import json
import os
from typing import Any, Dict, Optional

class MemoryManager:
    """
    Manages shared context and memory for the agent system.
    Persists data to a JSON file.
    """
    
    def __init__(self, storage_path: str = "workspace/memory.json"):
        self.storage_path = storage_path
        self.memory: Dict[str, Any] = {}
        self._load()

    def _load(self):
        """Load memory from disk"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    self.memory = json.load(f)
            except json.JSONDecodeError:
                self.memory = {}
                
    def _save(self):
        """Save memory to disk"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w') as f:
            json.dump(self.memory, f, indent=2)

    def set(self, key: str, value: Any, save: bool = True):
        """Set a value in memory"""
        self.memory[key] = value
        if save:
            self._save()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from memory"""
        return self.memory.get(key, default)

    def delete(self, key: str):
        """Remove a key from memory"""
        if key in self.memory:
            del self.memory[key]
            self._save()

    def list_keys(self) -> list:
        """List all keys"""
        return list(self.memory.keys())
        
    def clear(self):
        """Clear all memory"""
        self.memory = {}
        self._save()
