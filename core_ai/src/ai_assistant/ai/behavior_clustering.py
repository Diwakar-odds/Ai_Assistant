"""
User Behavior Clustering
Clusters usage sessions to identify patterns and user types

Features:
- K-Means clustering on session features
- Power-user vs casual-user identification
- Hidden workflow pattern discovery
- Cluster-specific personalization
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict, Counter

try:
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️ scikit-learn not available")


class BehaviorClusterer:
    """
    Clusters user behavior patterns
    """
    
    def __init__(self, db_path: str = "data/analytics/behavior_clustering.db",
                 n_clusters: int = 5):
        self.db_path = db_path
        self.n_clusters = n_clusters
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        if SKLEARN_AVAILABLE:
            self.clusterer = KMeans(n_clusters=n_clusters, random_state=42)
            self.scaler = StandardScaler()
            self.pca = PCA(n_components=min(10, n_clusters * 2))
            self.trained = False
        
        # Cluster profiles
        self.cluster_profiles = {}
        
        self._init_database()
        self._load_clusters()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    features TEXT NOT NULL,
                    cluster_id INTEGER,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_minutes REAL,
                    num_commands INTEGER DEFAULT 0,
                    command_types TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clusters (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    centroid TEXT NOT NULL,
                    size INTEGER DEFAULT 0,
                    characteristics TEXT,
                    last_updated TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_clusters (
                    user_id TEXT PRIMARY KEY,
                    primary_cluster INTEGER NOT NULL,
                    cluster_distribution TEXT NOT NULL,
                    user_type TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            """)
    
    def _load_clusters(self):
        """Load cluster profiles"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, name, description, centroid, characteristics
                FROM clusters
            """)
            
            for row in cursor.fetchall():
                cluster_id, name, desc, centroid_json, char_json = row
                self.cluster_profiles[cluster_id] = {
                    'name': name,
                    'description': desc,
                    'centroid': json.loads(centroid_json),
                    'characteristics': json.loads(char_json) if char_json else {}
                }
    
    def extract_session_features(self, session_data: Dict) -> np.ndarray:
        """Extract features from session"""
        features = []
        
        # Temporal features
        duration_min = session_data.get('duration_minutes', 0)
        features.append(min(duration_min / 60, 1.0))  # Normalize to hours
        
        hour = session_data.get('start_hour', 12)
        features.append(hour / 24.0)
        features.append(1 if 9 <= hour <= 17 else 0)  # Business hours
        features.append(session_data.get('day_of_week', 0) / 7.0)
        
        # Activity features
        num_commands = session_data.get('num_commands', 0)
        features.append(min(num_commands / 50, 1.0))
        
        commands_per_minute = num_commands / max(duration_min, 1)
        features.append(min(commands_per_minute / 5, 1.0))
        
        # Command type distribution
        cmd_types = session_data.get('command_types', {})
        features.append(cmd_types.get('automation', 0) / max(num_commands, 1))
        features.append(cmd_types.get('query', 0) / max(num_commands, 1))
        features.append(cmd_types.get('file_ops', 0) / max(num_commands, 1))
        features.append(cmd_types.get('coding', 0) / max(num_commands, 1))
        
        # Interaction style
        features.append(session_data.get('voice_usage_ratio', 0.0))
        features.append(session_data.get('error_rate', 0.0))
        features.append(session_data.get('avg_response_time', 1.0))
        
        # Expertise indicators
        features.append(session_data.get('advanced_features_used', 0) / 10.0)
        features.append(session_data.get('shortcuts_used', 0) / 10.0)
        
        return np.array(features)
    
    def add_session(self, user_id: str, session_id: str, 
                   session_data: Dict) -> int:
        """Add session to database"""
        features = self.extract_session_features(session_data)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO sessions
                (user_id, session_id, features, start_time, end_time, duration_minutes,
                 num_commands, command_types, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                session_id,
                json.dumps(features.tolist()),
                session_data.get('start_time', datetime.now().isoformat()),
                session_data.get('end_time'),
                session_data.get('duration_minutes', 0),
                session_data.get('num_commands', 0),
                json.dumps(session_data.get('command_types', {})),
                datetime.now().isoformat()
            ))
            return cursor.lastrowid
    
    def cluster_sessions(self):
        """Cluster all sessions using K-Means"""
        if not SKLEARN_AVAILABLE:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, features
                FROM sessions
            """)
            
            session_ids = []
            X = []
            
            for row in cursor.fetchall():
                session_id, features_json = row
                session_ids.append(session_id)
                X.append(json.loads(features_json))
            
            if len(X) < self.n_clusters:
                return
            
            X = np.array(X)
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Optional PCA for dimensionality reduction
            if X_scaled.shape[1] > 10:
                X_scaled = self.pca.fit_transform(X_scaled)
            
            # Cluster
            cluster_labels = self.clusterer.fit_predict(X_scaled)
            
            # Update database
            for session_id, cluster_id in zip(session_ids, cluster_labels):
                conn.execute("""
                    UPDATE sessions
                    SET cluster_id = ?
                    WHERE id = ?
                """, (int(cluster_id), session_id))
            
            self.trained = True
            
            # Analyze clusters
            self._analyze_clusters()
    
    def _analyze_clusters(self):
        """Analyze cluster characteristics"""
        with sqlite3.connect(self.db_path) as conn:
            for cluster_id in range(self.n_clusters):
                cursor = conn.execute("""
                    SELECT features, duration_minutes, num_commands, command_types
                    FROM sessions
                    WHERE cluster_id = ?
                """, (cluster_id,))
                
                features_list = []
                durations = []
                command_counts = []
                all_cmd_types = defaultdict(int)
                
                for row in cursor.fetchall():
                    features_json, duration, num_cmds, cmd_types_json = row
                    features_list.append(json.loads(features_json))
                    durations.append(duration or 0)
                    command_counts.append(num_cmds or 0)
                    
                    if cmd_types_json:
                        cmd_types = json.loads(cmd_types_json)
                        for cmd_type, count in cmd_types.items():
                            all_cmd_types[cmd_type] += count
                
                if not features_list:
                    continue
                
                # Compute cluster statistics
                features_array = np.array(features_list)
                centroid = features_array.mean(axis=0)
                
                # Characterize cluster
                avg_duration = np.mean(durations) if durations else 0
                avg_commands = np.mean(command_counts) if command_counts else 0
                
                # Determine cluster type
                cluster_type = self._determine_cluster_type(
                    avg_duration, avg_commands, all_cmd_types
                )
                
                characteristics = {
                    'avg_duration_minutes': float(avg_duration),
                    'avg_commands': float(avg_commands),
                    'commands_per_minute': float(avg_commands / max(avg_duration, 1)),
                    'dominant_command_types': dict(sorted(
                        all_cmd_types.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:3]),
                    'size': len(features_list)
                }
                
                # Save cluster profile
                conn.execute("""
                    INSERT OR REPLACE INTO clusters
                    (id, name, description, centroid, size, characteristics, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    cluster_id,
                    cluster_type['name'],
                    cluster_type['description'],
                    json.dumps(centroid.tolist()),
                    len(features_list),
                    json.dumps(characteristics),
                    datetime.now().isoformat()
                ))
                
                self.cluster_profiles[cluster_id] = {
                    'name': cluster_type['name'],
                    'description': cluster_type['description'],
                    'centroid': centroid.tolist(),
                    'characteristics': characteristics
                }
    
    def _determine_cluster_type(self, avg_duration: float, avg_commands: float,
                                cmd_types: Dict) -> Dict:
        """Determine cluster type from characteristics"""
        # High activity, long sessions
        if avg_duration > 30 and avg_commands > 50:
            return {
                'name': 'Power User',
                'description': 'Long, intensive sessions with high command usage'
            }
        
        # Short, frequent
        elif avg_duration < 5 and avg_commands < 10:
            return {
                'name': 'Quick Task',
                'description': 'Short sessions for specific quick tasks'
            }
        
        # Automation heavy
        elif cmd_types.get('automation', 0) > cmd_types.get('query', 0) * 2:
            return {
                'name': 'Automation User',
                'description': 'Focuses on automation and workflow tasks'
            }
        
        # Query heavy
        elif cmd_types.get('query', 0) > sum(cmd_types.values()) * 0.5:
            return {
                'name': 'Information Seeker',
                'description': 'Primarily uses for information queries'
            }
        
        # Coding focused
        elif cmd_types.get('coding', 0) > sum(cmd_types.values()) * 0.3:
            return {
                'name': 'Developer',
                'description': 'Development and coding activities'
            }
        
        else:
            return {
                'name': 'Casual User',
                'description': 'Balanced, moderate usage patterns'
            }
    
    def classify_user(self, user_id: str) -> Dict:
        """Classify user based on their session history"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT cluster_id, COUNT(*) as count
                FROM sessions
                WHERE user_id = ? AND cluster_id IS NOT NULL
                GROUP BY cluster_id
            """, (user_id,))
            
            cluster_dist = defaultdict(int)
            total = 0
            
            for row in cursor.fetchall():
                cluster_id, count = row
                if cluster_id is not None:
                    cluster_dist[cluster_id] = count
                    total += count
            
            if total == 0:
                return {
                    'user_id': user_id,
                    'primary_cluster': None,
                    'user_type': 'Unknown',
                    'cluster_distribution': {}
                }
            
            # Normalize distribution
            cluster_dist_norm = {
                k: v / total for k, v in cluster_dist.items()
            }
            
            # Primary cluster
            primary = max(cluster_dist.items(), key=lambda x: x[1])[0]
            
            # User type based on primary cluster
            profile = self.cluster_profiles.get(primary, {})
            user_type = profile.get('name', 'Unknown')
            
            result = {
                'user_id': user_id,
                'primary_cluster': primary,
                'user_type': user_type,
                'cluster_distribution': cluster_dist_norm,
                'total_sessions': total
            }
            
            # Save classification
            conn.execute("""
                INSERT OR REPLACE INTO user_clusters
                (user_id, primary_cluster, cluster_distribution, user_type, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                primary,
                json.dumps(cluster_dist_norm),
                user_type,
                datetime.now().isoformat()
            ))
            
            return result
    
    def get_cluster_insights(self) -> List[Dict]:
        """Get insights about all clusters"""
        insights = []
        
        for cluster_id, profile in self.cluster_profiles.items():
            insights.append({
                'cluster_id': cluster_id,
                'name': profile['name'],
                'description': profile['description'],
                'characteristics': profile.get('characteristics', {}),
                'size': profile.get('characteristics', {}).get('size', 0)
            })
        
        insights.sort(key=lambda x: x['size'], reverse=True)
        return insights
    
    def get_stats(self) -> Dict:
        """Get clustering statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(DISTINCT user_id) as users,
                    COUNT(*) as sessions,
                    COUNT(DISTINCT cluster_id) as clusters_used,
                    AVG(duration_minutes) as avg_duration,
                    AVG(num_commands) as avg_commands
                FROM sessions
                WHERE cluster_id IS NOT NULL
            """)
            
            row = cursor.fetchone()
            if row:
                return {
                    'total_users': row[0] or 0,
                    'total_sessions': row[1] or 0,
                    'clusters_identified': row[2] or 0,
                    'avg_session_duration': row[3] or 0,
                    'avg_commands_per_session': row[4] or 0,
                    'model_trained': self.trained if SKLEARN_AVAILABLE else False
                }
        
        return {}


def example_usage():
    """Demonstrate behavior clustering"""
    clusterer = BehaviorClusterer(n_clusters=3)
    
    print("Behavior Clustering Demo\n" + "="*50)
    
    # Add sample sessions
    print("\n1. Adding sample sessions...")
    
    sessions = [
        # Power user
        {'duration_minutes': 45, 'num_commands': 80, 'start_hour': 10,
         'command_types': {'automation': 40, 'coding': 30, 'query': 10}},
        {'duration_minutes': 60, 'num_commands': 100, 'start_hour': 14,
         'command_types': {'automation': 50, 'coding': 40, 'query': 10}},
        
        # Casual user
        {'duration_minutes': 10, 'num_commands': 15, 'start_hour': 20,
         'command_types': {'query': 10, 'automation': 5}},
        {'duration_minutes': 8, 'num_commands': 12, 'start_hour': 19,
         'command_types': {'query': 8, 'automation': 4}},
        
        # Developer
        {'duration_minutes': 30, 'num_commands': 40, 'start_hour': 11,
         'command_types': {'coding': 30, 'file_ops': 8, 'query': 2}},
        {'duration_minutes': 35, 'num_commands': 45, 'start_hour': 15,
         'command_types': {'coding': 35, 'file_ops': 7, 'query': 3}},
    ]
    
    for i, session_data in enumerate(sessions):
        user_type = 'power' if i < 2 else 'casual' if i < 4 else 'dev'
        clusterer.add_session(f'user_{user_type}', f'session_{i}', session_data)
    
    # Cluster sessions
    print("2. Clustering sessions...")
    if SKLEARN_AVAILABLE:
        clusterer.cluster_sessions()
        print("✅ Clustering complete")
    
    # Get insights
    print("\n3. Cluster Insights:")
    insights = clusterer.get_cluster_insights()
    for insight in insights:
        print(f"\n  {insight['name']} (Cluster {insight['cluster_id']})")
        print(f"    {insight['description']}")
        print(f"    Size: {insight['size']} sessions")
        if insight['characteristics']:
            print(f"    Avg duration: {insight['characteristics'].get('avg_duration_minutes', 0):.1f} min")
            print(f"    Avg commands: {insight['characteristics'].get('avg_commands', 0):.1f}")
    
    # Classify users
    print("\n4. User Classifications:")
    for user_id in ['user_power', 'user_casual', 'user_dev']:
        classification = clusterer.classify_user(user_id)
        print(f"  {user_id}: {classification['user_type']}")
    
    # Stats
    stats = clusterer.get_stats()
    print(f"\n5. Statistics:")
    print(f"  Total sessions: {stats['total_sessions']}")
    print(f"  Clusters: {stats['clusters_identified']}")


if __name__ == "__main__":
    example_usage()
