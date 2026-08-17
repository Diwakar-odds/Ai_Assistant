"""
VLM Quick Demo Script

Demonstrates the new Vision Language Model capabilities.
Run this to test that everything is working.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def demo_screen_analysis():
    """Demo 1: Analyze current screen."""
    print("\n" + "=" * 70)
    print("DEMO 1: Screen Analysis with VLM")
    print("=" * 70)
    
    try:
        from ai_assistant.multimodal import MultiModalAI
        
        print("\n[1] Initializing MultiModalAI...")
        vlm = MultiModalAI(use_new_architecture=True)
        print(f"    Using new architecture: {vlm.use_new_architecture}")
        
        print("\n[2] Capturing and analyzing screen...")
        print("    This will take a few seconds...")
        
        result = vlm.analyze_screen("Describe what applications and windows are visible")
        
        if isinstance(result, dict) and "analysis" in result:
            print("\n[3] VLM Analysis Result:")
            print("-" * 70)
            print(result["analysis"])
            print("-" * 70)
            return True
        else:
            print(f"\n[!] Unexpected result: {result}")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False


def demo_ui_element_detection():
    """Demo 2: Find UI elements on screen."""
    print("\n" + "=" * 70)
    print("DEMO 2: UI Element Detection")
    print("=" * 70)
    
    try:
        from ai_assistant.multimodal import MultiModalAI
        
        print("\n[1] Initializing VLM...")
        vlm = MultiModalAI()
        
        print("\n[2] Identifying all UI actions on screen...")
        result = vlm.identify_ui_actions()
        
        elements = result.get("elements", [])
        
        if elements:
            print(f"\n[3] Found {len(elements)} interactive elements:")
            print("-" * 70)
            for i, elem in enumerate(elements[:5]):  # Show first 5
                print(f"\n  Element {i+1}:")
                print(f"    Type: {elem.get('type', 'unknown')}")
                print(f"    Text: {elem.get('text', 'N/A')}")
                print(f"    Location: {elem.get('location', 'N/A')}")
            
            if len(elements) > 5:
                print(f"\n  ... and {len(elements) - 5} more elements")
            print("-" * 70)
            return True
        else:
            print("\n[!] No elements found")
            print(f"    Raw response: {result.get('raw_analysis', '')[:200]}...")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False


def demo_coordinate_extraction():
    """Demo 3: Extract coordinates of specific element."""
    print("\n" + "=" * 70)
    print("DEMO 3: Coordinate Extraction")
    print("=" * 70)
    
    print("\nWhat element would you like to find?")
    print("Examples: 'Start button', 'search bar', 'close button'")
    element = input("\nElement description: ").strip()
    
    if not element:
        element = "taskbar"
        print(f"Using default: '{element}'")
    
    try:
        from ai_assistant.multimodal import MultiModalAI
        
        print(f"\n[1] Looking for: {element}")
        vlm = MultiModalAI()
        
        result = vlm.extract_coordinates(element)
        
        print("\n[2] Result:")
        print("-" * 70)
        
        if result.get("found"):
            print(f"  ✓ Element found!")
            print(f"  Type: {result.get('element_type')}")
            print(f"  Text: {result.get('text', 'N/A')}")
            print(f"  Location: {result.get('location')}")
            
            coords = result.get('coordinates', {})
            if coords:
                print(f"  Coordinates: x={coords.get('x')}, y={coords.get('y')}")
            
            print(f"  Clickable: {result.get('clickable')}")
        else:
            print(f"  ✗ Element not found")
            print(f"  Reason: {result.get('reason', 'Unknown')}")
        
        print("-" * 70)
        return result.get("found", False)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False


def demo_task_planning():
    """Demo 4: AI task planning."""
    print("\n" + "=" * 70)
    print("DEMO 4: Automated Task Planning")
    print("=" * 70)
    
    print("\nDescribe a task you want to automate:")
    print("Examples:")
    print("  - 'save this file'")
    print("  - 'open the File menu'")
    print("  - 'minimize this window'")
    
    task = input("\nTask: ").strip()
    
    if not task:
        task = "close this window"
        print(f"Using default: '{task}'")
    
    try:
        from ai_assistant.multimodal import MultiModalAI
        
        print(f"\n[1] Analyzing task: {task}")
        vlm = MultiModalAI()
        
        plan = vlm.analyze_for_automation(task)
        
        print("\n[2] Task Plan:")
        print("-" * 70)
        
        if plan.get("possible"):
            print("  ✓ Task is possible!")
            
            steps = plan.get("steps", [])
            if steps:
                print(f"\n  Steps ({len(steps)}):")
                for i, step in enumerate(steps):
                    action = step.get('action', 'unknown')
                    target = step.get('target', 'N/A')
                    details = step.get('details', '')
                    print(f"    {i+1}. {action}: {target}")
                    if details:
                        print(f"       → {details}")
            
            warnings = plan.get("warnings", [])
            if warnings:
                print(f"\n  Warnings:")
                for warning in warnings:
                    print(f"    ! {warning}")
        else:
            print("  ✗ Task not possible")
            print(f"  Reason: {plan.get('error', 'Unknown')}")
        
        print("-" * 70)
        return plan.get("possible", False)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return False


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("VLM INTEGRATION DEMONSTRATION")
    print("=" * 70)
    print("\nThis script demonstrates the new Vision Language Model capabilities.")
    print("Make sure you have GEMINI_API_KEY set in your .env file.")
    
    # Check API key
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv("GEMINI_API_KEY"):
        print("\n[ERROR] GEMINI_API_KEY not found in environment!")
        print("Please set it in .env file or environment variables.")
        return 1
    
    demos = [
        ("Screen Analysis", demo_screen_analysis),
        ("UI Element Detection", demo_ui_element_detection),
        ("Coordinate Extraction", demo_coordinate_extraction),
        ("Task Planning", demo_task_planning),
    ]
    
    print("\n\nAvailable Demos:")
    for i, (name, _) in enumerate(demos):
        print(f"  {i+1}. {name}")
    print("  0. Run all demos")
    
    choice = input("\nSelect demo (0-4): ").strip()
    
    if choice == "0":
        # Run all
        results = []
        for name, demo_func in demos:
            try:
                success = demo_func()
                results.append((name, success))
            except Exception as e:
                print(f"\n[!] {name} crashed: {e}")
                results.append((name, False))
        
        # Summary
        print("\n" + "=" * 70)
        print("DEMO SUMMARY")
        print("=" * 70)
        for name, success in results:
            status = "PASS" if success else "FAIL"
            print(f"  [{status}] {name}")
        
        passed = sum(1 for _, s in results if s)
        print(f"\nTotal: {passed}/{len(results)} demos successful")
        
        return 0 if passed == len(results) else 1
        
    elif choice in ["1", "2", "3", "4"]:
        idx = int(choice) - 1
        name, demo_func = demos[idx]
        
        try:
            success = demo_func()
            
            print(f"\n{'='*70}")
            print(f"Demo Result: {'SUCCESS' if success else 'FAILED'}")
            print('='*70)
            
            return 0 if success else 1
        except Exception as e:
            print(f"\n[ERROR] Demo crashed: {e}")
            return 1
    else:
        print("\nInvalid choice")
        return 1


if __name__ == "__main__":
    exit(main())
