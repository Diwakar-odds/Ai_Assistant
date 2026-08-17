"""
Anomaly Detection for Security & Performance
Detects unusual command patterns and system behavior

Features:
- Isolation Forest for command pattern anomalies
- Statistical outlier detection
- Voice authentication anomaly detection
- Real-time alerting
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict, deque
import math

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ scikit-learn not available - using statistical detection")


class AnomalyDetector:
    """
    Detects anomalous behavior patterns
    """
    
    def __init__(self, db_path: str = "data/anomaly_detection.db",
                 contamination: float = 0.1):
        self.db_path = db_path
        self.contamination = contamination  # Expected anomaly rate
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        if SKLEARN_AVAILABLE:
            self.model = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=100
            )
            self.scaler = StandardScaler()
            self.trained = False
        
        # Statistical detection
        self.command_baseline = defaultdict(lambda: {'mean': 0, 'std': 1, 'count': 0})
        self.user_patterns = defaultdict(lambda: deque(maxlen=100))
        
        # Alert thresholds
        self.alert_threshold = 3.0  # Standard deviations
        
        self._init_database()
        self._load_baseline()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_data TEXT NOT NULL,
                    features TEXT,
                    anomaly_score REAL,
                    is_anomaly INTEGER DEFAULT 0,
                    user_id TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    event_id INTEGER,
                    description TEXT NOT NULL,
                    acknowledged INTEGER DEFAULT 0,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (event_id) REFERENCES events(id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS baselines (
                    metric_name TEXT PRIMARY KEY,
                    mean_value REAL NOT NULL,
                    std_value REAL NOT NULL,
                    sample_count INTEGER NOT NULL,
                    last_updated TEXT NOT NULL
                )
            """)
    
    def _load_baseline(self):
        """Load baseline statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT metric_name, mean_value, std_value, sample_count
                FROM baselines
            """)
            
            for row in cursor.fetchall():
                metric, mean, std, count = row
                self.command_baseline[metric] = {
                    'mean': mean,
                    'std': std,
                    'count': count
                }
    
    def _extract_command_features(self, event_data: Dict) -> np.ndarray:
        """Extract features from command event"""
        features = []
        
        # Command characteristics
        command = event_data.get('command', '')
        features.append(len(command))
        features.append(command.count(' '))
        features.append(1 if command.startswith('open_') else 0)
        features.append(1 if 'file' in command.lower() else 0)
        features.append(1 if 'network' in command.lower() else 0)
        
        # Temporal features
        hour = datetime.now().hour
        features.append(hour / 24.0)
        features.append(1 if 9 <= hour <= 17 else 0)  # Business hours
        features.append(datetime.now().weekday() / 7.0)
        
        # Context features
        context = event_data.get('context', {})
        features.append(context.get('system_load', 0.5))
        features.append(context.get('memory_usage', 0.5))
        features.append(1 if context.get('network_active', False) else 0)
        features.append(context.get('num_open_apps', 5) / 20.0)
        
        return np.array(features)
    
    def _extract_voice_features(self, event_data: Dict) -> np.ndarray:
        """Extract features from voice event"""
        features = []
        
        voice_data = event_data.get('voice_data', {})
        
        # Voice characteristics
        features.append(voice_data.get('pitch', 150.0) / 300.0)
        features.append(voice_data.get('energy', 0.5))
        features.append(voice_data.get('speaking_rate', 4.0) / 10.0)
        features.append(voice_data.get('confidence', 0.9))
        
        # Speaker similarity (cosine similarity with baseline)
        features.append(voice_data.get('speaker_similarity', 0.95))
        
        # Temporal
        features.append(datetime.now().hour / 24.0)
        
        # Background noise
        features.append(voice_data.get('background_noise', 0.1))
        
        return np.array(features)
    
    def detect_anomaly(self, event_type: str, event_data: Dict,
                      user_id: str = "default") -> Dict:
        """
        Detect if event is anomalous
        
        Returns:
            dict with 'is_anomaly', 'score', 'method', 'reasons'
        """
        # Extract features
        if event_type == 'command':
            features = self._extract_command_features(event_data)
        elif event_type == 'voice':
            features = self._extract_voice_features(event_data)
        elif event_type == 'system':
            features = self._extract_system_features(event_data)
        else:
            return {'is_anomaly': False, 'score': 0.0, 'method': 'unknown'}
        
        # Try ML detection
        if SKLEARN_AVAILABLE and self.trained:
            try:
                features_scaled = self.scaler.transform(features.reshape(1, -1))
                score = self.model.score_samples(features_scaled)[0]
                is_anomaly = self.model.predict(features_scaled)[0] == -1
                
                result = {
                    'is_anomaly': bool(is_anomaly),
                    'score': float(score),
                    'method': 'isolation_forest',
                    'reasons': self._analyze_anomaly(event_type, event_data, features)
                }
                
                # Record event
                self._record_event(event_type, event_data, features, score, is_anomaly, user_id)
                
                # Generate alert if needed
                if is_anomaly:
                    self._generate_alert(event_type, event_data, result)
                
                return result
            except:
                pass
        
        # Fallback to statistical detection
        return self._detect_statistical(event_type, event_data, features, user_id)
    
    def _detect_statistical(self, event_type: str, event_data: Dict,
                           features: np.ndarray, user_id: str) -> Dict:
        """Statistical anomaly detection"""
        anomalies = []
        max_z_score = 0.0
        
        # Check each feature against baseline
        feature_names = self._get_feature_names(event_type)
        
        for i, (feature_val, feature_name) in enumerate(zip(features, feature_names)):
            baseline = self.command_baseline.get(f"{event_type}_{feature_name}")
            
            if baseline and baseline['count'] > 10:
                z_score = abs((feature_val - baseline['mean']) / (baseline['std'] + 1e-6))
                
                if z_score > self.alert_threshold:
                    anomalies.append({
                        'feature': feature_name,
                        'value': float(feature_val),
                        'expected': baseline['mean'],
                        'z_score': z_score
                    })
                    max_z_score = max(max_z_score, z_score)
        
        is_anomaly = len(anomalies) > 0
        
        result = {
            'is_anomaly': is_anomaly,
            'score': -max_z_score if is_anomaly else 0.0,
            'method': 'statistical',
            'reasons': anomalies
        }
        
        # Record and alert
        self._record_event(event_type, event_data, features, result['score'], is_anomaly, user_id)
        
        if is_anomaly:
            self._generate_alert(event_type, event_data, result)
        
        # Update baseline
        self._update_baseline(event_type, features)
        
        return result
    
    def _get_feature_names(self, event_type: str) -> List[str]:
        """Get feature names for event type"""
        if event_type == 'command':
            return [
                'command_length', 'word_count', 'starts_open', 'contains_file',
                'contains_network', 'hour', 'business_hours', 'weekday',
                'system_load', 'memory_usage', 'network_active', 'open_apps'
            ]
        elif event_type == 'voice':
            return [
                'pitch', 'energy', 'speaking_rate', 'confidence',
                'speaker_similarity', 'hour', 'background_noise'
            ]
        return []
    
    def _analyze_anomaly(self, event_type: str, event_data: Dict,
                        features: np.ndarray) -> List[str]:
        """Analyze why event is anomalous"""
        reasons = []
        
        if event_type == 'command':
            command = event_data.get('command', '')
            
            # Unusual time
            hour = datetime.now().hour
            if hour < 6 or hour > 23:
                reasons.append(f"Command at unusual hour ({hour}:00)")
            
            # Suspicious command
            suspicious_keywords = ['delete', 'remove', 'format', 'rm -rf', 'drop table']
            if any(kw in command.lower() for kw in suspicious_keywords):
                reasons.append(f"Potentially dangerous command: {command}")
            
            # High frequency
            user_patterns = event_data.get('user_patterns', {})
            if user_patterns.get('commands_last_minute', 0) > 20:
                reasons.append("Unusually high command frequency")
        
        elif event_type == 'voice':
            voice_data = event_data.get('voice_data', {})
            
            # Low speaker similarity
            if voice_data.get('speaker_similarity', 1.0) < 0.7:
                reasons.append("Voice pattern doesn't match registered user")
            
            # Low confidence
            if voice_data.get('confidence', 1.0) < 0.5:
                reasons.append("Low voice recognition confidence")
            
            # Unusual background
            if voice_data.get('background_noise', 0.0) > 0.7:
                reasons.append("High background noise")
        
        return reasons
    
    def _record_event(self, event_type: str, event_data: Dict,
                     features: np.ndarray, score: float,
                     is_anomaly: bool, user_id: str):
        """Record event in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO events
                (event_type, event_data, features, anomaly_score, is_anomaly, user_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event_type,
                json.dumps(event_data),
                json.dumps(features.tolist()),
                score,
                1 if is_anomaly else 0,
                user_id,
                datetime.now().isoformat()
            ))
    
    def _generate_alert(self, event_type: str, event_data: Dict, result: Dict):
        """Generate security alert"""
        severity = 'high' if result['score'] < -2.0 else 'medium'
        
        description = f"Anomalous {event_type} detected. "
        if result['reasons']:
            description += " Reasons: " + ", ".join(
                r if isinstance(r, str) else r.get('feature', 'unknown')
                for r in result['reasons']
            )
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO alerts
                (alert_type, severity, description, timestamp)
                VALUES (?, ?, ?, ?)
            """, (
                event_type,
                severity,
                description,
                datetime.now().isoformat()
            ))
    
    def _update_baseline(self, event_type: str, features: np.ndarray):
        """Update baseline statistics"""
        feature_names = self._get_feature_names(event_type)
        
        for i, (feature_val, feature_name) in enumerate(zip(features, feature_names)):
            metric_name = f"{event_type}_{feature_name}"
            baseline = self.command_baseline[metric_name]
            
            # Online mean/std update
            n = baseline['count']
            old_mean = baseline['mean']
            
            new_count = n + 1
            new_mean = (n * old_mean + feature_val) / new_count
            
            if n > 0:
                new_std = math.sqrt(
                    ((n - 1) * baseline['std']**2 + (feature_val - old_mean) * (feature_val - new_mean)) / n
                )
            else:
                new_std = 0.1
            
            baseline['mean'] = new_mean
            baseline['std'] = new_std
            baseline['count'] = new_count
        
        # Persist periodically
        if baseline['count'] % 10 == 0:
            with sqlite3.connect(self.db_path) as conn:
                for i, feature_name in enumerate(feature_names):
                    metric_name = f"{event_type}_{feature_name}"
                    b = self.command_baseline[metric_name]
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO baselines
                        (metric_name, mean_value, std_value, sample_count, last_updated)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        metric_name,
                        b['mean'],
                        b['std'],
                        b['count'],
                        datetime.now().isoformat()
                    ))
    
    def _extract_system_features(self, event_data: Dict) -> np.ndarray:
        """Extract system performance features"""
        features = []
        
        features.append(event_data.get('cpu_usage', 0.5))
        features.append(event_data.get('memory_usage', 0.5))
        features.append(event_data.get('disk_io', 0.5))
        features.append(event_data.get('network_io', 0.5))
        features.append(event_data.get('process_count', 100) / 500.0)
        features.append(event_data.get('temperature', 50.0) / 100.0)
        
        return np.array(features)
    
    def train(self):
        """Train anomaly detection model"""
        if not SKLEARN_AVAILABLE:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT features
                FROM events
                WHERE is_anomaly = 0
                LIMIT 1000
            """)
            
            X = []
            for row in cursor.fetchall():
                features_json = row[0]
                if features_json:
                    X.append(json.loads(features_json))
            
            if len(X) > 50:
                X = np.array(X)
                X_scaled = self.scaler.fit_transform(X)
                self.model.fit(X_scaled)
                self.trained = True
    
    def get_alerts(self, severity: Optional[str] = None,
                   acknowledged: bool = False) -> List[Dict]:
        """Get recent alerts"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT id, alert_type, severity, description, timestamp, acknowledged
                FROM alerts
                WHERE 1=1
            """
            params = []
            
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            
            if not acknowledged:
                query += " AND acknowledged = 0"
            
            query += " ORDER BY timestamp DESC LIMIT 50"
            
            cursor = conn.execute(query, params)
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'id': row[0],
                    'type': row[1],
                    'severity': row[2],
                    'description': row[3],
                    'timestamp': row[4],
                    'acknowledged': bool(row[5])
                })
            
            return alerts
    
    def acknowledge_alert(self, alert_id: int):
        """Mark alert as acknowledged"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE alerts
                SET acknowledged = 1
                WHERE id = ?
            """, (alert_id,))
    
    def get_stats(self) -> Dict:
        """Get anomaly detection statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_anomaly = 1 THEN 1 ELSE 0 END) as anomalies,
                    (SELECT COUNT(*) FROM alerts WHERE acknowledged = 0) as unacked_alerts
                FROM events
            """)
            
            row = cursor.fetchone()
            if row:
                total, anomalies, unacked = row
                return {
                    'total_events': total or 0,
                    'anomalies_detected': anomalies or 0,
                    'anomaly_rate': (anomalies / total) if total else 0,
                    'unacknowledged_alerts': unacked or 0,
                    'model_trained': self.trained if SKLEARN_AVAILABLE else False
                }
        
        return {}


def example_usage():
    """Demonstrate anomaly detection"""
    detector = AnomalyDetector()
    
    print("Testing anomaly detection...\n")
    
    # Normal command
    result = detector.detect_anomaly(
        'command',
        {
            'command': 'open_chrome',
            'context': {'system_load': 0.3, 'memory_usage': 0.5}
        }
    )
    print(f"Normal command: Anomaly={result['is_anomaly']}, Score={result['score']:.2f}")
    
    # Suspicious command
    result = detector.detect_anomaly(
        'command',
        {
            'command': 'delete_all_files',
            'context': {'system_load': 0.9, 'memory_usage': 0.95}
        }
    )
    print(f"Suspicious command: Anomaly={result['is_anomaly']}, Score={result['score']:.2f}")
    if result['reasons']:
        print(f"  Reasons: {result['reasons']}")
    
    # Voice anomaly
    result = detector.detect_anomaly(
        'voice',
        {
            'voice_data': {
                'pitch': 180.0,
                'energy': 0.9,
                'speaker_similarity': 0.5,  # Low similarity
                'confidence': 0.3
            }
        }
    )
    print(f"\nVoice authentication: Anomaly={result['is_anomaly']}, Score={result['score']:.2f}")
    if result['reasons']:
        print(f"  Reasons: {result['reasons']}")
    
    # Get alerts
    alerts = detector.get_alerts()
    print(f"\n{len(alerts)} active alerts")
    
    # Stats
    stats = detector.get_stats()
    print(f"\nStatistics:")
    print(f"  Total events: {stats['total_events']}")
    print(f"  Anomalies: {stats['anomalies_detected']}")
    print(f"  Anomaly rate: {stats['anomaly_rate']:.1%}")


if __name__ == "__main__":
    example_usage()
