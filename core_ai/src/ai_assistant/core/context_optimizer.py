# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

#!/usr/bin/env python3
"""
Context Window Optimization Module
Handles intelligent history compression and semantic retrieval
to prevent context window thrashing.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import sqlite3

logger = logging.getLogger(__name__)


@dataclass
class MessageSummary:
    """Summary of a conversation segment."""
    original_messages: List[Dict[str, str]]
    summary_text: str
    key_points: List[str]
    tokens_original: int
    tokens_summary: int
    timestamp: str
    
    def compression_ratio(self) -> float:
        """Get compression ratio."""
        return self.tokens_summary / max(self.tokens_original, 1)


class ConversationCompressor:
    """Compresses conversation history while preserving context."""
    
    def __init__(self):
        """Initialize compressor."""
        self.compression_history: List[MessageSummary] = []
    
    def compress_messages(
        self,
        messages: List[Dict[str, str]],
        target_tokens: int,
        compression_ratio: float = 0.3
    ) -> List[Dict[str, str]]:
        """
        Compress messages to fit within token budget.
        
        Args:
            messages: Message list to compress
            target_tokens: Target token count
            compression_ratio: Compression strength (0.1-0.9)
            
        Returns:
            Compressed message list
        """
        if len(messages) <= 10:
            return messages  # Don't compress short conversations
        
        # Keep system message
        compressed = []
        if messages and messages[0].get("role") == "system":
            compressed.append(messages[0])
            messages = messages[1:]
        
        # Estimate tokens (rough)
        from ai_assistant.ai.conversational_ai import TokenCounter
        counter = TokenCounter()
        total_tokens = counter.count_messages(messages)
        
        if total_tokens <= target_tokens:
            compressed.extend(messages)
            return compressed
        
        # Need to compress
        compression_needed = total_tokens - target_tokens
        messages_to_compress = int(len(messages) * compression_ratio)
        
        logger.info(f"Compressing {messages_to_compress} messages ({compression_needed} tokens)")
        
        # Keep recent messages
        recent_count = len(messages) - messages_to_compress
        compressed.extend(messages[-recent_count:])
        
        # Summarize older messages
        older_messages = messages[:messages_to_compress]
        if older_messages:
            summary = self._create_simple_summary(older_messages)
            compressed.insert(
                1 if compressed and compressed[0].get("role") == "system" else 0,
                {
                    "role": "system",
                    "content": f"[Previous conversation summary]: {summary}"
                }
            )
        
        return compressed
    
    def _create_simple_summary(self, messages: List[Dict[str, str]]) -> str:
        """Create simple summary without LLM."""
        user_queries = [m["content"] for m in messages if m["role"] == "user"]
        
        if not user_queries:
            return "Earlier conversation"
        
        summary = f"Discussed: {', '.join(user_queries[:3])}"
        if len(user_queries) > 3:
            summary += f" and {len(user_queries) - 3} more topics"
        
        return summary
    
    def compress_with_llm(
        self,
        messages: List[Dict[str, str]],
        llm_provider,
        summary_length: str = "brief"
    ) -> str:
        """
        Compress messages using LLM summarization.
        
        Args:
            messages: Messages to summarize
            llm_provider: LLM provider instance
            summary_length: "brief", "detailed", "bullet_points"
            
        Returns:
            Summary text
        """
        prompt = self._build_summarization_prompt(messages, summary_length)
        
        try:
            summary = llm_provider.generate_response(
                [{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.5
            )
            return summary
        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            return self._create_simple_summary(messages)
    
    def _build_summarization_prompt(
        self,
        messages: List[Dict[str, str]],
        summary_length: str
    ) -> str:
        """Build prompt for LLM summarization."""
        conversation = "\n".join([
            f"{m['role'].upper()}: {m['content'][:200]}"
            for m in messages
        ])
        
        length_instructions = {
            "brief": "Provide a 1-2 sentence summary",
            "detailed": "Provide a 3-5 sentence summary with key points",
            "bullet_points": "Provide 3-5 bullet points summarizing the conversation"
        }
        
        return f"""Summarize the following conversation:

{conversation}

{length_instructions.get(summary_length, 'Provide a brief summary')}"""


class SemanticHistoryRetrieval:
    """Retrieves relevant messages from compressed history."""
    
    def __init__(self, db_path: str = "semantic_history.db"):
        """Initialize retrieval system."""
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS message_embeddings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message_text TEXT NOT NULL,
                        role TEXT NOT NULL,
                        embedding TEXT,
                        timestamp TEXT NOT NULL,
                        relevance_keywords TEXT
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"DB init failed: {e}")
    
    def store_message(
        self,
        message: str,
        role: str,
        keywords: Optional[List[str]] = None
    ):
        """Store message with keywords for retrieval."""
        try:
            keywords_str = json.dumps(keywords or [])
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO message_embeddings
                    (message_text, role, timestamp, relevance_keywords)
                    VALUES (?, ?, ?, ?)
                """, (
                    message,
                    role,
                    datetime.now().isoformat(),
                    keywords_str
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store message: {e}")
    
    def retrieve_relevant_messages(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, str]]:
        """
        Retrieve messages relevant to a query.
        
        Args:
            query: Query to find relevant messages for
            limit: Maximum messages to retrieve
            similarity_threshold: Minimum relevance score
            
        Returns:
            List of relevant messages
        """
        try:
            # Simple keyword matching (MVP)
            query_keywords = set(query.lower().split())
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT message_text, role, timestamp
                    FROM message_embeddings
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit * 2,))
                
                results = []
                for row in cursor:
                    msg_text, role, timestamp = row
                    # Simple keyword overlap
                    msg_keywords = set(msg_text.lower().split())
                    overlap = len(query_keywords & msg_keywords) / max(len(query_keywords), 1)
                    
                    if overlap >= similarity_threshold:
                        results.append({
                            "role": role,
                            "content": msg_text,
                            "timestamp": timestamp,
                            "relevance": overlap
                        })
                
                return sorted(results, key=lambda x: x["relevance"], reverse=True)[:limit]
        
        except Exception as e:
            logger.error(f"Message retrieval failed: {e}")
            return []
    
    def clear(self):
        """Clear stored messages."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM message_embeddings")
                conn.commit()
        except Exception as e:
            logger.error(f"Clear failed: {e}")


class SmartContextWindow:
    """
    Smart context window management.
    Combines compression and semantic retrieval.
    """
    
    def __init__(self, max_tokens: int = 4000):
        """Initialize context window manager."""
        self.max_tokens = max_tokens
        self.compressor = ConversationCompressor()
        self.retriever = SemanticHistoryRetrieval()
        self.message_history: List[Dict[str, str]] = []
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to history."""
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            msg.update(metadata)
        
        self.message_history.append(msg)
        
        # Store for semantic retrieval
        self.retriever.store_message(content, role)
    
    def get_optimized_history(
        self,
        current_query: str,
        include_semantic: bool = True
    ) -> List[Dict[str, str]]:
        """
        Get history optimized for current query.
        
        Uses combination of:
        1. System message (always)
        2. Recent messages (fit in budget)
        3. Semantically relevant historical messages
        
        Args:
            current_query: Current user query
            include_semantic: Whether to include retrieved messages
            
        Returns:
            Optimized message history
        """
        from ai_assistant.ai.conversational_ai import TokenCounter
        
        counter = TokenCounter()
        optimized = []
        budget = self.max_tokens
        
        # 1. Keep system message
        if self.message_history and self.message_history[0].get("role") == "system":
            optimized.append(self.message_history[0])
            budget -= counter.count(json.dumps(self.message_history[0]))
        
        # 2. Add recent messages (fill 70% of budget)
        recent_budget = int(budget * 0.7)
        recent_tokens = 0
        
        for msg in reversed(self.message_history[1:]):
            msg_tokens = counter.count(json.dumps(msg))
            if recent_tokens + msg_tokens > recent_budget:
                break
            optimized.insert(1 if optimized else 0, msg)
            recent_tokens += msg_tokens
        
        budget -= recent_tokens
        
        # 3. Add relevant historical messages (fill remaining 30% of budget)
        if include_semantic and budget > 200:
            relevant = self.retriever.retrieve_relevant_messages(
                current_query,
                limit=3,
                similarity_threshold=0.4
            )
            
            semantic_tokens = 0
            for msg in relevant:
                msg_tokens = counter.count(json.dumps(msg))
                if semantic_tokens + msg_tokens > budget:
                    break
                
                # Insert historical message with context label
                contextual_msg = msg.copy()
                contextual_msg["content"] = f"[From history] {msg['content']}"
                optimized.insert(1, contextual_msg)
                semantic_tokens += msg_tokens
        
        return optimized
    
    def get_stats(self) -> Dict[str, Any]:
        """Get context window statistics."""
        from ai_assistant.ai.conversational_ai import TokenCounter
        counter = TokenCounter()
        
        total_tokens = counter.count_messages(self.message_history)
        
        return {
            "total_messages": len(self.message_history),
            "total_tokens": total_tokens,
            "max_tokens": self.max_tokens,
            "utilization_percent": (total_tokens / self.max_tokens * 100) if self.max_tokens > 0 else 0,
            "compressed": any("summary" in m.get("content", "") for m in self.message_history)
        }


if __name__ == "__main__":
    # Demo
    ctx = SmartContextWindow(max_tokens=2000)
    
    # Add some messages
    ctx.add_message("system", "You are helpful")
    ctx.add_message("user", "What is Python?")
    ctx.add_message("assistant", "Python is a programming language...")
    ctx.add_message("user", "How do I install Python?")
    ctx.add_message("assistant", "You can install Python from python.org...")
    
    # Get optimized history
    optimized = ctx.get_optimized_history("How do I learn Python?")
    print(f"Optimized history: {len(optimized)} messages")
    
    # Get stats
    stats = ctx.get_stats()
    print(f"Stats: {stats}")

