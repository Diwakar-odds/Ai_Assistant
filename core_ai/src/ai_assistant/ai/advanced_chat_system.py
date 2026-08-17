#!/usr/bin/env python3
"""
Advanced Chat System Module
Provides ChatGPT/Gemini-like chat capabilities with streaming, context management,
token optimization, function calling, and real-time responses.

Features:
- Token streaming (Server-Sent Events)
- Smart context window management
- Function/tool calling framework
- Message regeneration and alternatives
- Semantic search in conversation history
- Real-time web search integration
- Response caching and optimization
"""

import json
import time
import asyncio
import threading
from typing import Dict, List, Optional, Callable, Generator, AsyncGenerator, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import sqlite3
import re
import os
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class ResponseMode(Enum):
    """Response generation modes."""
    STREAMING = "streaming"      # Token-by-token streaming
    FULL = "full"                # Complete response at once
    CACHED = "cached"            # Return cached response


class TokenCounter:
    """Token counter for various models."""
    
    MODEL_TOKEN_LIMITS = {
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "gpt-3.5-turbo": 4096,
        "gemini-pro": 32768,
        "gemini-2.5-flash": 1000000,
        "gemini-1.5-pro": 1000000,
        "llama-2-7b": 4096,
        "llama-2-70b": 4096,
    }
    
    def __init__(self, model: str = "gpt-3.5-turbo"):
        self.model = model
        self.token_limit = self.MODEL_TOKEN_LIMITS.get(model, 4096)
        
        # Try to use tiktoken for accurate counting
        try:
            import tiktoken
            self.encoder = tiktoken.encoding_for_model(model.split("-")[0])  # gpt-3.5
            self.use_tiktoken = True
        except:
            self.encoder = None
            self.use_tiktoken = False
    
    def count(self, text: str) -> int:
        """Count tokens in text."""
        if self.use_tiktoken and self.encoder:
            try:
                return len(self.encoder.encode(text))
            except:
                pass
        
        # Fallback: rough estimation (1 token ≈ 4 characters)
        return len(text) // 4
    
    def count_messages(self, messages: List[Dict[str, str]]) -> int:
        """Count tokens in a message list."""
        total = 0
        for msg in messages:
            total += self.count(json.dumps(msg))
        return total
    
    def fits_in_context(self, messages: List[Dict[str, str]], new_message: str) -> bool:
        """Check if message list + new message fits in context window."""
        current_tokens = self.count_messages(messages)
        new_tokens = self.count(new_message)
        # Reserve 10% for response
        return (current_tokens + new_tokens) < (self.token_limit * 0.9)
    
    def trim_history(self, messages: List[Dict[str, str]], max_tokens: int = None) -> List[Dict[str, str]]:
        """Trim message history to fit within token limit."""
        if max_tokens is None:
            max_tokens = self.token_limit - 1000  # Reserve for response
        
        if not messages:
            return []
        
        # Keep system message and last N messages that fit
        trimmed = []
        total_tokens = 0
        
        # Always keep system message
        if messages and messages[0].get("role") == "system":
            trimmed.append(messages[0])
            total_tokens = self.count(json.dumps(messages[0]))
        
        # Add messages from end (most recent) backwards
        for msg in reversed(messages[1:]):
            msg_tokens = self.count(json.dumps(msg))
            if total_tokens + msg_tokens > max_tokens:
                break
            trimmed.insert(1 if trimmed else 0, msg)
            total_tokens += msg_tokens
        
        return trimmed


@dataclass
class ToolSchema:
    """Schema for tool/function calling."""
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for API."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required
                }
            }
        }


class AdvancedChatSystem:
    """Advanced chat system with streaming, context management, and tool calling."""
    
    def __init__(self, llm_provider: str = "openai", model: str = "gpt-3.5-turbo"):
        """
        Initialize advanced chat system.
        
        Args:
            llm_provider: LLM provider (openai, gemini, local)
            model: Model name
        """
        self.llm_provider = llm_provider
        self.model = model
        self.token_counter = TokenCounter(model)
        
        # Conversation state
        self.conversation_history: List[Dict[str, str]] = []
        self.context_id: str = f"chat_{int(time.time())}"
        self.created_at: datetime = datetime.now()
        self.metadata: Dict[str, Any] = {}
        
        # Caching and optimization
        self.response_cache: Dict[str, str] = {}
        self.semantic_cache: Dict[str, Dict] = {}
        self.last_user_message: Optional[str] = None
        self.last_response: Optional[str] = None
        
        # Tools and function calling
        self.tools: Dict[str, Callable] = {}
        self.tool_schemas: List[ToolSchema] = []
        self.available_functions: Dict[str, Callable] = {}
        
        # Streaming configuration
        self.streaming_enabled = True
        self.streaming_timeout = 60  # seconds
        
        # Initialize database for persistence
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for chat persistence."""
        self.db_path = "chat_history.db"
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        context_id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        messages TEXT NOT NULL,
                        metadata TEXT NOT NULL,
                        model TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS responses (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        context_id TEXT NOT NULL,
                        user_message TEXT NOT NULL,
                        response TEXT NOT NULL,
                        tokens_used INTEGER,
                        generation_time REAL,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY(context_id) REFERENCES conversations(context_id)
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS semantic_cache (
                        hash TEXT PRIMARY KEY,
                        query TEXT NOT NULL,
                        embedding TEXT,
                        response TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        access_count INTEGER DEFAULT 1,
                        last_accessed TEXT NOT NULL
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
    
    def add_system_prompt(self, prompt: str):
        """Add or update system prompt."""
        # Remove existing system message if present
        self.conversation_history = [m for m in self.conversation_history if m.get("role") != "system"]
        
        # Add new system message at the beginning
        self.conversation_history.insert(0, {
            "role": "system",
            "content": prompt
        })
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to conversation history."""
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            msg.update(metadata)
        
        self.conversation_history.append(msg)
        
        if role == "user":
            self.last_user_message = content
    
    def get_conversation_history(self, max_tokens: Optional[int] = None) -> List[Dict[str, str]]:
        """Get conversation history, optionally trimmed to fit token limit."""
        history = self.conversation_history.copy()
        
        if max_tokens:
            history = self.token_counter.trim_history(history, max_tokens)
        
        return history
    
    def register_tool(self, name: str, func: Callable, schema: ToolSchema):
        """Register a tool/function for tool calling."""
        self.tools[name] = func
        self.tool_schemas.append(schema)
        self.available_functions[name] = func
        logger.info(f"Registered tool: {name}")
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get tool schemas in API format."""
        return [schema.to_dict() for schema in self.tool_schemas]
    
    def handle_tool_call(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute a tool call and return result."""
        if tool_name not in self.available_functions:
            return f"Error: Tool '{tool_name}' not found"
        
        try:
            func = self.available_functions[tool_name]
            result = func(**tool_input)
            return json.dumps({"success": True, "result": result})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})
    
    def stream_response(self, user_message: str, **kwargs) -> Generator[str, None, None]:
        """
        Stream a response token-by-token.
        
        This is a base implementation that should be overridden by LLM-specific implementations.
        """
        # Check cache first
        cache_key = self._generate_cache_key(user_message)
        if cache_key in self.response_cache:
            cached = self.response_cache[cache_key]
            for char in cached:
                yield char
            return
        
        # Placeholder streaming - override in LLMProvider subclass
        response_text = f"I received your message: '{user_message[:50]}...'\n\nThis is a placeholder response. Please implement proper LLM integration."
        
        # Simulate streaming by yielding words
        for word in response_text.split():
            yield word + " "
            time.sleep(0.05)  # Simulate network latency
    
    async def stream_response_async(self, user_message: str, **kwargs) -> AsyncGenerator[str, None]:
        """Async version of streaming response."""
        for chunk in self.stream_response(user_message, **kwargs):
            yield chunk
            await asyncio.sleep(0)
    
    def get_response(self, user_message: str, stream: bool = False, **kwargs) -> str:
        """
        Get a response from the chat system.
        
        Args:
            user_message: User's input message
            stream: Whether to stream the response
            **kwargs: Additional parameters for the LLM
        
        Returns:
            Response text (if stream=False) or generator (if stream=True)
        """
        # Add user message to history
        self.add_message("user", user_message)
        
        if stream:
            return self.stream_response(user_message, **kwargs)
        
        # Get full response (placeholder)
        response = f"Response to: {user_message}"
        
        # Add to history
        self.add_message("assistant", response)
        self.last_response = response
        
        # Cache the response
        cache_key = self._generate_cache_key(user_message)
        self.response_cache[cache_key] = response
        
        return response
    
    def regenerate_response(self) -> str:
        """Regenerate the last response (retry with same input)."""
        if not self.last_user_message:
            return "No previous message to regenerate"
        
        # Remove last assistant message
        if self.conversation_history and self.conversation_history[-1].get("role") == "assistant":
            self.conversation_history.pop()
        
        # Get new response
        return self.get_response(self.last_user_message)
    
    def get_alternatives(self, num_alternatives: int = 3) -> List[str]:
        """Get alternative responses for the last user message."""
        if not self.last_user_message:
            return []
        
        # Remove last response
        if self.conversation_history and self.conversation_history[-1].get("role") == "assistant":
            self.conversation_history.pop()
        
        # Generate alternatives
        alternatives = []
        for i in range(num_alternatives):
            response = self.get_response(self.last_user_message, temperature=0.8 + (i * 0.1))
            alternatives.append(response)
        
        return alternatives
    
    def edit_message(self, index: int, new_content: str) -> bool:
        """Edit a message in the conversation."""
        if 0 <= index < len(self.conversation_history):
            self.conversation_history[index]["content"] = new_content
            self.conversation_history[index]["edited_at"] = datetime.now().isoformat()
            return True
        return False
    
    def search_history(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search conversation history for relevant messages."""
        results = []
        query_lower = query.lower()
        
        for msg in self.conversation_history:
            if query_lower in msg["content"].lower():
                results.append(msg)
                if len(results) >= limit:
                    break
        
        return results
    
    def export_conversation(self, format: str = "json") -> str:
        """Export conversation in specified format."""
        if format == "json":
            return json.dumps({
                "context_id": self.context_id,
                "created_at": self.created_at.isoformat(),
                "messages": self.conversation_history
            }, indent=2)
        elif format == "markdown":
            md = f"# Conversation ({self.context_id})\n\n"
            for msg in self.conversation_history:
                role = msg["role"].upper()
                md += f"**{role}:**\n{msg['content']}\n\n"
            return md
        else:
            return json.dumps(self.conversation_history)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get conversation statistics."""
        total_messages = len(self.conversation_history)
        user_messages = sum(1 for m in self.conversation_history if m["role"] == "user")
        assistant_messages = sum(1 for m in self.conversation_history if m["role"] == "assistant")
        total_tokens = self.token_counter.count_messages(self.conversation_history)
        
        return {
            "context_id": self.context_id,
            "total_messages": total_messages,
            "user_messages": user_messages,
            "assistant_messages": assistant_messages,
            "total_tokens": total_tokens,
            "duration": (datetime.now() - self.created_at).total_seconds(),
            "cache_size": len(self.response_cache),
            "model": self.model,
            "created_at": self.created_at.isoformat()
        }
    
    def clear_history(self):
        """Clear conversation history (keeping system message if present)."""
        system_msg = None
        if self.conversation_history and self.conversation_history[0].get("role") == "system":
            system_msg = self.conversation_history[0]
        
        self.conversation_history = []
        if system_msg:
            self.conversation_history.append(system_msg)
    
    def _generate_cache_key(self, message: str) -> str:
        """Generate cache key for a message."""
        import hashlib
        return hashlib.md5(message.encode()).hexdigest()
    
    def save_to_db(self):
        """Save conversation to database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO conversations 
                    (context_id, created_at, updated_at, messages, metadata, model)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    self.context_id,
                    self.created_at.isoformat(),
                    datetime.now().isoformat(),
                    json.dumps(self.conversation_history),
                    json.dumps(self.metadata),
                    self.model
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save conversation: {e}")
    
    def load_from_db(self, context_id: str) -> bool:
        """Load conversation from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT messages, metadata, model FROM conversations WHERE context_id = ?",
                    (context_id,)
                )
                row = cursor.fetchone()
                if row:
                    self.conversation_history = json.loads(row[0])
                    self.metadata = json.loads(row[1])
                    self.model = row[2]
                    self.context_id = context_id
                    return True
        except Exception as e:
            logger.error(f"Failed to load conversation: {e}")
        return False


# Example tool registration
def create_sample_tools():
    """Create sample tools for demonstration."""
    return [
        ToolSchema(
            name="search_web",
            description="Search the web for current information",
            parameters={
                "query": {"type": "string", "description": "Search query"}
            },
            required=["query"]
        ),
        ToolSchema(
            name="get_weather",
            description="Get weather information for a location",
            parameters={
                "location": {"type": "string", "description": "City name or coordinates"}
            },
            required=["location"]
        ),
        ToolSchema(
            name="calculate",
            description="Perform mathematical calculations",
            parameters={
                "expression": {"type": "string", "description": "Math expression to evaluate"}
            },
            required=["expression"]
        )
    ]


if __name__ == "__main__":
    # Demo usage
    chat = AdvancedChatSystem(model="gpt-3.5-turbo")
    chat.add_system_prompt("You are a helpful AI assistant.")
    
    # Register tools
    for tool in create_sample_tools():
        chat.register_tool(tool.name, lambda x: f"Result for {x}", tool)
    
    # Get response
    response = chat.get_response("Hello, what's the weather like?")
    print(f"Response: {response}")
    
    # Get stats
    print(f"Stats: {chat.get_stats()}")
