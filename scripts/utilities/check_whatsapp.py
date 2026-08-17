#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick script to check if WhatsApp is discovered by the AI Assistant
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_whatsapp():
    print("=" * 60)
    print("Checking WhatsApp Discovery")
    print("=" * 60)
    
    try:
        from ai_assistant.modules.app_discovery import app_discovery
        
        # 1. Check if WhatsApp is in discovered apps
        all_apps = app_discovery.get_all_apps()
        print(f"\n[*] Total apps discovered: {len(all_apps)}")
        
        # 2. Search for WhatsApp variations
        whatsapp_variations = ['whatsapp', 'what\'s app', 'whats app', 'wa']
        found_apps = []
        
        print("\n[SEARCH] Searching for WhatsApp variations:")
        for variant in whatsapp_variations:
            result = app_discovery.find_app(variant)
            if result:
                found_apps.append((variant, result))
                print(f"  [YES] '{variant}' -> Found: {result}")
            else:
                print(f"  [NO]  '{variant}' -> Not found")
        
        # 3. Search in all apps for anything containing "whats"
        print("\n[APPS] Apps containing 'whats':")
        whats_apps = {name: path for name, path in all_apps.items() if 'whats' in name.lower()}
        if whats_apps:
            for name, path in whats_apps.items():
                print(f"  - {name}: {path}")
        else:
            print("  [NO] No apps found containing 'whats'")
        
        # 4. Use search function
        print("\n[SEARCH] Using search_apps function:")
        search_results = app_discovery.search_apps('whatsapp', limit=5)
        if search_results:
            for score, name, path in search_results:
                print(f"  - {name} (score: {score:.2f})")
                print(f"    Path: {path}")
        else:
            print("  [NO] No results from search")
        
        # 5. Test normalization
        print("\n[TEST] Testing Intent Recognizer normalization:")
        try:
            from ai_assistant.ai.intent_recognizer import IntentRecognizer
            recognizer = IntentRecognizer()
            
            test_inputs = ['whatsapp', 'what\'s app', 'whats app', 'WhatsApp']
            for test_input in test_inputs:
                normalized = recognizer.normalize_app_name(test_input)
                print(f"  '{test_input}' -> '{normalized}'")
        except Exception as e:
            print(f"  [WARN] Intent Recognizer not available: {e}")
        
        # 6. Test opening
        if found_apps:
            print("\n[CAPABILITY] Testing app opening capability:")
            print(f"  Using: {found_apps[0][0]} -> {found_apps[0][1]}")
            print("  (Not actually opening, just showing what would happen)")
            
            # Show the exact command that would be used
            from ai_assistant.modules.app_discovery import smart_open_application
            print(f"\n  Command: smart_open_application('{found_apps[0][0]}')")
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        
        if found_apps:
            print(f"[SUCCESS] WhatsApp IS FOUND in your system")
            print(f"   Best match: {found_apps[0][1]}")
            print(f"\n[INFO] Your AI can open WhatsApp using:")
            print(f"   - Voice: 'Open WhatsApp'")
            print(f"   - Text: 'open whatsapp'")
            print(f"   - Code: smart_open_application('whatsapp')")
        else:
            print("[FAIL] WhatsApp NOT FOUND in discovered apps")
            print("\n[INFO] Possible reasons:")
            print("   1. WhatsApp is not installed on this system")
            print("   2. It's installed but not in standard locations")
            print("   3. App database needs refresh")
            print("\n[FIX] Try:")
            print("   - Install WhatsApp Desktop from Microsoft Store")
            print("   - Run: app_discovery.refresh_database()")
            print("   - Use web version: 'https://web.whatsapp.com'")
        
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] Error checking WhatsApp: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_whatsapp()
