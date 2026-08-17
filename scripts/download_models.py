import os
import sys
from pathlib import Path

def install_package(package):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Ensure huggingface_hub is installed
try:
    from huggingface_hub import hf_hub_download
except ImportError:
    print("Installing huggingface_hub...")
    install_package("huggingface_hub")
    from huggingface_hub import hf_hub_download

MODELS = {
    "Llama-3.2-3B": {
        "repo": "Bartowski/Llama-3.2-3B-Instruct-GGUF",
        "file": "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
    },
    "Qwen-2.5-1.5B": {
        "repo": "Qwen/Qwen2.5-1.5B-Instruct-GGUF",
        "file": "qwen2.5-1.5b-instruct-q4_k_m.gguf"
    },
    "Llama-3.2-1B": {
        "repo": "Bartowski/Llama-3.2-1B-Instruct-GGUF",
        "file": "Llama-3.2-1B-Instruct-Q4_K_M.gguf"
    }
}

DEST_DIR = Path("model/local_models")
DEST_DIR.mkdir(parents=True, exist_ok=True)

print(f"Downloading optimized models to {DEST_DIR.absolute()}...")
print("These models are selected for 8GB RAM / 1GB VRAM systems.")

for name, config in MODELS.items():
    print(f"\n--- Downloading {name} ---")
    try:
        file_path = hf_hub_download(
            repo_id=config["repo"],
            filename=config["file"],
            local_dir=DEST_DIR,
            local_dir_use_symlinks=False
        )
        print(f"✅ Successfully downloaded: {name}")
    except Exception as e:
        print(f"❌ Failed to download {name}: {e}")

print("\nDone! You can now update 'local_ai_manager.py' to use one of these models.")
