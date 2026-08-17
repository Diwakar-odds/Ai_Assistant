"""
Self-Supervised Learning System
Learns representations without labeled data

Features:
- Masked language modeling
- Autoencoding
- Rotation prediction
- Jigsaw puzzle solving
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


class SelfSupervisedLearner:
    """
    Self-supervised learning for data-efficient training
    """
    
    def __init__(self, db_path: str = "data/self_supervised.db",
                 hidden_dim: int = 256,
                 mask_probability: float = 0.15):
        self.db_path = db_path
        self.hidden_dim = hidden_dim
        self.mask_probability = mask_probability
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        if TORCH_AVAILABLE:
            # Encoder
            self.encoder = nn.Sequential(
                nn.Linear(768, hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(hidden_dim, hidden_dim)
            )
            
            # Decoder (for autoencoding)
            self.decoder = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, 768)
            )
            
            # MLM head (masked language modeling)
            self.mlm_head = nn.Linear(hidden_dim, 768)
            
            self.optimizer = torch.optim.Adam(
                list(self.encoder.parameters()) + 
                list(self.decoder.parameters()) + 
                list(self.mlm_head.parameters()),
                lr=0.001
            )
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pretraining_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    sample_id TEXT NOT NULL,
                    loss REAL NOT NULL,
                    accuracy REAL,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learned_representations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_id TEXT NOT NULL,
                    representation TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    epoch INTEGER NOT NULL,
                    task_type TEXT NOT NULL,
                    avg_loss REAL NOT NULL,
                    avg_accuracy REAL,
                    timestamp TEXT NOT NULL
                )
            """)
    
    def mask_tokens(self, tokens: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Mask tokens for MLM (Masked Language Modeling)
        
        Returns:
            masked_tokens, mask_positions, original_tokens
        """
        masked = tokens.copy()
        mask = np.random.random(tokens.shape) < self.mask_probability
        
        # Store original values
        original = tokens[mask].copy()
        
        # Replace with mask token (0), random token (10%), or keep (10%)
        for i, should_mask in enumerate(mask):
            if should_mask:
                rand = random.random()
                if rand < 0.8:
                    masked[i] = 0  # Mask token
                elif rand < 0.9:
                    masked[i] = random.randint(1, len(tokens))  # Random token
                # else: keep original (10%)
        
        return masked, mask, original
    
    def mlm_loss(self, features, mask, targets):
        """
        Masked Language Modeling loss
        
        Args:
            features: Input features
            mask: Boolean mask indicating which tokens to predict
            targets: Original token values
        """
        # Encode
        hidden = self.encoder(features)
        
        # Predict masked tokens
        predictions = self.mlm_head(hidden)
        
        # Loss only on masked positions
        loss = F.mse_loss(
            predictions[mask],
            targets[mask]
        )
        
        # Accuracy (simplified)
        pred_vals = predictions[mask].detach()
        target_vals = targets[mask]
        accuracy = 1 - torch.mean(torch.abs(pred_vals - target_vals) / (torch.abs(target_vals) + 1))
        
        return loss, accuracy.item()
    
    def autoencoding_loss(self, features):
        """
        Autoencoding: reconstruct input from latent representation
        """
        # Encode
        hidden = self.encoder(features)
        
        # Decode
        reconstructed = self.decoder(hidden)
        
        # Reconstruction loss
        loss = F.mse_loss(reconstructed, features)
        
        # Accuracy (reconstruction quality)
        accuracy = 1 - torch.mean(torch.abs(reconstructed - features) / (torch.abs(features) + 1))
        
        return loss, accuracy.item()
    
    def rotation_prediction_loss(self, features):
        """
        Rotation prediction: predict which rotation was applied
        (Simulated for generic features)
        """
        batch_size = features.size(0)
        
        # Generate rotations (0, 90, 180, 270 degrees)
        rotations = torch.randint(0, 4, (batch_size,))
        
        # Simulate rotation by permuting features
        rotated_features = features.clone()
        for i, rot in enumerate(rotations):
            if rot == 1:
                rotated_features[i] = torch.roll(features[i], 192, 0)
            elif rot == 2:
                rotated_features[i] = torch.roll(features[i], 384, 0)
            elif rot == 3:
                rotated_features[i] = torch.roll(features[i], 576, 0)
        
        # Encode
        hidden = self.encoder(rotated_features)
        
        # Predict rotation (4-way classification)
        rotation_head = nn.Linear(self.hidden_dim, 4).to(hidden.device)
        predictions = rotation_head(hidden)
        
        # Loss
        loss = F.cross_entropy(predictions, rotations)
        
        # Accuracy
        pred_labels = torch.argmax(predictions, dim=1)
        accuracy = (pred_labels == rotations).float().mean().item()
        
        return loss, accuracy
    
    def train_task(self, samples: List[np.ndarray], task_type: str,
                   epochs: int = 5) -> Dict:
        """
        Train on self-supervised task
        
        Args:
            samples: List of feature vectors
            task_type: 'mlm', 'autoencoding', or 'rotation'
            epochs: Number of training epochs
        """
        if not TORCH_AVAILABLE or not samples:
            return {}
        
        self.encoder.train()
        
        total_loss = 0
        total_accuracy = 0
        num_batches = 0
        
        for epoch in range(epochs):
            epoch_loss = 0
            epoch_accuracy = 0
            
            for sample in samples:
                features = torch.tensor(sample, dtype=torch.float32).unsqueeze(0)
                
                # Select task
                if task_type == 'mlm':
                    # Mask tokens
                    masked_features, mask, original = self.mask_tokens(sample)
                    masked_features = torch.tensor(masked_features, dtype=torch.float32).unsqueeze(0)
                    mask_tensor = torch.tensor(mask).unsqueeze(0)
                    original_tensor = torch.tensor(original, dtype=torch.float32)
                    
                    loss, accuracy = self.mlm_loss(masked_features, mask_tensor, features)
                
                elif task_type == 'autoencoding':
                    loss, accuracy = self.autoencoding_loss(features)
                
                elif task_type == 'rotation':
                    loss, accuracy = self.rotation_prediction_loss(features)
                
                else:
                    continue
                
                # Backprop
                self.optimizer.zero_grad()
                loss.backward()
                self.optimizer.step()
                
                epoch_loss += loss.item()
                epoch_accuracy += accuracy
                num_batches += 1
            
            avg_epoch_loss = epoch_loss / len(samples)
            avg_epoch_acc = epoch_accuracy / len(samples)
            
            total_loss += avg_epoch_loss
            total_accuracy += avg_epoch_acc
            
            # Save metrics
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO training_metrics
                    (epoch, task_type, avg_loss, avg_accuracy, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (epoch, task_type, avg_epoch_loss, avg_epoch_acc, 
                     datetime.now().isoformat()))
        
        return {
            'task_type': task_type,
            'avg_loss': total_loss / epochs,
            'avg_accuracy': total_accuracy / epochs,
            'epochs': epochs,
            'num_samples': len(samples)
        }
    
    def extract_representation(self, features: np.ndarray) -> np.ndarray:
        """Extract learned representation"""
        if not TORCH_AVAILABLE:
            return features
        
        self.encoder.eval()
        
        with torch.no_grad():
            features_tensor = torch.tensor(features, dtype=torch.float32)
            if len(features_tensor.shape) == 1:
                features_tensor = features_tensor.unsqueeze(0)
            
            representation = self.encoder(features_tensor)
            
            return representation.numpy()
    
    def save_representation(self, sample_id: str, representation: np.ndarray,
                           task_type: str):
        """Save learned representation"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO learned_representations
                (sample_id, representation, task_type, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                sample_id,
                json.dumps(representation.tolist()),
                task_type,
                datetime.now().isoformat()
            ))
    
    def get_stats(self) -> Dict:
        """Get learning statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(DISTINCT task_type) as task_types,
                    COUNT(*) as total_tasks,
                    AVG(loss) as avg_loss,
                    AVG(accuracy) as avg_accuracy
                FROM pretraining_tasks
            """)
            
            row = cursor.fetchone()
            if row:
                return {
                    'task_types': row[0] or 0,
                    'total_tasks': row[1] or 0,
                    'avg_loss': row[2] or 0,
                    'avg_accuracy': row[3] or 0,
                    'model_available': TORCH_AVAILABLE
                }
        
        return {}


def example_usage():
    """Demonstrate self-supervised learning"""
    learner = SelfSupervisedLearner(hidden_dim=128, mask_probability=0.15)
    
    print("Self-Supervised Learning Demo\n" + "="*50)
    
    if not TORCH_AVAILABLE:
        print("⚠️ PyTorch not available - showing conceptual demo only")
        return
    
    # Generate sample data
    print("\n1. Generating unlabeled data...")
    samples = [np.random.randn(768) for _ in range(20)]
    print(f"  Generated {len(samples)} unlabeled samples")
    
    # Train on different tasks
    print("\n2. Training on self-supervised tasks...")
    
    tasks = ['autoencoding', 'mlm', 'rotation']
    
    for task in tasks:
        print(f"\n  Task: {task}")
        metrics = learner.train_task(samples[:10], task, epochs=3)
        print(f"    Loss: {metrics['avg_loss']:.4f}")
        print(f"    Accuracy: {metrics['avg_accuracy']:.2%}")
    
    # Extract representations
    print("\n3. Extracting learned representations...")
    for i, sample in enumerate(samples[:5]):
        representation = learner.extract_representation(sample)
        learner.save_representation(f'sample_{i}', representation[0], 'autoencoding')
        print(f"  Sample {i}: representation shape = {representation.shape}")
    
    # Stats
    stats = learner.get_stats()
    print(f"\n4. Statistics:")
    print(f"  Task types: {stats['task_types']}")
    print(f"  Total tasks: {stats['total_tasks']}")
    print(f"  Avg accuracy: {stats['avg_accuracy']:.2%}")


if __name__ == "__main__":
    example_usage()
