#!/usr/bin/env python3
"""
Comprehensive test for improved chat functionality
Tests all chat features and conversation patterns
"""

import sys
import os
import json
import requests
import time
import threading

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.conversational_ai import AdvancedConversationalAI

def test_conversational_responses():
    """Test the improved conversational AI responses"""
    print("\n" + "="*60)
    print("TESTING CONVERSATIONAL AI RESPONSES")
    print("="*60)
    
    # Initialize the conversational AI
    ai = AdvancedConversationalAI()
    
    # Test cases for various conversation patterns
    test_cases = [
        # Greetings
        ("hello", "greeting"),
        ("hi there", "greeting"),
        ("good morning", "greeting"),
        
        # Questions
        ("how are you?", "wellbeing"),
        ("what can you do?", "capabilities"),
        ("what's your name?", "identity"),
        
        # Commands
        ("play music", "music_command"),
        ("play something by coldplay", "music_command"),
        ("open notepad", "app_command"),
        ("search for python tutorials", "search_command"),
        
        # Casual conversation
        ("tell me a joke", "entertainment"),
        ("what's the weather like?", "information"),
        ("I'm feeling sad", "emotional_support"),
        ("that's awesome", "acknowledgment"),
        
        # Complex queries
        ("can you help me learn python programming?", "learning_assistance"),
        ("I need to organize my schedule", "productivity"),
        ("how do I fix my computer?", "technical_support"),
    ]
    
    results = []
    for query, expected_category in test_cases:
        print(f"\nTesting: '{query}'")
        print("-" * 40)
        
        try:
            response = ai.process_message(query)
            print(f"Response: {response}")
            
            # Check if response is appropriate (not too generic)
            is_appropriate = (
                len(response) > 20 and  # Not too short
                "I understand" not in response or len(response) > 50 and  # Not just generic understanding
                response != "I'm here to help you with various tasks and conversations." and
                "general assistance" not in response.lower()
            )
            
            results.append({
                'query': query,
                'response': response,
                'appropriate': is_appropriate,
                'category': expected_category
            })
            
            print(f"✓ Appropriate: {is_appropriate}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'query': query,
                'response': f"Error: {e}",
                'appropriate': False,
                'category': expected_category
            })
    
    return results

def test_command_processing():
    """Test command processing capabilities"""
    print("\n" + "="*60)
    print("TESTING COMMAND PROCESSING")
    print("="*60)
    
    # Initialize conversational AI (which handles commands)
    ai = AdvancedConversationalAI()
    
    command_tests = [
        "play music by the beatles",
        "open calculator",
        "search google for machine learning",
        "set a timer for 5 minutes",
        "what's the time",
        "open file manager",
        "play video",
        "take a screenshot"
    ]
    
    for command in command_tests:
        print(f"\nTesting command: '{command}'")
        print("-" * 40)
        
        try:
            # Test through conversational AI
            response = ai.process_message(command)
            print(f"AI Response: {response}")
            
        except Exception as e:
            print(f"❌ Error processing command: {e}")

def test_web_api():
    """Test the web API endpoints"""
    print("\n" + "="*60)
    print("TESTING WEB API")
    print("="*60)
    
    # Start the backend in a separate thread
    def start_backend():
        try:
            import modern_web_backend
        except Exception as e:
            print(f"Could not start backend: {e}")
    
    # Start backend
    backend_thread = threading.Thread(target=start_backend, daemon=True)
    backend_thread.start()
    
    # Wait for backend to start
    print("Waiting for backend to start...")
    time.sleep(3)
    
    # Test API endpoints
    api_tests = [
        {
            'endpoint': '/api/chat',
            'method': 'POST',
            'data': {'message': 'hello there'},
            'expected': 'response'
        },
        {
            'endpoint': '/api/chat',
            'method': 'POST',
            'data': {'message': 'play music'},
            'expected': 'response'
        },
        {
            'endpoint': '/api/chat',
            'method': 'POST',
            'data': {'message': 'what can you do?'},
            'expected': 'response'
        }
    ]
    
    for test in api_tests:
        print(f"\nTesting {test['method']} {test['endpoint']}")
        print("-" * 40)
        
        try:
            url = f"http://localhost:5000{test['endpoint']}"
            
            if test['method'] == 'POST':
                response = requests.post(url, json=test['data'], timeout=10)
            else:
                response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Success: {result}")
            else:
                print(f"❌ Failed: Status {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Could not connect to backend (may not be running)")
        except Exception as e:
            print(f"❌ Error: {e}")

def generate_test_report(conversation_results):
    """Generate a comprehensive test report"""
    print("\n" + "="*60)
    print("TEST REPORT SUMMARY")
    print("="*60)
    
    total_tests = len(conversation_results)
    appropriate_responses = sum(1 for r in conversation_results if r['appropriate'])
    
    print(f"Total conversation tests: {total_tests}")
    print(f"Appropriate responses: {appropriate_responses}")
    print(f"Success rate: {(appropriate_responses/total_tests)*100:.1f}%")
    
    print("\nDETAILED RESULTS:")
    print("-" * 40)
    
    for result in conversation_results:
        status = "✓" if result['appropriate'] else "❌"
        print(f"{status} [{result['category']}] '{result['query']}'")
        if not result['appropriate']:
            print(f"   Response: {result['response'][:100]}...")
    
    # Save detailed report
    report_path = "test_report_chat_improvements.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_tests': total_tests,
            'appropriate_responses': appropriate_responses,
            'success_rate': (appropriate_responses/total_tests)*100,
            'detailed_results': conversation_results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\nDetailed report saved to: {report_path}")

def main():
    """Run comprehensive chat testing"""
    print("Starting comprehensive chat functionality testing...")
    print("This will test conversational AI, command processing, and web API")
    
    # Test conversational responses
    conversation_results = test_conversational_responses()
    
    # Test command processing
    test_command_processing()
    
    # Test web API
    test_web_api()
    
    # Generate report
    generate_test_report(conversation_results)
    
    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60)
    print("Check the generated report for detailed results.")
    print("If success rate is below 80%, review the conversational AI responses.")

if __name__ == "__main__":
    main()