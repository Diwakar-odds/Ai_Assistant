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
        
        # Hardcoded to the preferred model file
        self.model_filename = "pulsar-final-q4_k_m.gguf"
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
                possible_paths = [
                    self.base_dir / "models" / self.model_filename,
                    Path(os.getcwd()) / "models" / self.model_filename,
                    Path(sys.executable).parent / "models" / self.model_filename,
                    Path(__file__).resolve().parent.parent.parent.parent.parent / "models" / self.model_filename
                ]
                
                found_path = None
                for p in possible_paths:
                    if p.exists():
                        found_path = p
                        break
                        
                if not found_path:
                    logger.error(f"Offline model not found in any standard path for {self.model_filename}")
                    raise FileNotFoundError(f"Offline model {self.model_filename} not found.")
                
                self.model_path = found_path
                    
                logger.info(f"Loading offline command model into memory: {self.model_filename}")
                print(f"Loading offline command model into memory: {self.model_filename}")
                
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
