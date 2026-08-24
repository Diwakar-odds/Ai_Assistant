import asyncio
from typing import Dict, Any, List

from ...models import Task, TaskResult
from ..base_agent import BaseAgent

class CommunicationAgent(BaseAgent):
    """
    Handles communications (Email, Messaging, Social).
    """
    
    def __init__(self, agent_id: str = "communication_01", config: Dict[str, Any] = None):
        super().__init__(agent_id, config or {})
        self.name = "Communication Agent"
        self.description = "Manages emails and messages."
        self.capabilities = ["send_email", "send_message", "post_social"]
        
    async def can_handle(self, task: Task) -> bool:
        """Check if task involves communication"""
        keywords = ["email", "send", "message", "post", "social", "whatsapp", "gmail"]
        return any(kw in task.description.lower() for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        """Execute communication tasks"""
        description = task.description.lower()
        
        if "email" in description:
            return await self._send_email(task)
        elif "message" in description or "whatsapp" in description:
            return await self._send_message(task)
            
        return TaskResult(success=False, error="Unknown communication task intent")

    async def _send_email(self, task: Task) -> TaskResult:
        """Simulate sending email"""
        recipient = task.params.get("to", "unknown@example.com")
        subject = task.params.get("subject", "No Subject")
        body = task.params.get("body", task.description)
        
        print(f"[{self.name}] 📧 Sending Email to {recipient}...")
        print(f"    Subject: {subject}")
        # print(f"    Body: {body[:50]}...")
        
        await asyncio.sleep(1) # Sim latency
        
        return TaskResult(
            success=True, 
            data={"status": "sent", "recipient": recipient, "type": "email"}
        )

    async def _send_message(self, task: Task) -> TaskResult:
        """Simulate sending instant message"""
        recipient = task.params.get("to", "unknown_user")
        body = task.params.get("body", task.description)
        
        print(f"[{self.name}] 💬 Sending Message to {recipient}...")
        
        await asyncio.sleep(0.5)
        
        return TaskResult(
            success=True,
            data={"status": "delivered", "recipient": recipient, "type": "message"}
        )