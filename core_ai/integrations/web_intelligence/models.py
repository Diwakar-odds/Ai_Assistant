"""
Data models and Enums for the Web Intelligence Subsystem.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class WebQueryMode(str, Enum):
    """Execution mode determined by the classifier."""
    BROWSER_ACTION = "browser_action"          # User wants browser opened (hands)
    BACKGROUND_GROUNDING = "background_grounding"  # Silent headless search -> LLM prompt RAG
    DEEP_RESEARCH = "deep_research"            # Multi-source analysis -> research agent
    DIRECT_CHAT = "direct_chat"                # No search needed; direct LLM reasoning


@dataclass
class SearchResult:
    """Individual search result item."""
    title: str
    url: str
    snippet: str
    source: str = "Web"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    relevance_score: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "timestamp": self.timestamp,
            "relevance_score": self.relevance_score,
        }


@dataclass
class ScrapedSource:
    """Scraped web page content."""
    url: str
    title: str
    content: str
    char_count: int
    success: bool
    error: Optional[str] = None


@dataclass
class GroundingResult:
    """Complete result returned to the chat/assistant pipeline."""
    mode: WebQueryMode
    query: str
    grounded_message: str
    context_block: str
    results: List[SearchResult] = field(default_factory=list)
    search_time_ms: float = 0.0
    source_engine: str = "none"
    cache_hit: bool = False
    offline_degraded: bool = False
    error: Optional[str] = None

    @property
    def has_grounding(self) -> bool:
        return bool(self.context_block and self.results)
