#!/usr/bin/env python3
"""
Offline LLM Provider
Provides offline AI capabilities using local models without requiring internet connectivity.
Supports:
- Ollama (llama2, mistral, neural-chat, etc.)
- Hugging Face transformers (BERT, DistilBERT, etc.)
- Local embeddings
"""

import os
import json
import logging
import re
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


class OllamaProvider(OfflineLLMProvider):
    """Ollama local model provider - requires Ollama to be installed and running."""
    
    def __init__(self, model: str = "llama2", host: str = "http://localhost:11434"):
        """
        Initialize Ollama provider.
        
        Args:
            model: Model name (llama2, mistral, neural-chat, etc.)
            host: Ollama server host (default: http://localhost:11434)
        """
        self.model = model
        self.host = host
        self.available = False
        
        try:
            import requests
            self.requests = requests
            self._check_availability()
        except ImportError:
            logger.error("requests library required for Ollama. Install with: pip install requests")
    
    def _check_availability(self) -> bool:
        """Check if Ollama server is running and model is available."""
        try:
            response = self.requests.get(f"{self.host}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]
                self.available = self.model in model_names or any(
                    self.model in m for m in model_names
                )
                if self.available:
                    logger.info(f"✅ Ollama model '{self.model}' is available")
                else:
                    logger.warning(f"⚠️ Model '{self.model}' not found. Available models: {model_names}")
            else:
                logger.warning(f"Ollama server returned status {response.status_code}")
        except self.requests.exceptions.ConnectionError:
            logger.warning(
                f"❌ Cannot connect to Ollama at {self.host}. "
                "Make sure Ollama is installed and running. "
                "Download from: https://ollama.ai"
            )
        except Exception as e:
            logger.warning(f"Error checking Ollama availability: {e}")
        
        return self.available
    
    def is_available(self) -> bool:
        """Check if Ollama is available."""
        return self.available or self._check_availability()
    
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response using Ollama."""
        if not self.is_available():
            return "Error: Ollama is not available. Please install and run Ollama."
        
        try:
            # Convert messages to prompt format
            prompt = self._format_prompt(messages)
            
            response = self.requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": kwargs.get("temperature", 0.7),
                },
                timeout=300  # 5 minutes timeout for generation
            )
            
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            else:
                logger.error(f"Ollama error: {response.text}")
                return f"Error: Ollama request failed ({response.status_code})"
        except self.requests.exceptions.Timeout:
            return "Error: Ollama request timed out. Try again."
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return f"Error: {str(e)}"
    
    def stream_response(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """Stream response from Ollama token-by-token."""
        if not self.is_available():
            yield "Error: Ollama is not available. Please install and run Ollama."
            return
        
        try:
            prompt = self._format_prompt(messages)
            
            response = self.requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "temperature": kwargs.get("temperature", 0.7),
                },
                timeout=300,
                stream=True
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        data = json.loads(line)
                        if data.get("response"):
                            yield data["response"]
            else:
                yield f"Error: Ollama request failed ({response.status_code})"
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            yield f"Error: {str(e)}"
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)."""
        # Ollama tokens are roughly 1 token per 4 characters
        return len(text) // 4
    
    def _format_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Format messages into a prompt string."""
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                prompt += f"System: {content}\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n"
            else:
                prompt += f"User: {content}\n"
        
        prompt += "Assistant: "
        return prompt


class TransformersProvider(OfflineLLMProvider):
    """Hugging Face Transformers provider for offline local models."""
    
    def __init__(self, model: str = "distilbert-base-uncased-finetuned-sst-2-english"):
        """
        Initialize Transformers provider.
        
        Args:
            model: Hugging Face model ID
        """
        self.model = model
        self.pipeline = None
        self.available = False
        
        try:
            from transformers import pipeline
            self._init_pipeline(pipeline)
        except ImportError:
            logger.error(
                "transformers library required. Install with: "
                "pip install transformers torch"
            )
    
    def _init_pipeline(self, pipeline_fn):
        """Initialize the transformation pipeline."""
        try:
            logger.info(f"Loading model: {self.model}")
            self.pipeline = pipeline_fn("text-generation", model=self.model)
            self.available = True
            logger.info(f"✅ Model '{self.model}' loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load model: {e}")
            logger.info("Models will be downloaded on first use (requires internet)")
    
    def is_available(self) -> bool:
        """Check if the model is available."""
        return self.available
    
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response using transformers."""
        if not self.is_available():
            return "Error: Model is not available. Loading on first use."
        
        try:
            prompt = self._format_prompt(messages)
            
            result = self.pipeline(
                prompt,
                max_length=kwargs.get("max_tokens", 512),
                temperature=kwargs.get("temperature", 0.7),
                do_sample=True
            )
            
            return result[0]["generated_text"].replace(prompt, "").strip()
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return f"Error: {str(e)}"
    
    def stream_response(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """Stream is not supported for transformers - returns full response."""
        response = self.generate_response(messages, **kwargs)
        yield response
    
    def count_tokens(self, text: str) -> int:
        """Estimate token count."""
        return len(text) // 4
    
    def _format_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Format messages into a prompt string."""
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                prompt += f"System: {content}\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n"
            else:
                prompt += f"User: {content}\n"
        
        prompt += "Assistant: "
        return prompt


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
            "what's your name": "I'm YourDaddy Assistant, your personal AI helper.",
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
        # Try Ollama first (best quality)
        ollama = OllamaProvider()
        if ollama.is_available():
            self.providers.append(ollama)
            logger.info("✅ Ollama provider available")
        
        # Try Transformers
        try:
            transformers = TransformersProvider()
            self.providers.append(transformers)
            logger.info("✅ Transformers provider available")
        except:
            pass
        
        # Simple provider as fallback
        simple = SimpleOfflineProvider()
        self.providers.append(simple)
        logger.info("✅ Simple offline provider available (fallback)")
        
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
