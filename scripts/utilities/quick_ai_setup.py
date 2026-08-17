#!/usr/bin/env python3
"""
Quick Setup Script for Real-Time AI Responses
Run this to configure your assistant for intelligent responses.
"""

import os
import json
import sys

def main():
    print("=" * 70)
    print(" YourDaddy Assistant - Quick AI Setup")
    print("=" * 70)
    print()
    print("🤖 This will enable real-time AI responses instead of hardcoded replies")
    print()
    
    # Check if already configured
    api_keys_file = "api_keys.json"
    has_gemini = os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_API_KEY") != "your_gemini_api_key_here"
    has_openai = os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your_openai_api_key_here"
    
    if os.path.exists(api_keys_file):
        try:
            with open(api_keys_file, 'r') as f:
                keys = json.load(f)
                if keys.get("GEMINI_API_KEY") and keys["GEMINI_API_KEY"] != "your_gemini_api_key_here":
                    has_gemini = True
                if keys.get("OPENAI_API_KEY") and keys["OPENAI_API_KEY"] != "your_openai_api_key_here":
                    has_openai = True
        except:
            pass
    
    if has_gemini or has_openai:
        print("✅ API Key already configured!")
        if has_gemini:
            print("   - Google Gemini: Available")
        if has_openai:
            print("   - OpenAI: Available")
        print()
        reconfigure = input("Do you want to reconfigure? (y/N): ").lower()
        if reconfigure != 'y':
            print("Setup cancelled. Your assistant is ready to use!")
            return
        print()
    
    print("Choose your AI provider:")
    print()
    print("1️⃣  Google Gemini (Recommended)")
    print("    ✓ FREE tier available")
    print("    ✓ Fast responses")
    print("    ✓ 60 requests/minute free")
    print("    → Get key: https://aistudio.google.com/app/apikey")
    print()
    print("2️⃣  OpenAI (GPT)")
    print("    ✓ High quality responses")
    print("    ✓ Multiple models (GPT-3.5, GPT-4)")
    print("    ✗ Paid service (requires billing)")
    print("    → Get key: https://platform.openai.com/api-keys")
    print()
    print("3️⃣  Skip (use offline mode)")
    print()
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    keys_data = {}
    if os.path.exists(api_keys_file):
        try:
            with open(api_keys_file, 'r') as f:
                keys_data = json.load(f)
        except:
            pass
    
    if choice == "1":
        print()
        print("=" * 70)
        print("Setting up Google Gemini")
        print("=" * 70)
        print()
        print("Steps to get your API key:")
        print("1. Open: https://aistudio.google.com/app/apikey")
        print("2. Sign in with your Google account")
        print("3. Click 'Create API Key'")
        print("4. Copy the key and paste it below")
        print()
        
        api_key = input("Paste your Gemini API Key: ").strip()
        
        if api_key and len(api_key) > 20:
            keys_data["GEMINI_API_KEY"] = api_key
            
            # Save to api_keys.json
            with open(api_keys_file, 'w') as f:
                json.dump(keys_data, f, indent=4)
            
            # Also set environment variable for current session
            os.environ["GEMINI_API_KEY"] = api_key
            
            print()
            print("✅ Gemini API key saved successfully!")
            print()
            
        else:
            print("❌ Invalid key. Please try again.")
            sys.exit(1)
    
    elif choice == "2":
        print()
        print("=" * 70)
        print("Setting up OpenAI")
        print("=" * 70)
        print()
        print("Steps to get your API key:")
        print("1. Open: https://platform.openai.com/api-keys")
        print("2. Sign in or create an account")
        print("3. Add billing information (required)")
        print("4. Click 'Create new secret key'")
        print("5. Copy the key and paste it below")
        print()
        
        api_key = input("Paste your OpenAI API Key: ").strip()
        
        if api_key and api_key.startswith("sk-"):
            keys_data["OPENAI_API_KEY"] = api_key
            
            # Save to api_keys.json
            with open(api_keys_file, 'w') as f:
                json.dump(keys_data, f, indent=4)
            
            # Also set environment variable for current session
            os.environ["OPENAI_API_KEY"] = api_key
            
            print()
            print("✅ OpenAI API key saved successfully!")
            print()
            
        else:
            print("❌ Invalid key format. OpenAI keys start with 'sk-'")
            sys.exit(1)
    
    elif choice == "3":
        print()
        print("⚠️  Running in offline mode")
        print("Your assistant will use rule-based responses instead of AI.")
        print("You can set up AI later by running this script again.")
        print()
        return
    
    else:
        print("Invalid choice. Exiting.")
        sys.exit(1)
    
    # Test the configuration
    print("=" * 70)
    print("Testing AI Connection...")
    print("=" * 70)
    print()
    
    try:
        from ai_assistant.modules.llm_provider import UnifiedChatInterface
        
        print("Initializing AI provider...")
        chat = UnifiedChatInterface(use_fallback=True)
        
        print("Sending test query...")
        response = chat.chat("Hello, are you working?", stream=False)
        
        if response and "Error" not in response:
            print()
            print("✅ SUCCESS! AI is working properly!")
            print()
            print(f"Test Response: {response[:200]}...")
            print()
        else:
            print()
            print("⚠️  AI responded but with an error:")
            print(f"   {response}")
            print()
            
    except Exception as e:
        print()
        print(f"⚠️  Test failed: {e}")
        print()
        print("Your key is saved, but there might be an issue.")
        print("Try restarting the application.")
        print()
    
    print("=" * 70)
    print("Setup Complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Restart your assistant application")
    print("2. Try asking: 'What is quantum computing?'")
    print("3. Enjoy real-time AI responses! 🚀")
    print()
    print("Note: Your API key is saved in 'api_keys.json'")
    print("      Keep this file secure and don't share it!")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
