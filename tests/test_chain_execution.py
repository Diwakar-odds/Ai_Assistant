import asyncio
import logging
import sys
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ChainTest")

# Ensure proper path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_assistant.core.chain_of_actions_manager import get_chain_manager
from ai_assistant.core.action_chain_models import ChainStatus

async def progress_callback(progress):
    """Callback to print progress updates"""
    print(f"\n[PROGRESS] Chain: {progress.chain_id} | Progress: {progress.completed_actions}/{progress.total_actions} ({progress.progress_percentage:.1f}%)")
    print(f"Status: {progress.status}")
    if progress.current_action:
        print(f"Current Action: {progress.current_action}")

async def main():
    print("==================================================")
    print("Testing Chain of Actions System")
    print("==================================================")
    
    manager = get_chain_manager()
    
    # Test Command: Something simple for the Stub/Real implementation
    # command = "Research about recent advancements in AI agents and summarize the key findings"
    # command = "Open youtube.com"
    command = "open notepad and write hello world"
    
    print(f"\n1. Executing Command: '{command}'")
    
    start_time = time.time()
    
    try:
        # Execute the chain
        result = await manager.execute_command(
            command,
            on_progress=progress_callback
        )
        
        # Save detailed debug info
        debug_info = {
            "command": command,
            "chain_id": result.chain_id if result else None,
            "success": result.success if result else False,
            "actions": result.action_results if result else []
        }
        with open("debug_plan_output.json", "w") as f:
            json.dump(debug_info, f, indent=2)
            
        duration = time.time() - start_time
        
        print("\n==================================================")
        print(f"Execution Completed in {duration:.2f} seconds")
        print("==================================================")
        
        if result:
            print(f"Chain ID: {result.chain_id}")
            print(f"Success: {result.success}")
            print(f"Actions Completed: {result.completed_actions}/{result.total_actions}")
            
            print("\nFinal Report:")
            for action_res in result.action_results:
                status = action_res.get('status', 'unknown')
                desc = action_res.get('description', 'No description')
                print(f"- [{status}] {desc}")
                
                output = action_res.get('result', '') or action_res.get('error', '')
                if output:
                    output_str = str(output)
                    print(f"  > Output: {output_str[:100]}..." if len(output_str) > 100 else f"  > Output: {output_str}")
                
            if result.errors:
                print("\nErrors:")
                for err in result.errors:
                    print(f"- {err}")
        else:
            print("Execution failed to return a result.")
            
    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
