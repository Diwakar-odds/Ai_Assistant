"""
Shared Embedder Singleton for Pulsar AI Assistant
Centralizes SentenceTransformer ('all-MiniLM-L6-v2') to:
1. Eliminate duplicate model loads across memory/RAG/cache/routing modules (saves ~250MB+ RAM).
2. Suppress TensorFlow overhead and warnings during model load.
3. Provide fast L2-normalized NumPy vector computations.
"""

import os
import sys
import threading
from typing import Optional, List, Union
import numpy as np

# Suppress heavy TensorFlow imports before transformers initializes
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="ai")

_embedder_lock = threading.Lock()
_shared_model = None
_model_attempted = False
_model_available = False


def is_embedder_available() -> bool:
    """Return True if sentence_transformers is installed and importable."""
    try:
        import importlib.util
        return importlib.util.find_spec("sentence_transformers") is not None
    except Exception:
        return False


def get_shared_embedder(model_name: str = "all-MiniLM-L6-v2"):
    """
    Thread-safe lazy-loader for the shared SentenceTransformer instance.
    Returns the loaded model or None if unavailable.
    """
    global _shared_model, _model_attempted, _model_available
    if _shared_model is not None:
        return _shared_model

    with _embedder_lock:
        if _shared_model is not None:
            return _shared_model
        if _model_attempted and not _model_available:
            return None

        _model_attempted = True
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"⚡ Loading shared embedder: {model_name}...")
            # Try offline / cached first to prevent online latency
            try:
                _shared_model = SentenceTransformer(model_name, local_files_only=True)
            except Exception:
                _shared_model = SentenceTransformer(model_name)
            _model_available = True
            logger.info(f"✅ Shared embedder loaded successfully: {model_name}")
            return _shared_model
        except Exception as e:
            logger.warning(f"Shared embedder failed to load ({e}). Vector operations will fallback.")
            _shared_model = None
            _model_available = False
            return None


def encode_text(text: str, normalize: bool = True) -> Optional[np.ndarray]:
    """
    Encode a single string into a 1D NumPy vector (384-dim for all-MiniLM-L6-v2).
    If normalize=True, output has L2 norm = 1.0.
    """
    model = get_shared_embedder()
    if model is None:
        return None
    try:
        vec = model.encode([text], convert_to_numpy=True, show_progress_bar=False)[0]
        if normalize:
            norm = np.linalg.norm(vec)
            if norm > 1e-12:
                vec = vec / norm
        return vec.astype(np.float32)
    except Exception as e:
        logger.warning(f"Embedding encode error: {e}")
        return None


def encode_batch(texts: List[str], normalize: bool = True) -> Optional[np.ndarray]:
    """
    Encode a batch of strings into a 2D NumPy array (N, 384).
    If normalize=True, each row has L2 norm = 1.0.
    """
    model = get_shared_embedder()
    if model is None or not texts:
        return None
    try:
        vecs = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        if normalize:
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms = np.maximum(norms, 1e-12)
            vecs = vecs / norms
        return vecs.astype(np.float32)
    except Exception as e:
        logger.warning(f"Batch embedding encode error: {e}")
        return None


def cosine_similarity(query_vec: np.ndarray, corpus_vecs: np.ndarray) -> np.ndarray:
    """
    High-performance cosine similarity via matrix dot-product.
    Assumes query_vec and corpus_vecs are already L2-normalized.
    query_vec: shape (D,) or (1, D)
    corpus_vecs: shape (N, D)
    Returns: 1D array of shape (N,) with similarity scores in [-1.0, 1.0].
    """
    q = query_vec.reshape(-1)
    return np.dot(corpus_vecs, q)
