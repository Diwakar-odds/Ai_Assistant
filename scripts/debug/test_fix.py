#!/usr/bin/env python3
"""
Test the fixed conversational AI logic
"""
import re

def test_math_detection_fixed(message):
    """Test the fixed math detection logic"""
    message_lower = message.lower()
    
    # Original condition
    original = any(word in message_lower for word in ['calculate', 'times', 'plus', 'minus', 'divided', 'multiply']) and 'what is' in message_lower
    
    # New condition (added pie/pi check)
    new_condition = original or ('pie' in message_lower or 'pi' in message_lower)
    
    print(f"Message: '{message}'")
    print(f"  Original logic would trigger: {original}")
    print(f"  New logic triggers: {new_condition}")
    print(f"  Should call _process_math_query: {new_condition}")
    
    if new_condition:
        # Simulate the _process_math_query logic
        query_lower = message.lower()
        if 'pie' in query_lower or 'pi' in query_lower:
            response = "The value of π (pi) is approximately 3.14159265359. It's the ratio of a circle's circumference to its diameter."
        else:
            response = "Would process other math..."
        print(f"  Response: {response}")
    
    return new_condition

test_queries = [
    "value of pie",
    "value of pi", 
    "what is pie",
    "what is pi",
    "pie value",
    "pi value",
    "what is 2 plus 2",  # Should still work with original logic
    "calculate 5 times 3"  # Should still work with original logic
]

print("🔧 Testing FIXED math detection logic...")
for query in test_queries:
    test_math_detection_fixed(query)
    print("-" * 50)

print("\n✅ Fixed logic test completed!")