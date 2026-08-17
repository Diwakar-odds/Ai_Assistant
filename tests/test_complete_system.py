"""
Complete System Test - Multi-Step Task Execution
Tests the full stack: Parser → Context → Orchestrator → App Controller
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import logging
from ai_assistant.core.task_chain_orchestrator import get_orchestrator
from ai_assistant.core.conversation_context import get_context_manager
from ai_assistant.ai.multi_step_parser import MultiStepCommandParser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_parser():
    """Test multi-step command parser."""
    print("\n" + "="*70)
    print("TEST 1: MULTI-STEP COMMAND PARSER")
    print("="*70 + "\n")
    
    parser = MultiStepCommandParser()
    
    test_commands = [
        "WhatsApp खोलो, मॉम को message करो",
        "YouTube खोलो, video play करो, 20 minutes skip करो",
        "Notepad open करो, Hello World लिखो",
        "Calculator खोलो फिर Chrome खोलो",
    ]
    
    for cmd in test_commands:
        print(f"\nCommand: {cmd}")
        print("-" * 70)
        
        steps = parser.parse_command(cmd)
        
        for step in steps:
            print(f"  Step {step.step}:")
            print(f"    Intent: {step.intent}")
            print(f"    Params: {step.params}")
            print(f"    Dependencies: {step.dependencies}")
        
        print()
    
    print("✅ Parser test complete!\n")


def test_context_manager():
    """Test conversation context manager."""
    print("\n" + "="*70)
    print("TEST 2: CONVERSATION CONTEXT MANAGER")
    print("="*70 + "\n")
    
    context = get_context_manager()
    context.reset()  # Start fresh
    
    print("1. Setting context variables...")
    context.set_var('current_app', 'whatsapp')
    context.set_var('selected_contact', 'Mom')
    
    print(f"   current_app = {context.get_var('current_app')}")
    print(f"   selected_contact = {context.get_var('selected_contact')}")
    
    print("\n2. Adding commands to history...")
    context.add_command("WhatsApp खोलो", intent="open_app", completed=True)
    context.add_command("मॉम को message करो", intent="send_message", completed=False)
    
    history = context.get_command_history(limit=5)
    print(f"   Command history: {len(history)} commands")
    for h in history:
        print(f"     - {h['command']} (completed={h['completed']})")
    
    print("\n3. Testing override detection...")
    is_override = context.is_override("नहीं, Papa को message करो")
    print(f"   Is override? {is_override}")
    
    print("\n4. Context summary:")
    summary = context.get_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    print("\n✅ Context manager test complete!\n")


def test_orchestrator_basic():
    """Test basic orchestrator functionality."""
    print("\n" + "="*70)
    print("TEST 3: TASK CHAIN ORCHESTRATOR - BASIC")
    print("="*70 + "\n")
    
    orchestrator = get_orchestrator()
    context = get_context_manager()
    context.reset()
    
    print("Test: Single app open command")
    print("-" * 70)
    
    result = orchestrator.execute_command("Notepad खोलो")
    
    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Steps completed: {result.steps_completed}/{result.total_steps}")
    print(f"  Message: {result.message}")
    
    if result.error:
        print(f"  Error: {result.error}")
    
    input("\nNotepad should be open. Press Enter to continue...")
    
    print("\n✅ Basic orchestrator test complete!\n")


def test_orchestrator_multistep():
    """Test multi-step command execution."""
    print("\n" + "="*70)
    print("TEST 4: TASK CHAIN ORCHESTRATOR - MULTI-STEP")
    print("="*70 + "\n")
    
    orchestrator = get_orchestrator()
    context = get_context_manager()
    context.reset()
    
    print("Test: Multi-step command")
    print("-" * 70)
    print("Command: 'Notepad खोलो, Hello from AI लिखो'")
    print()
    
    result = orchestrator.execute_command("Notepad खोलो, Hello from AI लिखो")
    
    print(f"\nResult:")
    print(f"  Success: {result.success}")
    print(f"  Steps completed: {result.steps_completed}/{result.total_steps}")
    print(f"  Message: {result.message}")
    
    print(f"\nStep details:")
    for i, step_result in enumerate(result.results, 1):
        print(f"  Step {i}:")
        print(f"    Intent: {step_result.get('intent')}")
        print(f"    Success: {step_result.get('success')}")
        if not step_result.get('success'):
            print(f"    Error: {step_result.get('error')}")
    
    input("\nNotepad should show 'Hello from AI'. Press Enter to continue...")
    
    print("\n✅ Multi-step orchestrator test complete!\n")


def test_context_awareness():
    """Test context-aware command execution."""
    print("\n" + "="*70)
    print("TEST 5: CONTEXT-AWARE EXECUTION")
    print("="*70 + "\n")
    
    orchestrator = get_orchestrator()
    context = get_context_manager()
    context.reset()
    
    print("Step 1: Open Notepad")
    result1 = orchestrator.execute_command("Notepad खोलो")
    print(f"  Result: {result1.success}")
    print(f"  Current app in context: {context.get_var('current_app')}")
    
    input("\nNotepad open. Press Enter...")
    
    print("\nStep 2: Type without specifying app (should infer from context)")
    result2 = orchestrator.execute_command("Testing context awareness लिखो")
    print(f"  Result: {result2.success}")
    print(f"  Context used app: {context.get_var('current_app')}")
    
    input("\nText should appear in Notepad. Press Enter...")
    
    print("\n✅ Context awareness test complete!\n")


def test_full_workflow():
    """Test complete workflow with multiple apps."""
    print("\n" + "="*70)
    print("TEST 6: COMPLETE WORKFLOW")
    print("="*70 + "\n")
    
    orchestrator = get_orchestrator()
    context = get_context_manager()
    context.reset()
    
    workflows = [
        {
            'name': 'Notepad Workflow',
            'command': 'Notepad खोलो, Testing complete system लिखो',
            'description': 'Open Notepad and type text'
        },
        {
            'name': 'Calculator Workflow',
            'command': 'Calculator खोलो',
            'description': 'Open Calculator'
        },
    ]
    
    for i, workflow in enumerate(workflows, 1):
        print(f"\nWorkflow {i}: {workflow['name']}")
        print(f"Description: {workflow['description']}")
        print(f"Command: {workflow['command']}")
        print("-" * 70)
        
        result = orchestrator.execute_command(workflow['command'])
        
        print(f"  Success: {result.success}")
        print(f"  Steps: {result.steps_completed}/{result.total_steps}")
        
        if result.error:
            print(f"  Error: {result.error}")
        
        input("Press Enter to continue to next workflow...")
    
    print("\n✅ Complete workflow test done!\n")


def interactive_test():
    """Interactive testing mode."""
    print("\n" + "="*70)
    print("INTERACTIVE TEST MODE")
    print("="*70 + "\n")
    
    orchestrator = get_orchestrator()
    context = get_context_manager()
    
    print("Enter commands to test the complete system.")
    print("Examples:")
    print("  - 'Notepad खोलो, Hello लिखो'")
    print("  - 'Calculator खोलो फिर Notepad खोलो'")
    print("  - 'quit' to exit")
    print()
    
    while True:
        command = input("\n🤖 Enter command: ").strip()
        
        if command.lower() in ['quit', 'exit', 'q']:
            break
        
        if not command:
            continue
        
        if command == 'status':
            status = orchestrator.get_current_status()
            print("\n📊 Current Status:")
            for key, value in status.items():
                print(f"  {key}: {value}")
            continue
        
        if command == 'context':
            summary = context.get_summary()
            print("\n📝 Context Summary:")
            for key, value in summary.items():
                print(f"  {key}: {value}")
            continue
        
        if command == 'reset':
            context.reset()
            print("✅ Context reset")
            continue
        
        # Execute command
        print(f"\n⚙️  Executing: {command}")
        print("-" * 70)
        
        result = orchestrator.execute_command(command)
        
        print(f"\n📋 Result:")
        print(f"  Success: {'✅' if result.success else '❌'} {result.success}")
        print(f"  Steps: {result.steps_completed}/{result.total_steps}")
        print(f"  Message: {result.message}")
        
        if result.error:
            print(f"  ⚠️  Error: {result.error}")
        
        # Show context changes
        print(f"\n🔍 Context:")
        print(f"  Current app: {context.get_var('current_app')}")
        print(f"  Last action: {context.get_var('last_action')}")
    
    print("\nExiting interactive mode...")


def main():
    """Main test runner."""
    print("\n" + "="*70)
    print("COMPLETE SYSTEM TEST SUITE")
    print("Multi-Step Task Execution System")
    print("="*70)
    
    print("\nSelect test mode:")
    print("1. Parser only")
    print("2. Context manager only")
    print("3. Basic orchestrator")
    print("4. Multi-step orchestrator")
    print("5. Context awareness")
    print("6. Complete workflow")
    print("7. Interactive mode")
    print("8. Run all tests (1-6)")
    print()
    
    choice = input("Enter choice (1-8): ").strip()
    
    if choice == '1':
        test_parser()
    elif choice == '2':
        test_context_manager()
    elif choice == '3':
        test_orchestrator_basic()
    elif choice == '4':
        test_orchestrator_multistep()
    elif choice == '5':
        test_context_awareness()
    elif choice == '6':
        test_full_workflow()
    elif choice == '7':
        interactive_test()
    elif choice == '8':
        test_parser()
        test_context_manager()
        test_orchestrator_basic()
        test_orchestrator_multistep()
        test_context_awareness()
        test_full_workflow()
    else:
        print("Invalid choice")
        return
    
    print("\n" + "="*70)
    print("ALL TESTS COMPLETE! ✅")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
