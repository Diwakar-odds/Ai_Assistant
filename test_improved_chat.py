#!/usr/bin/env python3
"""
Test improved chat responses with more diverse inputs
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
        if param == 'popular music':
            return f"🎵 Playing popular music playlist"
        else:
            return f"🎵 Playing {param}"
    else:
        return f"Action {action} executed with {param}"

def test_improved_chat():
    """Test improved chat responses"""
    print("🔍 Testing Improved Chat System...")
    print("="*60)
    
    # Initialize AI with automation callback
    ai = AdvancedConversationalAI(automation_callback=test_automation_callback)
    
    # Test various conversation patterns
    test_messages = [
        # Basic greetings and conversation
        "hello there",
        "hi how are you doing",
        "good morning",
        
        # Questions about capabilities  
        "what can you help me with",
        "tell me what you do",
        "what are your features",
        
        # Music requests (improved handling)
        "play music",
        "play some music",
        "play believer",
        "play something by coldplay",
        
        # Various command types
        "open chrome browser",
        "search for machine learning",
        "help me with something",
        "i need assistance with tasks",
        
        # Thank you and social
        "thank you so much",
        "who are you",
        "tell me about yourself",
        
        # Vague requests (should get helpful responses)
        "do something cool",
        "help",
        "can you assist me"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n{i}. User: {message}")
        response = ai.process_message(message)
        print(f"   AI: {response}")
        print("-" * 50)

if __name__ == "__main__":
    test_improved_chat()