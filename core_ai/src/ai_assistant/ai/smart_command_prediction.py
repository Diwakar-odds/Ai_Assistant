"""
Smart Command Prediction (Application)
Intelligent command suggestion and completion
"""

import numpy as np
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class SmartCommandPredictor:
    """
    Application-level intelligent command prediction
    Suggests commands based on context, history, and patterns
    """
    
    def __init__(self, db_path: str = "data/automation/smart_commands.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        self.command_history = []
        self.context_patterns = defaultdict(list)
        self.time_patterns = defaultdict(Counter)
        self.sequence_patterns = defaultdict(Counter)
        
        self._load_patterns()
        
        logger.info("Smart Command Predictor initialized")
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS command_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    command TEXT,
                    context TEXT,
                    hour INTEGER,
                    day_of_week INTEGER,
                    success INTEGER
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS command_sequences (
                    prev_command TEXT,
                    next_command TEXT,
                    count INTEGER,
                    last_seen TEXT,
                    PRIMARY KEY (prev_command, next_command)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    context TEXT,
                    predicted_commands TEXT,
                    selected_command TEXT,
                    prediction_correct INTEGER
                )
            """)
    
    def _load_patterns(self):
        """Load patterns from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Load command sequences
            cursor.execute("SELECT prev_command, next_command, count FROM command_sequences")
            for prev, next_cmd, count in cursor.fetchall():
                self.sequence_patterns[prev][next_cmd] = count
            
            # Load time patterns
            cursor.execute("""
                SELECT command, hour, COUNT(*) 
                FROM command_usage 
                GROUP BY command, hour
            """)
            for command, hour, count in cursor.fetchall():
                self.time_patterns[(command, hour)] = count
    
    def log_command(self, command: str, context: Dict = None, success: bool = True):
        """Log command usage"""
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO command_usage (timestamp, command, context, hour, day_of_week, success)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                now.isoformat(),
                command,
                json.dumps(context or {}),
                now.hour,
                now.weekday(),
                1 if success else 0
            ))
        
        # Update sequence patterns
        if self.command_history:
            prev_command = self.command_history[-1]
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO command_sequences (prev_command, next_command, count, last_seen)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(prev_command, next_command) DO UPDATE SET
                        count = count + 1,
                        last_seen = ?
                """, (prev_command, command, now.isoformat(), now.isoformat()))
            
            self.sequence_patterns[prev_command][command] += 1
        
        self.command_history.append(command)
        if len(self.command_history) > 100:
            self.command_history.pop(0)
    
    def predict_next_commands(self, 
                             context: Optional[Dict] = None,
                             top_k: int = 5) -> List[Tuple[str, float]]:
        """Predict most likely next commands"""
        scores = defaultdict(float)
        
        # Score based on sequence patterns
        if self.command_history:
            last_command = self.command_history[-1]
            if last_command in self.sequence_patterns:
                total = sum(self.sequence_patterns[last_command].values())
                for cmd, count in self.sequence_patterns[last_command].items():
                    scores[cmd] += 0.4 * (count / total)
        
        # Score based on time patterns
        current_hour = datetime.now().hour
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT command, COUNT(*) as freq
                FROM command_usage
                WHERE hour = ? AND success = 1
                GROUP BY command
                ORDER BY freq DESC
                LIMIT 10
            """, (current_hour,))
            
            hour_commands = cursor.fetchall()
            if hour_commands:
                total = sum(freq for _, freq in hour_commands)
                for cmd, freq in hour_commands:
                    scores[cmd] += 0.3 * (freq / total)
        
        # Score based on recent frequency
        recent_commands = Counter(self.command_history[-20:])
        if recent_commands:
            total = sum(recent_commands.values())
            for cmd, count in recent_commands.items():
                scores[cmd] += 0.2 * (count / total)
        
        # Score based on context
        if context:
            context_str = json.dumps(context)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT command, COUNT(*) as freq
                    FROM command_usage
                    WHERE context LIKE ?
                    GROUP BY command
                    LIMIT 5
                """, (f"%{context.get('keyword', '')}%",))
                
                context_commands = cursor.fetchall()
                if context_commands:
                    total = sum(freq for _, freq in context_commands)
                    for cmd, freq in context_commands:
                        scores[cmd] += 0.1 * (freq / total)
        
        # Sort and return top k
        sorted_predictions = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_predictions[:top_k]
    
    def autocomplete_command(self, partial: str) -> List[str]:
        """Autocomplete command based on partial input"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT command, COUNT(*) as freq
                FROM command_usage
                WHERE command LIKE ? AND success = 1
                GROUP BY command
                ORDER BY freq DESC
                LIMIT 10
            """, (f"{partial}%",))
            
            matches = [row[0] for row in cursor.fetchall()]
            return matches
    
    def get_popular_commands(self, time_range_hours: int = 24, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most popular commands in time range"""
        cutoff = datetime.now() - timedelta(hours=time_range_hours)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT command, COUNT(*) as freq
                FROM command_usage
                WHERE timestamp > ? AND success = 1
                GROUP BY command
                ORDER BY freq DESC
                LIMIT ?
            """, (cutoff.isoformat(), limit))
            
            return cursor.fetchall()
    
    def get_stats(self) -> Dict:
        """Get statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM command_usage")
            total_commands = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM command_usage WHERE success = 1")
            successful_commands = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT command) FROM command_usage")
            unique_commands = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM predictions WHERE prediction_correct = 1")
            correct_predictions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM predictions")
            total_predictions = cursor.fetchone()[0]
        
        return {
            'total_commands': total_commands,
            'successful_commands': successful_commands,
            'unique_commands': unique_commands,
            'success_rate': successful_commands / max(total_commands, 1),
            'prediction_accuracy': correct_predictions / max(total_predictions, 1),
            'sequence_patterns': len(self.sequence_patterns)
        }
