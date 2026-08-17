#!/usr/bin/env python3
"""
AI Status Checker - Verify your AI assistant configuration
Run this anytime to check if AI responses are properly configured.
"""

import os
import json
import sys

def print_header(text):
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)

def check_files():
    """Check if required files exist"""
    print_header("File Check")
    
    files_to_check = {
        "ai_assistant/modules/conversational_ai.py": "Core AI module",
        "ai_assistant/modules/llm_provider.py": "LLM provider",
        "quick_ai_setup.py": "Setup wizard",
        "api_keys.json": "API keys (optional)"
    }
    
    all_good = True
    for file_path, description in files_to_check.items():
        exists = os.path.exists(file_path)
        status = "✅" if exists else "❌"
        optional = " (optional)" if file_path == "api_keys.json" and not exists else ""
        print(f"{status} {description}: {file_path}{optional}")
        if not exists and file_path != "api_keys.json":
            all_good = False
    
    return all_good

def check_api_keys():
    """Check if API keys are configured"""
    print_header("API Key Configuration")
    
    has_gemini = False
    has_openai = False
    source = None
    
    # Check api_keys.json
    if os.path.exists("api_keys.json"):
        try:
            with open("api_keys.json", 'r') as f:
                keys = json.load(f)
                
            gemini_key = keys.get("GEMINI_API_KEY", "")
            openai_key = keys.get("OPENAI_API_KEY", "")
            
            if gemini_key and gemini_key != "your_gemini_api_key_here" and len(gemini_key) > 20:
                has_gemini = True
                source = "api_keys.json"
                print(f"✅ Gemini API key found in api_keys.json")
                print(f"   Key: {gemini_key[:8]}...{gemini_key[-8:]}")
            
            if openai_key and openai_key != "your_openai_api_key_here" and openai_key.startswith("sk-"):
                has_openai = True
                source = "api_keys.json"
                print(f"✅ OpenAI API key found in api_keys.json")
                print(f"   Key: {openai_key[:8]}...{openai_key[-8:]}")
                
        except Exception as e:
            print(f"⚠️  Error reading api_keys.json: {e}")
    
    # Check environment variables
    env_gemini = os.getenv("GEMINI_API_KEY")
    env_openai = os.getenv("OPENAI_API_KEY")
    
    if env_gemini and env_gemini != "your_gemini_api_key_here" and len(env_gemini) > 20:
        has_gemini = True
        if not source:
            source = "environment variable"
        print(f"✅ Gemini API key found in environment")
        print(f"   Key: {env_gemini[:8]}...{env_gemini[-8:]}")
    
    if env_openai and env_openai != "your_openai_api_key_here" and env_openai.startswith("sk-"):
        has_openai = True
        if not source:
            source = "environment variable"
        print(f"✅ OpenAI API key found in environment")
        print(f"   Key: {env_openai[:8]}...{env_openai[-8:]}")
    
    # Summary
    print()
    if has_gemini or has_openai:
        print("✅ API Configuration: READY")
        if has_gemini:
            print("   • Provider: Google Gemini (FREE)")
        if has_openai:
            print("   • Provider: OpenAI GPT (Paid)")
        return True
    else:
        print("❌ API Configuration: NOT CONFIGURED")
        print("   No valid API keys found")
        return False

def test_llm_connection():
    """Test LLM connection"""
    print_header("LLM Connection Test")
    
    try:
        print("Attempting to initialize LLM provider...")
        
        from ai_assistant.modules.llm_provider import UnifiedChatInterface
        
        chat = UnifiedChatInterface(use_fallback=True)
        print("✅ LLM provider initialized successfully")
        
        print("\nSending test query: 'Hello, are you working?'")
        response = chat.chat("Hello, are you working?", stream=False)
        
        if response and len(response) > 10 and "Error" not in response:
            print("✅ AI Response received successfully!")
            print(f"\n   Response: {response[:200]}...")
            return True
        else:
            print(f"⚠️  Received response but it may have errors:")
            print(f"   {response[:200]}...")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("   Some required modules may be missing")
        return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def check_internet():
    """Check internet connectivity"""
    print_header("Internet Connection")
    
    try:
        import requests
        response = requests.get("https://google.com", timeout=3)
        if response.status_code == 200:
            print("✅ Internet connection: ACTIVE")
            return True
        else:
            print("⚠️  Internet connection: SLOW")
            return True
    except:
        print("❌ Internet connection: OFFLINE")
        print("   AI features require internet connection")
        return False

def provide_recommendations(files_ok, api_ok, llm_ok, internet_ok):
    """Provide recommendations based on checks"""
    print_header("Recommendations")
    
    all_good = files_ok and api_ok and llm_ok and internet_ok
    
    if all_good:
        print("🎉 Everything looks great!")
        print("\nYour assistant is ready for AI-powered responses.")
        print("\nTry asking:")
        print("  • 'What is quantum computing?'")
        print("  • 'Explain how AI works'")
        print("  • 'Write a poem about technology'")
    else:
        print("⚠️  Some issues detected. Here's what to do:\n")
        
        if not files_ok:
            print("📁 Missing Files:")
            print("   → Ensure you're in the correct directory")
            print("   → Check if files were properly installed\n")
        
        if not api_ok:
            print("🔑 API Key Not Configured:")
            print("   → Run: python quick_ai_setup.py")
            print("   → Get free key: https://aistudio.google.com/app/apikey")
            print("   → Takes only 2 minutes!\n")
        
        if not llm_ok and api_ok:
            print("🔌 LLM Connection Issue:")
            print("   → Verify API key is correct")
            print("   → Check provider dashboard for status")
            print("   → Try restarting the application\n")
        
        if not internet_ok:
            print("🌐 No Internet Connection:")
            print("   → Connect to internet for AI features")
            print("   → Basic features will work offline\n")

def main():
    print("=" * 70)
    print(" AI Assistant Status Checker")
    print(" Verifying your AI configuration...")
    print("=" * 70)
    
    # Run all checks
    files_ok = check_files()
    api_ok = check_api_keys()
    internet_ok = check_internet()
    
    # Only test LLM if API is configured
    if api_ok and internet_ok:
        llm_ok = test_llm_connection()
    else:
        llm_ok = False
        if api_ok and not internet_ok:
            print_header("LLM Connection Test")
            print("⚠️  Skipped (no internet connection)")
        elif not api_ok:
            print_header("LLM Connection Test")
            print("⚠️  Skipped (API key not configured)")
    
    # Summary
    print_header("Status Summary")
    print(f"{'✅' if files_ok else '❌'} Required Files: {'OK' if files_ok else 'Missing'}")
    print(f"{'✅' if api_ok else '❌'} API Keys: {'Configured' if api_ok else 'Not Set'}")
    print(f"{'✅' if internet_ok else '❌'} Internet: {'Connected' if internet_ok else 'Offline'}")
    print(f"{'✅' if llm_ok else '❌'} AI Connection: {'Working' if llm_ok else 'Not Working'}")
    
    # Recommendations
    provide_recommendations(files_ok, api_ok, llm_ok, internet_ok)
    
    print("\n" + "=" * 70)
    if files_ok and api_ok and llm_ok and internet_ok:
        print(" Status: READY TO USE ✅")
    else:
        print(" Status: NEEDS SETUP ⚙️")
    print("=" * 70)
    print()
    
    # Exit code
    if files_ok and api_ok and llm_ok:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Needs attention

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStatus check cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
