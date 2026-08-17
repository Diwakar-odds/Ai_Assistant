"""
Active Learning System
Requests labels for uncertain predictions to reduce labeling effort

Features:
- Uncertainty sampling (least confident)
- Query-by-committee
- Expected model change
- Human-in-the-loop labeling interface
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import math

try:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier, VotingClassifier
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.svm import SVC
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ scikit-learn not available")


class ActiveLearner:
    """
    Active learning for sample-efficient model training
    """
    
    def __init__(self, db_path: str = "data/active_learning.db",
                 uncertainty_threshold: float = 0.3):
        self.db_path = db_path
        self.uncertainty_threshold = uncertainty_threshold
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        if SKLEARN_AVAILABLE:
            # Committee of diverse models
            self.committee = [
                RandomForestClassifier(n_estimators=50, random_state=i)
                for i in range(3)
            ]
            self.trained = False
        
        # Labeling queue
        self.unlabeled_pool = []
        self.labeling_queue = []
        
        self._init_database()
        self._load_queue()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_data TEXT NOT NULL,
                    features TEXT NOT NULL,
                    label INTEGER,
                    predicted_label INTEGER,
                    uncertainty REAL,
                    sampling_strategy TEXT,
                    labeled_by TEXT,
                    created_at TEXT NOT NULL,
                    labeled_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS labeling_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sample_id INTEGER NOT NULL,
                    priority REAL NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (sample_id) REFERENCES samples(id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    num_labeled INTEGER NOT NULL,
                    accuracy REAL NOT NULL,
                    f1_score REAL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_unlabeled 
                ON samples(label) WHERE label IS NULL
            """)
    
    def _load_queue(self):
        """Load pending labeling queue"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT lq.id, lq.sample_id, lq.priority, lq.reason, s.sample_data, s.features
                FROM labeling_queue lq
                JOIN samples s ON lq.sample_id = s.id
                WHERE lq.status = 'pending'
                ORDER BY lq.priority DESC
                LIMIT 100
            """)
            
            self.labeling_queue = []
            for row in cursor.fetchall():
                queue_id, sample_id, priority, reason, data, features = row
                self.labeling_queue.append({
                    'queue_id': queue_id,
                    'sample_id': sample_id,
                    'priority': priority,
                    'reason': reason,
                    'data': json.loads(data),
                    'features': json.loads(features)
                })
    
    def add_unlabeled_sample(self, sample_data: Dict, features: List[float]) -> int:
        """Add unlabeled sample to pool"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO samples (sample_data, features, created_at)
                VALUES (?, ?, ?)
            """, (
                json.dumps(sample_data),
                json.dumps(features),
                datetime.now().isoformat()
            ))
            return cursor.lastrowid
    
    def uncertainty_sampling(self, features: np.ndarray, sample_id: int = None) -> float:
        """
        Calculate prediction uncertainty (least confident)
        Lower = more uncertain
        """
        if not SKLEARN_AVAILABLE or not self.trained:
            return 0.5
        
        # Get predictions from all committee members
        predictions = []
        for model in self.committee:
            try:
                proba = model.predict_proba(features.reshape(1, -1))[0]
                predictions.append(proba)
            except:
                return 0.5
        
        # Average probabilities
        avg_proba = np.mean(predictions, axis=0)
        
        # Uncertainty = 1 - max_probability (least confident)
        uncertainty = 1.0 - np.max(avg_proba)
        
        return float(uncertainty)
    
    def query_by_committee(self, features: np.ndarray) -> float:
        """
        Calculate disagreement among committee members
        Higher = more disagreement = more informative
        """
        if not SKLEARN_AVAILABLE or not self.trained:
            return 0.5
        
        # Get predictions from each committee member
        votes = []
        for model in self.committee:
            try:
                pred = model.predict(features.reshape(1, -1))[0]
                votes.append(pred)
            except:
                return 0.5
        
        # Calculate vote entropy (disagreement)
        unique, counts = np.unique(votes, return_counts=True)
        probs = counts / len(votes)
        
        # Entropy
        entropy = -np.sum(probs * np.log2(probs + 1e-10))
        
        # Normalize by max entropy
        max_entropy = np.log2(len(unique))
        disagreement = entropy / max_entropy if max_entropy > 0 else 0.0
        
        return float(disagreement)
    
    def expected_model_change(self, features: np.ndarray, sample_id: int = None) -> float:
        """
        Estimate how much model would change if we label this sample
        Uses gradient magnitude as proxy
        """
        if not SKLEARN_AVAILABLE or not self.trained:
            return 0.5
        
        # Simplified: use uncertainty as proxy for expected change
        # In practice, would compute gradient magnitude
        uncertainty = self.uncertainty_sampling(features)
        
        # Samples with uncertain predictions likely to change model most
        return uncertainty
    
    def select_samples_to_label(self, strategy: str = 'uncertainty',
                                num_samples: int = 10) -> List[Dict]:
        """
        Select most informative samples for labeling
        
        Args:
            strategy: 'uncertainty', 'committee', 'expected_change', or 'hybrid'
            num_samples: Number of samples to select
        
        Returns:
            List of samples to label with priorities
        """
        # Get unlabeled samples
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, sample_data, features
                FROM samples
                WHERE label IS NULL
                LIMIT 1000
            """)
            
            candidates = []
            for row in cursor.fetchall():
                sample_id, data, features_json = row
                features = np.array(json.loads(features_json))
                
                # Calculate informativeness scores
                if strategy == 'uncertainty':
                    score = self.uncertainty_sampling(features, sample_id)
                elif strategy == 'committee':
                    score = self.query_by_committee(features)
                elif strategy == 'expected_change':
                    score = self.expected_model_change(features, sample_id)
                elif strategy == 'hybrid':
                    # Combine multiple strategies
                    unc = self.uncertainty_sampling(features, sample_id)
                    comm = self.query_by_committee(features)
                    exp = self.expected_model_change(features, sample_id)
                    score = (unc + comm + exp) / 3.0
                else:
                    score = 0.5
                
                candidates.append({
                    'sample_id': sample_id,
                    'data': json.loads(data),
                    'features': features.tolist(),
                    'score': score,
                    'strategy': strategy
                })
            
            # Sort by informativeness (higher = more informative)
            candidates.sort(key=lambda x: x['score'], reverse=True)
            
            # Add to labeling queue
            selected = candidates[:num_samples]
            
            for sample in selected:
                self._add_to_queue(
                    sample['sample_id'],
                    sample['score'],
                    f"Selected by {strategy} strategy (score: {sample['score']:.3f})"
                )
            
            return selected
    
    def _add_to_queue(self, sample_id: int, priority: float, reason: str):
        """Add sample to labeling queue"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO labeling_queue (sample_id, priority, reason, created_at)
                VALUES (?, ?, ?, ?)
            """, (sample_id, priority, reason, datetime.now().isoformat()))
        
        # Reload queue
        self._load_queue()
    
    def get_next_to_label(self, batch_size: int = 1) -> List[Dict]:
        """Get next samples to label from queue"""
        return self.labeling_queue[:batch_size]
    
    def provide_label(self, sample_id: int, label: int, labeled_by: str = "human"):
        """Provide label for a sample"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE samples
                SET label = ?, labeled_by = ?, labeled_at = ?
                WHERE id = ?
            """, (label, labeled_by, datetime.now().isoformat(), sample_id))
            
            # Mark as completed in queue
            conn.execute("""
                UPDATE labeling_queue
                SET status = 'completed'
                WHERE sample_id = ? AND status = 'pending'
            """, (sample_id,))
        
        # Reload queue
        self._load_queue()
        
        # Retrain periodically
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM samples WHERE label IS NOT NULL")
            labeled_count = cursor.fetchone()[0]
            
            if labeled_count % 10 == 0:  # Retrain every 10 labels
                self.train()
    
    def train(self):
        """Train committee models on labeled data"""
        if not SKLEARN_AVAILABLE:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT features, label
                FROM samples
                WHERE label IS NOT NULL
            """)
            
            X = []
            y = []
            
            for row in cursor.fetchall():
                features_json, label = row
                X.append(json.loads(features_json))
                y.append(label)
            
            if len(X) < 5:
                return
            
            X = np.array(X)
            y = np.array(y)
            
            # Train each committee member
            for model in self.committee:
                try:
                    model.fit(X, y)
                except:
                    pass
            
            self.trained = True
    
    def get_labeling_efficiency(self) -> Dict:
        """
        Calculate labeling efficiency metrics
        Shows how much accuracy we get per label
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT num_labeled, accuracy
                FROM model_performance
                ORDER BY num_labeled
            """)
            
            history = []
            for row in cursor.fetchall():
                history.append({
                    'num_labeled': row[0],
                    'accuracy': row[1]
                })
            
            if len(history) < 2:
                return {
                    'samples_per_1pct_accuracy': 0,
                    'current_accuracy': 0,
                    'total_labeled': 0
                }
            
            # Calculate samples needed per 1% accuracy improvement
            first = history[0]
            last = history[-1]
            
            accuracy_gain = last['accuracy'] - first['accuracy']
            samples_used = last['num_labeled'] - first['num_labeled']
            
            samples_per_pct = samples_used / (accuracy_gain * 100) if accuracy_gain > 0 else 0
            
            return {
                'samples_per_1pct_accuracy': samples_per_pct,
                'current_accuracy': last['accuracy'],
                'total_labeled': last['num_labeled'],
                'accuracy_improvement': accuracy_gain
            }
    
    def get_stats(self) -> Dict:
        """Get active learning statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN label IS NOT NULL THEN 1 ELSE 0 END) as labeled,
                    (SELECT COUNT(*) FROM labeling_queue WHERE status='pending') as pending
                FROM samples
            """)
            
            row = cursor.fetchone()
            if row:
                total, labeled, pending = row
                
                return {
                    'total_samples': total or 0,
                    'labeled_samples': labeled or 0,
                    'unlabeled_samples': (total - labeled) if total and labeled else 0,
                    'labeling_queue_size': pending or 0,
                    'labeling_percentage': (labeled / total * 100) if total else 0,
                    'model_trained': self.trained if SKLEARN_AVAILABLE else False
                }
        
        return {}


def example_usage():
    """Demonstrate active learning"""
    learner = ActiveLearner()
    
    print("Active Learning Demo\n" + "="*50)
    
    # Add some unlabeled samples
    print("\n1. Adding unlabeled samples...")
    for i in range(20):
        features = np.random.randn(10).tolist()
        sample_data = {'text': f'sample_{i}', 'id': i}
        learner.add_unlabeled_sample(sample_data, features)
    
    # Train initial model with a few labels
    print("2. Adding initial labels...")
    for i in range(1, 6):
        learner.provide_label(i, label=i % 2)  # Binary labels
    
    learner.train()
    
    # Select most informative samples
    print("\n3. Selecting most informative samples...")
    selected = learner.select_samples_to_label(strategy='hybrid', num_samples=5)
    
    print(f"Selected {len(selected)} samples for labeling:")
    for s in selected[:3]:
        print(f"  Sample {s['sample_id']}: score={s['score']:.3f}")
    
    # Get next to label
    print("\n4. Getting next samples from queue...")
    next_batch = learner.get_next_to_label(batch_size=3)
    print(f"Next {len(next_batch)} samples to label:")
    for sample in next_batch:
        print(f"  Sample {sample['sample_id']}: {sample['reason']}")
    
    # Get stats
    stats = learner.get_stats()
    print(f"\n5. Statistics:")
    print(f"  Total samples: {stats['total_samples']}")
    print(f"  Labeled: {stats['labeled_samples']} ({stats['labeling_percentage']:.1f}%)")
    print(f"  Queue size: {stats['labeling_queue_size']}")
    print(f"  Model trained: {stats['model_trained']}")
    
    efficiency = learner.get_labeling_efficiency()
    if efficiency['total_labeled'] > 0:
        print(f"\n6. Labeling Efficiency:")
        print(f"  Samples per 1% accuracy: {efficiency['samples_per_1pct_accuracy']:.1f}")


if __name__ == "__main__":
    example_usage()
