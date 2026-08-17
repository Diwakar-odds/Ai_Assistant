"""
Workflow Recommender (Application)
Intelligent workflow optimization and recommendations
"""

import numpy as np
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class WorkflowRecommender:
    """
    Application-level workflow recommendation system
    Suggests optimal workflows and automation opportunities
    """
    
    def __init__(self, db_path: str = "data/workflow_recommender.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        self.workflow_patterns = defaultdict(list)
        self.task_sequences = []
        self.efficiency_metrics = {}
        
        logger.info("Workflow Recommender initialized")
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT UNIQUE,
                    name TEXT,
                    description TEXT,
                    steps TEXT,
                    avg_duration REAL,
                    success_rate REAL,
                    usage_count INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT,
                    timestamp TEXT,
                    duration REAL,
                    success INTEGER,
                    context TEXT,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(workflow_id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    context TEXT,
                    recommended_workflow TEXT,
                    reason TEXT,
                    accepted INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS automation_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identified_at TEXT,
                    pattern_description TEXT,
                    estimated_time_saving REAL,
                    confidence REAL,
                    implemented INTEGER
                )
            """)
    
    def register_workflow(self,
                         workflow_id: str,
                         name: str,
                         steps: List[str],
                         description: str = ""):
        """Register a workflow"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO workflows 
                (workflow_id, name, description, steps, avg_duration, success_rate, usage_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow_id,
                name,
                description,
                json.dumps(steps),
                0.0,
                1.0,
                0
            ))
        
        logger.info(f"Workflow registered: {workflow_id}")
    
    def log_workflow_execution(self,
                              workflow_id: str,
                              duration: float,
                              success: bool,
                              context: Optional[Dict] = None):
        """Log workflow execution"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO workflow_executions 
                (workflow_id, timestamp, duration, success, context)
                VALUES (?, ?, ?, ?, ?)
            """, (
                workflow_id,
                datetime.now().isoformat(),
                duration,
                1 if success else 0,
                json.dumps(context or {})
            ))
            
            # Update workflow stats
            conn.execute("""
                UPDATE workflows
                SET usage_count = usage_count + 1
                WHERE workflow_id = ?
            """, (workflow_id,))
        
        self.task_sequences.append({
            'workflow_id': workflow_id,
            'timestamp': datetime.now(),
            'duration': duration,
            'success': success
        })
    
    def recommend_workflow(self, context: Dict) -> List[Tuple[str, float, str]]:
        """Recommend workflows based on context"""
        recommendations = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get workflows sorted by success rate and usage
            cursor.execute("""
                SELECT workflow_id, name, success_rate, usage_count
                FROM workflows
                WHERE usage_count > 0
                ORDER BY success_rate DESC, usage_count DESC
                LIMIT 5
            """)
            
            workflows = cursor.fetchall()
            
            for wf_id, name, success_rate, usage_count in workflows:
                # Score based on multiple factors
                score = success_rate * 0.6 + (usage_count / 100) * 0.4
                
                # Context matching
                cursor.execute("""
                    SELECT COUNT(*) FROM workflow_executions
                    WHERE workflow_id = ? AND context LIKE ?
                """, (wf_id, f"%{context.get('task_type', '')}%"))
                
                context_matches = cursor.fetchone()[0]
                if context_matches > 0:
                    score += 0.2
                
                reason = f"Success rate: {success_rate:.1%}, Used {usage_count} times"
                recommendations.append((wf_id, score, reason))
        
        # Sort by score
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations[:3]
    
    def identify_automation_opportunities(self) -> List[Dict]:
        """Identify repetitive patterns that can be automated"""
        opportunities = []
        
        # Analyze recent task sequences
        if len(self.task_sequences) < 10:
            return opportunities
        
        # Look for repeated sequences
        sequence_counts = defaultdict(int)
        for i in range(len(self.task_sequences) - 2):
            seq = tuple(t['workflow_id'] for t in self.task_sequences[i:i+3])
            sequence_counts[seq] += 1
        
        # Identify frequent sequences
        for sequence, count in sequence_counts.items():
            if count >= 3:  # Repeated at least 3 times
                avg_duration = np.mean([
                    t['duration'] for t in self.task_sequences 
                    if t['workflow_id'] in sequence
                ])
                
                opportunity = {
                    'pattern': ' → '.join(sequence),
                    'frequency': count,
                    'potential_time_saving': avg_duration * count * 0.7,  # 70% automation
                    'confidence': min(count / 10, 0.9)
                }
                opportunities.append(opportunity)
                
                # Save to database
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT INTO automation_opportunities 
                        (identified_at, pattern_description, estimated_time_saving, confidence, implemented)
                        VALUES (?, ?, ?, ?, 0)
                    """, (
                        datetime.now().isoformat(),
                        opportunity['pattern'],
                        opportunity['potential_time_saving'],
                        opportunity['confidence']
                    ))
        
        return opportunities
    
    def suggest_workflow_optimization(self, workflow_id: str) -> List[str]:
        """Suggest optimizations for a workflow"""
        suggestions = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get workflow executions
            cursor.execute("""
                SELECT duration, success FROM workflow_executions
                WHERE workflow_id = ?
                ORDER BY timestamp DESC
                LIMIT 20
            """, (workflow_id,))
            
            executions = cursor.fetchall()
            
            if len(executions) < 3:
                return ["Not enough data for optimization suggestions"]
            
            durations = [d for d, s in executions if s == 1]
            success_rate = sum(s for _, s in executions) / len(executions)
            
            if durations:
                avg_duration = np.mean(durations)
                std_duration = np.std(durations)
                
                # High variance suggests inconsistency
                if std_duration > avg_duration * 0.3:
                    suggestions.append("High variance in execution time - consider standardizing steps")
                
                # Long duration
                if avg_duration > 60:
                    suggestions.append(f"Average duration {avg_duration:.1f}s - look for parallelization opportunities")
            
            # Low success rate
            if success_rate < 0.8:
                suggestions.append(f"Success rate {success_rate:.1%} - review error-prone steps")
            
            # Check for common failures
            cursor.execute("""
                SELECT context FROM workflow_executions
                WHERE workflow_id = ? AND success = 0
                LIMIT 5
            """, (workflow_id,))
            
            failures = cursor.fetchall()
            if failures:
                suggestions.append("Recent failures detected - review error logs")
        
        return suggestions if suggestions else ["Workflow performing optimally"]
    
    def get_workflow_analytics(self, workflow_id: str) -> Dict:
        """Get detailed analytics for a workflow"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*), AVG(duration), AVG(success)
                FROM workflow_executions
                WHERE workflow_id = ?
            """, (workflow_id,))
            
            count, avg_duration, success_rate = cursor.fetchone()
            
            # Get recent trend
            cursor.execute("""
                SELECT timestamp, duration, success
                FROM workflow_executions
                WHERE workflow_id = ?
                ORDER BY timestamp DESC
                LIMIT 10
            """, (workflow_id,))
            
            recent = cursor.fetchall()
        
        return {
            'workflow_id': workflow_id,
            'total_executions': count or 0,
            'avg_duration': float(avg_duration) if avg_duration else 0,
            'success_rate': float(success_rate) if success_rate else 0,
            'recent_executions': len(recent)
        }
    
    def get_stats(self) -> Dict:
        """Get statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM workflows")
            total_workflows = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM workflow_executions")
            total_executions = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(success) FROM workflow_executions")
            overall_success_rate = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM automation_opportunities WHERE implemented = 0")
            pending_opportunities = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(estimated_time_saving) FROM automation_opportunities WHERE implemented = 0")
            potential_savings = cursor.fetchone()[0]
        
        return {
            'total_workflows': total_workflows,
            'total_executions': total_executions,
            'overall_success_rate': float(overall_success_rate) if overall_success_rate else 0,
            'pending_opportunities': pending_opportunities,
            'potential_time_savings': float(potential_savings) if potential_savings else 0
        }
