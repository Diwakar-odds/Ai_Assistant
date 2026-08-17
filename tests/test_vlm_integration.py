"""
Test script for VLM Integration

Quick tests to verify VLM provider architecture is working correctly.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_vlm_provider():
    """Test VLM provider initialization."""
    print("=" * 60)
    print("TEST 1: VLM Provider Initialization")
    print("=" * 60)
    
    try:
        from ai_assistant.vision.vlm_provider import VLMProvider, VLMResponse
        from ai_assistant.vision.gemini_vision_provider import GeminiVisionProvider
        
        print("✅ VLM modules imported successfully")
        
        # Initialize provider
        provider = GeminiVisionProvider()
        print(f"✅ GeminiVisionProvider initialized")
        print(f"   Provider: {provider.provider_name}")
        print(f"   Features: {', '.join(provider.supported_features[:3])}...")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_multimodal_integration():
    """Test MultiModalAI with new VLM architecture."""
    print("\n" + "=" * 60)
    print("TEST 2: MultiModalAI Integration")
    print("=" * 60)
    
    try:
        from ai_assistant.multimodal import MultiModalAI
        
        vlm = MultiModalAI(use_new_architecture=True)
        print("✅ MultiModalAI initialized with new architecture")
        print(f"   Using new architecture: {vlm.use_new_architecture}")
        
        # Test new methods
        if hasattr(vlm, 'extract_coordinates'):
            print("✅ New method 'extract_coordinates' available")
        if hasattr(vlm, 'identify_ui_actions'):
            print("✅ New method 'identify_ui_actions' available")
        if hasattr(vlm, 'analyze_for_automation'):
            print("✅ New method 'analyze_for_automation' available")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_screen_analysis():
    """Test screen analysis with VLM."""
    print("\n" + "=" * 60)
    print("TEST 3: Screen Analysis")
    print("=" * 60)
    
    try:
        from ai_assistant.multimodal import MultiModalAI
        
        vlm = MultiModalAI(use_new_architecture=True)
        
        print("📸 Capturing and analyzing screen...")
        result = vlm.analyze_screen("Briefly describe what's on the screen")
        
        if isinstance(result, dict) and "analysis" in result:
            analysis = result["analysis"]
            print(f"✅ Analysis successful!")
            print(f"   Preview: {analysis[:150]}...")
            return True
        else:
            print(f"⚠️ Unexpected result format: {type(result)}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_visual_automation():
    """Test visual automation engine."""
    print("\n" + "=" * 60)
    print("TEST 4: Visual Automation Engine")
    print("=" * 60)
    
    try:
        from ai_assistant.automation.visual_automation import VisualAutomationEngine
        
        engine = VisualAutomationEngine(safety_mode=True)
        print("✅ VisualAutomationEngine initialized")
        print(f"   Safety mode: {engine.safety_mode}")
        
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\nVLM Integration Test Suite")
    print("=" * 60)
    
    tests = [
        ("VLM Provider", test_vlm_provider),
        ("MultiModalAI Integration", test_multimodal_integration),
        ("Screen Analysis", test_screen_analysis),
        ("Visual Automation", test_visual_automation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ {name} crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n*** All tests passed!")
        return 0
    else:
        print(f"\n*** {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())
