#!/usr/bin/env python3
"""
Simple test for the pi query processing without complex imports
"""
import re

def test_math_query(query):
    """Test the math query processing logic"""
    try:
        query_lower = query.lower()
        
        # Extract numbers and operations
        if 'pie' in query_lower or 'pi' in query_lower:
            return "The value of π (pi) is approximately 3.14159265359. It's the ratio of a circle's circumference to its diameter."
        
        return "No math operation detected"
        
    except Exception as e:
        return f"Error: {e}"

# Test the query processing
test_queries = [
    "value of pie",
    "value of pi", 
    "what is pie",
    "what is pi",
    "pie value",
    "pi value"
]

print("🧮 Testing math query processing...")
for query in test_queries:
    print(f"\n📝 Query: '{query}'")
    response = test_math_query(query)
    print(f"🤖 Response: {response}")
    print("-" * 50)

# Now test if we can check what the actual assistant is doing
print("\n🔍 Checking WebSocket message flow...")
print("The frontend sends: {'message': 'value of pie', 'model': 'openai'}")
print("This goes to handle_command() in modern_web_backend.py")
print("Which calls assistant.process_command()")
print("Which should call conversational_ai.process_message()")
print("Which should call _process_math_query() if math words are detected")

# Let's check if the math detection logic is working
def check_math_detection(message):
    """Check if math detection logic works"""
    message_lower = message.lower()
    math_keywords = ['calculate', 'times', 'plus', 'minus', 'divided', 'multiply']
    has_what_is = 'what is' in message_lower
    has_value_of = 'value of' in message_lower
    has_pie_pi = 'pie' in message_lower or 'pi' in message_lower
    
    print(f"Message: '{message}'")
    print(f"  Has math keywords: {any(word in message_lower for word in math_keywords)}")
    print(f"  Has 'what is': {has_what_is}")
    print(f"  Has 'value of': {has_value_of}")
    print(f"  Has pie/pi: {has_pie_pi}")
    print(f"  Should trigger math: {(any(word in message_lower for word in math_keywords) and has_what_is) or has_pie_pi}")
    return has_pie_pi or (any(word in message_lower for word in math_keywords) and has_what_is)

print("\n🔍 Testing math detection logic...")
for query in test_queries:
    check_math_detection(query)
    print("-" * 30)

print("\n✅ Simple test completed!")