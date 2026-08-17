#!/usr/bin/env python3
"""
Web Search Integration Module
Integrates real-time web search into chat responses.
Provides search trigger detection, result formatting, and response enhancement.
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SearchTriggerType(Enum):
    """Triggers for web search."""
    KNOWLEDGE_DEPENDENT = "knowledge_dependent"  # Queries needing current info
    UNKNOWN_ENTITY = "unknown_entity"  # Unknown people, places, events
    CURRENT_EVENTS = "current_events"  # News, weather, current topics
    FACTUAL_QUERY = "factual_query"  # Specific facts (stocks, sports)
    MANUAL = "manual"  # User explicitly requests search


@dataclass
class SearchResult:
    """A single search result."""
    title: str
    url: str
    snippet: str
    source: str
    timestamp: Optional[str] = None
    relevance_score: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "timestamp": self.timestamp,
            "relevance_score": self.relevance_score
        }


@dataclass
class SearchResponse:
    """Response from web search."""
    query: str
    results: List[SearchResult]
    trigger_type: SearchTriggerType
    search_time: float
    total_results: int
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "trigger_type": self.trigger_type.value,
            "search_time": self.search_time,
            "total_results": self.total_results,
            "timestamp": self.timestamp
        }


class WebSearchTrigger:
    """Detects when web search should be used."""
    
    # Keywords indicating knowledge-dependent queries
    KNOWLEDGE_DEPENDENT_KEYWORDS = {
        "current", "latest", "recent", "today", "now",
        "what is happening", "what's new", "breaking",
        "update", "status", "live", "real-time"
    }
    
    # Keywords for factual queries
    FACTUAL_KEYWORDS = {
        "weather", "stock", "price", "score", "result",
        "who is", "what is", "where is", "when did",
        "population", "distance", "capital", "president"
    }
    
    # Keywords for unknown entities
    UNKNOWN_ENTITY_KEYWORDS = {
        "who is", "who are", "what is", "what are",
        "tell me about", "describe", "explain", "define"
    }
    
    # Current event patterns
    CURRENT_EVENT_KEYWORDS = {
        "news", "headlines", "events", "happening",
        "trending", "viral", "scandal", "controversy"
    }
    
    @classmethod
    def should_search(cls, message: str) -> tuple[bool, SearchTriggerType]:
        """
        Determine if message should trigger web search.
        
        Args:
            message: User message
            
        Returns:
            (should_search, trigger_type)
        """
        message_lower = message.lower()
        
        # Check for explicit search request
        if any(word in message_lower for word in ["search", "google", "look up", "find out"]):
            return True, SearchTriggerType.MANUAL
        
        # Check for knowledge-dependent queries
        if any(word in message_lower for word in cls.KNOWLEDGE_DEPENDENT_KEYWORDS):
            return True, SearchTriggerType.KNOWLEDGE_DEPENDENT
        
        # Check for factual queries
        if any(word in message_lower for word in cls.FACTUAL_KEYWORDS):
            return True, SearchTriggerType.FACTUAL_QUERY
        
        # Check for current events
        if any(word in message_lower for word in cls.CURRENT_EVENT_KEYWORDS):
            return True, SearchTriggerType.CURRENT_EVENTS
        
        # Check for unknown entity questions
        if any(word in message_lower for word in cls.UNKNOWN_ENTITY_KEYWORDS):
            return True, SearchTriggerType.UNKNOWN_ENTITY
        
        return False, None


class WebSearchCache:
    """Cache for web search results to reduce API calls."""
    
    def __init__(self, ttl_hours: int = 24):
        """Initialize cache."""
        self.cache: Dict[str, tuple[SearchResponse, datetime]] = {}
        self.ttl = timedelta(hours=ttl_hours)
    
    def get(self, query: str) -> Optional[SearchResponse]:
        """Get cached search results."""
        if query in self.cache:
            response, timestamp = self.cache[query]
            if datetime.now() - timestamp < self.ttl:
                return response
            else:
                # Expired, remove
                del self.cache[query]
        return None
    
    def set(self, query: str, response: SearchResponse):
        """Cache search results."""
        self.cache[query] = (response, datetime.now())
    
    def clear(self):
        """Clear cache."""
        self.cache.clear()
    
    def cleanup(self):
        """Remove expired entries."""
        now = datetime.now()
        expired = [q for q, (_, ts) in self.cache.items() if now - ts > self.ttl]
        for q in expired:
            del self.cache[q]


class WebSearchIntegration:
    """Integrates web search into chat."""
    
    def __init__(self, cache_ttl_hours: int = 24):
        """Initialize web search integration."""
        self.cache = WebSearchCache(cache_ttl_hours)
        self.trigger = WebSearchTrigger()
        self.search_count = 0
    
    def should_search_for_message(self, message: str) -> tuple[bool, SearchTriggerType]:
        """Check if message should trigger search."""
        return self.trigger.should_search(message)
    
    def search_web(self, query: str, max_results: int = 5) -> Optional[SearchResponse]:
        """
        Perform web search.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            
        Returns:
            SearchResponse or None if failed
        """
        # Check cache first
        cached = self.cache.get(query)
        if cached:
            logger.info(f"🔍 Using cached search for: {query}")
            return cached
        
        logger.info(f"🌐 Searching web for: {query}")
        
        try:
            start_time = time.time()
            
            # Try to use automation_tools_new's search_google
            try:
                from automation_tools_new import search_google
                results = search_google(query, max_results=max_results)
                
                if results:
                    search_results = []
                    for result in results:
                        if isinstance(result, dict):
                            search_results.append(SearchResult(
                                title=result.get("title", ""),
                                url=result.get("link", ""),
                                snippet=result.get("snippet", ""),
                                source="Google"
                            ))
                    
                    search_time = time.time() - start_time
                    response = SearchResponse(
                        query=query,
                        results=search_results[:max_results],
                        trigger_type=SearchTriggerType.MANUAL,
                        search_time=search_time,
                        total_results=len(search_results),
                        timestamp=datetime.now().isoformat()
                    )
                    
                    # Cache result
                    self.cache.set(query, response)
                    self.search_count += 1
                    
                    logger.info(f"✅ Found {len(search_results)} results in {search_time:.2f}s")
                    return response
            except ImportError:
                logger.warning("search_google not available, trying DuckDuckGo")
                return self._search_duckduckgo(query, max_results)
        
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return None
    
    def _search_duckduckgo(self, query: str, max_results: int = 5) -> Optional[SearchResponse]:
        """Fallback search using DuckDuckGo."""
        try:
            import requests
            
            start_time = time.time()
            
            # Use duckduckgo instant answer API
            params = {
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1
            }
            
            response = requests.get(
                "https://api.duckduckgo.com/",
                params=params,
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            # Add instant answer if available
            if data.get("AbstractText"):
                results.append(SearchResult(
                    title="Direct Answer",
                    url=data.get("AbstractURL", ""),
                    snippet=data.get("AbstractText", ""),
                    source="DuckDuckGo"
                ))
            
            # Add related topics
            for topic in data.get("RelatedTopics", [])[:max_results-1]:
                if "FirstURL" in topic:
                    results.append(SearchResult(
                        title=topic.get("Text", ""),
                        url=topic.get("FirstURL", ""),
                        snippet=topic.get("Text", ""),
                        source="DuckDuckGo"
                    ))
            
            if results:
                search_time = time.time() - start_time
                search_response = SearchResponse(
                    query=query,
                    results=results,
                    trigger_type=SearchTriggerType.MANUAL,
                    search_time=search_time,
                    total_results=len(results),
                    timestamp=datetime.now().isoformat()
                )
                
                self.cache.set(query, search_response)
                self.search_count += 1
                
                return search_response
        
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
        
        return None
    
    def format_results_for_llm(self, search_response: SearchResponse) -> str:
        """
        Format search results for inclusion in LLM prompt.
        
        Args:
            search_response: SearchResponse
            
        Returns:
            Formatted string for LLM
        """
        if not search_response or not search_response.results:
            return ""
        
        formatted = f"\n📊 Web Search Results for '{search_response.query}':\n\n"
        
        for i, result in enumerate(search_response.results, 1):
            formatted += f"{i}. **{result.title}**\n"
            formatted += f"   Source: {result.source}\n"
            formatted += f"   URL: {result.url}\n"
            formatted += f"   {result.snippet}\n\n"
        
        formatted += f"*Search completed in {search_response.search_time:.2f}s*\n"
        
        return formatted
    
    def enhance_prompt_with_search(
        self,
        user_message: str,
        search_response: SearchResponse
    ) -> str:
        """
        Enhance user prompt with search results context.
        
        Args:
            user_message: Original user message
            search_response: Search results
            
        Returns:
            Enhanced prompt for LLM
        """
        search_context = self.format_results_for_llm(search_response)
        
        enhanced = f"""User asked: {user_message}

{search_context}

Based on the above search results, provide an informative answer to the user's question."""
        
        return enhanced
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get search statistics."""
        return {
            "searches_performed": self.search_count,
            "cached_queries": len(self.cache.cache),
            "cache_ttl_hours": self.cache.ttl.total_seconds() / 3600
        }


# Integration helper function
def integrate_search_into_chat(chat_system):
    """
    Integrate web search into a chat system.
    
    Usage:
        chat = AdvancedChatSystem()
        search_integration = integrate_search_into_chat(chat)
        
        message = "What's the latest news about AI?"
        search_needed, trigger = search_integration.should_search_for_message(message)
        
        if search_needed:
            search_results = search_integration.search_web(message)
            enhanced_prompt = search_integration.enhance_prompt_with_search(
                message, search_results
            )
            response = chat.get_response(enhanced_prompt)
    """
    return WebSearchIntegration()


if __name__ == "__main__":
    # Demo
    search = WebSearchIntegration()
    
    # Test trigger detection
    test_queries = [
        "What's the latest news?",
        "What is Python?",
        "Tell me about current events",
        "Simple greeting"
    ]
    
    for query in test_queries:
        should_search, trigger_type = search.should_search_for_message(query)
        print(f"Query: '{query}'")
        print(f"  Should search: {should_search}")
        if trigger_type:
            print(f"  Trigger type: {trigger_type.value}")
        print()
    
    # Test search
    result = search.search_web("What's the weather in New York?")
    if result:
        print(f"\nSearch Results: {result.total_results} found")
        print(result.format_results_for_llm())
