"""
DEPRECATED — This module is no longer used.
Functionality has moved to MemoryRetrieval (core_ai/src/ai_assistant/ai/memory_retrieval.py).
"""
import warnings

class SmartMemoryRetrieval:
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "SmartMemoryRetrieval is deprecated. Use MemoryRetrieval instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        
    def enhance_response_with_memory(self, *args, **kwargs):
        return None
        
    def __getattr__(self, name):
        def _missing(*args, **kwargs):
            return None
        return _missing
