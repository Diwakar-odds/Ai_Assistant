"""
Causal Inference System
Understands cause-effect relationships for better decision making

Features:
- Causal graph construction
- Do-calculus for interventions
- Backdoor adjustment
- Counterfactual reasoning
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from collections import defaultdict, deque

try:
    import numpy as np
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print("⚠️ scipy not available")


class CausalInference:
    """
    Causal inference for understanding cause-effect
    """
    
    def __init__(self, db_path: str = "data/causal_inference.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Causal graph: adjacency list
        self.causal_graph = defaultdict(set)  # parent -> children
        self.reverse_graph = defaultdict(set)  # child -> parents
        
        # Learned causal strengths
        self.causal_strengths = {}  # (cause, effect) -> strength
        
        self._init_database()
        self._load_causal_graph()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS causal_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cause TEXT NOT NULL,
                    effect TEXT NOT NULL,
                    strength REAL NOT NULL,
                    confidence REAL NOT NULL,
                    evidence_count INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    UNIQUE(cause, effect)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interventions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    variable TEXT NOT NULL,
                    intervention_value REAL NOT NULL,
                    observed_effects TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    variables TEXT NOT NULL,
                    observation_values TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
    
    def _load_causal_graph(self):
        """Load causal graph from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT cause, effect, strength
                FROM causal_edges
            """)
            
            for row in cursor.fetchall():
                cause, effect, strength = row
                self.causal_graph[cause].add(effect)
                self.reverse_graph[effect].add(cause)
                self.causal_strengths[(cause, effect)] = strength
    
    def add_causal_edge(self, cause: str, effect: str, strength: float,
                       confidence: float = 0.8):
        """Add causal edge to graph"""
        self.causal_graph[cause].add(effect)
        self.reverse_graph[effect].add(cause)
        self.causal_strengths[(cause, effect)] = strength
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO causal_edges
                (cause, effect, strength, confidence, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (cause, effect, strength, confidence, datetime.now().isoformat()))
    
    def learn_causal_structure(self, observations: List[Dict[str, float]]) -> Dict:
        """
        Learn causal structure from observational data
        Uses correlation + temporal ordering as proxy for causation
        """
        if not observations or not SCIPY_AVAILABLE:
            return {}
        
        # Extract variables
        variables = list(observations[0].keys())
        
        # Compute correlations
        discovered_edges = []
        
        for i, var1 in enumerate(variables):
            for var2 in variables[i+1:]:
                # Get values
                vals1 = [obs[var1] for obs in observations if var1 in obs]
                vals2 = [obs[var2] for obs in observations if var2 in obs]
                
                if len(vals1) < 3 or len(vals2) < 3:
                    continue
                
                # Correlation
                correlation, p_value = stats.pearsonr(vals1, vals2)
                
                # If significant correlation
                if abs(correlation) > 0.3 and p_value < 0.05:
                    # Assume temporal ordering (var1 -> var2 if var1 appears earlier)
                    # In practice, would use more sophisticated methods
                    
                    strength = abs(correlation)
                    confidence = 1 - p_value
                    
                    # Add edge
                    self.add_causal_edge(var1, var2, strength, confidence)
                    discovered_edges.append({
                        'cause': var1,
                        'effect': var2,
                        'strength': strength,
                        'confidence': confidence
                    })
        
        return {
            'num_edges': len(discovered_edges),
            'edges': discovered_edges
        }
    
    def get_parents(self, variable: str) -> Set[str]:
        """Get direct causes of variable"""
        return self.reverse_graph.get(variable, set())
    
    def get_children(self, variable: str) -> Set[str]:
        """Get direct effects of variable"""
        return self.causal_graph.get(variable, set())
    
    def get_ancestors(self, variable: str) -> Set[str]:
        """Get all ancestors (transitive causes)"""
        ancestors = set()
        queue = deque([variable])
        visited = set()
        
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            
            parents = self.get_parents(node)
            ancestors.update(parents)
            queue.extend(parents)
        
        return ancestors
    
    def get_descendants(self, variable: str) -> Set[str]:
        """Get all descendants (transitive effects)"""
        descendants = set()
        queue = deque([variable])
        visited = set()
        
        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            
            children = self.get_children(node)
            descendants.update(children)
            queue.extend(children)
        
        return descendants
    
    def backdoor_adjustment(self, treatment: str, outcome: str) -> Optional[Set[str]]:
        """
        Find variables to adjust for (backdoor criterion)
        To estimate causal effect of treatment on outcome
        """
        # Find confounders: common ancestors of treatment and outcome
        treatment_ancestors = self.get_ancestors(treatment)
        outcome_ancestors = self.get_ancestors(outcome)
        
        confounders = treatment_ancestors & outcome_ancestors
        
        # Backdoor criterion: block all backdoor paths
        # Simplified: return all confounders
        return confounders
    
    def estimate_causal_effect(self, treatment: str, outcome: str,
                              observations: List[Dict[str, float]]) -> Dict:
        """
        Estimate causal effect of treatment on outcome
        Using backdoor adjustment
        """
        if not observations:
            return {}
        
        # Find adjustment set
        adjustment_set = self.backdoor_adjustment(treatment, outcome)
        
        # Compute effect (simplified: just correlation)
        treatment_vals = [obs.get(treatment, 0) for obs in observations]
        outcome_vals = [obs.get(outcome, 0) for obs in observations]
        
        if not SCIPY_AVAILABLE or len(treatment_vals) < 3:
            # Fallback: mean difference
            treated = [outcome_vals[i] for i, t in enumerate(treatment_vals) if t > 0]
            control = [outcome_vals[i] for i, t in enumerate(treatment_vals) if t <= 0]
            
            effect = np.mean(treated) - np.mean(control) if treated and control else 0
            
            return {
                'treatment': treatment,
                'outcome': outcome,
                'estimated_effect': effect,
                'adjustment_set': list(adjustment_set) if adjustment_set else [],
                'method': 'mean_difference'
            }
        
        # Use correlation as proxy
        correlation, p_value = stats.pearsonr(treatment_vals, outcome_vals)
        
        return {
            'treatment': treatment,
            'outcome': outcome,
            'estimated_effect': correlation,
            'p_value': p_value,
            'adjustment_set': list(adjustment_set) if adjustment_set else [],
            'method': 'correlation'
        }
    
    def do_intervention(self, variable: str, value: float) -> Dict:
        """
        Simulate intervention (do-calculus)
        Predict effects of setting variable to value
        """
        # Get all descendants (variables affected by intervention)
        affected = self.get_descendants(variable)
        
        # Predict effects
        effects = {}
        
        for effect_var in affected:
            # Look up causal strength
            strength = self.causal_strengths.get((variable, effect_var), 0)
            
            # Predict change (simplified linear model)
            predicted_change = strength * value
            
            effects[effect_var] = predicted_change
        
        # Save intervention
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO interventions
                (variable, intervention_value, observed_effects, timestamp)
                VALUES (?, ?, ?, ?)
            """, (
                variable,
                value,
                json.dumps(effects),
                datetime.now().isoformat()
            ))
        
        return {
            'intervention': {variable: value},
            'predicted_effects': effects,
            'num_affected': len(effects)
        }
    
    def counterfactual(self, observation: Dict[str, float],
                      intervention: Dict[str, float]) -> Dict:
        """
        Counterfactual reasoning: what would happen if...?
        
        Args:
            observation: What actually happened
            intervention: What we want to change
        """
        # Start with observed values
        counterfactual_world = observation.copy()
        
        # Apply intervention
        counterfactual_world.update(intervention)
        
        # Propagate effects through causal graph
        for var, value in intervention.items():
            effects = self.do_intervention(var, value)
            
            # Update counterfactual world
            for effect_var, change in effects['predicted_effects'].items():
                if effect_var in counterfactual_world:
                    counterfactual_world[effect_var] += change
        
        # Compare
        differences = {
            var: counterfactual_world[var] - observation[var]
            for var in observation.keys()
            if var in counterfactual_world
        }
        
        return {
            'factual': observation,
            'counterfactual': counterfactual_world,
            'differences': differences
        }
    
    def get_stats(self) -> Dict:
        """Get causal inference statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_edges,
                    AVG(strength) as avg_strength,
                    AVG(confidence) as avg_confidence,
                    (SELECT COUNT(*) FROM interventions) as total_interventions
                FROM causal_edges
            """)
            
            row = cursor.fetchone()
            if row:
                return {
                    'total_edges': row[0] or 0,
                    'avg_strength': row[1] or 0,
                    'avg_confidence': row[2] or 0,
                    'total_interventions': row[3] or 0,
                    'variables': len(set(list(self.causal_graph.keys()) + 
                                       list(self.reverse_graph.keys())))
                }
        
        return {}


def example_usage():
    """Demonstrate causal inference"""
    causal = CausalInference()
    
    print("Causal Inference Demo\n" + "="*50)
    
    # Build causal graph
    print("\n1. Building causal graph...")
    causal.add_causal_edge('exercise', 'fitness', strength=0.7, confidence=0.9)
    causal.add_causal_edge('diet', 'fitness', strength=0.6, confidence=0.85)
    causal.add_causal_edge('fitness', 'health', strength=0.8, confidence=0.95)
    causal.add_causal_edge('age', 'health', strength=-0.3, confidence=0.7)
    
    print("  Added 4 causal edges")
    
    # Query graph
    print("\n2. Querying causal relationships...")
    print(f"  Causes of health: {causal.get_parents('health')}")
    print(f"  Effects of exercise: {causal.get_descendants('exercise')}")
    
    # Backdoor adjustment
    print("\n3. Finding confounders...")
    confounders = causal.backdoor_adjustment('exercise', 'health')
    print(f"  Variables to adjust for: {confounders}")
    
    # Intervention
    print("\n4. Simulating intervention...")
    result = causal.do_intervention('exercise', 1.0)
    print(f"  Increasing exercise by 1.0:")
    for var, effect in result['predicted_effects'].items():
        print(f"    {var}: {effect:+.3f}")
    
    # Counterfactual
    print("\n5. Counterfactual reasoning...")
    observation = {'exercise': 0.2, 'diet': 0.5, 'fitness': 0.4, 'health': 0.6, 'age': 0.5}
    intervention = {'exercise': 0.8}
    
    cf = causal.counterfactual(observation, intervention)
    print(f"  Factual: exercise={observation['exercise']}, health={observation['health']:.2f}")
    print(f"  Counterfactual: exercise={intervention['exercise']}, health={cf['counterfactual']['health']:.2f}")
    print(f"  Difference: {cf['differences']['health']:+.2f}")
    
    # Stats
    stats = causal.get_stats()
    print(f"\n6. Statistics:")
    print(f"  Total edges: {stats['total_edges']}")
    print(f"  Variables: {stats['variables']}")
    print(f"  Avg causal strength: {stats['avg_strength']:.2f}")


if __name__ == "__main__":
    example_usage()
