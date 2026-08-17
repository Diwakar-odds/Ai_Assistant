"""Quick test of local AI installation"""

print("=" * 60)
print("LOCAL AI INSTALLATION TEST")
print("=" * 60)

# Test 1: Import llama-cpp-python
print("\n1. Testing llama-cpp-python import...")
try:
    from llama_cpp import Llama
    print("   ✅ llama-cpp-python installed successfully")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    print("   Install with: pip install llama-cpp-python")
    exit(1)

# Test 2: Import local AI manager
print("\n2. Testing local AI manager import...")
try:
    from ai_assistant.local_ai_manager import LocalAIManager
    print("   ✅ LocalAIManager imported successfully")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    exit(1)

# Test 3: Check for model files
print("\n3. Checking for model files...")
from pathlib import Path

model_dir = Path("model/local_models")
if not model_dir.exists():
    print(f"   ⚠️ Model directory doesn't exist: {model_dir}")
    print("   Creating directory...")
    model_dir.mkdir(parents=True, exist_ok=True)

models_found = list(model_dir.glob("*.gguf"))
if models_found:
    print(f"   ✅ Found {len(models_found)} model(s):")
    for model in models_found:
        size_mb = model.stat().st_size / (1024 * 1024)
        print(f"      - {model.name} ({size_mb:.1f} MB)")
else:
    print("   ⚠️ No models found in model/local_models/")
    print("\n   📥 Download TinyLlama with:")
    print("      pip install huggingface-hub")
    print("      huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF \\")
    print("        tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \\")
    print("        --local-dir model/local_models")

# Test 4: Try to initialize LocalAIManager
print("\n4. Testing LocalAIManager initialization...")
try:
    manager = LocalAIManager()
    print("   ✅ LocalAIManager initialized")
    
    if models_found:
        print(f"\n5. Testing model loading with {models_found[0].name}...")
        if manager.load_model(str(models_found[0]), threads=4):
            print("   ✅ Model loaded successfully!")
            
            print("\n6. Testing inference...")
            response = manager.generate("Say hello in one sentence.", max_tokens=50)
            print(f"   Response: {response}")
            
            stats = manager.get_stats()
            print(f"\n   Performance: {stats['avg_tokens_per_sec']:.1f} tokens/sec")
            
            manager.unload_model()
        else:
            print("   ❌ Failed to load model")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
