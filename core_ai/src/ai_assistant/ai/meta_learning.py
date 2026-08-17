"""
Model-Agnostic Meta-Learning (MAML)
Quick adaptation to new tasks with few examples
"""

import numpy as np
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available, using simplified meta-learning")


@dataclass
class Task:
    """Single task for meta-learning"""
    task_id: str
    support_set: List[Tuple[np.ndarray, np.ndarray]]  # (input, output) pairs
    query_set: List[Tuple[np.ndarray, np.ndarray]]
    task_type: str  # 'classification', 'regression', etc.
    metadata: Dict[str, Any]


@dataclass
class MetaLearningResult:
    """Result of meta-learning episode"""
    task_id: str
    pre_adaptation_loss: float
    post_adaptation_loss: float
    improvement: float
    num_gradient_steps: int


if TORCH_AVAILABLE:
    class MetaLearnerNetwork(nn.Module):
        """Neural network for meta-learning"""
        
        def __init__(self, input_dim: int, output_dim: int, hidden_dim: int = 64):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, output_dim)
            )
        
        def forward(self, x):
            return self.net(x)
        
        def clone(self):
            """Create a deep copy of the network"""
            cloned = MetaLearnerNetwork(
                input_dim=self.net[0].in_features,
                output_dim=self.net[-1].out_features,
                hidden_dim=self.net[2].in_features
            )
            cloned.load_state_dict(self.state_dict())
            return cloned


class MAMLLearner:
    """
    Model-Agnostic Meta-Learning implementation
    Learn to learn: meta-optimize for fast adaptation
    """
    
    def __init__(self,
                 input_dim: int,
                 output_dim: int,
                 hidden_dim: int = 64,
                 meta_lr: float = 0.001,
                 inner_lr: float = 0.01,
                 num_inner_steps: int = 5,
                 db_path: str = "data/meta_learning.db"):
        
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.meta_lr = meta_lr
        self.inner_lr = inner_lr
        self.num_inner_steps = num_inner_steps
        self.db_path = db_path
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        if TORCH_AVAILABLE:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.meta_model = MetaLearnerNetwork(input_dim, output_dim, hidden_dim).to(self.device)
            self.meta_optimizer = optim.Adam(self.meta_model.parameters(), lr=meta_lr)
        else:
            # Fallback: simple prototype-based learning
            self.prototypes = {}
            self.task_history = defaultdict(list)
        
        self.task_count = 0
        
        logger.info(f"MAML initialized: {input_dim}D input, {output_dim}D output")
    
    def _init_database(self):
        """Initialize database for meta-learning tasks"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE,
                    task_type TEXT,
                    timestamp TEXT,
                    support_size INTEGER,
                    query_size INTEGER,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta_episodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    task_id TEXT,
                    pre_adapt_loss REAL,
                    post_adapt_loss REAL,
                    improvement REAL,
                    num_steps INTEGER,
                    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS adaptations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    timestamp TEXT,
                    adaptation_steps INTEGER,
                    final_loss REAL,
                    success INTEGER
                )
            """)
    
    def register_task(self, task: Task):
        """Register a new task"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tasks 
                (task_id, task_type, timestamp, support_size, query_size, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                task.task_id,
                task.task_type,
                datetime.now().isoformat(),
                len(task.support_set),
                len(task.query_set),
                json.dumps(task.metadata)
            ))
        
        self.task_count += 1
    
    def inner_loop_adapt(self, task: Task, model=None) -> Tuple[Any, List[float]]:
        """
        Perform inner loop adaptation on a task
        Returns: (adapted_model, losses)
        """
        if not TORCH_AVAILABLE:
            # Fallback: compute prototype
            task_prototype = np.mean([x for x, _ in task.support_set], axis=0)
            self.prototypes[task.task_id] = task_prototype
            return None, [0.0]
        
        # Use provided model or meta-model
        if model is None:
            adapted_model = self.meta_model.clone()
        else:
            adapted_model = model.clone()
        
        # Create optimizer for inner loop
        inner_optimizer = optim.SGD(adapted_model.parameters(), lr=self.inner_lr)
        
        losses = []
        
        # Adapt on support set
        for step in range(self.num_inner_steps):
            total_loss = 0
            
            for x, y in task.support_set:
                x_tensor = torch.FloatTensor(x).unsqueeze(0).to(self.device)
                y_tensor = torch.FloatTensor(y).unsqueeze(0).to(self.device)
                
                # Forward pass
                pred = adapted_model(x_tensor)
                
                # Compute loss (MSE for regression, CE for classification)
                if task.task_type == 'classification':
                    loss = F.cross_entropy(pred, y_tensor.long())
                else:
                    loss = F.mse_loss(pred, y_tensor)
                
                # Backward pass
                inner_optimizer.zero_grad()
                loss.backward()
                inner_optimizer.step()
                
                total_loss += loss.item()
            
            avg_loss = total_loss / len(task.support_set)
            losses.append(avg_loss)
        
        return adapted_model, losses
    
    def evaluate_on_query(self, task: Task, model=None) -> float:
        """Evaluate model on query set"""
        if not TORCH_AVAILABLE:
            # Fallback: distance to prototype
            if task.task_id not in self.prototypes:
                return 1.0
            
            prototype = self.prototypes[task.task_id]
            distances = [np.linalg.norm(x - prototype) for x, _ in task.query_set]
            return np.mean(distances)
        
        if model is None:
            model = self.meta_model
        
        model.eval()
        total_loss = 0
        
        with torch.no_grad():
            for x, y in task.query_set:
                x_tensor = torch.FloatTensor(x).unsqueeze(0).to(self.device)
                y_tensor = torch.FloatTensor(y).unsqueeze(0).to(self.device)
                
                pred = model(x_tensor)
                
                if task.task_type == 'classification':
                    loss = F.cross_entropy(pred, y_tensor.long())
                else:
                    loss = F.mse_loss(pred, y_tensor)
                
                total_loss += loss.item()
        
        return total_loss / len(task.query_set)
    
    def meta_train_step(self, tasks: List[Task]) -> Dict[str, float]:
        """
        Single meta-training step on a batch of tasks
        """
        if not TORCH_AVAILABLE:
            # Fallback: just compute prototypes
            for task in tasks:
                self.inner_loop_adapt(task)
            return {'meta_loss': 0.0}
        
        self.meta_model.train()
        meta_loss = 0
        
        for task in tasks:
            # Evaluate before adaptation
            pre_adapt_loss = self.evaluate_on_query(task, self.meta_model)
            
            # Inner loop adaptation
            adapted_model, _ = self.inner_loop_adapt(task, self.meta_model)
            
            # Evaluate after adaptation on query set
            post_adapt_loss = self.evaluate_on_query(task, adapted_model)
            
            # Accumulate meta-loss (we want to minimize post-adaptation loss)
            meta_loss += post_adapt_loss
            
            # Store result
            result = MetaLearningResult(
                task_id=task.task_id,
                pre_adaptation_loss=pre_adapt_loss,
                post_adaptation_loss=post_adapt_loss,
                improvement=pre_adapt_loss - post_adapt_loss,
                num_gradient_steps=self.num_inner_steps
            )
            self._save_episode(result)
        
        # Meta-optimization step
        meta_loss /= len(tasks)
        
        self.meta_optimizer.zero_grad()
        meta_loss_tensor = torch.tensor(meta_loss, requires_grad=True)
        meta_loss_tensor.backward()
        self.meta_optimizer.step()
        
        return {'meta_loss': meta_loss}
    
    def adapt_to_new_task(self, task: Task, num_steps: Optional[int] = None) -> Dict[str, Any]:
        """
        Quickly adapt to a new task using meta-learned initialization
        """
        self.register_task(task)
        
        if num_steps is None:
            num_steps = self.num_inner_steps
        
        # Perform adaptation
        adapted_model, losses = self.inner_loop_adapt(task)
        
        # Evaluate
        final_loss = self.evaluate_on_query(task, adapted_model)
        
        # Store adaptation result
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO adaptations (task_id, timestamp, adaptation_steps, final_loss, success)
                VALUES (?, ?, ?, ?, ?)
            """, (
                task.task_id,
                datetime.now().isoformat(),
                num_steps,
                final_loss,
                1 if final_loss < 0.5 else 0
            ))
        
        return {
            'task_id': task.task_id,
            'adapted': True,
            'final_loss': final_loss,
            'adaptation_trajectory': losses
        }
    
    def _save_episode(self, result: MetaLearningResult):
        """Save meta-learning episode"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO meta_episodes 
                (timestamp, task_id, pre_adapt_loss, post_adapt_loss, improvement, num_steps)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                result.task_id,
                result.pre_adaptation_loss,
                result.post_adaptation_loss,
                result.improvement,
                result.num_gradient_steps
            ))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get meta-learning statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM tasks")
            total_tasks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM meta_episodes")
            total_episodes = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(improvement) FROM meta_episodes")
            avg_improvement = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM adaptations WHERE success = 1")
            successful_adaptations = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM adaptations")
            total_adaptations = cursor.fetchone()[0]
        
        return {
            'total_tasks': total_tasks,
            'total_episodes': total_episodes,
            'avg_improvement': float(avg_improvement) if avg_improvement else 0,
            'successful_adaptations': successful_adaptations,
            'total_adaptations': total_adaptations,
            'success_rate': successful_adaptations / max(total_adaptations, 1),
            'torch_available': TORCH_AVAILABLE
        }


class FewShotClassifier:
    """
    Few-shot classification using MAML
    Learn to classify with few examples per class
    """
    
    def __init__(self, feature_dim: int, num_classes: int):
        self.maml = MAMLLearner(
            input_dim=feature_dim,
            output_dim=num_classes,
            hidden_dim=64
        )
        self.num_classes = num_classes
    
    def train_on_tasks(self, task_distribution: List[Task], num_iterations: int = 100):
        """Train on a distribution of tasks"""
        for iteration in range(num_iterations):
            # Sample batch of tasks
            batch_size = min(4, len(task_distribution))
            task_batch = np.random.choice(task_distribution, batch_size, replace=False)
            
            # Meta-train
            losses = self.maml.meta_train_step(list(task_batch))
            
            if iteration % 10 == 0:
                logger.info(f"Iteration {iteration}: Meta-loss={losses['meta_loss']:.4f}")
    
    def classify_few_shot(self, 
                         support_examples: List[Tuple[np.ndarray, int]],
                         query_example: np.ndarray) -> int:
        """
        Classify a query example given few support examples
        """
        # Create task
        support_set = [(x, np.eye(self.num_classes)[y]) for x, y in support_examples]
        query_set = [(query_example, np.zeros(self.num_classes))]  # Dummy label
        
        task = Task(
            task_id=f"classify_{datetime.now().timestamp()}",
            support_set=support_set,
            query_set=query_set,
            task_type='classification',
            metadata={}
        )
        
        # Adapt to task
        result = self.maml.adapt_to_new_task(task)
        
        # Make prediction (simplified - would need actual forward pass)
        # For now, return most similar class from support set
        distances = [np.linalg.norm(query_example - x) for x, _ in support_examples]
        return support_examples[np.argmin(distances)][1]


# Example usage
def example_meta_learning():
    """Example of using meta-learning for few-shot tasks"""
    
    # Create meta-learner
    maml = MAMLLearner(input_dim=10, output_dim=5)
    
    # Generate synthetic tasks
    tasks = []
    for i in range(20):
        # Each task: learn a different linear function
        support_set = [(np.random.randn(10), np.random.randn(5)) for _ in range(5)]
        query_set = [(np.random.randn(10), np.random.randn(5)) for _ in range(3)]
        
        task = Task(
            task_id=f"task_{i}",
            support_set=support_set,
            query_set=query_set,
            task_type='regression',
            metadata={'description': f'Synthetic task {i}'}
        )
        tasks.append(task)
    
    # Meta-train
    for epoch in range(10):
        task_batch = tasks[epoch * 2:(epoch + 1) * 2]
        losses = maml.meta_train_step(task_batch)
        logger.info(f"Epoch {epoch}: {losses}")
    
    # Test adaptation to new task
    new_task = tasks[0]
    result = maml.adapt_to_new_task(new_task)
    logger.info(f"Adaptation result: {result}")
    
    return maml
