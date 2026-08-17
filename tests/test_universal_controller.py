"""
Test script for Universal App Controller
Demonstrates how it works with ANY app without specific code.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ai_assistant.core.universal_app_controller import get_universal_controller
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_basic_operations():
    """Test basic app operations."""
    print("\n" + "="*60)
    print("TESTING UNIVERSAL APP CONTROLLER")
    print("="*60 + "\n")
    
    controller = get_universal_controller()
    
    # Test 1: Open Notepad (simple app)
    print("\n[Test 1] Opening Notepad...")
    result = controller.execute_action("Notepad", "open", {})
    print(f"Result: {result}")
    
    input("\nNotepad should be open. Press Enter to continue...")
    
    # Test 2: Type text in Notepad
    print("\n[Test 2] Typing text in Notepad...")
    result = controller.execute_action("Notepad", "type_text", {
        "text": "Hello from Universal App Controller!\nThis works with ANY app!"
    })
    print(f"Result: {result}")
    
    input("\nText should appear in Notepad. Press Enter to continue...")
    
    # Test 3: Check active apps
    print("\n[Test 3] Checking active apps...")
    active_apps = controller.get_active_apps()
    print(f"Active apps: {active_apps}")
    
    # Test 4: Close Notepad
    print("\n[Test 4] Closing Notepad...")
    result = controller.close_app("Notepad")
    print(f"Result: {result}")
    
    print("\n" + "="*60)
    print("BASIC TESTS COMPLETE")
    print("="*60 + "\n")


def test_app_discovery_integration():
    """Test integration with existing AppDiscovery."""
    print("\n" + "="*60)
    print("TESTING APP DISCOVERY INTEGRATION")
    print("="*60 + "\n")
    
    controller = get_universal_controller()
    
    print("Available actions:")
    print("1. Open any installed app")
    print("2. Type 'list' to see installed apps")
    print("3. Type 'quit' to exit")
    
    while True:
        app_name = input("\nEnter app name (or command): ").strip()
        
        if app_name.lower() == 'quit':
            break
        
        if app_name.lower() == 'list':
            from ai_assistant.modules.app_discovery import app_discovery
            apps = app_discovery.get_all_apps()
            print(f"\nInstalled apps (showing first 20):")
            for i, (name, path) in enumerate(list(apps.items())[:20]):
                print(f"  {i+1}. {name}")
            continue
        
        if not app_name:
            continue
        
        print(f"\nOpening {app_name}...")
        result = controller.open_app(app_name)
        print(f"Result: {result}")
        
        if result['success']:
            print(f"\n{app_name} is now open!")
            print("What would you like to do?")
            print("1. Type 'close' to close it")
            print("2. Type 'type <text>' to type in it")
            print("3. Press Enter to continue")
            
            action = input("> ").strip()
            
            if action == 'close':
                controller.close_app(app_name)
                print(f"{app_name} closed.")
            elif action.startswith('type '):
                text = action[5:]
                controller.execute_action(app_name, "type_text", {"text": text})
                print(f"Typed: {text}")


def demo_multi_app_workflow():
    """Demonstrate multi-app workflow."""
    print("\n" + "="*60)
    print("DEMO: MULTI-APP WORKFLOW")
    print("="*60 + "\n")
    
    print("This demo will:")
    print("1. Open Notepad")
    print("2. Type a message")
    print("3. Open Calculator")
    print("4. Show both apps are managed")
    print()
    
    input("Press Enter to start...")
    
    controller = get_universal_controller()
    
    # Step 1: Open Notepad
    print("\n[Step 1] Opening Notepad...")
    controller.open_app("Notepad")
    
    # Step 2: Type in Notepad
    print("[Step 2] Typing in Notepad...")
    controller.execute_action("Notepad", "type_text", {
        "text": "Multi-app workflow demo!\n\nThis is Notepad."
    })
    
    input("\nNotepad ready. Press Enter to continue...")
    
    # Step 3: Open Calculator
    print("\n[Step 3] Opening Calculator...")
    controller.open_app("Calculator")
    
    input("\nCalculator open. Press Enter to continue...")
    
    # Step 4: Show managed apps
    print("\n[Step 4] Active apps:")
    active_apps = controller.get_active_apps()
    for app in active_apps:
        info = controller.get_app_info(app)
        print(f"  - {app}: {info}")
    
    print("\n[Cleanup] Closing apps...")
    controller.close_app("Notepad")
    controller.close_app("Calculator")
    
    print("\nDemo complete!")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("UNIVERSAL APP CONTROLLER - TEST SUITE")
    print("="*60)
    print("\nSelect test:")
    print("1. Basic operations (Notepad)")
    print("2. App discovery integration")
    print("3. Multi-app workflow demo")
    print("4. Run all tests")
    print()
    
    choice = input("Enter choice (1-4): ").strip()
    
    if choice == '1':
        test_basic_operations()
    elif choice == '2':
        test_app_discovery_integration()
    elif choice == '3':
        demo_multi_app_workflow()
    elif choice == '4':
        test_basic_operations()
        test_app_discovery_integration()
        demo_multi_app_workflow()
    else:
        print("Invalid choice")
    
    print("\nAll tests complete! ✅")
