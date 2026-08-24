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
                self.model_path = self.base_dir / "models" / self.model_filename
                
                if not self.model_path.exists():
                    logger.error(f"Offline model not found at {self.model_path}")
                    raise FileNotFoundError(f"Offline model not found at {self.model_path}")
                    
                logger.info(f"Loading offline command model into memory: {self.model_filename}")
                print(f"Loading offline command model into memory: {self.model_filename}")
                
                # Load the model!
                self.llm = Llama(
                    model_path=str(self.model_path),
                    n_gpu_layers=0,  # CPU only
                    n_ctx=2048,      # Context window large enough for chat
                    verbose=False    # Keep logs clean
                )
                logger.info("Local GGUF model successfully loaded into RAM.")
                
            return self.llm

# Expose a global instance
gguf_manager = GGUFModelManager()
