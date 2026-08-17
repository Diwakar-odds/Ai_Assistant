# 🚀 Local AI Quickstart - 8GB RAM Edition

**Optimized for your hardware:** 8GB RAM, 1GB GPU (CPU-only mode)

---

## 📋 **Prerequisites**

- **RAM:** 8GB (will use ~2-3GB for AI)
- **Storage:** ~1.5GB free
- **Python:** 3.9+
- **OS:** Windows/Linux/Mac

---

## 🎯 **Step 1: Install Dependencies**

### Option A: Quick Install
```bash
pip install llama-cpp-python huggingface-hub
```

### Option B: Optimized Install (Faster on modern CPUs)
```bash
# Windows (PowerShell)
$env:CMAKE_ARGS="-DLLAMA_AVX2=ON"
pip install llama-cpp-python --force-reinstall --no-cache-dir

# Linux/Mac
CMAKE_ARGS="-DLLAMA_AVX2=ON" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### Option C: Full Requirements
```bash
pip install -r requirements_local_ai.txt
```

**Verify Installation:**
```bash
python -c "from llama_cpp import Llama; print('✅ Ready!')"
```

---

## 📥 **Step 2: Download Model**

### Recommended: TinyLlama-1.1B (~700MB)

**Method 1: Automatic (recommended)**
```bash
pip install huggingface-hub
huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf --local-dir model/local_models
```

**Method 2: Manual**
1. Visit: https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/tree/main
2. Download: `tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf` (700MB)
3. Place in: `F:\bn\assitant\model\local_models\`

### Alternative: Qwen2-0.5B (~400MB) - Faster
```bash
huggingface-cli download Qwen/Qwen2-0.5B-Instruct-GGUF qwen2-0_5b-instruct-q4_k_m.gguf --local-dir model/local_models
```

---

## 🧪 **Step 3: Test Local AI**

### Quick Test
```bash
python ai_assistant/local_ai_manager.py
```

Expected output:
```
🚀 Local AI Manager - Quick Test

✅ Model already exists: model/local_models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
🔄 Loading model: tinyllama-1.1b-chat-v1.0.Q4_K_M
💻 CPU threads: 4
✅ Model loaded in 2.3s
📊 RAM usage: ~700MB

============================================================

❓ What is the capital of France?
------------------------------------------------------------
🤖 The capital of France is Paris.
⚡ 12.4 tokens/sec (15 tokens in 1.2s)
------------------------------------------------------------
```

### Interactive Python Test
```python
from ai_assistant.local_ai_manager import LocalAIManager

# Initialize
manager = LocalAIManager()

# Load model
model_path = "model/local_models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
manager.load_model(model_path, threads=4)

# Single query
response = manager.generate("Explain Python decorators in simple terms")
print(response)

# Chat with history
manager.chat("Hello! What can you help me with?")
manager.chat("Write a Python function to reverse a string")
manager.chat("Now optimize it for performance")

# View stats
print(manager.get_stats())

# Cleanup
manager.unload_model()
```

---

## 🎨 **Step 4: Integrate with Your Backend**

Add to `modern_web_backend.py`:

```python
from ai_assistant.local_ai_manager import LocalAIManager

# Initialize at startup
local_ai = LocalAIManager()
model_path = "model/local_models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
if os.path.exists(model_path):
    local_ai.load_model(model_path, threads=4)
    print("✅ Local AI ready")

# API endpoint
@app.route('/api/local_ai/chat', methods=['POST'])
def local_ai_chat():
    data = request.json
    message = data.get('message', '')
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    response = local_ai.chat(message, max_tokens=512)
    
    return jsonify({
        'response': response,
        'stats': local_ai.get_stats()
    })

# Reset conversation
@app.route('/api/local_ai/reset', methods=['POST'])
def local_ai_reset():
    local_ai.clear_history()
    return jsonify({'message': 'Conversation reset'})

# Performance stats
@app.route('/api/local_ai/stats', methods=['GET'])
def local_ai_stats():
    return jsonify(local_ai.get_stats())
```

---

## 🎛️ **Step 5: Add Frontend UI**

Create chat interface in `SettingsDetail.tsx`:

```typescript
const testLocalAI = async () => {
  const response = await fetch('http://localhost:5000/api/local_ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: 'Hello from local AI!' })
  });
  
  const data = await response.json();
  console.log('Response:', data.response);
  console.log('Speed:', data.stats.avg_tokens_per_sec, 'tokens/sec');
};
```

---

## ⚡ **Performance Expectations**

### Your Hardware (8GB RAM, CPU-only)

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| **TinyLlama-1.1B** | 700MB | 10-15 tok/s | ⭐⭐⭐⭐ | **Recommended** - General tasks |
| **Qwen2-0.5B** | 400MB | 15-25 tok/s | ⭐⭐⭐ | Quick responses, simple tasks |

### Optimization Tips

1. **CPU Threads:** Start with 4, adjust based on your CPU cores
   ```python
   manager.load_model(model_path, threads=4)  # Adjust 2-8
   ```

2. **Context Length:** Reduce for faster responses
   ```python
   # In local_ai_manager.py, line 92
   n_ctx=1024,  # Reduce from 2048 to 1024
   ```

3. **Temperature:** Lower = faster, more deterministic
   ```python
   manager.generate(prompt, temperature=0.5)  # 0.5 instead of 0.7
   ```

4. **Close Other Apps:** Free RAM before using AI

---

## 🔍 **Troubleshooting**

### "DLL load failed" or "Library not found"
```bash
# Windows: Install Visual C++ Redistributable
# Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe

# Linux: Install build tools
sudo apt install build-essential

# Mac: Install Xcode Command Line Tools
xcode-select --install
```

### "Out of memory"
```python
# Reduce context window
n_ctx=1024  # Instead of 2048

# Use smaller model (Qwen2-0.5B instead of TinyLlama-1.1B)
```

### Slow responses (< 5 tokens/sec)
```python
# Increase CPU threads
threads=6  # Or 8, depending on your CPU

# Enable AVX2 optimization (reinstall llama-cpp-python as shown in Step 1B)
```

### Model not found
```bash
# Check path
ls model/local_models/

# Re-download
huggingface-cli download TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf --local-dir model/local_models
```

---

## 🎯 **Next Steps**

1. ✅ **Test basic inference** (Step 3)
2. 📊 **Benchmark your hardware** (run multiple queries, check avg speed)
3. 🔧 **Integrate with backend** (Step 4)
4. 🎨 **Build frontend UI** (Step 5)
5. 🚀 **Advanced:**
   - Fine-tuning on your data (requires ~4-6GB extra RAM)
   - Knowledge base with RAG (ChromaDB)
   - Hybrid routing (local for simple, API for complex)

---

## 📚 **Resources**

- **llama-cpp-python:** https://github.com/abetlen/llama-cpp-python
- **TinyLlama Models:** https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF
- **Qwen2 Models:** https://huggingface.co/Qwen/Qwen2-0.5B-Instruct-GGUF
- **GGUF Format:** Quantized models optimized for CPU inference

---

## 💡 **Tips for 8GB RAM**

✅ **DO:**
- Close browser/heavy apps before using AI
- Use TinyLlama or Qwen2 (< 1GB models)
- Monitor RAM usage with Task Manager
- Use streaming for long responses

❌ **DON'T:**
- Try models > 2B parameters (too slow/crash)
- Run multiple models simultaneously
- Use context > 2048 tokens
- Expect GPU-level speed (10-15 tok/s is good!)

---

**Ready to start?** Run: `python ai_assistant/local_ai_manager.py`
