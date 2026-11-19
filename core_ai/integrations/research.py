# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

import logging
from typing import List, Optional
from core_ai.ai.llm_provider import UnifiedChatInterface
from core_ai.integrations.web_intelligence import get_web_intelligence

logger = logging.getLogger(__name__)


class ResearchManager:
    """
    Manages web research tasks by routing through the centralized WebIntelligenceService.
    Backward-compatible facade for legacy callers.
    """

    def __init__(self):
        try:
            try:
                from backend.services.settings_manager import get_provider, get_model
            except ImportError:
                from settings_manager import get_provider, get_model
            _sm_provider, _sm_model = get_provider(), get_model()
        except Exception:
            _sm_provider, _sm_model = None, None
        self.llm = UnifiedChatInterface(provider=_sm_provider, model=_sm_model)

    def perform_research(self, topic: str) -> str:
        """
        Performs comprehensive research on a topic.
        1. Searches and scrapes web pages via WebIntelligenceService.
        2. Synthesizes a structured report using LLM.
        """
        logger.info(f"Starting research on: {topic}")
        try:
            web_intel = get_web_intelligence()
            sources = web_intel.search_and_scrape(topic, num_urls=3, max_chars_per_url=2500)
            if not sources:
                return f"I tried to research '{topic}', but I couldn't find any relevant search results."

            aggregated_content = ""
            for s in sources:
                aggregated_content += f"\n--- Source: {s.title} ({s.url}) ---\n{s.content[:2500]}\n"

            prompt = (
                f"You are a research assistant. I have gathered the following information from the web regarding '{topic}'. "
                f"Please provide a comprehensive and well-structured research report based on this information. "
                f"Cite the sources provided where appropriate.\n\n"
                f"Research Data:\n{aggregated_content}"
            )
            return self.llm.chat(prompt)
        except Exception as e:
            return f"Research failed due to an error: {e}"

    def _search_web(self, query: str) -> List[str]:
        """Backward-compatible search returning URLs."""
        try:
            results = get_web_intelligence().search(query, num_results=5)
            return [r.url for r in results]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def _scrape_url(self, url: str) -> Optional[str]:
        """Backward-compatible single URL scraper."""
        try:
            return get_web_intelligence().scrape_url(url, max_chars=3000)
        except Exception as e:
            logger.error(f"Scrape failed: {e}")
            return None


# Singleton instance
_research_manager = None


def research_topic(topic: str) -> str:
    """Wrapper function to perform research on a topic."""
    global _research_manager
    if _research_manager is None:
        _research_manager = ResearchManager()
    return _research_manager.perform_research(topic)
