#!/usr/bin/env python3
"""Quick test to verify AI responses are working"""

from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

print("=" * 70)
print("Testing AI Response System")
print("=" * 70)

# Check keys
gemini_key = os.getenv("GEMINI_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

print(f"\n✅ Gemini key: {'Found' if gemini_key else 'Missing'}")
print(f"✅ OpenAI key: {'Found' if openai_key else 'Missing'}")

# Test LLM provider
print("\n" + "=" * 70)
print("Testing LLM Provider...")
print("=" * 70)

try:
    from core_ai.modules.llm_provider import UnifiedChatInterface
    
    print("\n📡 Initializing LLM provider...")
    chat = UnifiedChatInterface(use_fallback=True)
    
    print("✅ LLM provider initialized successfully!")
    
    print("\n🤖 Sending test query: 'Hello, can you count to 3?'")
    response = chat.chat("Hello, can you count to 3?", stream=False)
    
    print("\n" + "=" * 70)
    print("AI Response:")
    print("=" * 70)
    print(response)
    print("=" * 70)
    
    if len(response) > 20 and "Error" not in response:
        print("\n🎉 SUCCESS! AI is generating real-time responses!")
    else:
        print("\n⚠️  Response received but may have issues")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("Test Complete!")
print("=" * 70)
