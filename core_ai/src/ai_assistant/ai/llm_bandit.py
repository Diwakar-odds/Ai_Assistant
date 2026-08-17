"""
Multi-Armed Bandit for LLM Selection
Automatically selects best LLM for each task type

Features:
- Thompson Sampling for exploration-exploitation
- Contextual bandits with task features
- Cost-aware selection (balance quality vs cost)
- Dynamic model switching based on performance
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict
import random
import math

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("⚠️ numpy not available")


class LLMBandit:
    """
    Multi-armed bandit for optimal LLM selection
    """
    
    def __init__(self, db_path: str = "data/llm_bandit.db",
                 exploration_rate: float = 0.1):
        self.db_path = db_path
        self.exploration_rate = exploration_rate
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Available LLMs with costs (per 1k tokens)
        self.llms = {
            'gpt-4': {'cost': 0.03, 'latency': 2.0, 'quality_baseline': 0.95},
            'gpt-3.5': {'cost': 0.002, 'latency': 0.5, 'quality_baseline': 0.85},
            'claude-3': {'cost': 0.015, 'latency': 1.5, 'quality_baseline': 0.93},
            'local-llama': {'cost': 0.0, 'latency': 3.0, 'quality_baseline': 0.75},
        }
        
        # Task-specific performance
        self.task_performance = defaultdict(lambda: defaultdict(
            lambda: {'alpha': 1, 'beta': 1}  # Beta distribution params
        ))
        
        self._init_database()
        self._load_performance()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS selections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    task_features TEXT NOT NULL,
                    selected_llm TEXT NOT NULL,
                    quality_score REAL,
                    latency REAL,
                    cost REAL,
                    user_feedback INTEGER,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_performance (
                    task_type TEXT NOT NULL,
                    llm_name TEXT NOT NULL,
                    successes INTEGER DEFAULT 0,
                    failures INTEGER DEFAULT 0,
                    avg_quality REAL DEFAULT 0.0,
                    avg_latency REAL DEFAULT 0.0,
                    total_cost REAL DEFAULT 0.0,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (task_type, llm_name)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_contexts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    context_features TEXT NOT NULL,
                    best_llm TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
    
    def _load_performance(self):
        """Load historical performance data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT task_type, llm_name, successes, failures
                FROM llm_performance
            """)
            
            for row in cursor.fetchall():
                task_type, llm_name, successes, failures = row
                self.task_performance[task_type][llm_name] = {
                    'alpha': successes + 1,
                    'beta': failures + 1
                }
    
    def extract_task_features(self, task: Dict) -> Dict:
        """Extract features from task"""
        features = {}
        
        # Task type
        features['task_type'] = task.get('type', 'general')
        
        # Complexity indicators
        text = task.get('text', '')
        features['length'] = min(len(text) / 1000, 1.0)  # Normalize
        features['complexity'] = len(text.split()) / 100.0
        
        # Requirements
        features['needs_reasoning'] = 1 if 'reasoning' in task.get('requirements', []) else 0
        features['needs_creativity'] = 1 if 'creative' in task.get('requirements', []) else 0
        features['needs_speed'] = 1 if 'fast' in task.get('requirements', []) else 0
        features['cost_sensitive'] = 1 if task.get('budget') == 'low' else 0
        
        return features
    
    def thompson_sampling(self, task_type: str, llm_name: str) -> float:
        """
        Thompson Sampling: sample from posterior distribution
        Returns expected reward
        """
        params = self.task_performance[task_type][llm_name]
        
        if NUMPY_AVAILABLE:
            # Sample from Beta distribution
            return np.random.beta(params['alpha'], params['beta'])
        else:
            # Fallback: use mean of Beta distribution
            alpha, beta = params['alpha'], params['beta']
            return alpha / (alpha + beta)
    
    def select_llm(self, task: Dict) -> Dict:
        """
        Select best LLM for task using contextual bandit
        
        Returns:
            dict with 'llm', 'reason', 'expected_quality', 'expected_cost'
        """
        features = self.extract_task_features(task)
        task_type = features['task_type']
        
        # Exploration vs exploitation
        if random.random() < self.exploration_rate:
            # Explore: random selection
            llm = random.choice(list(self.llms.keys()))
            reason = "exploration"
        else:
            # Exploit: Thompson Sampling
            scores = {}
            
            for llm_name, llm_info in self.llms.items():
                # Sample expected quality from posterior
                quality_sample = self.thompson_sampling(task_type, llm_name)
                
                # Adjust for task requirements
                if features.get('needs_speed') and llm_info['latency'] > 2.0:
                    quality_sample *= 0.8  # Penalty for slow models
                
                if features.get('cost_sensitive') and llm_info['cost'] > 0.01:
                    quality_sample *= 0.7  # Penalty for expensive models
                
                if features.get('needs_reasoning'):
                    # Prefer stronger models
                    if llm_name in ['gpt-4', 'claude-3']:
                        quality_sample *= 1.2
                
                scores[llm_name] = quality_sample
            
            # Select best
            llm = max(scores.items(), key=lambda x: x[1])[0]
            reason = "exploitation"
        
        # Compute expected metrics
        llm_info = self.llms[llm]
        params = self.task_performance[task_type][llm]
        
        expected_quality = params['alpha'] / (params['alpha'] + params['beta'])
        expected_cost = llm_info['cost'] * features.get('length', 0.5)
        
        return {
            'llm': llm,
            'reason': reason,
            'expected_quality': expected_quality,
            'expected_cost': expected_cost,
            'expected_latency': llm_info['latency'],
            'task_features': features
        }
    
    def record_outcome(self, task_type: str, llm: str, 
                      quality_score: float, latency: float,
                      cost: float, user_feedback: Optional[int] = None):
        """Record outcome and update performance"""
        # Determine success (quality > 0.7)
        success = quality_score >= 0.7
        
        # Update Beta distribution params
        if success:
            self.task_performance[task_type][llm]['alpha'] += 1
        else:
            self.task_performance[task_type][llm]['beta'] += 1
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            # Record selection
            conn.execute("""
                INSERT INTO selections
                (task_type, task_features, selected_llm, quality_score, 
                 latency, cost, user_feedback, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_type,
                json.dumps({}),
                llm,
                quality_score,
                latency,
                cost,
                user_feedback,
                datetime.now().isoformat()
            ))
            
            # Update performance stats
            cursor = conn.execute("""
                SELECT successes, failures, avg_quality, avg_latency, total_cost
                FROM llm_performance
                WHERE task_type = ? AND llm_name = ?
            """, (task_type, llm))
            
            row = cursor.fetchone()
            
            if row:
                successes, failures, avg_q, avg_l, total_c = row
                
                if success:
                    successes += 1
                else:
                    failures += 1
                
                # Update averages
                n = successes + failures
                avg_quality = (avg_q * (n - 1) + quality_score) / n
                avg_latency = (avg_l * (n - 1) + latency) / n
                total_cost += cost
                
                conn.execute("""
                    UPDATE llm_performance
                    SET successes = ?, failures = ?, avg_quality = ?,
                        avg_latency = ?, total_cost = ?, last_updated = ?
                    WHERE task_type = ? AND llm_name = ?
                """, (
                    successes, failures, avg_quality, avg_latency, total_cost,
                    datetime.now().isoformat(), task_type, llm
                ))
            else:
                conn.execute("""
                    INSERT INTO llm_performance
                    (task_type, llm_name, successes, failures, avg_quality,
                     avg_latency, total_cost, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_type, llm,
                    1 if success else 0,
                    0 if success else 1,
                    quality_score,
                    latency,
                    cost,
                    datetime.now().isoformat()
                ))
    
    def get_best_llm_for_task(self, task_type: str) -> Dict:
        """Get best performing LLM for task type"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT llm_name, successes, failures, avg_quality, avg_latency, total_cost
                FROM llm_performance
                WHERE task_type = ?
                ORDER BY avg_quality DESC
                LIMIT 1
            """, (task_type,))
            
            row = cursor.fetchone()
            
            if row:
                llm, succ, fail, quality, latency, cost = row
                return {
                    'llm': llm,
                    'success_rate': succ / (succ + fail) if (succ + fail) > 0 else 0,
                    'avg_quality': quality,
                    'avg_latency': latency,
                    'total_cost': cost,
                    'total_uses': succ + fail
                }
        
        return {}
    
    def get_performance_summary(self) -> Dict[str, Dict]:
        """Get performance summary for all LLMs"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT llm_name,
                       SUM(successes) as total_succ,
                       SUM(failures) as total_fail,
                       AVG(avg_quality) as overall_quality,
                       AVG(avg_latency) as overall_latency,
                       SUM(total_cost) as overall_cost
                FROM llm_performance
                GROUP BY llm_name
            """)
            
            summary = {}
            
            for row in cursor.fetchall():
                llm, succ, fail, quality, latency, cost = row
                summary[llm] = {
                    'success_rate': succ / (succ + fail) if (succ + fail) > 0 else 0,
                    'total_uses': succ + fail,
                    'avg_quality': quality or 0,
                    'avg_latency': latency or 0,
                    'total_cost': cost or 0,
                    'cost_per_use': (cost / (succ + fail)) if (succ + fail) > 0 else 0
                }
            
            return summary
    
    def get_stats(self) -> Dict:
        """Get bandit statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_selections,
                    COUNT(DISTINCT task_type) as task_types,
                    COUNT(DISTINCT selected_llm) as llms_used,
                    AVG(quality_score) as avg_quality,
                    SUM(cost) as total_cost
                FROM selections
            """)
            
            row = cursor.fetchone()
            if row:
                return {
                    'total_selections': row[0] or 0,
                    'task_types': row[1] or 0,
                    'llms_used': row[2] or 0,
                    'avg_quality': row[3] or 0,
                    'total_cost': row[4] or 0
                }
        
        return {}


def example_usage():
    """Demonstrate LLM bandit"""
    bandit = LLMBandit(exploration_rate=0.2)
    
    print("LLM Multi-Armed Bandit Demo\n" + "="*50)
    
    # Simulate task selections
    print("\n1. Simulating task selections...")
    
    tasks = [
        {'type': 'coding', 'text': 'Write a Python function' * 10, 'requirements': ['reasoning']},
        {'type': 'creative', 'text': 'Write a story', 'requirements': ['creative']},
        {'type': 'simple', 'text': 'What is 2+2?', 'requirements': ['fast'], 'budget': 'low'},
        {'type': 'coding', 'text': 'Debug this code' * 15, 'requirements': ['reasoning']},
    ]
    
    for i, task in enumerate(tasks):
        selection = bandit.select_llm(task)
        print(f"\n  Task {i+1} ({task['type']}): Selected {selection['llm']}")
        print(f"    Reason: {selection['reason']}")
        print(f"    Expected quality: {selection['expected_quality']:.2f}")
        print(f"    Expected cost: ${selection['expected_cost']:.4f}")
        
        # Simulate outcome
        # GPT-4 and Claude perform better on reasoning
        if task['type'] == 'coding' and selection['llm'] in ['gpt-4', 'claude-3']:
            quality = 0.9
        elif task['type'] == 'simple':
            quality = 0.85
        else:
            quality = 0.75
        
        latency = bandit.llms[selection['llm']]['latency']
        cost = selection['expected_cost']
        
        bandit.record_outcome(task['type'], selection['llm'], quality, latency, cost)
    
    # Get best LLMs
    print("\n2. Best LLMs by task type:")
    for task_type in ['coding', 'creative', 'simple']:
        best = bandit.get_best_llm_for_task(task_type)
        if best:
            print(f"  {task_type}: {best['llm']} (quality: {best['avg_quality']:.2f})")
    
    # Performance summary
    print("\n3. Overall Performance:")
    summary = bandit.get_performance_summary()
    for llm, metrics in summary.items():
        print(f"  {llm}:")
        print(f"    Success rate: {metrics['success_rate']:.1%}")
        print(f"    Uses: {metrics['total_uses']}")
        print(f"    Avg quality: {metrics['avg_quality']:.2f}")
        print(f"    Total cost: ${metrics['total_cost']:.4f}")
    
    # Stats
    stats = bandit.get_stats()
    print(f"\n4. Statistics:")
    print(f"  Total selections: {stats['total_selections']}")
    print(f"  Task types: {stats['task_types']}")
    print(f"  Average quality: {stats['avg_quality']:.2f}")


if __name__ == "__main__":
    example_usage()
