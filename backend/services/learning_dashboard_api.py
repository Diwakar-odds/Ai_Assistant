# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Learning Dashboard API Helper
Provides comprehensive learning statistics, database info, and history
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class LearningDashboardAPI:
    """Provides data for the learning dashboard"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.databases = self._get_all_databases()
    
    def _get_all_databases(self) -> List[Dict]:
        """Get list of all learning databases"""
        db_files = list(self.data_dir.glob("*.db"))
        
        databases = []
        for db_path in db_files:
            try:
                size = db_path.stat().st_size
                databases.append({
                    'name': db_path.name,
                    'path': str(db_path),
                    'size_kb': round(size / 1024, 2),
                    'size_mb': round(size / 1024 / 1024, 2)
                })
            except Exception as e:
                logger.error(f"Error reading {db_path.name}: {e}")
        
        return sorted(databases, key=lambda x: x['size_kb'], reverse=True)
    
    def get_dashboard_data(self) -> Dict:
        """Get complete dashboard data"""
        return {
            'summary': self.get_summary_stats(),
            'databases': self.get_database_stats(),
            'recent_activity': self.get_recent_activity(),
            'growth_trend': self.get_growth_trend(),
            'system_breakdown': self.get_system_breakdown()
        }
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics"""
        total_size = sum(db['size_kb'] for db in self.databases)
        
        # Count records in key databases
        memory_records = self._count_records('memory.db', 'enhanced_memory')
        learning_records = self._count_records('enhanced_learning.db', 'knowledge_nodes')
        
        return {
            'total_databases': len(self.databases),
            'total_size_mb': round(total_size / 1024, 2),
            'total_conversations': self._count_records('memory.db', 'memory'),
            'enhanced_records': memory_records,
            'learning_nodes': learning_records,
            'active_systems': self._count_active_systems(),
            'last_updated': datetime.now().isoformat()
        }
    
    def get_database_stats(self) -> List[Dict]:
        """Get detailed stats for each database"""
        stats = []
        
        for db_info in self.databases:
            db_path = Path(db_info['path'])
            if not db_path.exists():
                continue
            
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                # Get tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                total_records = 0
                table_info = []
                
                for (table_name,) in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    total_records += count
                    
                    if count > 0:
                        table_info.append({
                            'name': table_name,
                            'records': count
                        })
                
                conn.close()
                
                stats.append({
                    'database': db_info['name'],
                    'size_kb': db_info['size_kb'],
                    'total_records': total_records,
                    'tables': table_info,
                    'has_data': total_records > 0
                })
            except Exception as e:
                stats.append({
                    'database': db_info['name'],
                    'size_kb': db_info['size_kb'],
                    'error': str(e),
                    'has_data': False
                })
        
        return sorted(stats, key=lambda x: x.get('total_records', 0), reverse=True)
    
    def get_recent_activity(self, limit: int = 10) -> List[Dict]:
        """Get recent learning activity"""
        activities = []
        
        # Get recent conversations
        memory_db = self.data_dir / 'memory.db'
        if memory_db.exists():
            try:
                conn = sqlite3.connect(str(memory_db))
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT timestamp, speaker, content, importance_level, category
                    FROM enhanced_memory
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                
                for row in cursor.fetchall():
                    activities.append({
                        'timestamp': row[0],
                        'type': 'conversation',
                        'speaker': row[1],
                        'content': row[2][:100],
                        'importance': row[3],
                        'category': row[4]
                    })
                
                conn.close()
            except Exception as e:
                logger.error(f"Error getting recent activity: {e}")
        
        return activities
    
    def get_growth_trend(self, days: int = 30) -> Dict:
        """Get growth trend over time"""
        daily_stats = []
        
        memory_db = self.data_dir / 'memory.db'
        if not memory_db.exists():
            return {'daily': [], 'weekly': [], 'monthly': []}
        
        try:
            conn = sqlite3.connect(str(memory_db))
            cursor = conn.cursor()
            
            # Get daily conversation counts
            cursor.execute("""
                SELECT DATE(timestamp) as date, COUNT(*) as count
                FROM enhanced_memory
                WHERE timestamp >= date('now', '-30 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """)
            
            for row in cursor.fetchall():
                daily_stats.append({
                    'date': row[0],
                    'conversations': row[1]
                })
            
            conn.close()
        except Exception as e:
            logger.error(f"Error getting growth trend: {e}")
        
        return {
            'daily': daily_stats[:7],  # Last 7 days
            'weekly': self._aggregate_weekly(daily_stats),
            'monthly': self._aggregate_monthly(daily_stats)
        }
    
    def get_system_breakdown(self) -> List[Dict]:
        """Get breakdown by learning system"""
        systems = [
            {'name': 'Memory System', 'db': 'memory.db', 'table': 'enhanced_memory'},
            {'name': 'Enhanced Learning', 'db': 'enhanced_learning.db', 'table': 'knowledge_nodes'},
            {'name': 'Behavior Clustering', 'db': 'behavior_clustering.db', 'table': 'sessions'},
            {'name': 'Conversation Clustering', 'db': 'conversation_clustering.db', 'table': 'conversations'},
            {'name': 'Command Sequences', 'db': 'command_sequences.db', 'table': 'transitions'},
            {'name': 'Command Success', 'db': 'command_success.db', 'table': 'commands'},
            {'name': 'Smart Commands', 'db': 'smart_commands.db', 'table': 'examples'},
            {'name': 'Context Responses', 'db': 'context_aware_responses.db', 'table': 'contexts'},
            {'name': 'Query Cache', 'db': 'query_cache.db', 'table': 'queries'},
            {'name': 'Knowledge Graph', 'db': 'personal_knowledge.db', 'table': 'facts'},
        ]
        
        breakdown = []
        for system in systems:
            db_path = self.data_dir / system['db']
            records = 0
            status = 'inactive'
            
            if db_path.exists():
                records = self._count_records(system['db'], system['table'])
                status = 'active' if records > 0 else 'empty'
            
            breakdown.append({
                'name': system['name'],
                'database': system['db'],
                'records': records,
                'status': status
            })
        
        return breakdown
    
    def search_memory(self, query: str, limit: int = 20) -> List[Dict]:
        """Search memory database"""
        results = []
        memory_db = self.data_dir / 'memory.db'
        
        if not memory_db.exists():
            return results
        
        try:
            conn = sqlite3.connect(str(memory_db))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT timestamp, speaker, content, importance_level, category
                FROM enhanced_memory
                WHERE content LIKE ?
                ORDER BY importance_level DESC, timestamp DESC
                LIMIT ?
            """, (f'%{query}%', limit))
            
            for row in cursor.fetchall():
                results.append({
                    'timestamp': row[0],
                    'speaker': row[1],
                    'content': row[2],
                    'importance': row[3],
                    'category': row[4]
                })
            
            conn.close()
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
        
        return results
    
    def get_database_content(self, db_name: str, table_name: str, 
                           limit: int = 50, offset: int = 0) -> Dict:
        """Get content from a specific database table"""
        db_path = self.data_dir / db_name
        
        if not db_path.exists():
            return {'error': 'Database not found'}
        
        try:
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get column names
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            
            # Get total count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total = cursor.fetchone()[0]
            
            # Get data
            cursor.execute(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (limit, offset))
            rows = cursor.fetchall()
            
            data = []
            for row in rows:
                data.append(dict(row))
            
            conn.close()
            
            return {
                'columns': columns,
                'data': data,
                'total': total,
                'limit': limit,
                'offset': offset
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _count_records(self, db_name: str, table_name: str) -> int:
        """Count records in a table"""
        db_path = self.data_dir / db_name
        if not db_path.exists():
            return 0
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0
    
    def _count_active_systems(self) -> int:
        """Count how many learning systems have data"""
        active = 0
        for db in self.databases:
            db_path = Path(db['path'])
            if db_path.exists():
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    
                    for (table,) in tables:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        if cursor.fetchone()[0] > 0:
                            active += 1
                            break
                    
                    conn.close()
                except Exception:
                    pass
        
        return active
    
    def _aggregate_weekly(self, daily_stats: List[Dict]) -> List[Dict]:
        """Aggregate daily stats to weekly"""
        # Simple implementation - can be enhanced
        return daily_stats[:4] if len(daily_stats) > 0 else []
    
    def _aggregate_monthly(self, daily_stats: List[Dict]) -> List[Dict]:
        """Aggregate daily stats to monthly"""
        # Simple implementation - can be enhanced
        return daily_stats[:1] if len(daily_stats) > 0 else []


if __name__ == "__main__":
    api = LearningDashboardAPI()
    dashboard = api.get_dashboard_data()
    print(json.dumps(dashboard, indent=2))
