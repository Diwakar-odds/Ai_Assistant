import os
from dotenv import load_dotenv
import google.generativeai as genai
from openai import OpenAI

load_dotenv()

def list_gemini_models():
    print("\n=== Google Gemini Models ===")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found")
        return

    try:
        genai.configure(api_key=api_key)
        print(f"API Key: {api_key[:5]}...{api_key[-5:]}")
        for model in genai.list_models():
            if 'generateContent' in model.supported_generation_methods:
                print(f"- {model.name}")
    except Exception as e:
        print(f"❌ Error listing Gemini models: {e}")

def list_openai_models():
    print("\n=== OpenAI Models ===")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found")
        return

    try:
        client = OpenAI(api_key=api_key)
        print(f"API Key: {api_key[:5]}...{api_key[-5:]}")
        models = client.models.list()
        # Filter for gpt models to keep list short
        gpt_models = [m.id for m in models.data if 'gpt' in m.id]
        gpt_models.sort()
        for model_id in gpt_models:
            print(f"- {model_id}")
    except Exception as e:
        print(f"❌ Error listing OpenAI models: {e}")

if __name__ == "__main__":
    list_gemini_models()
    list_openai_models()
