
import sys
import os
import inspect

# Add project root to path
sys.path.append(os.getcwd())

def check_module_integrity():
    print("Checking Voice System Integrity...")
    
    # Check 1: Automation Tools
    try:
        import ai_assistant.automation_tools_new as automation
        print("✅ Automation System: Connected")
        print(f"   - Functions found: {len([f for f in dir(automation) if not f.startswith('_')])}")
    except ImportError as e:
        print(f"❌ Automation System: Failed ({e})")

    # Check 2: Advanced AI (Conversational AI)
    try:
        from ai_assistant.modules.conversational_ai import AdvancedConversationalAI
        print("✅ Advanced AI Features: Connected")
        
        # Check for process_message method (used for handling voice commands)
        if hasattr(AdvancedConversationalAI, 'process_message'):
            print("   - Voice Processing Logic: Verified ('process_message' exists)")
        else:
             print("   - Voice Processing Logic: Missing 'process_message'")
             
        # Check command execution
        if hasattr(AdvancedConversationalAI, '_try_execute_command'):
             print("   - Command Execution Logic: Verified ('_try_execute_command' exists)")
        
    except ImportError as e:
        print(f"❌ Advanced AI Features: Failed ({e})")

    # Check 3: Chain of Actions
    try:
        from ai_assistant.core.chain_of_actions_manager import ChainOfActionsManager
        print("✅ Chain of Actions Method: Connected")
        print("   - Manager Class Verified")
    except ImportError as e:
        print(f"❌ Chain of Actions Method: Failed ({e})")

    # Check 4: Multi-Agent System (if applicable)
    # Usually part of ChainOfActions or specific agent modules
    try:
        from ai_assistant.core.chain_of_actions_manager import AgentType
        print("✅ Different Agents: Connected") 
    except ImportError:
        # Try finding agents directory
        if os.path.exists('ai_assistant/agents') or os.path.exists('ai_assistant/core/agents'):
            print("✅ Different Agents: Agent directories found")
        else:
            print("⚠️ Different Agents: Specific modules not found (might be implemented differently)")

if __name__ == "__main__":
    check_module_integrity()
