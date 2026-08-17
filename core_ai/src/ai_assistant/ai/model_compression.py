"""
Model Compression System
Reduces model size and latency through quantization, pruning, and distillation

Features:
- Dynamic quantization for CPU inference
- Structured pruning
- Knowledge distillation
- Mixed precision support
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Any
from pathlib import Path
import os

if TYPE_CHECKING:
    import torch
    import torch.nn as nn

try:
    import torch
    import torch.nn as nn
    import torch.nn.utils.prune as prune
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("⚠️ torch not available")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class ModelCompressor:
    """
    Compress models for efficient deployment
    """
    
    def __init__(self, db_path: str = "data/model_compression.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compressed_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    original_size_mb REAL NOT NULL,
                    compressed_size_mb REAL NOT NULL,
                    compression_ratio REAL NOT NULL,
                    method TEXT NOT NULL,
                    accuracy_loss REAL,
                    speedup_factor REAL,
                    model_path TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compression_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id INTEGER NOT NULL,
                    metric_name TEXT NOT NULL,
                    original_value REAL NOT NULL,
                    compressed_value REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (model_id) REFERENCES compressed_models(id)
                )
            """)
    
    def quantize_dynamic(self, model, dtype=None):
        """
        Apply dynamic quantization (CPU inference)
        Reduces precision of weights/activations at inference time
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available")
        if dtype is None:
            dtype = torch.qint8
        if not TORCH_AVAILABLE:
            return model, {}
        
        # Get original size
        original_size = self._get_model_size(model)
        
        # Apply dynamic quantization to linear and LSTM layers
        quantized_model = torch.quantization.quantize_dynamic(
            model,
            {nn.Linear, nn.LSTM},
            dtype=dtype
        )
        
        # Get compressed size
        compressed_size = self._get_model_size(quantized_model)
        
        metrics = {
            'method': 'dynamic_quantization',
            'original_size_mb': original_size,
            'compressed_size_mb': compressed_size,
            'compression_ratio': original_size / compressed_size if compressed_size > 0 else 1.0,
            'dtype': str(dtype)
        }
        
        return quantized_model, metrics
    
    def prune_model(self, model, amount: float = 0.3):
        """
        Apply structured pruning to remove less important weights
        
        Args:
            model: PyTorch model
            amount: Fraction of parameters to prune (0.3 = 30%)
        """
        if not TORCH_AVAILABLE:
            return model, {}
        
        original_size = self._get_model_size(model)
        original_params = sum(p.numel() for p in model.parameters())
        
        # Apply L1 unstructured pruning to all Linear layers
        for name, module in model.named_modules():
            if isinstance(module, nn.Linear):
                prune.l1_unstructured(module, name='weight', amount=amount)
                # Make pruning permanent
                prune.remove(module, 'weight')
        
        # Count remaining parameters
        pruned_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        compressed_size = self._get_model_size(model)
        
        metrics = {
            'method': 'pruning',
            'original_size_mb': original_size,
            'compressed_size_mb': compressed_size,
            'compression_ratio': original_size / compressed_size if compressed_size > 0 else 1.0,
            'original_params': original_params,
            'pruned_params': pruned_params,
            'params_removed': original_params - pruned_params,
            'prune_amount': amount
        }
        
        return model, metrics
    
    def distill_model(self, teacher, student,
                     train_loader, epochs: int = 5, 
                     temperature: float = 3.0,
                     alpha: float = 0.5):
        """
        Knowledge distillation: train smaller student model from teacher
        
        Args:
            teacher: Large pre-trained teacher model
            student: Smaller student model to train
            train_loader: DataLoader for training
            temperature: Softening temperature for distillation
            alpha: Weight between hard and soft targets (0-1)
        """
        if not TORCH_AVAILABLE:
            return student, {}
        
        teacher.eval()
        student.train()
        
        original_size = self._get_model_size(teacher)
        student_size = self._get_model_size(student)
        
        optimizer = torch.optim.Adam(student.parameters(), lr=0.001)
        criterion = nn.KLDivLoss(reduction='batchmean')
        hard_criterion = nn.CrossEntropyLoss()
        
        total_loss = 0
        
        for epoch in range(epochs):
            epoch_loss = 0
            
            for batch_idx, (data, target) in enumerate(train_loader):
                optimizer.zero_grad()
                
                # Teacher predictions (no gradient)
                with torch.no_grad():
                    teacher_output = teacher(data)
                
                # Student predictions
                student_output = student(data)
                
                # Soft targets (distillation loss)
                soft_targets = nn.functional.softmax(teacher_output / temperature, dim=1)
                soft_prob = nn.functional.log_softmax(student_output / temperature, dim=1)
                distillation_loss = criterion(soft_prob, soft_targets) * (temperature ** 2)
                
                # Hard targets (classification loss)
                hard_loss = hard_criterion(student_output, target)
                
                # Combined loss
                loss = alpha * hard_loss + (1 - alpha) * distillation_loss
                
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
            
            total_loss += epoch_loss
        
        metrics = {
            'method': 'distillation',
            'teacher_size_mb': original_size,
            'student_size_mb': student_size,
            'compression_ratio': original_size / student_size if student_size > 0 else 1.0,
            'epochs': epochs,
            'temperature': temperature,
            'alpha': alpha,
            'final_loss': total_loss / epochs
        }
        
        return student, metrics
    
    def apply_mixed_precision(self, model):
        """
        Convert model to mixed precision (FP16/FP32) for faster inference
        """
        if not TORCH_AVAILABLE:
            return model, {}
        
        original_size = self._get_model_size(model)
        
        # Convert to half precision
        model_fp16 = model.half()
        
        compressed_size = self._get_model_size(model_fp16)
        
        metrics = {
            'method': 'mixed_precision',
            'original_size_mb': original_size,
            'compressed_size_mb': compressed_size,
            'compression_ratio': original_size / compressed_size if compressed_size > 0 else 1.0,
            'precision': 'FP16'
        }
        
        return model_fp16, metrics
    
    def compress_pipeline(self, model, 
                         methods: List[str] = ['quantize', 'prune'],
                         save_path: Optional[str] = None) -> Dict:
        """
        Apply multiple compression methods in sequence
        
        Args:
            model: Model to compress
            methods: List of methods ['quantize', 'prune', 'mixed_precision']
            save_path: Path to save compressed model
        
        Returns:
            Comprehensive metrics
        """
        if not TORCH_AVAILABLE:
            return {}
        
        original_size = self._get_model_size(model)
        compressed_model = model
        all_metrics = []
        
        for method in methods:
            if method == 'quantize':
                compressed_model, metrics = self.quantize_dynamic(compressed_model)
            elif method == 'prune':
                compressed_model, metrics = self.prune_model(compressed_model, amount=0.3)
            elif method == 'mixed_precision':
                compressed_model, metrics = self.apply_mixed_precision(compressed_model)
            else:
                continue
            
            all_metrics.append(metrics)
        
        final_size = self._get_model_size(compressed_model)
        
        # Save compressed model
        if save_path and TORCH_AVAILABLE:
            torch.save(compressed_model.state_dict(), save_path)
        
        # Overall metrics
        pipeline_metrics = {
            'methods': methods,
            'original_size_mb': original_size,
            'final_size_mb': final_size,
            'overall_compression_ratio': original_size / final_size if final_size > 0 else 1.0,
            'size_reduction': original_size - final_size,
            'individual_metrics': all_metrics,
            'model_path': save_path
        }
        
        # Save to database
        self._save_compression_record(
            model_name='pipeline_model',
            metrics=pipeline_metrics
        )
        
        return pipeline_metrics
    
    def _get_model_size(self, model) -> float:
        """Get model size in MB"""
        if not TORCH_AVAILABLE:
            return 0.0
        
        # Save to temp file
        temp_path = 'temp_model.pt'
        torch.save(model.state_dict(), temp_path)
        
        size_mb = os.path.getsize(temp_path) / (1024 * 1024)
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return size_mb
    
    def _save_compression_record(self, model_name: str, metrics: Dict):
        """Save compression record to database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO compressed_models
                (model_name, original_size_mb, compressed_size_mb, compression_ratio,
                 method, model_path, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                model_name,
                metrics.get('original_size_mb', 0),
                metrics.get('final_size_mb', 0),
                metrics.get('overall_compression_ratio', 1.0),
                ','.join(metrics.get('methods', [])),
                metrics.get('model_path'),
                datetime.now().isoformat()
            ))
    
    def get_compression_history(self) -> List[Dict]:
        """Get history of model compressions"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT model_name, original_size_mb, compressed_size_mb,
                       compression_ratio, method, created_at
                FROM compressed_models
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'model_name': row[0],
                    'original_size_mb': row[1],
                    'compressed_size_mb': row[2],
                    'compression_ratio': row[3],
                    'methods': row[4].split(','),
                    'created_at': row[5]
                })
            
            return history
    
    def get_stats(self) -> Dict:
        """Get compression statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    AVG(compression_ratio) as avg_ratio,
                    SUM(original_size_mb - compressed_size_mb) as total_saved_mb
                FROM compressed_models
            """)
            
            row = cursor.fetchone()
            if row:
                return {
                    'total_compressions': row[0] or 0,
                    'avg_compression_ratio': row[1] or 1.0,
                    'total_size_saved_mb': row[2] or 0
                }
        
        return {}


def example_usage():
    """Demonstrate model compression"""
    compressor = ModelCompressor()
    
    print("Model Compression Demo\n" + "="*50)
    
    if not TORCH_AVAILABLE:
        print("⚠️ PyTorch not available - showing conceptual demo only")
        return
    
    # Create a simple model
    print("\n1. Creating sample model...")
    model = nn.Sequential(
        nn.Linear(100, 256),
        nn.ReLU(),
        nn.Linear(256, 128),
        nn.ReLU(),
        nn.Linear(128, 10)
    )
    
    original_size = compressor._get_model_size(model)
    print(f"  Original size: {original_size:.2f} MB")
    
    # Quantization
    print("\n2. Applying dynamic quantization...")
    quantized, metrics = compressor.quantize_dynamic(model)
    print(f"  Compressed size: {metrics['compressed_size_mb']:.2f} MB")
    print(f"  Compression ratio: {metrics['compression_ratio']:.2f}x")
    
    # Pruning
    print("\n3. Applying pruning (30% sparsity)...")
    pruned, metrics = compressor.prune_model(model, amount=0.3)
    print(f"  Parameters removed: {metrics.get('params_removed', 0):,}")
    print(f"  Compression ratio: {metrics['compression_ratio']:.2f}x")
    
    # Pipeline
    print("\n4. Full compression pipeline...")
    pipeline_metrics = compressor.compress_pipeline(
        model,
        methods=['prune', 'quantize'],
        save_path='data/compressed_model.pt'
    )
    print(f"  Original: {pipeline_metrics['original_size_mb']:.2f} MB")
    print(f"  Final: {pipeline_metrics['final_size_mb']:.2f} MB")
    print(f"  Overall ratio: {pipeline_metrics['overall_compression_ratio']:.2f}x")
    print(f"  Size saved: {pipeline_metrics['size_reduction']:.2f} MB")
    
    # Stats
    stats = compressor.get_stats()
    print(f"\n5. Statistics:")
    print(f"  Total compressions: {stats['total_compressions']}")
    print(f"  Avg compression ratio: {stats['avg_compression_ratio']:.2f}x")
    print(f"  Total space saved: {stats['total_size_saved_mb']:.2f} MB")


if __name__ == "__main__":
    example_usage()
