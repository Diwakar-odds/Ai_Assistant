"""
Import Verification Script
Verifies that all critical imports work correctly after refactoring
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

print("=" * 70)
print("IMPORT VERIFICATION AFTER REFACTORING")
print("=" * 70)

# Track results
passed = []
failed = []
warnings_count = 0

def test_import(module_path, description):
    """Test importing a module"""
    global warnings_count
    try:
        print(f"\n[TEST] {description}...")
        print(f"       Importing: {module_path}")
        
        # Capture deprecation warnings
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            __import__(module_path)
            
            if w:
                warnings_count += len(w)
                for warning in w:
                    if issubclass(warning.category, DeprecationWarning):
                        print(f"       ⚠️  Deprecation: {warning.message}")
        
        print(f"       ✅ SUCCESS")
        passed.append((module_path, description))
        return True
    except ImportError as e:
        print(f"       ❌ FAILED: {e}")
        failed.append((module_path, description, str(e)))
        return False
    except Exception as e:
        print(f"       ❌ ERROR: {e}")
        failed.append((module_path, description, str(e)))
        return False

print("\n" + "-" * 70)
print("TESTING PRIMARY IMPORTS (from canonical locations)")
print("-" * 70)

# Primary imports from canonical locations
test_import("ai_assistant.services.modern_web_backend", "Backend - Services (Canonical)")
test_import("ai_assistant.voice.advanced_voice", "Voice - Advanced (Canonical)")
test_import("ai_assistant.voice.neural_voice_engine", "Voice - Neural TTS (Canonical)")
test_import("ai_assistant.modules.conversational_ai", "AI - Conversational (Canonical)")
test_import("ai_assistant.modules.llm_provider", "AI - LLM Provider (Canonical)")
test_import("ai_assistant.modules.memory", "AI - Memory (Canonical)")

print("\n" + "-" * 70)
print("TESTING BACKWARD COMPATIBILITY (deprecated import paths)")
print("-"* 70)

# Backward compatibility imports (should work with deprecation warnings)
test_import("ai_assistant.apps.modern_web_backend", "Backend - Apps (Deprecated Alias)")
test_import("ai_assistant.modules.advanced_voice", "Voice - Advanced (Deprecated Alias)")
test_import("ai_assistant.modules.neural_voice_engine", "Voice - Neural TTS (Deprecated Alias)")
test_import("ai_assistant.ai.conversational_ai", "AI - Conversational (Deprecated Alias)")
test_import("ai_assistant.ai.llm_provider", "AI - LLM Provider (Deprecated Alias)")
test_import("ai_assistant.ai.memory", "AI - Memory (Deprecated Alias)")

print("\n" + "=" * 70)
print("VERIFICATION SUMMARY")
print("=" * 70)

print(f"\n✅ Passed: {len(passed)} imports")
if warnings_count > 0:
   print (f"⚠️  Deprecation Warnings: {warnings_count} (expected for backward compatibility)")

if failed:
    print(f"\n❌ Failed: {len(failed)} imports")
    print("\nFailed Imports:")
    for module_path, description, error in failed:
        print(f"  - {description}")
        print(f"    Path: {module_path}")
        print(f"    Error: {error}")
    
    print("\n" + "=" * 70)
    print("❌ VERIFICATION FAILED - Some imports are broken")
    print("=" * 70)
    sys.exit(1)
else:
    print("\n" + "=" * 70)
    print("✅ VERIFICATION SUCCESSFUL - All imports working!")
    print("=" * 70)
    print("\n📝 Notes:")
    print("  - Deprecation warnings are expected for backward compatibility")
    print("  - Old import paths should be updated to new canonical locations")
    print("  - Deprecated aliases will be removed in a future version")
    sys.exit(0)
