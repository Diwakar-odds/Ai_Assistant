"""
Embeddings and vector search utilities for RAG.
Uses OpenAI embeddings and FAISS for similarity search.
"""
import os
import numpy as np
from typing import List

try:
    import faiss
except ImportError:
    faiss = None

class EmbeddingStore:
    def __init__(self, dim=1536):
        self.dim = dim
        self.texts = []
        self.embeddings = []
        if faiss:
            self.index = faiss.IndexFlatL2(dim)
        else:
            self.index = None

    def add(self, text: str, embedding: List[float]):
        self.texts.append(text)
        self.embeddings.append(np.array(embedding, dtype=np.float32))
        if self.index:
            self.index.add(np.array([embedding], dtype=np.float32))

    def search(self, query_embedding: List[float], top_k=5):
        if self.index:
            D, I = self.index.search(np.array([query_embedding], dtype=np.float32), top_k)
            return [self.texts[i] for i in I[0] if i < len(self.texts)]
        else:
            # Fallback: cosine similarity
            scores = [np.dot(query_embedding, emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb)) for emb in self.embeddings]
            top_indices = np.argsort(scores)[::-1][:top_k]
            return [self.texts[i] for i in top_indices]


def get_openai_embedding(text: str, api_key: str = None) -> List[float]:
    """Get OpenAI embedding for text."""
    import requests
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    url = "https://api.openai.com/v1/embeddings"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"input": text, "model": "text-embedding-3-small"}
    resp = requests.post(url, headers=headers, json=data, timeout=10)
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]
