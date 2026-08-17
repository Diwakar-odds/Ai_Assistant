#!/usr/bin/env python3
"""
Debug script to test the pi/pie query processing flow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Test the conversational AI directly
try:
    from modules.conversational_ai import AdvancedConversationalAI
    
    print("🔍 Testing Conversational AI directly...")
    ai = AdvancedConversationalAI()
    
    test_queries = [
        "value of pie",
        "value of pi", 
        "what is pie",
        "what is pi",
        "pie value",
        "pi value"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        response = ai.process_message(query)
        print(f"🤖 Response: {response}")
        print("-" * 50)
        
    # Test the math query processing directly
    print("\n🧮 Testing _process_math_query directly...")
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        response = ai._process_math_query(query)
        print(f"🤖 Math Response: {response}")
        print("-" * 50)
        
except Exception as e:
    print(f"❌ Conversational AI test failed: {e}")
    import traceback
    traceback.print_exc()

# Test the backend assistant
try:
    print("\n\n🏢 Testing Modern Assistant...")
    from modern_web_backend import assistant
    
    for query in test_queries:
        print(f"\n📝 Query: '{query}'")
        response = assistant.process_command(query)
        print(f"🤖 Assistant Response: {response}")
        print("-" * 50)
        
except Exception as e:
    print(f"❌ Modern Assistant test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ Debug script completed!")