"""
Quick Demo: Multi-Step Task Execution System

This demonstrates the AI-powered task planning and execution.

Usage:
    python test_task_execution.py
"""

import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ai_assistant.automation.task_planner import TaskPlanner, TaskPlan
from ai_assistant.automation.browser_automation import BrowserAutomation, YouTubeAutomation
from ai_assistant.automation.app_automation import StickyNotesAutomation, WhatsAppAutomation

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def demo_task_planning():
    """Demonstrate task planning"""
    print("\n" + "="*70)
    print("🧠 TASK PLANNING DEMONSTRATION")
    print("="*70)
    
    # Create planner
    planner = TaskPlanner(llm_provider="gemini")
    
    # Test commands
    test_commands = [
        "Open YouTube and go to history",
        "Send a WhatsApp message to mom saying hello",
        "Open sticky notes and read the notes"
    ]
    
    for cmd in test_commands:
        print(f"\n{'─'*70}")
        print(f"📝 Command: {cmd}")
        print('─'*70)
        
        try:
            plan = planner.create_plan(cmd)
            
            print(f"\n✅ Plan created: {len(plan.actions)} actions")
            print(f"   Safety level: {plan.safety_level}")
            print(f"   Requires confirmation: {plan.requires_confirmation}")
            print(f"   Estimated duration: {plan.estimated_duration}s")
            
            print(f"\n📋 Action Plan:")
            for i, action in enumerate(plan.actions, 1):
                print(f"\n   {i}. {action.type.value.upper()}")
                print(f"      Description: {action.description}")
                if action.parameters:
                    print(f"      Parameters: {action.parameters}")
                if action.dependencies:
                    print(f"      Dependencies: {action.dependencies}")
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
            logger.exception("Planning failed")


def demo_browser_automation():
    """Demonstrate browser automation"""
    print("\n" + "="*70)
    print("🌐 BROWSER AUTOMATION DEMONSTRATION")
    print("="*70)
    
    print("\n⚠️  This will open a browser window. Continue? (y/n): ", end="")
    if input().lower() != 'y':
        print("Skipped.")
        return
    
    browser = BrowserAutomation()
    
    try:
        print("\n1️⃣  Starting browser...")
        browser.start_browser()
        
        print("2️⃣  Navigating to Google...")
        browser.navigate("https://www.google.com")
        
        print("3️⃣  Finding search box...")
        if browser.type_text("search", "Python programming"):
            print("✅ Typed into search box")
        
        print("\n4️⃣  Taking screenshot...")
        screenshot_path = browser.take_screenshot("demo_screenshot.png")
        print(f"✅ Screenshot saved: {screenshot_path}")
        
        input("\nPress Enter to close browser...")
        
    finally:
        browser.close()


def demo_sticky_notes():
    """Demonstrate Sticky Notes automation"""
    print("\n" + "="*70)
    print(" 📝 STICKY NOTES DEMONSTRATION")
    print("="*70)
    
    print("\n⚠️  This requires:")
    print("   - Windows Sticky Notes app")
    print("   - Tesseract OCR installed")
    print("\nContinue? (y/n): ", end="")
    
    if input().lower() != 'y':
        print("Skipped.")
        return
    
    sticky = StickyNotesAutomation()
    
    print("\n1️⃣  Opening Sticky Notes...")
    if sticky.open_sticky_notes():
        print("✅ Sticky Notes opened")
        
        print("\n2️⃣  Reading existing notes...")
        notes = sticky.read_notes(speak=False)
        
        if notes:
            print(f"\n✅ Found {len(notes)} notes:")
            for i, note in enumerate(notes, 1):
                print(f"   {i}. {note[:100]}...")
        else:
            print("   No notes found")
        
        print("\n3️⃣  Would you like to create a test note? (y/n): ", end="")
        if input().lower() == 'y':
            sticky.create_note("Test note from automation demo")
            print("✅ Test note created")


def demo_whatsapp():
    """Demonstrate WhatsApp automation"""
    print("\n" + "="*70)
    print("💬 WHATSAPP DEMONSTRATION")
    print("="*70)
    
    print("\n⚠️  This requires:")
    print("   - WhatsApp Web logged in")
    print("   - Contact configured in config/contacts.json")
    print("\nThis is a safe demo (won't actually send).")
    print("Continue? (y/n): ", end="")
    
    if input().lower() != 'y':
        print("Skipped.")
        return
    
    whatsapp = WhatsAppAutomation()
    
    print("\n📋 WhatsApp automation would:")
    print("   1. Open WhatsApp Web")
    print("   2. Find contact")
    print("   3. Type message")
    print("   4. Send message")
    print("\n✅ Module loaded successfully")


def main():
    """Main demonstration"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║        🤖 MULTI-STEP TASK EXECUTION SYSTEM - DEMONSTRATION          ║
║                                                                      ║
║  This demo showcases the AI-powered task planning and execution     ║
║  system that can handle complex commands like:                      ║
║                                                                      ║
║  • "Open YouTube, go to history and clear it"                       ║
║  • "Open sticky notes and recite the notes"                         ║
║  • "Send a WhatsApp message to mom"                                 ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    print("\nChoose a demonstration:")
    print("1. 🧠 Task Planning (AI-powered command decomposition)")
    print("2. 🌐 Browser Automation (Element detection & interaction)")
    print("3. 📝 Sticky Notes Automation (OCR & TTS)")
    print("4. 💬 WhatsApp Automation (Message sending)")
    print("5. 🎯 Run all demos")
    print("0. Exit")
    
    choice = input("\nEnter choice (0-5): ").strip()
    
    if choice == '1':
        demo_task_planning()
    elif choice == '2':
        demo_browser_automation()
    elif choice == '3':
        demo_sticky_notes()
    elif choice == '4':
        demo_whatsapp()
    elif choice == '5':
        demo_task_planning()
        demo_browser_automation()
        demo_sticky_notes()
        demo_whatsapp()
    elif choice == '0':
        print("\n👋 Goodbye!")
        return
    else:
        print("\n❌ Invalid choice")
        return
    
    print("\n" + "="*70)
    print("✅ DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("• Integrate with conversational AI")
    print("• Add global keyboard shortcuts")
    print("• Implement screen reading & translation")
    print("• Create web UI for task visualization")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        logger.exception("Demo failed")
