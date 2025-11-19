#!/usr/bin/env python3
"""
Debug chat responses to identify the issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.conversational_ai import AdvancedConversationalAI

def test_automation_callback(action, param):
    """Simple test automation callback"""
    print(f"Automation callback called: action='{action}', param='{param}'")
    
    if action == 'open_application':
        return f"✅ Opening {param}"
    elif action == 'search_google':
        return f"🔍 Searching for {param}"
    elif action == 'play_music':
        return f"🎵 Playing {param}"
    else:
        return f"Action {action} executed with {param}"

def test_chat():
    """Test chat responses"""
    print("🔍 Testing Chat System...")
    print("="*50)
    
    # Initialize AI with automation callback
    ai = AdvancedConversationalAI(automation_callback=test_automation_callback)
    
    # Test different types of messages
    test_messages = [
        "hello",
        "how are you",
        "what can you do",
        "open chrome",
        "play music",
        "search for python tutorial",
        "what is 10 plus 5",
        "help me",
        "i need assistance",
        "do something"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. User: {message}")
        response = ai.process_message(message)
        print(f"   AI: {response}")
        print("-" * 40)

if __name__ == "__main__":
    test_chat()