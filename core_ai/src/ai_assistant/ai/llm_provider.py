#!/usr/bin/env python3
"""
LLM Provider Abstraction Layer
Supports OpenAI (GPT-4, GPT-3.5), Google Gemini, and local models.
Provides streaming, token counting, and unified interface.
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Generator, Any, Callable, Union
from abc import ABC, abstractmethod
from datetime import datetime
import re
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
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


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo", base_url: Optional[str] = None):
        """Initialize OpenAI provider."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        self.model = model
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        try:
            from openai import OpenAI, APIError
            if self.base_url:
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            else:
                self.client = OpenAI(api_key=self.api_key)
            self.APIError = APIError
        except ImportError:
            raise ImportError("OpenAI package required: pip install openai")
        
        # Token counter
        try:
            import tiktoken
            self.encoder = tiktoken.encoding_for_model(model.split("-")[0])
        except:
            self.encoder = None
    
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a complete response from OpenAI."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2000),
                top_p=kwargs.get("top_p", 1.0),
                presence_penalty=kwargs.get("presence_penalty", 0),
                frequency_penalty=kwargs.get("frequency_penalty", 0),
                tools=kwargs.get("tools"),  # For function calling
                tool_choice=kwargs.get("tool_choice"),
            )
            
            return response.choices[0].message.content
        except self.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return f"Error: {str(e)}"
    
    def stream_response(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """Stream response from OpenAI token-by-token."""
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2000),
                top_p=kwargs.get("top_p", 1.0),
                stream=True,  # Enable streaming
                tools=kwargs.get("tools"),
                tool_choice=kwargs.get("tool_choice"),
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except self.APIError as e:
            logger.error(f"OpenAI streaming error: {e}")
            yield f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            yield f"Error: {str(e)}"
    
    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken."""
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except:
                pass
        # Fallback
        return len(text) // 4


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.5-flash"):
        """Initialize Gemini provider."""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(model)
        except ImportError:
            raise ImportError("Google Generative AI package required: pip install google-generativeai")
        except Exception as e:
            logger.error(f"Gemini initialization failed: {e}")
            raise
    
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response from Gemini."""
        try:
            # Convert messages to Gemini format
            history = []
            for msg in messages[:-1]:  # Everything except last
                if msg["role"] == "system":
                    continue
                history.append({
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [msg["content"]]
                })
            
            # Start chat session
            chat = self.client.start_chat(history=history)
            
            # Send last message with generation config
            last_message = messages[-1]["content"]
            
            # Create generation config
            generation_config = {
                'temperature': kwargs.get("temperature", 0.7),
                'top_p': kwargs.get("top_p", 0.95),
                'top_k': kwargs.get("top_k", 40),
                'max_output_tokens': kwargs.get("max_tokens", 2048)
            }
            
            response = chat.send_message(
                last_message,
                generation_config=generation_config
            )
            
            return response.text
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return f"Error: {str(e)}"
    
    def stream_response(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """Stream response from Gemini."""
        try:
            # Convert messages
            history = []
            for msg in messages[:-1]:
                if msg["role"] == "system":
                    continue
                history.append({
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [msg["content"]]
                })
            
            chat = self.client.start_chat(history=history)
            last_message = messages[-1]["content"]
            
            # Create generation config
            generation_config = {
                'temperature': kwargs.get("temperature", 0.7),
                'top_p': kwargs.get("top_p", 0.95),
                'top_k': kwargs.get("top_k", 40),
                'max_output_tokens': kwargs.get("max_tokens", 2048)
            }
            
            response = chat.send_message(
                last_message,
                stream=True,
                generation_config=generation_config
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini streaming failed: {e}")
            yield f"Error: {str(e)}"
    
    def count_tokens(self, text: str) -> int:
        """Count tokens using Gemini's API."""
        try:
            response = self.client.count_tokens(text)
            return response.total_tokens
        except:
            # Fallback estimate
            return len(text) // 4


class LocalLLMProvider(LLMProvider):
    """Local LLM provider using Ollama or compatible API."""
    
    def __init__(self, api_url: str = "http://localhost:11434", model: str = "llama2"):
        """Initialize local LLM provider."""
        self.api_url = api_url
        self.model = model
        
        try:
            import requests
            self.requests = requests
        except ImportError:
            raise ImportError("requests package required: pip install requests")
    
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response from local LLM."""
        try:
            prompt = self._format_messages(messages)
            
            response = self.requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": kwargs.get("temperature", 0.7),
                    "top_p": kwargs.get("top_p", 0.95),
                },
                timeout=120
            )
            
            if response.status_code == 200:
                return response.json()["response"]
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            logger.error(f"Local LLM generation failed: {e}")
            return f"Error: {str(e)}"
    
    def stream_response(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """Stream response from local LLM."""
        try:
            prompt = self._format_messages(messages)
            
            response = self.requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "temperature": kwargs.get("temperature", 0.7),
                },
                stream=True,
                timeout=120
            )
            
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    yield data.get("response", "")
        except Exception as e:
            logger.error(f"Local LLM streaming failed: {e}")
            yield f"Error: {str(e)}"
    
    def count_tokens(self, text: str) -> int:
        """Estimate tokens for local LLM."""
        # Simple estimation: 1 token â‰ˆ 4 characters
        return len(text) // 4
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages as prompt for local LLM."""
        formatted = ""
        for msg in messages:
            role = msg["role"].upper()
            content = msg["content"]
            formatted += f"{role}: {content}\n\n"
        formatted += "ASSISTANT: "
        return formatted


class OfflineProvider(LLMProvider):
    """Offline LLM provider using local models with fallback strategies."""
    
    def __init__(self, **kwargs):
        """Initialize offline provider with fallback chain."""
        self.offline_llm = None
        self._init_offline_llm()
    
    def _init_offline_llm(self):
        """Initialize offline LLM manager."""
        try:
            from offline_llm_provider import get_offline_llm
            self.offline_llm = get_offline_llm()
            logger.info(f"Offline provider initialized: {self.offline_llm.get_provider_info()}")
        except Exception as e:
            logger.warning(f"Failed to initialize offline LLM: {e}")
            logger.info("Using simple offline fallback")
    
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate response using offline provider."""
        if self.offline_llm:
            return self.offline_llm.generate_response(messages, **kwargs)
        else:
            return "Error: Offline provider not available."
    
    def stream_response(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """Stream response using offline provider."""
        if self.offline_llm:
            yield from self.offline_llm.stream_response(messages, **kwargs)
        else:
            yield "Error: Offline provider not available."
    
    def count_tokens(self, text: str) -> int:
        """Count tokens."""
        if self.offline_llm:
            return self.offline_llm.count_tokens(text)
        return len(text) // 4
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages as prompt."""
        formatted = ""
        for msg in messages:
            role = msg["role"].upper()
            content = msg["content"]
            formatted += f"{role}: {content}\n\n"
        formatted += "ASSISTANT: "
        return formatted


class LLMFactory:
    """Factory for creating LLM providers."""
    
    PROVIDERS = {
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "local": LocalLLMProvider,
        "ollama": LocalLLMProvider,
        "offline": OfflineProvider,
    }
    
    @classmethod
    def create(cls, provider: str = "openai", **kwargs) -> LLMProvider:
        """Create an LLM provider."""
        provider_lower = provider.lower()
        
        if provider_lower not in cls.PROVIDERS:
            available = ", ".join(cls.PROVIDERS.keys())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")
        
        provider_class = cls.PROVIDERS[provider_lower]
        return provider_class(**kwargs)
    
    @classmethod
    def detect_provider(cls) -> tuple[str, str]:
        """Detect available provider using smart network-aware configuration."""
        try:
            from ai_assistant.ai.network_aware_llm import get_optimal_llm_config
            config = get_optimal_llm_config()
            provider = config["provider"]
            model = config["model"]
            
            logger.info(f"Smart provider selection: {provider} ({model})")
            logger.info(f"Network status: {'Online' if config['network_status'] else 'Offline'}")
            
            return (provider, model)
        except Exception as e:
            logger.error(f"Smart provider detection failed: {e}")
            # Fallback to online providers only
            if os.getenv("OPENAI_API_KEY"):
                return ("openai", "gpt-3.5-turbo")
            elif os.getenv("GEMINI_API_KEY"):
                return ("gemini", "gemini-pro")
            else:
                raise RuntimeError("No API keys configured. Please set OPENAI_API_KEY or GEMINI_API_KEY")
    
    @classmethod
    def create_with_fallback(cls, preferred_provider: Optional[str] = None, **kwargs) -> LLMProvider:
        """
        Create provider with automatic fallback to offline.
        
        Args:
            preferred_provider: Preferred provider name
            **kwargs: Additional arguments for provider
        
        Returns:
            LLM provider instance
        """
        provider = preferred_provider
        
        if provider is None:
            provider, model = cls.detect_provider()
            kwargs.setdefault('model', model)
        
        # Try preferred provider first
        try:
            return cls.create(provider, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to create {provider} provider: {e}")
            raise
            
            # Fallback to offline
            # if provider != "offline":
            #     logger.info("Falling back to offline provider")
            #     try:
            #         return cls.create("offline", **kwargs)
            #     except Exception as e2:
            #         logger.error(f"Offline provider also failed: {e2}")
            #         raise


class UnifiedChatInterface:
    """Unified chat interface that abstracts LLM provider."""
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None, use_fallback: bool = True):
        """
        Initialize unified chat interface.
        
        Args:
            provider: Preferred LLM provider
            model: Model to use
            use_fallback: Whether to fallback to offline mode
        """
        if provider is None or model is None:
            detected_provider, detected_model = LLMFactory.detect_provider()
            provider = provider or detected_provider
            model = model or detected_model
        
        logger.info(f"Initializing {provider} with model {model}")
        
        # Try to create provider with fallback support
        if use_fallback:
            self.provider = LLMFactory.create_with_fallback(provider, model=model)
        else:
            self.provider = LLMFactory.create(provider, model=model)
        
        self.provider_name = provider
        self.model = model
        self.conversation_history: List[Dict[str, str]] = []
        self.offline_mode = isinstance(self.provider, OfflineProvider)
        
        if self.offline_mode:
            logger.warning("âš ï¸ Running in offline mode - features may be limited")
    
    def is_offline(self) -> bool:
        """Check if currently in offline mode."""
        return self.offline_mode
    
    def add_system_message(self, content: str):
        """Add system message."""
        self.conversation_history.insert(0, {"role": "system", "content": content})
    
    def add_user_message(self, content: str):
        """Add user message."""
        self.conversation_history.append({"role": "user", "content": content})
    
    def add_assistant_message(self, content: str):
        """Add assistant message."""
        self.conversation_history.append({"role": "assistant", "content": content})
    
    def chat(self, user_message: str, stream: bool = False, **kwargs) -> Union[str, Generator[str, None, None]]:
        """Send a chat message and get response."""
        self.add_user_message(user_message)
        
        if stream:
            return self.provider.stream_response(self.conversation_history, **kwargs)
        else:
            response = self.provider.generate_response(self.conversation_history, **kwargs)
            self.add_assistant_message(response)
            return response
    
    def reset(self):
        """Reset conversation history."""
        system_msg = None
        if self.conversation_history and self.conversation_history[0].get("role") == "system":
            system_msg = self.conversation_history[0]
        
        self.conversation_history = []
        if system_msg:
            self.conversation_history.append(system_msg)


if __name__ == "__main__":
    # Example usage
    try:
        # Auto-detect provider
        chat = UnifiedChatInterface()
        chat.add_system_message("You are a helpful AI assistant.")
        
        # Test non-streaming
        print("Testing non-streaming response:")
        response = chat.chat("What is Python?", stream=False)
        print(f"Response: {response}\n")
        
        # Test streaming
        print("Testing streaming response:")
        for chunk in chat.chat("Tell me a joke", stream=True):
            print(chunk, end="", flush=True)
        print()
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have OPENAI_API_KEY or GEMINI_API_KEY set")

