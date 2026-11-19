# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="backend")

import logging
from typing import Dict, List, Optional, Any
from core_ai.integrations.web_intelligence import (
    get_web_intelligence,
    WebQueryMode,
    SearchResult as ModernSearchResult,
    GroundingResult,
)

logger = logging.getLogger(__name__)


class WebSearchIntegration:
    """
    Backward-compatibility forwarder to the centralized WebIntelligenceService.
    Eliminates duplicated DuckDuckGo scraping while keeping legacy code functional.
    """

    def __init__(self):
        self.service = get_web_intelligence()

    def search_web(self, query: str, max_results: int = 5) -> Optional[Any]:
        """Perform search using centralized WebIntelligenceService."""
        try:
            results = self.service.search(query, num_results=max_results)
            return results
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return None

    def should_search_for_message(self, message: str) -> tuple[bool, str]:
        """Classify message intent."""
        mode, query = self.service.classify(message)
        needs_search = mode in (WebQueryMode.BACKGROUND_GROUNDING, WebQueryMode.DEEP_RESEARCH)
        return needs_search, mode.value

    def enhance_prompt_with_search(self, user_message: str, search_results: List[Any]) -> str:
        """Format prompt with live context block."""
        grounding = self.service.ground_prompt(user_message)
        return grounding.grounded_message

    def get_search_stats(self) -> Dict[str, Any]:
        """Return cache stats."""
        return self.service.cache.stats()


def integrate_search_into_chat(chat_system=None):
    """Factory helper."""
    return WebSearchIntegration()
