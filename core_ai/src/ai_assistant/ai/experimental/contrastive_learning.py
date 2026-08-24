"""
Contrastive Learning System
Learns better embeddings through contrastive objectives

Features:
- SimCLR-style contrastive learning
- Positive/negative pair generation
- Temperature-scaled loss
- Embedding quality improvement
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Any
from pathlib import Path
import random

if TYPE_CHECKING:
    import torch
    import torch.nn as nn

try:
    import numpy as np
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠️ torch not available")


class ContrastiveLearner:
    """
    Contrastive learning for better embeddings
    """
    
    def __init__(self, db_path: str = "data/contrastive_learning.db",
                 embedding_dim: int = 128,
                 temperature: float = 0.5):
        self.db_path = db_path
        self.embedding_dim = embedding_dim
        self.temperature = temperature
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        if TORCH_AVAILABLE:
            # Simple projection head
            self.encoder = nn.Sequential(
                nn.Linear(768, 256),  # Assuming 768-dim input (BERT-like)
                nn.ReLU(),
                nn.Linear(256, embedding_dim)
            )
            self.optimizer = torch.optim.Adam(self.encoder.parameters(), lr=0.001)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_id TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    label TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS contrastive_pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    anchor_id TEXT NOT NULL,
                    positive_id TEXT NOT NULL,
                    negative_id TEXT NOT NULL,
                    similarity_score REAL,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    epoch INTEGER NOT NULL,
                    loss REAL NOT NULL,
                    num_pairs INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
    
    def generate_pairs(self, samples: List[Dict]) -> List[Dict]:
        """
        Generate contrastive pairs (anchor, positive, negative)
        
        Args:
            samples: List of {id, features, label}
        
        Returns:
            List of {anchor, positive, negative} triplets
        """
        pairs = []
        
        # Group by label for positive pairs
        label_groups = {}
        for sample in samples:
            label = sample.get('label', 'unknown')
            if label not in label_groups:
                label_groups[label] = []
            label_groups[label].append(sample)
        
        # Generate triplets
        for sample in samples:
            anchor = sample
            label = anchor.get('label', 'unknown')
            
            # Positive: same label
            same_label = label_groups.get(label, [])
            if len(same_label) > 1:
                positive = random.choice([s for s in same_label if s['id'] != anchor['id']])
            else:
                continue  # Skip if no positive available
            
            # Negative: different label
            diff_labels = [s for s in samples if s.get('label') != label]
            if diff_labels:
                negative = random.choice(diff_labels)
            else:
                continue
            
            pairs.append({
                'anchor': anchor,
                'positive': positive,
                'negative': negative
            })
        
        return pairs
    
    def nt_xent_loss(self, anchor, positive, negative):
        """
        NT-Xent (Normalized Temperature-scaled Cross Entropy) Loss
        Used in SimCLR
        """
        # Normalize embeddings
        anchor = F.normalize(anchor, dim=1)
        positive = F.normalize(positive, dim=1)
        negative = F.normalize(negative, dim=1)
        
        # Positive similarity
        pos_sim = torch.sum(anchor * positive, dim=1) / self.temperature
        
        # Negative similarity
        neg_sim = torch.sum(anchor * negative, dim=1) / self.temperature
        
        # Concatenate
        logits = torch.cat([pos_sim.unsqueeze(1), neg_sim.unsqueeze(1)], dim=1)
        
        # Labels (positive is always first)
        labels = torch.zeros(logits.size(0), dtype=torch.long)
        
        # Cross-entropy loss
        loss = F.cross_entropy(logits, labels)
        
        return loss
    
    def triplet_loss(self, anchor, positive, negative, margin: float = 1.0):
        """
        Triplet loss: ||anchor - positive||^2 - ||anchor - negative||^2 + margin
        """
        pos_dist = F.pairwise_distance(anchor, positive)
        neg_dist = F.pairwise_distance(anchor, negative)
        
        loss = F.relu(pos_dist - neg_dist + margin)
        
        return loss.mean()
    
    def train_batch(self, pairs: List[Dict], loss_type: str = 'nt_xent') -> float:
        """
        Train on batch of contrastive pairs
        
        Args:
            pairs: List of {anchor, positive, negative} with features
            loss_type: 'nt_xent' or 'triplet'
        """
        if not TORCH_AVAILABLE or not pairs:
            return 0.0
        
        self.encoder.train()
        
        # Extract features
        anchors = torch.tensor([p['anchor']['features'] for p in pairs], dtype=torch.float32)
        positives = torch.tensor([p['positive']['features'] for p in pairs], dtype=torch.float32)
        negatives = torch.tensor([p['negative']['features'] for p in pairs], dtype=torch.float32)
        
        # Encode
        anchor_emb = self.encoder(anchors)
        positive_emb = self.encoder(positives)
        negative_emb = self.encoder(negatives)
        
        # Compute loss
        if loss_type == 'nt_xent':
            loss = self.nt_xent_loss(anchor_emb, positive_emb, negative_emb)
        else:  # triplet
            loss = self.triplet_loss(anchor_emb, positive_emb, negative_emb)
        
        # Backprop
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        return loss.item()
    
    def train_epoch(self, samples: List[Dict], batch_size: int = 32,
                   loss_type: str = 'nt_xent') -> float:
        """Train one epoch on samples"""
        # Generate pairs
        pairs = self.generate_pairs(samples)
        
        if not pairs:
            return 0.0
        
        total_loss = 0
        num_batches = 0
        
        # Batch training
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i:i+batch_size]
            loss = self.train_batch(batch, loss_type)
            total_loss += loss
            num_batches += 1
        
        avg_loss = total_loss / num_batches if num_batches > 0 else 0
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO training_history (epoch, loss, num_pairs, timestamp)
                VALUES (?, ?, ?, ?)
            """, (1, avg_loss, len(pairs), datetime.now().isoformat()))
        
        return avg_loss
    
    def encode(self, features: np.ndarray) -> np.ndarray:
        """Encode features to embeddings"""
        if not TORCH_AVAILABLE:
            return features  # Fallback: return original
        
        self.encoder.eval()
        
        with torch.no_grad():
            features_tensor = torch.tensor(features, dtype=torch.float32)
            if len(features_tensor.shape) == 1:
                features_tensor = features_tensor.unsqueeze(0)
            
            embeddings = self.encoder(features_tensor)
            
            return embeddings.numpy()
    
    def save_embedding(self, sample_id: str, embedding: np.ndarray, 
                      label: Optional[str] = None):
        """Save embedding to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO embeddings (sample_id, embedding, label, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                sample_id,
                json.dumps(embedding.tolist()),
                label,
                datetime.now().isoformat()
            ))
    
    def find_similar(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict]:
        """Find similar samples by embedding"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT sample_id, embedding, label
                FROM embeddings
            """)
            
            similarities = []
            
            # Normalize query
            query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)
            
            for row in cursor.fetchall():
                sample_id, emb_json, label = row
                emb = np.array(json.loads(emb_json))
                
                # Cosine similarity
                emb_norm = emb / (np.linalg.norm(emb) + 1e-10)
                similarity = np.dot(query_norm, emb_norm)
                
                similarities.append({
                    'sample_id': sample_id,
                    'label': label,
                    'similarity': float(similarity)
                })
            
            # Sort and return top-k
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:top_k]
    
    def evaluate_embedding_quality(self, test_samples: List[Dict]) -> Dict:
        """
        Evaluate embedding quality using retrieval metrics
        """
        if not test_samples:
            return {}
        
        correct = 0
        total = 0
        
        for sample in test_samples:
            # Encode query
            query_emb = self.encode(np.array(sample['features']))
            
            # Find similar
            similar = self.find_similar(query_emb[0], top_k=5)
            
            # Check if top-1 has same label
            if similar and similar[0]['label'] == sample.get('label'):
                correct += 1
            
            total += 1
        
        accuracy = correct / total if total > 0 else 0
        
        return {
            'retrieval_accuracy': accuracy,
            'test_samples': total
        }
    
    def get_stats(self) -> Dict:
        """Get learning statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_embeddings,
                    (SELECT COUNT(*) FROM contrastive_pairs) as total_pairs,
                    (SELECT AVG(loss) FROM training_history) as avg_loss
                FROM embeddings
            """)
            
            row = cursor.fetchone()
            if row:
                return {
                    'total_embeddings': row[0] or 0,
                    'total_pairs': row[1] or 0,
                    'avg_loss': row[2] or 0,
                    'model_available': TORCH_AVAILABLE
                }
        
        return {}


def example_usage():
    """Demonstrate contrastive learning"""
    learner = ContrastiveLearner(embedding_dim=64, temperature=0.5)
    
    print("Contrastive Learning Demo\n" + "="*50)
    
    if not TORCH_AVAILABLE:
        print("⚠️ PyTorch not available - showing conceptual demo only")
        return
    
    # Generate sample data
    print("\n1. Generating sample data...")
    samples = []
    
    # Class 0: low values
    for i in range(20):
        features = np.random.randn(768) * 0.5 - 1.0
        samples.append({'id': f'sample_{i}_class0', 'features': features.tolist(), 'label': 'class_0'})
    
    # Class 1: high values
    for i in range(20):
        features = np.random.randn(768) * 0.5 + 1.0
        samples.append({'id': f'sample_{i}_class1', 'features': features.tolist(), 'label': 'class_1'})
    
    print(f"  Generated {len(samples)} samples")
    
    # Generate pairs
    print("\n2. Generating contrastive pairs...")
    pairs = learner.generate_pairs(samples)
    print(f"  Generated {len(pairs)} triplets")
    
    # Train
    print("\n3. Training with contrastive loss...")
    for epoch in range(3):
        loss = learner.train_epoch(samples, batch_size=16, loss_type='nt_xent')
        print(f"  Epoch {epoch+1}: loss = {loss:.4f}")
    
    # Evaluate
    print("\n4. Evaluating embedding quality...")
    test_samples = samples[:10]
    metrics = learner.evaluate_embedding_quality(test_samples)
    print(f"  Retrieval accuracy: {metrics['retrieval_accuracy']:.1%}")
    
    # Save embeddings
    print("\n5. Saving embeddings...")
    for sample in samples[:5]:
        emb = learner.encode(np.array(sample['features']))
        learner.save_embedding(sample['id'], emb[0], sample['label'])
    
    # Find similar
    print("\n6. Finding similar samples...")
    query = samples[0]
    query_emb = learner.encode(np.array(query['features']))
    similar = learner.find_similar(query_emb[0], top_k=3)
    
    print(f"  Query: {query['id']} (label: {query['label']})")
    for s in similar:
        print(f"    {s['sample_id']}: similarity={s['similarity']:.3f}, label={s['label']}")
    
    # Stats
    stats = learner.get_stats()
    print(f"\n7. Statistics:")
    print(f"  Total embeddings: {stats['total_embeddings']}")
    print(f"  Total pairs: {stats['total_pairs']}")
    print(f"  Avg loss: {stats['avg_loss']:.4f}")


if __name__ == "__main__":
    example_usage()
