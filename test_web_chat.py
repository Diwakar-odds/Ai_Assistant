#!/usr/bin/env python3
"""
Simple chat API test - tests the conversational AI directly with automation callback
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.conversational_ai import AdvancedConversationalAI

def test_automation_callback(action, param):
    """Test automation callback that simulates real automation tools"""
    print(f"🔧 Automation: {action}({param})")
    
    if action == 'open_application':
        return f"Opened {param} successfully"
    elif action == 'search_google':
        return f"Searching Google for '{param}'"
    elif action == 'play_music':
        if param == 'popular music':
            return f"Playing popular music playlist"
        else:
            return f"Playing '{param}'"
    elif action == 'close_application':
        return f"Closed {param}"
    elif action == 'set_volume':
        return f"Volume set to {param}%"
    else:
        return f"Executed {action} with parameter: {param}"

def simulate_web_chat():
    """Simulate the web chat interface"""
    print("💬 YourDaddy Assistant - Chat Interface Simulation")
    print("="*60)
    print("This simulates how your web chat interface should work.")
    print("Type 'quit' to exit.")
    print("-"*60)
    
    # Initialize the conversational AI with automation
    ai = AdvancedConversationalAI(automation_callback=test_automation_callback)
    
    while True:
        try:
            # Get user input
            user_input = input("\\n👤 You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\\n🤖 Assistant: Goodbye! Have a great day! 👋")
                break
            
            if not user_input:
                continue
            
            # Process the message
            print("\\n🤖 Assistant:", end=" ")
            response = ai.process_message(user_input)
            print(response)
            
        except KeyboardInterrupt:
            print("\\n\\n🤖 Assistant: Goodbye! Have a great day! 👋")
            break
        except Exception as e:
            print(f"\\n❌ Error: {str(e)}")

if __name__ == "__main__":
    simulate_web_chat()