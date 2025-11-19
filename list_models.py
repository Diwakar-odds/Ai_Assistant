#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check available Gemini models
"""

import os
import google.generativeai as genai

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("No GEMINI_API_KEY found")
    exit(1)

print(f"API Key: {api_key[:10]}...{api_key[-5:]}")
print()

try:
    genai.configure(api_key=api_key)
    print("✅ Configured Gemini API")
    print()
    print("Available models:")
    print("=" * 70)
    
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"  ✅ {model.name}")
            print(f"     Description: {model.description[:80]}...")
            print(f"     Methods: {', '.join(model.supported_generation_methods)}")
            print()
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
