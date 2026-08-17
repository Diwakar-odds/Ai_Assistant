from typing import Dict, Any, List, Optional
import os

from ..base_agent import BaseAgent
from ..models import Task, TaskResult

class WriterAgent(BaseAgent):
    """
    Handles content generation, writing, and summarization using LLMs.
    """
    
    def __init__(self, agent_id: str = "writer-001", config: Dict[str, Any] = None):
        super().__init__(agent_id, config or {})
        self.name = "Writer Agent"
        self.category = "writer"
        self.capabilities = [
            "write_article",
            "summarize_text",
            "draft_email",
            "proofread"
        ]
        self._mock_mode = True  # Default to mock if api keys absent
        
    async def can_handle(self, task: Task) -> bool:
        """Check if task involves writing"""
        keywords = ["write", "draft", "summarize", "blog", "article", "email", "essay", "proofread"]
        return any(kw in task.description.lower() for kw in keywords)
    
    async def execute(self, task: Task) -> TaskResult:
        """Execute writing task"""
        try:
            desc = task.description.lower()
            topic = task.params.get("topic", desc)
            content_type = task.params.get("type", "text")
            
            # Simple simulation for now to avoid needing real API keys immediately
            # In a real scenario, this would call self.llm.generate()
            
            if self._mock_mode:
                content = self._generate_mock_content(topic, content_type)
            else:
                # TODO: Implement real LLM call
                content = f"[Real LLM generation placeholder for: {topic}]"
            
            # Save if requested
            filename = task.params.get("filename")
            output_path = None
            if filename:
                output_path = os.path.abspath(os.path.join("outputs", filename))
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return TaskResult(
                success=True,
                data={"content": content},
                output_path=output_path
            )
            
        except Exception as e:
            return TaskResult(success=False, error=str(e))

    def _generate_mock_content(self, topic: str, content_type: str) -> str:
        """Generate plausible mock content for testing"""
        if "email" in content_type.lower() or "email" in topic.lower():
            return f"""Subject: Regarding {topic}

Dear Team,

I wanted to share some updates regarding {topic}. We have made significant progress and I believe we are on track.

Best regards,
AI Assistant"""
        
        elif "summarize" in topic.lower():
             return f"Summary of {topic}: The main points are X, Y, and Z. Overall it is a positive development."
             
        else:
            return f"""# {topic.title()}

This is a generated article about {topic}. 

## Introduction
{topic} is an important subject in today's world.

## Key Points
1. Point one about {topic}
2. Point two about {topic}

## Conclusion
In conclusion, {topic} continues to evolve."""
