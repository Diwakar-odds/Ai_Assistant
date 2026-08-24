import asyncio
import sys
import os
import traceback

print("Adding path...")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
print("Path added.")

try:
    print("Importing agents.models...")
    from ai_assistant.agents.models import Task, TaskResult
    print("Imported agents.models.")
    
    print("Importing agents.base_agent...")
    from ai_assistant.agents.base_agent import BaseAgent
    print("Imported agents.base_agent.")
    
    print("Importing agents.registry...")
    from ai_assistant.agents.registry import AgentRegistry
    print("Imported agents.registry.")
    
    print("Importing core.multi_agent_coordinator...")
    from ai_assistant.core.multi_agent_coordinator import MultiAgentCoordinator
    print("Imported core.multi_agent_coordinator.")
    
except Exception as e:
    print(f"Import Error: {e}")
    traceback.print_exc()
    pass

class MockAgent(BaseAgent):
    def __init__(self):
        super().__init__("mock-agent-001", {})
        self.name = "Mock Agent"
        self.capabilities = ["mock_capability"]
        
    async def can_handle(self, task: Task) -> bool:
        return "mock" in task.description.lower()
        
    async def execute(self, task: Task) -> TaskResult:
        print(f"MockAgent executing: {task.description}")
        return TaskResult(success=True, data={"message": "Mock execution successful"})

async def main():
    try:
        print("Starting Multi-Agent Foundation Verification...")
        
        # 1. Initialize Registry
        registry = AgentRegistry()
        print("Registry initialized.")
        
        # 2. Register Mock Agent
        agent = MockAgent()
        registry.register_agent(agent)
        
        # 3. Initialize Coordinator
        coordinator = MultiAgentCoordinator(registry)
        print("Coordinator initialized.")
        
        # 4. Create Task
        task = Task(description="Run a mock test task")
        print(f"Created task: {task.description}")
        
        # 5. Execute Task
        print("Executing task...")
        result = await coordinator.execute_task(task)
        print(f"Task executed. Result: {result}")
        
        # 6. Verify Result
        if result.success and result.data.get("message") == "Mock execution successful":
            print("✅ Verification SUCCESS!")
        else:
            print(f"❌ Verification FAILED: {result}")
            
    except Exception as e:
        print(f"Runtime Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    print("Running main...")
    asyncio.run(main())
    print("Main finished.")
