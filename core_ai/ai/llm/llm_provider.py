# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

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

logger = get_logger(__name__, log_category="app")


LOCAL_PROVIDERS = frozenset({"gguf", "local", "offline"})


def is_local_provider(provider: Optional[str]) -> bool:
    """Return True if the provider name refers to a local/offline inference backend."""
    if not provider:
        return False
    return str(provider).strip().lower() in LOCAL_PROVIDERS


def _read_generation_defaults() -> tuple[float, int]:
    """Read temperature & max_tokens from central settings_manager safely."""
    import sys
    from pathlib import Path
    try:
        backend_dir = str(Path(__file__).resolve().parents[4] / 'backend')
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from settings_manager import get_temperature, get_max_tokens
        return float(get_temperature()), int(get_max_tokens())
    except Exception:
        return 0.7, 1024


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
        if not api_key:
            try:
                import sys
                from pathlib import Path
                backend_dir = str(Path(__file__).resolve().parents[4] / 'backend')
                if backend_dir not in sys.path:
                    sys.path.insert(0, backend_dir)
                from settings_manager import get_api_key
                api_key = get_api_key("openai")
            except Exception:
                api_key = None
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
            import sys
            from pathlib import Path
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'backend'))
                from settings_manager import get_temperature, get_max_tokens
                default_temp = get_temperature()
                default_max = get_max_tokens()
            except ImportError:
                default_temp = 0.7
                default_max = 2000

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", default_temp),
                max_tokens=kwargs.get("max_tokens", default_max),
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
        if not api_key:
            try:
                import sys
                from pathlib import Path
                backend_dir = str(Path(__file__).resolve().parents[4] / 'backend')
                if backend_dir not in sys.path:
                    sys.path.insert(0, backend_dir)
                from settings_manager import get_api_key
                api_key = get_api_key("gemini")
            except Exception:
                api_key = None
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
            system_prompt = "\n\n".join([m["content"] for m in messages if m.get("role") == "system"])
            non_system = [m for m in messages if m.get("role") != "system"]
            if not non_system:
                non_system = [{"role": "user", "content": system_prompt}]
                system_prompt = ""
            elif system_prompt:
                first_msg = dict(non_system[0])
                first_msg["content"] = f"[System Instructions & Context]\n{system_prompt}\n\n{first_msg['content']}"
                non_system = [first_msg] + non_system[1:]

            # Convert messages to Gemini format
            history = []
            for msg in non_system[:-1]:  # Everything except last
                history.append({
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [msg["content"]]
                })
            
            # Start chat session
            chat = self.client.start_chat(history=history)
            
            # Send last message with generation config
            last_message = non_system[-1]["content"]
            
            # Create generation config
            import sys
            from pathlib import Path
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'backend'))
                from settings_manager import get_temperature, get_max_tokens
                default_temp = get_temperature()
                default_max = get_max_tokens()
            except ImportError:
                default_temp = 0.7
                default_max = 2048

            generation_config = {
                'temperature': kwargs.get("temperature", default_temp),
                'top_p': kwargs.get("top_p", 0.95),
                'top_k': kwargs.get("top_k", 40),
                'max_output_tokens': kwargs.get("max_tokens", default_max)
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
            system_prompt = "\n\n".join([m["content"] for m in messages if m.get("role") == "system"])
            non_system = [m for m in messages if m.get("role") != "system"]
            if not non_system:
                non_system = [{"role": "user", "content": system_prompt}]
                system_prompt = ""
            elif system_prompt:
                first_msg = dict(non_system[0])
                first_msg["content"] = f"[System Instructions & Context]\n{system_prompt}\n\n{first_msg['content']}"
                non_system = [first_msg] + non_system[1:]

            # Convert messages
            history = []
            for msg in non_system[:-1]:
                history.append({
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [msg["content"]]
                })
            
            chat = self.client.start_chat(history=history)
            last_message = non_system[-1]["content"]
            
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


class GGUFProvider(LLMProvider):
    """Local GGUF model provider using llama_cpp via singleton manager."""

    def __init__(self, **kwargs):
        """Initialize GGUF provider with optional requested model name."""
        try:
            from ai_assistant.ai.gguf_model_manager import gguf_manager
        except ImportError:
            from src.ai_assistant.ai.gguf_model_manager import gguf_manager

        self._mgr = gguf_manager
        requested_model = kwargs.get("model")
        self.llm = gguf_manager.get_model(model_name=requested_model)
        self.model = (
            gguf_manager.model_path.stem
            if getattr(gguf_manager, "model_path", None)
            else (requested_model or "pulsar-final-q4_k_m")
        )

    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for Llama 3 Instruct."""
        formatted = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
        formatted += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        return formatted

    def _estimate_tokens(self, llm: Any, text: str) -> int:
        try:
            return len(llm.tokenize(text.encode("utf-8"), add_bos=False)) + 6
        except Exception:
            return max(1, len(text) // 3) + 6

    def _prepare_messages_and_limits(
        self,
        llm: Any,
        messages: List[Dict[str, str]],
        requested_max_tokens: int,
    ) -> tuple[List[Dict[str, str]], int]:
        """Deduplicate system messages and trim oldest history to stay safely within n_ctx."""
        try:
            n_ctx = int(llm.n_ctx()) if callable(getattr(llm, "n_ctx", None)) else 2048
        except Exception:
            n_ctx = 2048

        system_parts: List[str] = []
        non_system: List[Dict[str, str]] = []
        for msg in messages or []:
            if not isinstance(msg, dict):
                continue
            role = str(msg.get("role", "user")).strip().lower() or "user"
            content = str(msg.get("content", "") or "")
            if not content:
                continue
            if role == "system":
                if content not in system_parts:
                    system_parts.append(content)
            else:
                non_system.append({"role": role, "content": content})

        if not non_system and system_parts:
            non_system = [{"role": "user", "content": system_parts.pop(0)}]

        max_gen = max(64, min(int(requested_max_tokens), 256, max(128, n_ctx // 4)))
        max_prompt_tokens = max(256, n_ctx - max_gen - 32)

        system_msg: Optional[Dict[str, str]] = None
        if system_parts:
            sys_text = system_parts[-1]
            # Ensure system prompt has ample budget (preserving high-priority living context & memory)
            sys_budget = max(256, max_prompt_tokens - 300)
            if self._estimate_tokens(llm, sys_text) > sys_budget:
                sys_text = sys_text[: sys_budget * 3]
            system_msg = {"role": "system", "content": sys_text}

        sys_tokens = self._estimate_tokens(llm, system_msg["content"]) if system_msg else 0
        remaining_budget = max(128, max_prompt_tokens - sys_tokens)

        kept_reversed: List[Dict[str, str]] = []
        used_tokens = 0
        for msg in reversed(non_system):
            t_est = self._estimate_tokens(llm, msg["content"])
            if not kept_reversed:
                # Always keep the latest user turn, truncating only if larger than budget
                if t_est > remaining_budget:
                    msg = {
                        "role": msg["role"],
                        "content": msg["content"][-(remaining_budget * 3):],
                    }
                    t_est = self._estimate_tokens(llm, msg["content"])
                kept_reversed.append(msg)
                used_tokens += t_est
            elif used_tokens + t_est <= remaining_budget:
                kept_reversed.append(msg)
                used_tokens += t_est
            else:
                break

        prepared: List[Dict[str, str]] = []
        if system_msg:
            prepared.append(system_msg)
        prepared.extend(reversed(kept_reversed))
        return prepared, max_gen

    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate full response using local GGUF model."""
        try:
            default_temp, default_max = _read_generation_defaults()
            llm = self._mgr.get_model(model_name=self.model)
            self.llm = llm
            prepared_msgs, safe_max_tokens = self._prepare_messages_and_limits(
                llm,
                messages,
                int(kwargs.get("max_tokens", default_max)),
            )

            completion_kwargs = {
                "messages": prepared_msgs,
                "max_tokens": safe_max_tokens,
                "temperature": kwargs.get("temperature", default_temp),
                "top_p": kwargs.get("top_p", 0.9),
                "repeat_penalty": 1.1,
            }
            if "response_format" in kwargs:
                completion_kwargs["response_format"] = kwargs["response_format"]

            logger.info(f"[GGUF:{self.model}] Generating sync response ({len(prepared_msgs)} msgs, max_tokens={safe_max_tokens})")
            with self._mgr._infer_lock:
                response = llm.create_chat_completion(**completion_kwargs)
            return str(response["choices"][0]["message"]["content"] or "").strip()
        except Exception as e:
            logger.error(f"GGUF generation failed: {e}")
            return f"Error: {str(e)}"

    def stream_response(self, messages: List[Dict[str, str]], **kwargs) -> Generator[str, None, None]:
        """Stream response using local GGUF model."""
        try:
            default_temp, default_max = _read_generation_defaults()
            llm = self._mgr.get_model(model_name=self.model)
            self.llm = llm
            prepared_msgs, safe_max_tokens = self._prepare_messages_and_limits(
                llm,
                messages,
                int(kwargs.get("max_tokens", default_max)),
            )

            logger.info(f"[GGUF:{self.model}] Streaming response ({len(prepared_msgs)} msgs, max_tokens={safe_max_tokens})")
            with self._mgr._infer_lock:
                stream = llm.create_chat_completion(
                    messages=prepared_msgs,
                    max_tokens=safe_max_tokens,
                    temperature=kwargs.get("temperature", default_temp),
                    top_p=kwargs.get("top_p", 0.9),
                    repeat_penalty=1.1,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk["choices"][0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield text
        except Exception as e:
            logger.error(f"GGUF streaming failed: {e}")
            yield f"Error: {str(e)}"

    def count_tokens(self, text: str) -> int:
        """Count tokens using llama_cpp tokenizer."""
        try:
            if self.llm is not None:
                return len(self.llm.tokenize(text.encode("utf-8")))
        except Exception:
            pass
        return len(text) // 4


class LLMFactory:
    """Factory for creating LLM providers."""

    PROVIDERS = {
        "gguf": GGUFProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "google": GeminiProvider,
        "local": GGUFProvider,
        "offline": OfflineProvider,
    }

    @classmethod
    def normalize_provider(cls, provider: Optional[str]) -> str:
        """Normalize legacy/alias provider identifiers cleanly."""
        p = str(provider or "").strip().lower()
        if p == "google":
            return "gemini"
        if p == "local":
            return "gguf"
        return p

    @classmethod
    def sanitize_model_for_provider(cls, provider: str, model: Optional[str]) -> str:
        """Ensure model names never leak across incompatible providers (e.g., gemini model -> gguf)."""
        p = cls.normalize_provider(provider)
        m = str(model or "").strip()
        ml = m.lower()
        if p == "gguf":
            if not m or any(tok in ml for tok in ("gemini", "gpt-", "claude", "llama3.", "qwen2.5-coder")):
                return "pulsar-final-q4_k_m"
            return m
        if p == "gemini":
            if not m or any(tok in ml for tok in ("pulsar", "gpt-", "claude")):
                return "gemini-2.5-flash"
            return m
        if p == "openai":
            if not m or any(tok in ml for tok in ("pulsar", "gemini", "claude")):
                return "gpt-4o-mini"
            return m
        return m

    @classmethod
    def create(cls, provider: str = "openai", **kwargs) -> LLMProvider:
        """Create an LLM provider."""
        provider_lower = cls.normalize_provider(provider)

        if provider_lower not in cls.PROVIDERS:
            available = ", ".join(cls.PROVIDERS.keys())
            raise ValueError(f"Unknown provider: {provider}. Available: {available}")

        if "model" in kwargs:
            kwargs["model"] = cls.sanitize_model_for_provider(provider_lower, kwargs.get("model"))

        provider_class = cls.PROVIDERS[provider_lower]
        return provider_class(**kwargs)

    @classmethod
    def detect_provider(cls) -> tuple[str, str]:
        """Detect provider from user settings (single source of truth)."""
        try:
            from settings_manager import get_provider, get_model
            return (get_provider(), get_model())
        except ImportError:
            import sys
            from pathlib import Path
            try:
                sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'backend'))
                from settings_manager import get_provider, get_model
                return (get_provider(), get_model())
            except ImportError:
                if os.getenv("GEMINI_API_KEY"):
                    return ("gemini", "gemini-2.5-flash")
                return ("gguf", "pulsar-final-q4_k_m")

    @classmethod
    def create_with_fallback(cls, preferred_provider: Optional[str] = None, **kwargs) -> LLMProvider:
        """
        Create provider with automatic fallback to local GGUF ONLY when preferred
        provider is a cloud provider. Explicit local providers never silently switch.
        """
        provider = cls.normalize_provider(preferred_provider) if preferred_provider else None

        if not provider:
            provider, model = cls.detect_provider()
            provider = cls.normalize_provider(provider)
            kwargs.setdefault('model', model)

        # Try preferred provider first
        try:
            return cls.create(provider, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to create {provider} provider: {e}")
            if not is_local_provider(provider):
                logger.info("Attempting automatic fallback to local GGUF model...")
                try:
                    return cls.create("gguf", model="pulsar-final-q4_k_m")
                except Exception as fallback_err:
                    logger.error(f"Fallback to GGUF failed: {fallback_err}")
            raise e


class UnifiedChatInterface:
    """Unified chat interface that abstracts LLM provider."""
    
    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None, use_fallback: bool = True):
        """
        Initialize unified chat interface.

        Strict isolation guarantee: when a local provider ('gguf', 'local',
        'offline') is resolved, `use_fallback` is disabled so local requests NEVER
        silently fall back or route to Google Gemini / OpenAI.
        """
        if provider is None or model is None:
            detected_provider, detected_model = LLMFactory.detect_provider()
            provider = provider or detected_provider
            model = model or detected_model

        raw_prov = str(provider or "").strip().lower()
        provider_norm = LLMFactory.normalize_provider(raw_prov)
        model_sanitized = LLMFactory.sanitize_model_for_provider(provider_norm, model)

        factory_provider = "offline" if raw_prov == "offline" else provider_norm

        # Never silently fall back from a requested local provider to cloud AI
        allow_fallback = bool(use_fallback) and not is_local_provider(raw_prov) and not is_local_provider(provider_norm)

        logger.info(f"Initializing {factory_provider} with model {model_sanitized} (allow_fallback={allow_fallback})")

        if allow_fallback:
            try:
                self.provider = LLMFactory.create(factory_provider, model=model_sanitized)
                self.provider_name = factory_provider
                self.model = getattr(self.provider, "model", model_sanitized) or model_sanitized
            except Exception as e:
                logger.warning(f"Failed to create preferred provider {factory_provider}: {e}")
                candidates = [("gguf", "pulsar-final-q4_k_m")]
                try:
                    det_prov, det_model = LLMFactory.detect_provider()
                    det_prov_norm = LLMFactory.normalize_provider(det_prov)
                    if det_prov_norm and det_prov_norm != factory_provider:
                        candidates.insert(0, (det_prov_norm, det_model))
                except Exception:
                    pass
                candidates.extend([("gemini", "gemini-2.5-flash"), ("openai", "gpt-4o-mini")])

                recovered = False
                for fb_prov, fb_model in candidates:
                    if fb_prov == factory_provider:
                        continue
                    try:
                        self.provider = LLMFactory.create(fb_prov, model=fb_model)
                        self.provider_name = fb_prov
                        self.model = getattr(self.provider, "model", fb_model) or fb_model
                        logger.info(f"Fallback recovered using {fb_prov} ({self.model})")
                        recovered = True
                        break
                    except Exception:
                        continue
                if not recovered:
                    raise e
        else:
            self.provider = LLMFactory.create(factory_provider, model=model_sanitized)
            self.provider_name = factory_provider
            self.model = getattr(self.provider, "model", model_sanitized) or model_sanitized

        self.use_fallback = allow_fallback
        self.conversation_history: List[Dict[str, str]] = []

        # Single source of truth for Pulsar assistant persona (prevents base-model identity leaks)
        try:
            from ai_assistant.core.jarvis_persona import build_persona_system_prompt
            default_system_prompt = build_persona_system_prompt(
                provider=self.provider_name,
                model=self.model,
            )
        except Exception:
            default_system_prompt = (
                "You are Pulsar, a smart, helpful, and human-like AI companion created by Diwakar. "
                "You MUST NEVER identify as a large language model trained by Google or any other company. "
                "You MUST NEVER mention Gemma, OpenAI, Google, or any base models. "
                "Keep your answers brief and directly address the user. "
                "CRITICAL: Always reply in the exact same language the user speaks. If the user speaks in Hindi or Hinglish, you MUST reply naturally in Hindi or Hinglish."
            )
        self.conversation_history.append({"role": "system", "content": default_system_prompt})

        self.offline_mode = is_local_provider(self.provider_name) or isinstance(
            self.provider, (OfflineProvider, GGUFProvider)
        )
        
        if self.offline_mode:
            logger.warning("š  Running in offline mode - features may be limited")
    
    def is_offline(self) -> bool:
        """Check if currently in offline mode."""
        return self.offline_mode
    
    def set_system_message(self, content: str):
        """Set or replace the leading system message without stacking duplicates."""
        if not content:
            return
        if self.conversation_history and self.conversation_history[0].get("role") == "system":
            self.conversation_history[0] = {"role": "system", "content": content}
        else:
            self.conversation_history.insert(0, {"role": "system", "content": content})

    def add_system_message(self, content: str):
        """Replace leading system message cleanly (backward-compatible alias)."""
        self.set_system_message(content)
    
    def add_user_message(self, content: str):
        """Add user message."""
        self.conversation_history.append({"role": "user", "content": content})
    
    def add_assistant_message(self, content: str):
        """Add assistant message."""
        self.conversation_history.append({"role": "assistant", "content": content})

    def _drop_trailing_user_message(self, user_message: str) -> None:
        if (
            self.conversation_history
            and self.conversation_history[-1].get("role") == "user"
            and self.conversation_history[-1].get("content") == user_message
        ):
            self.conversation_history.pop()
    
    def chat(self, user_message: str, stream: bool = False, **kwargs) -> Union[str, Generator[str, None, None]]:
        """Send a chat message and get response."""
        self.add_user_message(user_message)
        
        try:
            if stream:
                def _capturing_stream():
                    full_response = ""
                    try:
                        for chunk in self.provider.stream_response(self.conversation_history, **kwargs):
                            if chunk:
                                full_response += chunk
                                yield chunk
                    except Exception as stream_err:
                        logger.error(f"Stream iteration failed: {stream_err}")
                        self._drop_trailing_user_message(user_message)
                        yield f"Error: Generation failed: {stream_err}"
                        return
                    if full_response and not full_response.strip().startswith("Error:"):
                        self.add_assistant_message(full_response)
                    else:
                        self._drop_trailing_user_message(user_message)
                return _capturing_stream()
            else:
                response = self.provider.generate_response(self.conversation_history, **kwargs)
                if str(response or "").strip().startswith("Error:"):
                    raise Exception(response)
                self.add_assistant_message(response)
                return response
        except Exception as e:
            logger.error(f"Chat generation failed: {e}")
            self._drop_trailing_user_message(user_message)
            if stream:
                def _error_stream():
                    yield f"Error: Generation failed: {e}"
                return _error_stream()
            return f"Error: {e}"
    
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
        logger.debug("Testing non-streaming response:")
        response = chat.chat("What is Python?", stream=False)
        print(f"Response: {response}\n")
        
        # Test streaming
        logger.debug("Testing streaming response:")
        for chunk in chat.chat("Tell me a joke", stream=True):
            print(chunk, end="", flush=True)
        print()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        print("Make sure you have OPENAI_API_KEY or GEMINI_API_KEY set")

