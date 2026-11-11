import sys
import subprocess
import os
import time

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__, log_category="app")
except Exception:
    import logging
    logger = logging.getLogger(__name__)

def check_fix():
    print("Checking Local Model Setup...")
    
    # 1. Check for compiler
    print("\n1. Checking for C++ Compiler...")
    try:
        subprocess.check_call(["cl"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Compiler found!")
        HAS_COMPILER = True
    except:
        print("Compiler (cl.exe) not found in PATH.")
        print("   If you installed Visual Studio Build Tools, you may need to restart your terminal/PC.")
        HAS_COMPILER = False

    # 2. Try to import llama_cpp
    print("\n2. Verification of 'llama-cpp-python'...")
    try:
        import llama_cpp
        print("llama-cpp-python is importable!")
    except Exception:
        print("Import failed. Attempting repair...")
        
        if HAS_COMPILER:
            print("Compiler detected. Rebuilding from source...")
            cmd = [sys.executable, "-m", "pip", "install", "llama-cpp-python", 
                   "--force-reinstall", "--no-binary", "llama-cpp-python", "--no-cache-dir"]
        else:
            print("No compiler. Trying pre-built wheel (v0.2.77)...")
            cmd = [sys.executable, "-m", "pip", "install", "llama-cpp-python==0.2.77",
                   "numpy<2.0", "--force-reinstall", "--extra-index-url", "https://abetlen.github.io/llama-cpp-python/whl/cpu"]
        
        try:
            subprocess.check_call(cmd)
            print("Repair attempted. Retrying import...")
            import llama_cpp
            print("Import successful!")
        except Exception as e2:
            print(f"Repair failed: {e2}")
            return

    # 3. Run Manager Test
    print("\n3. Testing Local GGUF Model Manager...")
    try:
        from ai_assistant.ai.gguf_model_manager import get_gguf_manager, llama_cpp_available
        print(f"llama_cpp available: {llama_cpp_available()}")
        mgr = get_gguf_manager()
        print(f"GGUF Manager status: {mgr.get_status()}")
    except Exception as e:
        logger.debug(f"Test failed: {e}")

if __name__ == "__main__":
    check_fix()
    input("\nPress Enter to exit...")
