"""Quick test of local AI installation"""

#"=" * 60)
#"LOCAL AI INSTALLATION TEST")
#"=" * 60)

# Test 1: Import llama-cpp-python
#"\n1. Testing llama-cpp-python import...")
try:
    from llama_cpp import Llama
    #"   ✅ llama-cpp-python installed successfully")
except ImportError as e:
    #f"   ❌ Import failed: {e}")
    #"   Install with: pip install llama-cpp-python")
    #

# Test 2: Import local AI manager
#"\n2. Testing local AI manager import...")
try:
    from ai_assistant.local_ai_manager import LocalAIManager
    #"   ✅ LocalAIManager imported successfully")
except ImportError as e:
    #f"   ❌ Import failed: {e}")
    #

# Test 3: Check for model files
#"\n3. Checking for model files...")
from pathlib import Path

model_dir = Path("model/local_models")
if not model_dir.exists():
    #f"   ⚠️ Model directory doesn't exist: {model_dir}")
    #"   Creating directory...")
    model_dir.mkdir(parents=True, exist_ok=True)

models_found = list(model_dir.glob("*.gguf"))
if models_found:
    #f"   ✅ Found {len(models_found)} model(s):")
    for model in models_found:
        size_mb = model.stat().st_size / (1024 * 1024)
        #f"      - {model.name} ({size_mb:.1f} MB)")
else:
    #"   ⚠️ No models found in model/local_models/")
    #"\n   📥 Download TinyLlama with:")
    #"      pip install huggingface-hub")
    #"      huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF \\")
    #"        tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf \\")
    #"        --local-dir model/local_models")

# Test 4: Try to initialize LocalAIManager
#"\n4. Testing LocalAIManager initialization...")
try:
    manager = LocalAIManager()
    #"   ✅ LocalAIManager initialized")
    
    if models_found:
        #f"\n5. Testing model loading with {models_found[0].name}...")
        if manager.load_model(str(models_found[0]), threads=4):
            #"   ✅ Model loaded successfully!")
            
            #"\n6. Testing inference...")
            response = manager.generate("Say hello in one sentence.", max_tokens=50)
            #f"   Response: {response}")
            
            stats = manager.get_stats()
            #f"\n   Performance: {stats['avg_tokens_per_sec']:.1f} tokens/sec")
            
            manager.unload_model()
        else:
            #"   ❌ Failed to load model")
    
except Exception as e:
    #f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

#"\n" + "=" * 60)
#"TEST COMPLETE")
#"=" * 60)
