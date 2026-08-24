# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Markov Chain Command Sequence Predictor
Predicts next likely command based on command history

Features:
- N-gram transition matrices (2-gram, 3-gram)
- Time-aware predictions
- Context-conditional transitions
- Confidence scoring
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
from pathlib import Path
import math


class CommandMarkovChain:
    """
    Predicts next command using Markov chain models
    """
    
    def __init__(self, db_path: str = "data/automation/command_sequences.db",
                 order: int = 2,
                 context_aware: bool = True):
        self.db_path = db_path
        self.order = order  # N-gram order (2 = bigram, 3 = trigram)
        self.context_aware = context_aware
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Transition matrices
        self.transitions = defaultdict(Counter)  # state -> {next_command: count}
        self.context_transitions = defaultdict(lambda: defaultdict(Counter))
        
        # Command history buffer
        self.history_buffer = []
        
        self._init_database()
        self._load_transitions()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS command_sequences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    command TEXT NOT NULL,
                    context TEXT,
                    timestamp TEXT NOT NULL,
                    session_id TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transition_matrix (
                    state TEXT NOT NULL,
                    next_command TEXT NOT NULL,
                    context TEXT,
                    count INTEGER DEFAULT 1,
                    confidence REAL DEFAULT 0.0,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (state, next_command, context)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    current_state TEXT NOT NULL,
                    predicted_command TEXT NOT NULL,
                    actual_command TEXT,
                    confidence REAL NOT NULL,
                    was_correct INTEGER,
                    timestamp TEXT NOT NULL
                )
            """)
    
    def _load_transitions(self):
        """Load transition matrix from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT state, next_command, context, count
                FROM transition_matrix
            """)
            
            for row in cursor.fetchall():
                state, next_cmd, context_str, count = row
                
                if context_str:
                    context = json.loads(context_str)
                    context_key = self._serialize_context(context)
                    self.context_transitions[context_key][state][next_cmd] = count
                else:
                    self.transitions[state][next_cmd] = count
    
    def _serialize_context(self, context: Dict) -> str:
        """Serialize context dict to string key"""
        if not context:
            return "default"
        
        # Extract key context features
        features = []
        for key in ['time_of_day', 'day_of_week', 'location', 'app']:
            if key in context:
                features.append(f"{key}={context[key]}")
        
        return "|".join(features) if features else "default"
    
    def _get_state(self, history: List[str]) -> str:
        """Create state from command history"""
        if len(history) == 0:
            return "<START>"
        
        # Use last N commands as state
        state_commands = history[-self.order:]
        return " -> ".join(state_commands)
    
    def record_command(self, command: str, context: Optional[Dict] = None,
                      user_id: str = "default", session_id: Optional[str] = None):
        """Record a command in the sequence"""
        now = datetime.now()
        
        # Add to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO command_sequences
                (user_id, command, context, timestamp, session_id)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                command,
                json.dumps(context) if context else None,
                now.isoformat(),
                session_id
            ))
        
        # Update transition matrix
        if len(self.history_buffer) > 0:
            state = self._get_state(self.history_buffer)
            
            if self.context_aware and context:
                context_key = self._serialize_context(context)
                self.context_transitions[context_key][state][command] += 1
                
                # Save to database
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO transition_matrix
                        (state, next_command, context, count, last_updated)
                        VALUES (
                            ?, ?, ?,
                            COALESCE((SELECT count + 1 FROM transition_matrix 
                                     WHERE state=? AND next_command=? AND context=?), 1),
                            ?
                        )
                    """, (
                        state, command, json.dumps(context),
                        state, command, json.dumps(context),
                        now.isoformat()
                    ))
            else:
                self.transitions[state][command] += 1
                
                # Save to database
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("""
                        INSERT OR REPLACE INTO transition_matrix
                        (state, next_command, context, count, last_updated)
                        VALUES (
                            ?, ?, NULL,
                            COALESCE((SELECT count + 1 FROM transition_matrix 
                                     WHERE state=? AND next_command=? AND context IS NULL), 1),
                            ?
                        )
                    """, (state, command, state, command, now.isoformat()))
        
        # Update history buffer
        self.history_buffer.append(command)
        
        # Keep buffer limited
        if len(self.history_buffer) > 10:
            self.history_buffer.pop(0)
    
    def predict_next(self, current_history: Optional[List[str]] = None,
                    context: Optional[Dict] = None,
                    top_k: int = 5) -> List[Dict]:
        """
        Predict next likely commands
        
        Returns:
            List of dicts with 'command', 'confidence', 'count'
        """
        history = current_history if current_history else self.history_buffer
        
        if len(history) == 0:
            return []
        
        state = self._get_state(history)
        
        # Get transitions for this state
        if self.context_aware and context:
            context_key = self._serialize_context(context)
            next_counts = self.context_transitions[context_key].get(state, Counter())
        else:
            next_counts = self.transitions.get(state, Counter())
        
        if not next_counts:
            return []
        
        # Calculate probabilities
        total = sum(next_counts.values())
        predictions = []
        
        for command, count in next_counts.most_common(top_k):
            confidence = count / total
            predictions.append({
                'command': command,
                'confidence': confidence,
                'count': count,
                'state': state
            })
        
        return predictions
    
    def get_common_sequences(self, min_length: int = 2, 
                            min_frequency: int = 3) -> List[Dict]:
        """Find common command sequences"""
        sequences = defaultdict(int)
        
        with sqlite3.connect(self.db_path) as conn:
            # Get all commands ordered by time
            cursor = conn.execute("""
                SELECT command, timestamp, session_id
                FROM command_sequences
                ORDER BY timestamp
            """)
            
            session_commands = defaultdict(list)
            
            for row in cursor.fetchall():
                command, timestamp, session_id = row
                if session_id:
                    session_commands[session_id].append(command)
        
        # Extract n-grams
        for session_id, commands in session_commands.items():
            for i in range(len(commands) - min_length + 1):
                sequence = tuple(commands[i:i + min_length])
                sequences[sequence] += 1
        
        # Filter by frequency
        common = [
            {
                'sequence': list(seq),
                'frequency': freq,
                'length': len(seq)
            }
            for seq, freq in sequences.items()
            if freq >= min_frequency
        ]
        
        # Sort by frequency
        common.sort(key=lambda x: x['frequency'], reverse=True)
        
        return common
    
    def validate_prediction(self, predicted_command: str, actual_command: str,
                          state: str, confidence: float):
        """Record prediction accuracy"""
        was_correct = 1 if predicted_command == actual_command else 0
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO predictions
                (current_state, predicted_command, actual_command, confidence, was_correct, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                state,
                predicted_command,
                actual_command,
                confidence,
                was_correct,
                datetime.now().isoformat()
            ))
    
    def get_accuracy_stats(self) -> Dict:
        """Get prediction accuracy statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(was_correct) as correct,
                    AVG(confidence) as avg_confidence
                FROM predictions
            """)
            
            row = cursor.fetchone()
            if row and row[0] > 0:
                total, correct, avg_conf = row
                return {
                    'total_predictions': total,
                    'correct_predictions': correct,
                    'accuracy': correct / total,
                    'average_confidence': avg_conf
                }
        
        return {
            'total_predictions': 0,
            'correct_predictions': 0,
            'accuracy': 0.0,
            'average_confidence': 0.0
        }
    
    def get_stats(self) -> Dict:
        """Get command sequence statistics (alias for get_accuracy_stats)"""
        with sqlite3.connect(self.db_path) as conn:
            # Get sequence counts
            cursor = conn.execute("SELECT COUNT(*) FROM command_sequences")
            total_sequences = cursor.fetchone()[0]
            
            # Get unique commands
            cursor = conn.execute("SELECT COUNT(DISTINCT command) FROM command_sequences")
            unique_commands = cursor.fetchone()[0]
        
        # Get prediction stats
        pred_stats = self.get_accuracy_stats()
        
        return {
            'total_sequences': total_sequences,
            'unique_commands': unique_commands,
            **pred_stats
        }
    
    def clear_old_data(self, days: int = 30):
        """Remove old command sequences"""
        cutoff = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                DELETE FROM command_sequences
                WHERE timestamp < ?
            """, (cutoff.isoformat(),))


def example_usage():
    """Demonstrate command sequence prediction"""
    predictor = CommandMarkovChain(order=2)
    
    # Simulate command sequences
    sequences = [
        ["open_chrome", "search_google", "close_chrome"],
        ["open_chrome", "search_google", "open_youtube"],
        ["open_chrome", "search_google", "close_chrome"],
        ["open_vscode", "write_code", "run_tests"],
        ["open_vscode", "write_code", "run_tests"],
    ]
    
    print("Training on command sequences...")
    for seq in sequences:
        predictor.history_buffer = []  # Reset for each session
        for cmd in seq:
            predictor.record_command(
                cmd,
                context={'time_of_day': 'morning'}
            )
    
    # Predict next command
    print("\nCurrent: ['open_chrome', 'search_google']")
    predictions = predictor.predict_next(
        current_history=['open_chrome', 'search_google'],
        top_k=3
    )
    
    print("Predicted next commands:")
    for pred in predictions:
        print(f"  {pred['command']}: {pred['confidence']:.1%} (seen {pred['count']} times)")
    
    # Find common sequences
    print("\nCommon command sequences:")
    common = predictor.get_common_sequences(min_length=2, min_frequency=2)
    for seq_info in common[:5]:
        print(f"  {' -> '.join(seq_info['sequence'])}: {seq_info['frequency']} times")
    
    # Accuracy stats
    stats = predictor.get_accuracy_stats()
    print(f"\nPrediction Accuracy: {stats['accuracy']:.1%}")


if __name__ == "__main__":
    example_usage()
