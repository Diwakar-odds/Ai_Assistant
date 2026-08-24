import asyncio
from typing import Dict, Any, List

from ...models import Task, TaskResult
from ..base_agent import BaseAgent

class WebAgent(BaseAgent):
    """
    Handles general web automation (Forms, Interaction, Dynamic Scraping).
    """
    
    def __init__(self, agent_id: str = "web_01", config: Dict[str, Any] = None):
        super().__init__(agent_id, config or {})
        self.name = "Web Agent"
        self.description = "Automates browser interactions."
        self.capabilities = ["browse_page", "fill_form", "click_element"]
        
    async def can_handle(self, task: Task) -> bool:
        """Check if task involves web interaction"""
        keywords = ["browser", "website", "fill", "form", "login", "click", "interact", "scrape dynamic"]
        return any(kw in task.description.lower() for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        """Execute web tasks"""
        description = task.description.lower()
        url = task.params.get("url")
        
        if "fill" in description or "form" in description:
            return await self._fill_form(task)
        elif "click" in description or "interact" in description:
            return await self._interact(task)
        elif "browse" in description or "visit" in description:
            return await self._browse(task)
            
        return TaskResult(success=False, error="Unknown web task intent")

    async def _browse(self, task: Task) -> TaskResult:
        """Visit a URL"""
        url = task.params.get("url")
        print(f"[{self.name}] 🌐 Visiting: {url}...")
        await asyncio.sleep(1)
        return TaskResult(success=True, data={"title": "Page Title Placeholder", "url": url})

    async def _fill_form(self, task: Task) -> TaskResult:
        """Fill a web form"""
        url = task.params.get("url")
        fields = task.params.get("fields", {})
        
        print(f"[{self.name}] 📝 Filling form at {url}...")
        for field, value in fields.items():
            print(f"    - Setting '{field}' to '{value}'")
            
        await asyncio.sleep(1.5)
        return TaskResult(success=True, data={"status": "submitted", "fields": list(fields.keys())})

    async def _interact(self, task: Task) -> TaskResult:
        """Click or Type"""
        action = task.params.get("action", "click")
        selector = task.params.get("selector", "body")
        
        print(f"[{self.name}] 🖱️ Action {action} on {selector}...")
        return TaskResult(success=True, data={"status": "completed"})