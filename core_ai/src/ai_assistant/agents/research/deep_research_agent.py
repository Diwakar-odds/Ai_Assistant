import os
import json
import asyncio
import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List

from ..base_agent import BaseAgent
from ..models import Task, TaskResult
from ...local_ai_manager import LocalAIManager

class DeepResearchAgent(BaseAgent):
    """
    Replicates the 'last30days-skill' workflow:
    1. Topic Analysis
    2. Parallel Web Search
    3. LLM Synthesis
    """
    
    def __init__(self, agent_id: str = "deep-research-001", config: Dict[str, Any] = None):
        super().__init__(agent_id, config or {})
        self.name = "Deep Research Agent"
        self.category = "research"
        self.capabilities = [
            "deep_research",
            "social_synthesis",
            "multi_source_scrape"
        ]
        self.ai_manager = LocalAIManager()
        
    async def can_handle(self, task: Task) -> bool:
        """Check if task requires deep research/synthesis"""
        keywords = ["deep research", "synthesize", "comprehensive analysis", "market research"]
        return any(kw in task.description.lower() for kw in keywords)
    
    async def execute(self, task: Task) -> TaskResult:
        """Execute the 3-step deep research pipeline"""
        try:
            print(f"[{self.name}] Starting Deep Research pipeline for: {task.description}")
            
            # Step 1: Pre-research (Extract core queries)
            print(f"[{self.name}] Step 1: Analyzing Topic...")
            queries = self._generate_search_queries(task.description)
            print(f"[{self.name}] Generated Queries: {queries}")
            
            # Step 2: Parallel Search & Scrape
            print(f"[{self.name}] Step 2: Parallel Web Search...")
            raw_data = await self._parallel_search_and_scrape(queries)
            
            # Step 3: Synthesis
            print(f"[{self.name}] Step 3: Synthesizing Results via LLM...")
            synthesis = self._synthesize_results(task.description, raw_data)
            
            # Save results
            output_file = f"deep_research_{task.task_id[:8]}.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(synthesis)
            
            return TaskResult(
                success=True,
                data={"synthesis": synthesis, "raw_data_count": len(raw_data)},
                output_path=output_file
            )
            
        except Exception as e:
            return TaskResult(success=False, error=str(e))

    def _generate_search_queries(self, prompt: str) -> List[str]:
        """Use simple heuristics or LLM to generate targeted search queries"""
        # For robustness, we fallback to heuristic if LLM isn't loaded
        clean_prompt = prompt.lower().replace("deep research", "").replace("synthesize", "").strip()
        return [
            f"{clean_prompt} latest news",
            f"{clean_prompt} overview reddit",
            f"{clean_prompt} analysis"
        ]
        
    async def _parallel_search_and_scrape(self, queries: List[str]) -> List[Dict]:
        """Perform searches and scrape the top results"""
        try:
            from googlesearch import search
        except ImportError:
            return [{"error": "googlesearch-python not installed"}]
            
        all_results = []
        visited_urls = set()
        
        for q in queries:
            try:
                for url in search(q, num_results=2, advanced=True):
                    if url.url in visited_urls:
                        continue
                    visited_urls.add(url.url)
                    
                    # Scrape
                    content = self._scrape_text(url.url)
                    all_results.append({
                        "url": url.url,
                        "title": url.title,
                        "content": content[:1000]  # Limit context window size
                    })
            except Exception as e:
                print(f"Search failed for {q}: {e}")
                
        return all_results
        
    def _scrape_text(self, url: str) -> str:
        """Helper to scrape text from a URL"""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Remove scripts/styles
                for script in soup(["script", "style"]):
                    script.decompose()
                return " ".join(soup.stripped_strings)
            return ""
        except:
            return ""
            
    def _synthesize_results(self, original_prompt: str, raw_data: List[Dict]) -> str:
        """Use LLM to generate a final markdown brief"""
        if not self.ai_manager.is_ollama_running():
            return "ERROR: Ollama is not running. Could not synthesize data."
            
        model = self.ai_manager.find_best_available_model()
        if not model or not self.ai_manager.load_model(model):
            return "ERROR: Could not load local LLM."
            
        # Prepare context
        context = f"Topic: {original_prompt}\n\nScraped Data:\n"
        for idx, item in enumerate(raw_data):
            context += f"Source {idx+1} ({item['url']}): {item.get('content', '')}\n\n"
            
        prompt = f"""
        You are an elite research analyst. Synthesize the following scraped web data into a comprehensive Markdown report.
        Address the user's original topic: "{original_prompt}".
        
        Include:
        - Executive Summary
        - Key Findings
        - Sources (URL list)
        
        Raw Data:
        {context}
        """
        
        synthesis = self.ai_manager.generate(prompt, max_tokens=1500, temperature=0.3)
        return synthesis
