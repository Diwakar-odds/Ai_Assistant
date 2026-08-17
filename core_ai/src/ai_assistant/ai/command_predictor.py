"""
Command Success Predictor
Predicts if a command will succeed before execution

Features:
- Historical success/failure analysis
- Context-based predictions
- Pre-execution validation
- Confidence scoring
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import Counter, defaultdict

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ scikit-learn not available - using rule-based prediction")


class CommandSuccessPredictor:
    """
    Predicts command success probability using ML
    """
    
    def __init__(self, db_path: str = "data/automation/command_success.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        if SKLEARN_AVAILABLE:
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.scaler = StandardScaler()
            self.trained = False
        
        # Rule-based fallback
        self.command_stats = defaultdict(lambda: {'success': 0, 'failure': 0})
        self.context_stats = defaultdict(lambda: defaultdict(lambda: {'success': 0, 'failure': 0}))
        
        self._init_database()
        self._load_stats()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS command_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    command_type TEXT,
                    context TEXT,
                    predicted_success REAL,
                    actual_success INTEGER NOT NULL,
                    error_message TEXT,
                    execution_time REAL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS feature_importance (
                    feature_name TEXT PRIMARY KEY,
                    importance REAL NOT NULL,
                    last_updated TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prediction_accuracy (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    total_predictions INTEGER DEFAULT 0,
                    correct_predictions INTEGER DEFAULT 0,
                    accuracy REAL DEFAULT 0.0
                )
            """)
    
    def _load_stats(self):
        """Load historical statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT command, context, actual_success, COUNT(*)
                FROM command_executions
                GROUP BY command, context, actual_success
            """)
            
            for row in cursor.fetchall():
                command, context_str, success, count = row
                
                if success:
                    self.command_stats[command]['success'] += count
                else:
                    self.command_stats[command]['failure'] += count
                
                if context_str:
                    context = json.loads(context_str)
                    context_key = self._serialize_context(context)
                    
                    if success:
                        self.context_stats[command][context_key]['success'] += count
                    else:
                        self.context_stats[command][context_key]['failure'] += count
    
    def _serialize_context(self, context: Dict) -> str:
        """Serialize context to string"""
        features = []
        for key in sorted(context.keys()):
            features.append(f"{key}={context[key]}")
        return "|".join(features)
    
    def _extract_features(self, command: str, context: Optional[Dict] = None) -> np.ndarray:
        """Extract features for ML model"""
        features = []
        
        # Command features
        features.append(len(command))
        features.append(command.count(' '))
        features.append(1 if command.startswith('open_') else 0)
        features.append(1 if command.startswith('close_') else 0)
        features.append(1 if 'file' in command.lower() else 0)
        
        # Historical success rate
        stats = self.command_stats[command]
        total = stats['success'] + stats['failure']
        hist_success_rate = stats['success'] / total if total > 0 else 0.5
        features.append(hist_success_rate)
        features.append(total)  # Number of times seen
        
        # Context features
        if context:
            features.append(context.get('system_load', 0.5))
            features.append(1 if context.get('network_available', True) else 0)
            features.append(context.get('memory_available_gb', 4.0))
            features.append(context.get('hour_of_day', 12) / 24.0)
            features.append(1 if context.get('dependencies_met', True) else 0)
        else:
            features.extend([0.5, 1, 4.0, 0.5, 1])  # Default values
        
        return np.array(features)
    
    def predict_success(self, command: str, context: Optional[Dict] = None) -> Dict:
        """
        Predict if command will succeed
        
        Returns:
            dict with 'success_probability', 'confidence', 'method', 'warnings'
        """
        # Try ML model first
        if SKLEARN_AVAILABLE and self.trained:
            try:
                features = self._extract_features(command, context).reshape(1, -1)
                features_scaled = self.scaler.transform(features)
                
                # Get probability
                proba = self.model.predict_proba(features_scaled)[0]
                success_prob = proba[1]  # Probability of success class
                
                # Get confidence (how sure the model is)
                confidence = max(proba)
                
                return {
                    'success_probability': success_prob,
                    'confidence': confidence,
                    'method': 'ml_model',
                    'warnings': self._generate_warnings(command, context, success_prob)
                }
            except Exception as e:
                print(f"ML prediction failed: {e}")
        
        # Fallback to rule-based
        return self._predict_rule_based(command, context)
    
    def _predict_rule_based(self, command: str, context: Optional[Dict] = None) -> Dict:
        """Rule-based prediction fallback"""
        # Check command history
        stats = self.command_stats.get(command, {'success': 0, 'failure': 0})
        total = stats['success'] + stats['failure']
        
        if total > 0:
            success_prob = stats['success'] / total
        else:
            # No history - use conservative estimate
            success_prob = 0.7
        
        # Adjust based on context
        if context:
            context_key = self._serialize_context(context)
            ctx_stats = self.context_stats[command].get(context_key, {'success': 0, 'failure': 0})
            ctx_total = ctx_stats['success'] + ctx_stats['failure']
            
            if ctx_total > 0:
                ctx_success_prob = ctx_stats['success'] / ctx_total
                # Weight context more heavily if we have data
                success_prob = 0.3 * success_prob + 0.7 * ctx_success_prob
        
        confidence = min(total / 10, 1.0)  # More executions = more confidence
        
        return {
            'success_probability': success_prob,
            'confidence': confidence,
            'method': 'rule_based',
            'warnings': self._generate_warnings(command, context, success_prob)
        }
    
    def _generate_warnings(self, command: str, context: Optional[Dict],
                          success_prob: float) -> List[str]:
        """Generate warnings based on prediction"""
        warnings = []
        
        if success_prob < 0.5:
            warnings.append(f"⚠️ Low success probability ({success_prob:.1%})")
        
        if context:
            if context.get('system_load', 0) > 0.8:
                warnings.append("⚠️ High system load may affect execution")
            
            if not context.get('network_available', True):
                if 'network' in command.lower() or 'online' in command.lower():
                    warnings.append("⚠️ Network not available - command may fail")
            
            if context.get('memory_available_gb', 100) < 1.0:
                warnings.append("⚠️ Low memory available")
            
            if not context.get('dependencies_met', True):
                warnings.append("⚠️ Required dependencies not met")
        
        # Command-specific warnings
        stats = self.command_stats.get(command, {'success': 0, 'failure': 0})
        if stats['failure'] > stats['success']:
            warnings.append(f"⚠️ This command historically fails more often")
        
        return warnings
    
    def record_execution(self, command: str, success: bool,
                        context: Optional[Dict] = None,
                        predicted_success: Optional[float] = None,
                        error_message: Optional[str] = None,
                        execution_time: Optional[float] = None,
                        command_type: Optional[str] = None):
        """Record command execution result"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO command_executions
                (command, command_type, context, predicted_success, actual_success, 
                 error_message, execution_time, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                command,
                command_type,
                json.dumps(context) if context else None,
                predicted_success,
                1 if success else 0,
                error_message,
                execution_time,
                datetime.now().isoformat()
            ))
        
        # Update in-memory stats
        if success:
            self.command_stats[command]['success'] += 1
        else:
            self.command_stats[command]['failure'] += 1
        
        if context:
            context_key = self._serialize_context(context)
            if success:
                self.context_stats[command][context_key]['success'] += 1
            else:
                self.context_stats[command][context_key]['failure'] += 1
        
        # Retrain periodically
        if SKLEARN_AVAILABLE:
            total_executions = sum(s['success'] + s['failure'] for s in self.command_stats.values())
            if total_executions % 50 == 0:  # Retrain every 50 executions
                self.train()
    
    def train(self):
        """Train ML model on historical data"""
        if not SKLEARN_AVAILABLE:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT command, context, actual_success
                FROM command_executions
            """)
            
            X = []
            y = []
            
            for row in cursor.fetchall():
                command, context_str, success = row
                context = json.loads(context_str) if context_str else None
                
                features = self._extract_features(command, context)
                X.append(features)
                y.append(success)
            
            if len(X) > 10:  # Minimum data for training
                X = np.array(X)
                y = np.array(y)
                
                # Scale features
                X_scaled = self.scaler.fit_transform(X)
                
                # Train model
                self.model.fit(X_scaled, y)
                self.trained = True
                
                # Save feature importance
                if hasattr(self.model, 'feature_importances_'):
                    feature_names = [
                        'command_length', 'word_count', 'starts_open', 'starts_close',
                        'contains_file', 'hist_success_rate', 'times_seen',
                        'system_load', 'network_available', 'memory_available',
                        'hour_of_day', 'dependencies_met'
                    ]
                    
                    with sqlite3.connect(self.db_path) as conn:
                        for name, importance in zip(feature_names, self.model.feature_importances_):
                            conn.execute("""
                                INSERT OR REPLACE INTO feature_importance
                                (feature_name, importance, last_updated)
                                VALUES (?, ?, ?)
                            """, (name, float(importance), datetime.now().isoformat()))
    
    def get_stats(self) -> Dict:
        """Get prediction statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN actual_success = 1 THEN 1 ELSE 0 END) as successes,
                    AVG(CASE 
                        WHEN predicted_success IS NOT NULL THEN
                            CASE WHEN (predicted_success > 0.5 AND actual_success = 1) OR
                                      (predicted_success <= 0.5 AND actual_success = 0)
                            THEN 1 ELSE 0 END
                        END) as prediction_accuracy
                FROM command_executions
                WHERE predicted_success IS NOT NULL
            """)
            
            row = cursor.fetchone()
            if row:
                total, successes, pred_acc = row
                
                return {
                    'total_executions': total or 0,
                    'total_successes': successes or 0,
                    'overall_success_rate': (successes / total) if total else 0,
                    'prediction_accuracy': pred_acc or 0,
                    'model_trained': self.trained if SKLEARN_AVAILABLE else False,
                    'commands_tracked': len(self.command_stats)
                }
        
        return {}


def example_usage():
    """Demonstrate command success prediction"""
    predictor = CommandSuccessPredictor()
    
    # Simulate some executions
    print("Recording command executions...")
    
    commands = [
        ("open_chrome", True, {'system_load': 0.3, 'memory_available_gb': 8.0}),
        ("open_chrome", True, {'system_load': 0.4, 'memory_available_gb': 7.5}),
        ("open_nonexistent_app", False, {'system_load': 0.2, 'memory_available_gb': 8.0}),
        ("search_google", True, {'network_available': True}),
        ("search_google", False, {'network_available': False}),
    ]
    
    for cmd, success, context in commands:
        # Predict first
        prediction = predictor.predict_success(cmd, context)
        print(f"\n{cmd}: Predicted {prediction['success_probability']:.1%} success")
        
        # Record actual result
        predictor.record_execution(cmd, success, context, prediction['success_probability'])
    
    # Train model
    if SKLEARN_AVAILABLE:
        predictor.train()
        print("\n✅ Model trained")
    
    # Test prediction
    print("\n" + "="*50)
    print("Testing prediction for new command...")
    test_context = {'system_load': 0.5, 'memory_available_gb': 6.0, 'network_available': True}
    prediction = predictor.predict_success("open_chrome", test_context)
    
    print(f"Command: open_chrome")
    print(f"Success probability: {prediction['success_probability']:.1%}")
    print(f"Confidence: {prediction['confidence']:.1%}")
    print(f"Method: {prediction['method']}")
    if prediction['warnings']:
        print("Warnings:")
        for warning in prediction['warnings']:
            print(f"  {warning}")
    
    # Stats
    stats = predictor.get_stats()
    print(f"\nStatistics:")
    print(f"  Total executions: {stats['total_executions']}")
    print(f"  Success rate: {stats['overall_success_rate']:.1%}")
    print(f"  Prediction accuracy: {stats['prediction_accuracy']:.1%}")


if __name__ == "__main__":
    example_usage()
