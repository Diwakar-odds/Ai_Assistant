"""
Adaptive Voice Recognition (Application)
Voice model adaptation for better recognition
"""

import numpy as np
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class AdaptiveVoiceRecognition:
    """
    Application-level adaptive voice recognition
    Learns user's voice patterns and improves accuracy
    """
    
    def __init__(self, db_path: str = "data/adaptive_voice.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
        self.user_vocabulary = defaultdict(int)
        self.pronunciation_variants = defaultdict(list)
        self.correction_history = []
        self.accent_profile = {}
        
        self._load_adaptations()
        
        logger.info("Adaptive Voice Recognition initialized")
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recognition_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    audio_hash TEXT,
                    recognized_text TEXT,
                    confidence REAL,
                    corrected_text TEXT,
                    correction_source TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_vocabulary (
                    word TEXT PRIMARY KEY,
                    frequency INTEGER,
                    last_used TEXT,
                    pronunciation_variants TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS accent_profile (
                    phoneme TEXT PRIMARY KEY,
                    common_substitutions TEXT,
                    confidence REAL
                )
            """)
    
    def _load_adaptations(self):
        """Load user-specific adaptations"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Load vocabulary
            cursor.execute("SELECT word, frequency FROM user_vocabulary")
            for word, freq in cursor.fetchall():
                self.user_vocabulary[word] = freq
            
            logger.info(f"Loaded {len(self.user_vocabulary)} vocabulary items")
    
    def log_recognition(self, 
                       audio_hash: str,
                       recognized_text: str,
                       confidence: float):
        """Log voice recognition result"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO recognition_logs 
                (timestamp, audio_hash, recognized_text, confidence)
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                audio_hash,
                recognized_text,
                confidence
            ))
        
        # Update vocabulary
        for word in recognized_text.lower().split():
            self.user_vocabulary[word] += 1
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO user_vocabulary (word, frequency, last_used)
                    VALUES (?, 1, ?)
                    ON CONFLICT(word) DO UPDATE SET
                        frequency = frequency + 1,
                        last_used = ?
                """, (word, datetime.now().isoformat(), datetime.now().isoformat()))
    
    def apply_correction(self,
                        audio_hash: str,
                        corrected_text: str,
                        source: str = "user"):
        """Apply user correction to improve model"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE recognition_logs
                SET corrected_text = ?, correction_source = ?
                WHERE audio_hash = ?
            """, (corrected_text, source, audio_hash))
        
        self.correction_history.append({
            'audio_hash': audio_hash,
            'corrected_text': corrected_text,
            'timestamp': datetime.now().isoformat()
        })
        
        # Learn from correction
        self._learn_from_correction(audio_hash, corrected_text)
    
    def _learn_from_correction(self, audio_hash: str, corrected_text: str):
        """Learn patterns from user corrections"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT recognized_text FROM recognition_logs
                WHERE audio_hash = ?
            """, (audio_hash,))
            
            result = cursor.fetchone()
            if result:
                recognized = result[0]
                
                # Identify substitution patterns
                recognized_words = recognized.lower().split()
                corrected_words = corrected_text.lower().split()
                
                # Store pronunciation variants
                for rec_word, corr_word in zip(recognized_words, corrected_words):
                    if rec_word != corr_word:
                        self.pronunciation_variants[corr_word].append(rec_word)
    
    def get_vocabulary_boost(self) -> List[str]:
        """Get user's frequently used words for recognition boost"""
        # Return top frequent words
        sorted_words = sorted(
            self.user_vocabulary.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [word for word, _ in sorted_words[:100]]
    
    def suggest_corrections(self, recognized_text: str) -> List[str]:
        """Suggest potential corrections based on user patterns"""
        suggestions = []
        words = recognized_text.lower().split()
        
        for i, word in enumerate(words):
            # Check pronunciation variants
            for correct_word, variants in self.pronunciation_variants.items():
                if word in variants:
                    # Suggest replacement
                    new_words = words.copy()
                    new_words[i] = correct_word
                    suggestions.append(' '.join(new_words))
        
        return suggestions[:3]
    
    def get_confidence_adjustment(self, recognized_text: str) -> float:
        """Adjust confidence based on user vocabulary"""
        words = recognized_text.lower().split()
        known_words = sum(1 for w in words if w in self.user_vocabulary)
        
        if len(words) == 0:
            return 1.0
        
        # Boost confidence if many words are in user vocabulary
        vocabulary_ratio = known_words / len(words)
        adjustment = 1.0 + 0.2 * vocabulary_ratio
        
        return min(adjustment, 1.5)
    
    def analyze_accent_patterns(self) -> Dict:
        """Analyze user's accent patterns"""
        patterns = defaultdict(Counter)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT recognized_text, corrected_text
                FROM recognition_logs
                WHERE corrected_text IS NOT NULL
            """)
            
            for recognized, corrected in cursor.fetchall():
                if recognized and corrected:
                    # Simple character-level analysis
                    for r_char, c_char in zip(recognized.lower(), corrected.lower()):
                        if r_char != c_char:
                            patterns[c_char][r_char] += 1
        
        return dict(patterns)
    
    def get_stats(self) -> Dict:
        """Get statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM recognition_logs")
            total_recognitions = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM recognition_logs WHERE corrected_text IS NOT NULL")
            total_corrections = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(confidence) FROM recognition_logs")
            avg_confidence = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM user_vocabulary")
            vocabulary_size = cursor.fetchone()[0]
        
        return {
            'total_recognitions': total_recognitions,
            'total_corrections': total_corrections,
            'correction_rate': total_corrections / max(total_recognitions, 1),
            'avg_confidence': float(avg_confidence) if avg_confidence else 0,
            'vocabulary_size': vocabulary_size,
            'pronunciation_variants': len(self.pronunciation_variants)
        }
