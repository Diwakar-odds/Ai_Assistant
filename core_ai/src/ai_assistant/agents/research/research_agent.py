from typing import Dict, Any, List, Optional
import os
import json
import requests
from bs4 import BeautifulSoup

from ..base_agent import BaseAgent
from ..models import Task, TaskResult

class ResearchAgent(BaseAgent):
    """
    Handles web research, searching, and simple scraping.
    """
    
    def __init__(self, agent_id: str = "research-001", config: Dict[str, Any] = None):
        super().__init__(agent_id, config or {})
        self.name = "Research Agent"
        self.category = "research"
        self.capabilities = [
            "web_search",
            "wikipedia_summary",
            "scrape_url"
        ]
        
    async def can_handle(self, task: Task) -> bool:
        """Check if task involves research"""
        keywords = ["search", "find", "lookup", "research", "scrape", "wikipedia", "google", "investigate"]
        return any(kw in task.description.lower() for kw in keywords)
    
    async def execute(self, task: Task) -> TaskResult:
        """Execute research task"""
        try:
            desc = task.description.lower()
            
            # Simple routing based on description
            if "wikipedia" in desc:
                return await self._search_wikipedia(task)
            elif "scrape" in desc or "extract" in desc:
                return await self._scrape_url(task)
            else:
                return await self._web_search(task)
                
        except Exception as e:
            return TaskResult(success=False, error=str(e))

    # --- Capabilities ---

    async def _web_search(self, task: Task) -> TaskResult:
        try:
            from googlesearch import search
        except ImportError:
            return TaskResult(success=False, error="googlesearch-python not installed")
            
        query = task.params.get("query", task.description)
        num_results = task.params.get("num_results", 5)
        
        print(f"Research Agent Searching: {query}")
        
        results = []
        try:
            # search() returns a generator
            for url in search(query, num_results=num_results, advanced=True):
                results.append({
                    "title": url.title,
                    "url": url.url,
                    "description": url.description
                })
        except Exception as e:
             return TaskResult(success=False, error=f"Search failed: {e}")

        # Save results
        output_file = f"search_{task.task_id[:8]}.json"
        
        return TaskResult(
            success=True,
            data={"results": results},
            output_path=output_file
        )

    async def _search_wikipedia(self, task: Task) -> TaskResult:
        try:
            import wikipedia
        except ImportError:
            return TaskResult(success=False, error="wikipedia library not installed")
            
        query = task.params.get("query", task.description.replace("wikipedia", "").strip())
        sentences = task.params.get("sentences", 3)
        
        try:
            summary = wikipedia.summary(query, sentences=sentences)
            page = wikipedia.page(query, auto_suggest=False)
            
            return TaskResult(
                success=True,
                data={
                    "summary": summary,
                    "url": page.url,
                    "title": page.title
                }
            )
        except wikipedia.exceptions.DisambiguationError as e:
            return TaskResult(success=False, error=f"Ambiguous query. Options: {e.options[:5]}")
        except wikipedia.exceptions.PageError:
            return TaskResult(success=False, error="Page not found")
            
    async def _scrape_url(self, task: Task) -> TaskResult:
        url = task.params.get("url")
        if not url:
            return TaskResult(success=False, error="No URL provided for scraping")
            
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Simple extraction: title and paragraphs
            title = soup.title.string if soup.title else ""
            paragraphs = [p.get_text().strip() for p in soup.find_all('p') if p.get_text().strip()]
            
            return TaskResult(
                success=True,
                data={
                    "url": url,
                    "title": title,
                    "text_content": paragraphs[:10] # Limit for now
                }
            )
        except Exception as e:
            return TaskResult(success=False, error=f"Scraping failed: {e}")