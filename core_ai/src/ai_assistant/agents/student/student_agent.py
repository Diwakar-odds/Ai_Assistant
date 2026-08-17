import random
from typing import Dict, Any, List

from ...models import Task, TaskResult
from ..base_agent import BaseAgent

class StudentAgent(BaseAgent):
    """
    Handles educational tasks (Math, Quizzes, Study).
    """
    
    def __init__(self, agent_id: str = "student_01", config: Dict[str, Any] = None):
        super().__init__(agent_id, config or {})
        self.name = "Student Agent"
        self.description = "Helps with studying and math."
        self.capabilities = ["solve_math", "generate_quiz", "summarize_notes"]
        
    async def can_handle(self, task: Task) -> bool:
        """Check if task is educational"""
        keywords = ["math", "quiz", "study", "homework", "learn", "solve", "question", "exam"]
        return any(kw in task.description.lower() for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        """Execute student tasks"""
        description = task.description.lower()
        
        if "quiz" in description or "exam" in description:
            return await self._generate_quiz(task)
        elif "math" in description or "solve" in description:
            return await self._solve_math(task)
            
        return TaskResult(success=False, error="Unknown educational task intent")

    async def _solve_math(self, task: Task) -> TaskResult:
        """Solve a math problem (Mock)"""
        problem = task.description
        # In reality, would use WolframAlpha or LLM
        print(f"[{self.name}] 🧠 Solving: {problem}")
        
        return TaskResult(
             success=True,
             data={"solution": "42 (This is a mock solution)"}
        )

    async def _generate_quiz(self, task: Task) -> TaskResult:
        """Generate a quiz"""
        topic = task.params.get("topic", "General Knowledge")
        num_questions = task.params.get("count", 3)
        
        print(f"[{self.name}] 📝 Generating {num_questions} questions on {topic}...")
        
        questions = []
        for i in range(num_questions):
            questions.append({
                "id": i+1,
                "question": f"Question about {topic} #{i+1}?",
                "options": ["Option A", "Option B", "Option C"],
                "answer": "Option A"
            })
            
        return TaskResult(
            success=True,
            data={"quiz": list(questions)}
        )
