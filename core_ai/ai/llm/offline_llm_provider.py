#!/usr/bin/env python3
"""
Offline LLM Provider
Provides offline AI capabilities using simple fallback when primary fails.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Generator, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class OfflineLLMProvider(ABC):
    """Abstract base class for offline LLM providers."""
    
    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a complete response."""
        pass
    
    @abstractmethod
    def stream_response(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """Stream a response token-by-token."""
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass

class SimpleOfflineProvider(OfflineLLMProvider):
    """Simple fallback provider for basic text matching and rule-based responses."""
    
    def __init__(self):
        """Initialize simple offline provider."""
        self.available = True
        self.knowledge_base = self._init_knowledge_base()
    
    def _init_knowledge_base(self) -> Dict[str, str]:
        """Initialize basic knowledge base for common queries."""
        return {
            "hello": "Hello! I'm your offline assistant. How can I help you?",
            "hi": "Hi there! I'm running in offline mode. What would you like to know?",
            "how are you": "I'm running offline, but functioning well! How can I assist you?",
            "what's your name": "I'm Pulsar Assistant, your personal AI helper.",
            "time": "I don't have real-time capabilities in offline mode, but I can help with other things.",
            "date": "I don't have real-time capabilities in offline mode.",
            "weather": "I can't check weather in offline mode, but I can help with other tasks.",
            "help": self._get_help_text(),
        }
    
    def _get_help_text(self) -> str:
        """Get help text."""
        return """
Offline Assistant Help:
- I can answer general knowledge questions
- I can help with text processing and analysis
- I can assist with file operations
- I can perform local automations
- Internet-dependent features (weather, news, etc.) are not available

What would you like help with?
"""
    
    def is_available(self) -> bool:
        """Simple provider is always available."""
        return True
    
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response using simple rule-based matching."""
        if not messages:
            return "No query provided."
        
        # Get the last user message
        last_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "").lower().strip()
                break
        
        # Try exact match first
        if last_message in self.knowledge_base:
            return self.knowledge_base[last_message]
        
        # Try keyword matching
        for key, response in self.knowledge_base.items():
            if key in last_message:
                return response
        
        # Default response
        return (
            "I'm running in simple offline mode. I can help with basic tasks, but for complex "
            "AI conversations, I need to be connected to the internet. "
            f"Your query was: '{last_message}'"
        )
    
    def stream_response(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """Stream response (returns full response)."""
        response = self.generate_response(messages, **kwargs)
        yield response
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count."""
        return len(text) // 4

class OfflineLLMManager:
    """Manager for offline LLM providers with fallback chain."""
    
    def __init__(self):
        """Initialize with multiple offline providers."""
        self.providers = []
        self.current_provider = None
        
        # Try to initialize providers in order of preference
        self._init_providers()
    
    def _init_providers(self):
        """Initialize available providers."""
        # Simple provider as fallback
        simple = SimpleOfflineProvider()
        self.providers.append(simple)
        logger.info("Simple offline provider available (fallback)")
        
        # Set current provider
        if self.providers:
            self.current_provider = self.providers[0]
            logger.info(f"Using provider: {type(self.current_provider).__name__}")
    
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response with fallback chain."""
        for provider in self.providers:
            try:
                if provider.is_available():
                    self.current_provider = provider
                    return provider.generate_response(messages, **kwargs)
            except Exception as e:
                logger.warning(f"Provider {type(provider).__name__} failed: {e}")
                continue
        
        return "Error: No offline provider available."
    
    def stream_response(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """Stream response with fallback chain."""
        for provider in self.providers:
            try:
                if provider.is_available():
                    self.current_provider = provider
                    yield from provider.stream_response(messages, **kwargs)
                    return
            except Exception as e:
                logger.warning(f"Provider {type(provider).__name__} failed: {e}")
                continue
        
        yield "Error: No offline provider available."
    
    def count_tokens(self, text: str) -> int:
        """Count tokens using current provider."""
        if self.current_provider:
            return self.current_provider.count_tokens(text)
        return len(text) // 4
    
    def get_provider_info(self) -> Dict[str, Any]:
        """Get information about available providers."""
        return {
            "current": type(self.current_provider).__name__ if self.current_provider else None,
            "available_providers": [type(p).__name__ for p in self.providers],
            "count": len(self.providers)
        }

# Convenience function
def get_offline_llm() -> OfflineLLMManager:
    """Get the offline LLM manager instance."""
    return OfflineLLMManager()
