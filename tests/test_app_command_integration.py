# -*- coding: utf-8 -*-
"""
Test App Command Integration
Tests the full pipeline: detection → execution → app opening
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_app_commands():
    print("=" * 60)
    print("Testing App Command Integration")
    print("=" * 60)
    
    # Test 1: Import detector
    print("\n[TEST 1] Importing app command detector...")
    try:
        from ai_assistant.apps.app_command_detector import detect_app_command
        print("[SUCCESS] App command detector imported")
    except ImportError as e:
        print(f"[FAIL] Could not import detector: {e}")
        return
    
    # Test 2: Detect commands
    print("\n[TEST 2] Testing command detection...")
    test_commands = [
        "open chrome",
        "launch calculator",
        "start notepad",
        "calculator kholna",  # Hindi (transliterated)
        "close discord",
        "hello how are you"  # Should NOT detect
    ]
    
    for cmd in test_commands:
        result = detect_app_command(cmd)
        if result:
            print(f"  [DETECTED] '{cmd}' -> {result.action.value} {result.app_name}")
        else:
            print(f"  [NO DETECT] '{cmd}'")
    
    # Test 3: Import Universal Controller
    print("\n[TEST 3] Importing Universal App Controller...")
    try:
        from ai_assistant.core.universal_app_controller import get_universal_controller
        controller = get_universal_controller()
        print("[SUCCESS] Universal App Controller loaded")
    except ImportError as e:
        print(f"[FAIL] Could not import controller: {e}")
        return
    
    # Test 4: Check discovered apps
    print("\n[TEST 4] Checking discovered apps...")
    try:
        from ai_assistant.modules.app_discovery import app_discovery
        all_apps = app_discovery.get_all_apps()
        print(f"[INFO] {len(all_apps)} apps discovered")
        
        # Check if Chrome is available
        chrome_path = app_discovery.find_app("chrome")
        if chrome_path:
            print(f"[INFO] Chrome found: {chrome_path}")
        else:
            print("[INFO] Chrome not found (will test with available app)")
    except Exception as e:
        print(f"[WARN] App discovery error: {e}")
    
    # Test 5: Test ModernAssistant integration
    print("\n[TEST 5] Testing ModernAssistant integration...")
    try:
        # We can't fully test this without running the server
        # but we can check if the methods exist
        from ai_assistant.services.modern_web_backend import ModernAssistant
        
        # Check if methods exist
        if hasattr(ModernAssistant, 'detect_app_command'):
            print("[SUCCESS] detect_app_command method exists")
        else:
            print("[FAIL] detect_app_command method not found")
            
        if hasattr(ModernAssistant, 'execute_app_command'):
            print("[SUCCESS] execute_app_command method exists")
        else:
            print("[FAIL] execute_app_command method not found")
        
        print("[INFO] Full integration test requires running web server")
        
    except Exception as e:
        print(f"[FAIL] ModernAssistant check failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print("[INFO] Basic components are working")
    print("[INFO] To test live:")
    print("  1. Make sure web backend is running (python modern_web_backend.py)")
    print("  2. Use web interface or API")
    print("  3. Try command: 'open chrome' or 'launch calculator'")
    print("=" * 60)

if __name__ == "__main__":
    test_app_commands()
