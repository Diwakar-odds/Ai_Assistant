# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
GGUF Model Manager
Centralized Singleton manager for the local Llama GGUF model.
Ensures the 4.6GB model is loaded exactly once into RAM and shared across
intent classification and text generation.
"""

import os
import sys
import logging
import threading
from pathlib import Path

# Lazily load llama_cpp
try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False

logger = logging.getLogger(__name__)

class GGUFModelManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GGUFModelManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
            
    def __init__(self):
        # Prevent re-initialization
        if getattr(self, '_initialized', False):
            return
            
        self.llm = None
        self.model_path = None
        self.base_dir = Path(__file__).resolve().parents[4]
        
        # Hardcoded default or auto-detect in models folder
        self.model_filename = "pulsar-final-q3_k_m.gguf"
        self._initialized = True

    def get_model(self) -> 'Llama':
        """
        Returns the singleton instance of the Llama model.
        Loads it into memory on first access.
        """
        if not LLAMA_AVAILABLE:
            raise ImportError("llama-cpp-python is not installed. Please run: pip install llama-cpp-python")
            
        with self._lock:
            if self.llm is None:
                # Check models directory candidates for any downloaded .gguf file
                candidate_model_dirs = [
                    self.base_dir / "models",
                    Path(os.getcwd()) / "models",
                    Path(sys.executable).parent / "models",
                    Path(sys.executable).parent / "_internal" / "models",
                    Path(getattr(sys, '_MEIPASS', '')) / "models" if getattr(sys, '_MEIPASS', None) else None,
                    Path(__file__).resolve().parent.parent.parent.parent.parent / "models"
                ]
                
                found_path = None
                preferred_names = ["pulsar-final-q4_k_m.gguf", "pulsar-final-q3_k_m.gguf", "pulsar-final-q4_k_m.gguf", self.model_filename]
                
                for mdir in candidate_model_dirs:
                    if mdir and mdir.exists():
                        for pref in preferred_names:
                            candidate = mdir / pref
                            if candidate.exists():
                                found_path = candidate
                                break
                        if found_path:
                            break
                        gguf_files = list(mdir.glob("*.gguf"))
                        if gguf_files:
                            found_path = gguf_files[0]
                            break

                if not found_path:
                    logger.error(f"Offline model not found in any standard path for {self.model_filename}")
                    raise FileNotFoundError(f"Offline model not found. Please place your .gguf file in the models/ folder.")
                
                self.model_path = found_path
                    
                logger.info(f"Loading offline command model into memory: {self.model_path.name}")
                print(f"Loading offline command model into memory: {self.model_path.name}")
                
                # OS-Level Optimization for Intel Core Ultra
                import multiprocessing
                
                # Intel Core Ultra 7 has 6 P-Cores. Llama.cpp runs fastest when restricted to physical P-Cores.
                # Avoid Hyperthreads and E-Cores which cause L3 cache thrashing.
                optimal_threads = 6
                
                # Load the model!
                self.llm = Llama(
                    model_path=str(self.model_path),
                    n_gpu_layers=0,       # CPU only
                    n_ctx=2048,           # Context window large enough for chat
                    n_threads=optimal_threads, # Force strict thread limit (prevents E-Core slowdown)
                    n_batch=512,          # Optimize prompt processing batch size
                    use_mlock=True,       # Force Windows to keep model in RAM (prevent pagefile swapping)
                    use_mmap=True,        # Use memory mapping for fast loading
                    verbose=False         # Keep logs clean
                )
                logger.info(f"Local GGUF model loaded into RAM with {optimal_threads} physical threads & mlock.")

                
        return self.llm

# Expose a global instance
gguf_manager = GGUFModelManager()
