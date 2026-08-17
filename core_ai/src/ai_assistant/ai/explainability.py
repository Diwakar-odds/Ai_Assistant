"""
Explainable AI (XAI) System
Provides interpretable explanations for model predictions

Features:
- Feature importance (SHAP-style values)
- Counterfactual explanations
- Example-based explanations
- Natural language rationales
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict

try:
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.tree import DecisionTreeClassifier
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ scikit-learn not available")


class ExplainabilityEngine:
    """
    Provides interpretable explanations for predictions
    """
    
    def __init__(self, db_path: str = "data/explainability.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Feature names for interpretation
        self.feature_names = []
        self.model = None
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS explanations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prediction_id TEXT NOT NULL,
                    prediction TEXT NOT NULL,
                    feature_importance TEXT NOT NULL,
                    counterfactuals TEXT,
                    similar_examples TEXT,
                    natural_language TEXT,
                    explanation_type TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feature_metadata (
                    feature_name TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    value_type TEXT NOT NULL,
                    importance_baseline REAL DEFAULT 0.0,
                    last_updated TEXT NOT NULL
                )
            """)
    
    def set_feature_names(self, names: List[str], descriptions: Optional[List[str]] = None):
        """Set feature names for interpretability"""
        self.feature_names = names
        
        if descriptions is None:
            descriptions = [f"Feature: {name}" for name in names]
        
        with sqlite3.connect(self.db_path) as conn:
            for name, desc in zip(names, descriptions):
                conn.execute("""
                    INSERT OR REPLACE INTO feature_metadata
                    (feature_name, description, value_type, last_updated)
                    VALUES (?, ?, ?, ?)
                """, (name, desc, 'numeric', datetime.now().isoformat()))
    
    def compute_feature_importance(self, features: np.ndarray, 
                                   prediction: int,
                                   model=None) -> List[Dict]:
        """
        Compute feature importance scores (SHAP-style)
        """
        if model is None:
            model = self.model
        
        if model is None or not SKLEARN_AVAILABLE:
            # Fallback: all features equally important
            return [
                {
                    'feature': self.feature_names[i] if i < len(self.feature_names) else f'feature_{i}',
                    'value': float(features[i]),
                    'importance': 1.0 / len(features),
                    'direction': 'positive'
                }
                for i in range(len(features))
            ]
        
        # Simplified SHAP: Compute marginal contributions
        importance_scores = []
        
        if hasattr(model, 'feature_importances_'):
            # Tree-based models
            importances = model.feature_importances_
        else:
            # Use permutation importance approximation
            importances = self._permutation_importance(features, model)
        
        # Scale by feature values
        for i, (feature_val, base_importance) in enumerate(zip(features, importances)):
            # Contribution = importance * |value|
            contribution = base_importance * abs(feature_val)
            
            # Direction: positive if pushes toward prediction
            direction = 'positive' if feature_val > 0 else 'negative'
            
            importance_scores.append({
                'feature': self.feature_names[i] if i < len(self.feature_names) else f'feature_{i}',
                'value': float(feature_val),
                'importance': float(contribution),
                'direction': direction,
                'base_importance': float(base_importance)
            })
        
        # Sort by importance
        importance_scores.sort(key=lambda x: x['importance'], reverse=True)
        
        return importance_scores
    
    def _permutation_importance(self, features: np.ndarray, model) -> np.ndarray:
        """Compute permutation importance"""
        try:
            baseline_pred = model.predict_proba(features.reshape(1, -1))[0]
            importances = []
            
            for i in range(len(features)):
                # Permute this feature
                perturbed = features.copy()
                perturbed[i] = 0  # or random value
                
                perturbed_pred = model.predict_proba(perturbed.reshape(1, -1))[0]
                
                # Importance = change in prediction
                importance = np.abs(baseline_pred - perturbed_pred).max()
                importances.append(importance)
            
            return np.array(importances)
        except:
            return np.ones(len(features)) / len(features)
    
    def generate_counterfactual(self, features: np.ndarray,
                               current_prediction: int,
                               desired_prediction: int,
                               model=None,
                               max_changes: int = 3) -> Optional[Dict]:
        """
        Generate counterfactual: minimal changes to flip prediction
        
        Returns:
            dict with 'original', 'counterfactual', 'changes'
        """
        if model is None:
            model = self.model
        
        if model is None:
            return None
        
        # Greedy search: change features one by one
        counterfactual = features.copy()
        changes = []
        
        for _ in range(max_changes):
            best_change = None
            best_distance = float('inf')
            
            # Try changing each feature
            for i in range(len(features)):
                # Try different values
                for delta in [-1, -0.5, 0.5, 1]:
                    test_features = counterfactual.copy()
                    test_features[i] += delta
                    
                    try:
                        pred = model.predict(test_features.reshape(1, -1))[0]
                        
                        if pred == desired_prediction:
                            # Found flip!
                            distance = abs(delta)
                            
                            if distance < best_distance:
                                best_distance = distance
                                best_change = {
                                    'feature_idx': i,
                                    'feature_name': self.feature_names[i] if i < len(self.feature_names) else f'feature_{i}',
                                    'original_value': float(counterfactual[i]),
                                    'new_value': float(test_features[i]),
                                    'change': float(delta)
                                }
                    except:
                        continue
            
            if best_change:
                counterfactual[best_change['feature_idx']] = best_change['new_value']
                changes.append(best_change)
                
                # Check if prediction flipped
                try:
                    pred = model.predict(counterfactual.reshape(1, -1))[0]
                    if pred == desired_prediction:
                        return {
                            'original': features.tolist(),
                            'counterfactual': counterfactual.tolist(),
                            'changes': changes,
                            'num_changes': len(changes)
                        }
                except:
                    break
            else:
                break
        
        return None
    
    def find_similar_examples(self, features: np.ndarray,
                             examples_db: List[Tuple[np.ndarray, int, Dict]],
                             top_k: int = 3) -> List[Dict]:
        """
        Find similar past examples (case-based reasoning)
        
        Args:
            features: Current feature vector
            examples_db: List of (features, label, metadata) tuples
            top_k: Number of examples to return
        """
        if not examples_db:
            return []
        
        similarities = []
        
        for ex_features, ex_label, ex_metadata in examples_db:
            # Euclidean distance
            distance = np.linalg.norm(features - ex_features)
            similarity = 1 / (1 + distance)
            
            similarities.append({
                'features': ex_features.tolist(),
                'label': ex_label,
                'metadata': ex_metadata,
                'similarity': float(similarity),
                'distance': float(distance)
            })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similarities[:top_k]
    
    def generate_natural_language_explanation(self, 
                                             prediction: int,
                                             feature_importance: List[Dict],
                                             counterfactual: Optional[Dict] = None,
                                             similar_examples: Optional[List[Dict]] = None) -> str:
        """
        Generate human-readable explanation
        """
        explanation_parts = []
        
        # Main prediction
        explanation_parts.append(f"Prediction: {prediction}")
        
        # Top features
        if feature_importance:
            top_features = feature_importance[:3]
            explanation_parts.append("\nKey factors:")
            for feat in top_features:
                direction = "increases" if feat['direction'] == 'positive' else "decreases"
                explanation_parts.append(
                    f"  • {feat['feature']}: {feat['value']:.2f} "
                    f"({direction} likelihood, importance: {feat['importance']:.2f})"
                )
        
        # Counterfactual
        if counterfactual:
            explanation_parts.append(
                f"\nTo change the outcome, you would need to modify {counterfactual['num_changes']} feature(s):"
            )
            for change in counterfactual['changes'][:2]:
                explanation_parts.append(
                    f"  • Change {change['feature_name']} from {change['original_value']:.2f} "
                    f"to {change['new_value']:.2f}"
                )
        
        # Similar examples
        if similar_examples:
            explanation_parts.append(f"\nSimilar past cases:")
            for ex in similar_examples[:2]:
                metadata = ex.get('metadata', {})
                desc = metadata.get('description', 'No description')
                explanation_parts.append(
                    f"  • {desc} (similarity: {ex['similarity']:.1%})"
                )
        
        return "\n".join(explanation_parts)
    
    def explain_prediction(self, prediction_id: str,
                          features: np.ndarray,
                          prediction: int,
                          model=None,
                          examples_db: Optional[List] = None) -> Dict:
        """
        Generate comprehensive explanation for a prediction
        
        Returns:
            dict with all explanation types
        """
        # Feature importance
        feature_importance = self.compute_feature_importance(features, prediction, model)
        
        # Counterfactual (if binary classification)
        counterfactual = None
        if prediction in [0, 1]:
            desired = 1 - prediction
            counterfactual = self.generate_counterfactual(
                features, prediction, desired, model
            )
        
        # Similar examples
        similar_examples = None
        if examples_db:
            similar_examples = self.find_similar_examples(features, examples_db)
        
        # Natural language
        nl_explanation = self.generate_natural_language_explanation(
            prediction,
            feature_importance,
            counterfactual,
            similar_examples
        )
        
        # Save to database
        explanation = {
            'prediction_id': prediction_id,
            'prediction': prediction,
            'feature_importance': feature_importance,
            'counterfactual': counterfactual,
            'similar_examples': similar_examples,
            'natural_language': nl_explanation
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO explanations
                (prediction_id, prediction, feature_importance, counterfactuals,
                 similar_examples, natural_language, explanation_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prediction_id,
                str(prediction),
                json.dumps(feature_importance),
                json.dumps(counterfactual) if counterfactual else None,
                json.dumps(similar_examples) if similar_examples else None,
                nl_explanation,
                'comprehensive',
                datetime.now().isoformat()
            ))
        
        return explanation
    
    def get_feature_importance_summary(self) -> Dict[str, float]:
        """Get aggregate feature importance across all predictions"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT feature_importance
                FROM explanations
            """)
            
            importance_sum = defaultdict(float)
            count = 0
            
            for row in cursor.fetchall():
                importances = json.loads(row[0])
                for feat in importances:
                    importance_sum[feat['feature']] += feat['importance']
                count += 1
            
            if count > 0:
                return {feat: imp / count for feat, imp in importance_sum.items()}
            
            return {}
    
    def get_stats(self) -> Dict:
        """Get explainability statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(counterfactuals) as with_counterfactuals,
                    COUNT(similar_examples) as with_examples
                FROM explanations
            """)
            
            row = cursor.fetchone()
            if row:
                total, cf, ex = row
                return {
                    'total_explanations': total or 0,
                    'with_counterfactuals': cf or 0,
                    'with_examples': ex or 0,
                    'feature_count': len(self.feature_names)
                }
        
        return {}


def example_usage():
    """Demonstrate explainability"""
    engine = ExplainabilityEngine()
    
    print("Explainable AI Demo\n" + "="*50)
    
    # Set feature names
    feature_names = ['age', 'income', 'credit_score', 'debt_ratio']
    descriptions = [
        'Age in years',
        'Annual income in thousands',
        'Credit score (300-850)',
        'Debt-to-income ratio'
    ]
    engine.set_feature_names(feature_names, descriptions)
    
    # Create simple model
    if SKLEARN_AVAILABLE:
        model = DecisionTreeClassifier(max_depth=3, random_state=42)
        X_train = np.random.randn(100, 4)
        y_train = (X_train[:, 2] > 0).astype(int)  # Credit score determines outcome
        model.fit(X_train, y_train)
        engine.model = model
    
    # Example prediction
    features = np.array([35, 75, 720, 0.3])  # age, income, credit_score, debt_ratio
    prediction = 1
    
    print("\n1. Generating explanation...")
    print(f"Input: {dict(zip(feature_names, features))}")
    
    # Generate explanation
    explanation = engine.explain_prediction(
        'pred_001',
        features,
        prediction,
        engine.model
    )
    
    print("\n2. Natural Language Explanation:")
    print(explanation['natural_language'])
    
    print("\n3. Top Feature Importances:")
    for feat in explanation['feature_importance'][:3]:
        print(f"  {feat['feature']}: {feat['importance']:.3f}")
    
    if explanation['counterfactual']:
        print("\n4. Counterfactual:")
        print(f"  Changes needed: {explanation['counterfactual']['num_changes']}")
        for change in explanation['counterfactual']['changes']:
            print(f"    {change['feature_name']}: {change['original_value']:.2f} → {change['new_value']:.2f}")
    
    # Stats
    stats = engine.get_stats()
    print(f"\n5. Statistics:")
    print(f"  Total explanations: {stats['total_explanations']}")
    print(f"  Features tracked: {stats['feature_count']}")


if __name__ == "__main__":
    example_usage()
