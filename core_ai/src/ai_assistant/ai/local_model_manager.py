"""
Local Model Manager (Alias / Wrapper for LocalAIManager)
Forwards to local_ai_manager.py for unified Ollama / GGUF model handling.
"""

from ai_assistant.ai.local_ai_manager import LocalAIManager

LocalModelManager = LocalAIManager

__all__ = ['LocalModelManager', 'LocalAIManager']
