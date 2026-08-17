import os
from dotenv import load_dotenv
import requests

def debug_environment():
    print("="*60)
    print("Debugging Environment Configuration")
    print("="*60)
    
    # 1. Check .env file existence
    env_path = os.path.abspath('.env')
    print(f"Looking for .env at: {env_path}")
    if os.path.exists(env_path):
        print("✅ .env file found.")
    else:
        print("❌ .env file NOT found in current directory.")
        # Try to find it in parent directories?
        # load_dotenv() does this automatically, but let's see what it finds.

    # 2. Load environment
    print("\nLoading environment variables...")
    load_dotenv()
    
    # 3. Check Keys
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    print(f"\nGEMINI_API_KEY status: {'✅ Found' if gemini_key else '❌ Missing'}")
    if gemini_key:
        print(f"  Length: {len(gemini_key)}")
        print(f"  Prefix: {gemini_key[:4]}...")
        if gemini_key == "your_gemini_api_key_here":
            print("  ⚠️ WARNING: Key appears to be the default placeholder!")

    print(f"OPENAI_API_KEY status: {'✅ Found' if openai_key else '❌ Missing'}")
    if openai_key:
        print(f"  Length: {len(openai_key)}")
        print(f"  Prefix: {openai_key[:4]}...")
        if openai_key == "your_openai_api_key_here":
            print("  ⚠️ WARNING: Key appears to be the default placeholder!")

    # 4. Test Connectivity if keys exist
    if gemini_key and gemini_key != "your_gemini_api_key_here":
        print("\nTesting Gemini API...")
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print("✅ Gemini API Connection Successful!")
            else:
                print(f"❌ Gemini API Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ Gemini Connection Failed: {e}")

    if openai_key and openai_key != "your_openai_api_key_here":
        print("\nTesting OpenAI API...")
        try:
            url = "https://api.openai.com/v1/models"
            headers = {"Authorization": f"Bearer {openai_key}"}
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                print("✅ OpenAI API Connection Successful!")
            else:
                print(f"❌ OpenAI API Error: {response.status_code}")
        except Exception as e:
            print(f"❌ OpenAI Connection Failed: {e}")

if __name__ == "__main__":
    debug_environment()
