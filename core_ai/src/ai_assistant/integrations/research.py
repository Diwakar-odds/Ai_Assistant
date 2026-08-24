# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
import urllib.parse
from ai_assistant.ai.llm_provider import UnifiedChatInterface

logger = logging.getLogger(__name__)

class ResearchManager:
    """
    Manages web research tasks by searching, scraping, and synthesizing information
    using the LLM.
    """
    
    def __init__(self):
        self.llm = UnifiedChatInterface()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def perform_research(self, topic: str) -> str:
        """
        Performs comprehensive research on a topic.
        1. Searches the web.
        2. Scrapes top results.
        3. Synthesizes a report using LLM.
        """
        print(f"ðŸ” Starting research on: {topic}")
        
        # 1. Search
        urls = self._search_web(topic)
        if not urls:
            return f"I tried to research '{topic}', but I couldn't find any relevant search results."
            
        print(f"Found {len(urls)} sources. Reading content...")
        
        # 2. Scrape
        aggregated_content = ""
        successful_sources = 0
        
        for url in urls[:3]:  # Limit to top 3 to save tokens and time
            try:
                print(f"Reading: {url}")
                content = self._scrape_url(url)
                if content:
                    aggregated_content += f"\n--- Source: {url} ---\n{content[:3000]}\n" # Limit chars per source
                    successful_sources += 1
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
                continue
                
        if not aggregated_content:
            return f"I found some links for '{topic}', but I was unable to read their content to generate a report."

        # 3. Synthesize
        print("Synthesizing report...")
        prompt = (
            f"You are a research assistant. I have gathered the following information from the web regarding '{topic}'. "
            f"Please provide a comprehensive and well-structured research report based on this information. "
            f"Cite the sources provided where appropriate.\n\n"
            f"Research Data:\n{aggregated_content}"
        )
        
        try:
            response = self.llm.chat(prompt)
            return response
        except Exception as e:
            return f"I gathered the data, but failed to generate the report due to an error: {e}"

    def _search_web(self, query: str) -> List[str]:
        """
        Searches DuckDuckGo for the query and returns a list of URLs.
        """
        try:
            # Using DuckDuckGo HTML version which is easier to scrape
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            for link in soup.find_all('a', class_='result__a'):
                href = link.get('href')
                if href and href.startswith('http'):
                    results.append(href)
                    if len(results) >= 5:
                        break
            
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def _scrape_url(self, url: str) -> Optional[str]:
        """
        Scrapes the main text content from a URL.
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
                
            # Get text
            text = soup.get_text()
            
            # Break into lines and remove leading/trailing space on each
            lines = (line.strip() for line in text.splitlines())
            # Break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # Drop blank lines
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.error(f"Scraping error for {url}: {e}")
            return None

# Singleton instance
_research_manager = None

def research_topic(topic: str) -> str:
    """
    Wrapper function to perform research on a topic.
    """
    global _research_manager
    if _research_manager is None:
        _research_manager = ResearchManager()
    return _research_manager.perform_research(topic)


