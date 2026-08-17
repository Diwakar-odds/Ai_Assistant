import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(r"c:\users\hp\appdata\roaming\python\python39\site-packages")

from ai_assistant.agents.loader import AgentLoader
from ai_assistant.workflow.orchestrator import WorkflowOrchestrator

async def main():
    print("Testing Workflow Orchestration...")
    
    # 1. Load Registry
    registry = AgentLoader.load_all_agents()
    
    # 2. Init Orchestrator
    orchestrator = WorkflowOrchestrator(registry)
    
    # 3. Run Pipeline
    topic = "The Planet Mars"
    results = await orchestrator.run_video_pipeline(topic)
    
    # 4. Verify
    if "error" in results:
        print(f"❌ Pipeline Failed: {results['error']}")
    else:
        print("\n✅ Pipeline Execution Successful!")
        print("Detailed Results:")
        for stage, data in results.items():
            print(f"  - {stage.upper()}: {str(data)[:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
