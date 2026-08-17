"""
Domain-Adapted Embeddings
Fine-tune embeddings for user's specific domain
"""

import numpy as np
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


@dataclass
class DomainExample:
    """Training example for domain adaptation"""
    text: str
    domain_label: str
    timestamp: str
    metadata: Dict[str, Any]


class DomainAdapter(nn.Module if TORCH_AVAILABLE else object):
    """Adapter network for domain-specific fine-tuning"""
    
    def __init__(self, embedding_dim: int, adapter_dim: int = 64):
        if TORCH_AVAILABLE:
            super().__init__()
            self.down_project = nn.Linear(embedding_dim, adapter_dim)
            self.up_project = nn.Linear(adapter_dim, embedding_dim)
            self.activation = nn.ReLU()
        else:
            self.down_matrix = np.random.randn(adapter_dim, embedding_dim) * 0.01
            self.up_matrix = np.random.randn(embedding_dim, adapter_dim) * 0.01
    
    def forward(self, x):
        """Adapter forward pass"""
        if TORCH_AVAILABLE:
            # Bottleneck architecture
            h = self.activation(self.down_project(x))
            adapted = self.up_project(h)
            return x + adapted  # Residual connection
        else:
            # Simple linear transformation
            h = np.maximum(0, np.dot(x, self.down_matrix.T))
            adapted = np.dot(h, self.up_matrix.T)
            return x + adapted


class DomainAdaptedEmbeddings:
    """
    Domain-adapted embeddings system
    Fine-tunes pre-trained embeddings for specific domains
    """
    
    def __init__(self,
                 base_model: str = "all-MiniLM-L6-v2",
                 adapter_dim: int = 64,
                 db_path: str = "data/domain_embeddings.db"):
        
        self.db_path = db_path
        self.adapter_dim = adapter_dim
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        # Load base embedding model
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.base_model = SentenceTransformer(base_model)
                self.embedding_dim = self.base_model.get_sentence_embedding_dimension()
            except:
                logger.warning(f"Failed to load {base_model}, using fallback")
                self.base_model = None
                self.embedding_dim = 384
        else:
            self.base_model = None
            self.embedding_dim = 384
        
        # Domain-specific adapters
        self.adapters = {}
        self.domain_examples = defaultdict(list)
        self.domain_stats = {}
        
        logger.info(f"Domain embeddings initialized: {base_model}")
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS domains (
                    domain_id TEXT PRIMARY KEY,
                    description TEXT,
                    num_examples INTEGER,
                    created_at TEXT,
                    last_trained TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS domain_examples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain_id TEXT,
                    text TEXT,
                    timestamp TEXT,
                    metadata TEXT,
                    FOREIGN KEY (domain_id) REFERENCES domains(domain_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings_cache (
                    text_hash TEXT PRIMARY KEY,
                    domain_id TEXT,
                    embedding TEXT,
                    timestamp TEXT
                )
            """)
    
    def register_domain(self, domain_id: str, description: str = ""):
        """Register a new domain"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO domains (domain_id, description, num_examples, created_at)
                VALUES (?, ?, ?, ?)
            """, (domain_id, description, 0, datetime.now().isoformat()))
        
        # Create adapter for this domain
        self.adapters[domain_id] = DomainAdapter(self.embedding_dim, self.adapter_dim)
        
        logger.info(f"Domain registered: {domain_id}")
    
    def add_domain_example(self, domain_id: str, text: str, metadata: Dict = None):
        """Add training example for domain adaptation"""
        if domain_id not in self.adapters:
            self.register_domain(domain_id)
        
        example = DomainExample(
            text=text,
            domain_label=domain_id,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        self.domain_examples[domain_id].append(example)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO domain_examples (domain_id, text, timestamp, metadata)
                VALUES (?, ?, ?, ?)
            """, (domain_id, text, example.timestamp, json.dumps(metadata or {})))
            
            conn.execute("""
                UPDATE domains SET num_examples = num_examples + 1 WHERE domain_id = ?
            """, (domain_id,))
    
    def get_base_embedding(self, text: str) -> np.ndarray:
        """Get base embedding from pre-trained model"""
        if self.base_model is not None:
            return self.base_model.encode(text, convert_to_numpy=True)
        else:
            # Fallback: simple TF-IDF style embedding
            words = text.lower().split()
            embedding = np.zeros(self.embedding_dim)
            for i, word in enumerate(words[:self.embedding_dim]):
                embedding[i] = hash(word) % 100 / 100.0
            return embedding
    
    def get_adapted_embedding(self, text: str, domain_id: str) -> np.ndarray:
        """Get domain-adapted embedding"""
        # Get base embedding
        base_emb = self.get_base_embedding(text)
        
        # Apply domain adapter if available
        if domain_id in self.adapters:
            if TORCH_AVAILABLE:
                base_tensor = torch.FloatTensor(base_emb).unsqueeze(0)
                with torch.no_grad():
                    adapted_tensor = self.adapters[domain_id](base_tensor)
                adapted_emb = adapted_tensor.squeeze(0).numpy()
            else:
                adapted_emb = self.adapters[domain_id].forward(base_emb)
            
            return adapted_emb
        else:
            return base_emb
    
    def train_adapter(self, domain_id: str, num_epochs: int = 10):
        """Train adapter on domain examples"""
        if domain_id not in self.adapters:
            logger.warning(f"Domain {domain_id} not registered")
            return
        
        if len(self.domain_examples[domain_id]) < 2:
            logger.warning(f"Not enough examples for domain {domain_id}")
            return
        
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not available, skipping adapter training")
            return
        
        adapter = self.adapters[domain_id]
        optimizer = torch.optim.Adam([
            {'params': adapter.down_project.parameters()},
            {'params': adapter.up_project.parameters()}
        ], lr=0.001)
        
        examples = self.domain_examples[domain_id]
        
        for epoch in range(num_epochs):
            total_loss = 0
            
            for example in examples:
                # Get base embedding
                base_emb = self.get_base_embedding(example.text)
                base_tensor = torch.FloatTensor(base_emb).unsqueeze(0)
                
                # Forward through adapter
                adapted = adapter(base_tensor)
                
                # Contrastive loss: push away from random embeddings
                random_emb = torch.randn_like(adapted)
                
                # Maximize similarity to base, minimize to random
                loss = -F.cosine_similarity(adapted, base_tensor).mean() + \
                       F.cosine_similarity(adapted, random_emb).mean()
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                total_loss += loss.item()
            
            if epoch % 5 == 0:
                avg_loss = total_loss / len(examples)
                logger.info(f"Domain {domain_id} Epoch {epoch}: Loss={avg_loss:.4f}")
        
        # Update database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE domains SET last_trained = ? WHERE domain_id = ?
            """, (datetime.now().isoformat(), domain_id))
        
        logger.info(f"Adapter trained for domain: {domain_id}")
    
    def compute_domain_similarity(self, text: str, domain_id: str) -> float:
        """Compute similarity between text and domain"""
        if domain_id not in self.domain_examples:
            return 0.0
        
        # Get adapted embedding
        query_emb = self.get_adapted_embedding(text, domain_id)
        
        # Compare with domain examples
        similarities = []
        for example in self.domain_examples[domain_id][:20]:  # Sample
            example_emb = self.get_adapted_embedding(example.text, domain_id)
            sim = np.dot(query_emb, example_emb) / (
                np.linalg.norm(query_emb) * np.linalg.norm(example_emb) + 1e-8
            )
            similarities.append(sim)
        
        return float(np.mean(similarities)) if similarities else 0.0
    
    def detect_domain(self, text: str) -> Tuple[str, float]:
        """Detect most likely domain for text"""
        if len(self.adapters) == 0:
            return "unknown", 0.0
        
        domain_scores = {}
        for domain_id in self.adapters.keys():
            score = self.compute_domain_similarity(text, domain_id)
            domain_scores[domain_id] = score
        
        best_domain = max(domain_scores, key=domain_scores.get)
        best_score = domain_scores[best_domain]
        
        return best_domain, best_score
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM domains")
            num_domains = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM domain_examples")
            total_examples = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT domain_id, num_examples FROM domains ORDER BY num_examples DESC LIMIT 5
            """)
            top_domains = cursor.fetchall()
        
        return {
            'num_domains': num_domains,
            'total_examples': total_examples,
            'num_adapters': len(self.adapters),
            'top_domains': [{'domain': d[0], 'examples': d[1]} for d in top_domains],
            'sentence_transformers_available': SENTENCE_TRANSFORMERS_AVAILABLE,
            'torch_available': TORCH_AVAILABLE
        }
