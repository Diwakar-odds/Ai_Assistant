import asyncio
from typing import Optional

class InteractionManager:
    """
    Manages direct interaction with the human user.
    Supports asking questions and requesting approval.
    """
    
    def __init__(self):
        self.mode = "cli" # or 'api', 'gui'

    async def ask_user(self, question: str) -> str:
        """
        Ask the user a question and get a text response.
        """
        print(f"\n\n# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

[SYSTEM] ❓ Question: {question}")
        # In a real async web app, this would push a socket event and wait.
        # For CLI, we use input (blocking, so run in thread if needed)
        
        # Simulating non-blocking input for this environment logic
        # return await asyncio.to_thread(input, ">> ")
        
        # Mock for automation context
        print(">> (Mock User): Proceed")
        return "Proceed"

    async def request_approval(self, action_description: str) -> bool:
        """
        Request Yes/No approval for an action.
        """
        print(f"\n[SYSTEM] ⚠️ Approval Required: {action_description}")
        print("[SYSTEM] Proceed? (y/n)")
        
        # Mock
        print(">> (Mock User): y")
        return True
