# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Advanced Intent Classification and Named Entity Recognition
Uses transformer-based models with transfer learning for personalized understanding

Features:
- Intent classification with confidence scores
- Named Entity Recognition (NER) for extracting app names, dates, etc.
- User-specific vocabulary learning
- Few-shot learning for new intents
- Continuous improvement from corrections
"""

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from collections import Counter, defaultdict
from pathlib import Path
import re

# Optional advanced ML libraries
try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("⚠️ sentence-transformers not available. Using fallback intent matching.")

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import LabelEncoder
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


@dataclass
class Intent:
    """Intent classification result"""
    intent_name: str
    confidence: float
    entities: Dict[str, List[str]]
    slot_values: Dict[str, str]


@dataclass
class Entity:
    """Named entity"""
    text: str
    type: str
    start: int
    end: int
    confidence: float


class IntentClassifier:
    """
    Intent classification using semantic similarity
    Learns from user corrections and adaptsto personal vocabulary
    """
    
    def __init__(self, db_path: str = "data/intent_classifier.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Load or initialize sentence transformer
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            self.model = SentenceTransformer('all-MiniLM-L6-v2')  # Fast & good
            self.use_transformers = True
        else:
            self.model = None
            self.use_transformers = False
        
        # Intent definitions with examples
        self.intent_examples = self._initialize_intents()
        self.intent_embeddings = {}
        
        # User-specific learned patterns
        self.user_patterns = defaultdict(list)
        
        # Initialize database
        self._init_database()
        self._load_user_patterns()
        
        # Precompute embeddings
        if self.use_transformers:
            self._precompute_embeddings()
    
    def _initialize_intents(self) -> Dict[str, List[str]]:
        """Initialize intent categories with examples"""
        return {
            'open_application': [
                "open chrome",
                "launch spotify",
                "start notepad",
                "run visual studio code",
                "open calculator",
            ],
            'close_application': [
                "close browser",
                "quit chrome",
                "exit notepad",
                "kill spotify",
                "shutdown excel",
            ],
            'search_web': [
                "search for python tutorials",
                "google machine learning",
                "look up weather forecast",
                "find restaurants nearby",
                "search latest news",
            ],
            'file_operation': [
                "create new file",
                "delete old documents",
                "move files to downloads",
                "rename document",
                "organize my files",
            ],
            'system_control': [
                "increase volume",
                "lock screen",
                "shut down computer",
                "restart system",
                "sleep mode",
            ],
            'information_query': [
                "what's the weather",
                "what time is it",
                "how's my schedule",
                "check my emails",
                "show me latest news",
            ],
            'task_automation': [
                "remind me to call john",
                "schedule a meeting",
                "set timer for 10 minutes",
                "create weekly backup",
                "send email to team",
            ],
            'conversational': [
                "hello",
                "how are you",
                "thank you",
                "what can you do",
                "help me",
            ],
        }
    
    def _init_database(self):
        """Initialize database for learning"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS intent_corrections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_input TEXT NOT NULL,
                    predicted_intent TEXT NOT NULL,
                    corrected_intent TEXT NOT NULL,
                    confidence REAL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_vocabulary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_term TEXT NOT NULL,
                    user_term TEXT NOT NULL,
                    intent TEXT,
                    frequency INTEGER DEFAULT 1,
                    last_used TEXT NOT NULL
                )
            """)
    
    def _load_user_patterns(self):
        """Load learned user patterns"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT corrected_intent, user_input
                FROM intent_corrections
                WHERE timestamp > datetime('now', '-30 days')
            """)
            
            for intent, user_input in cursor.fetchall():
                self.user_patterns[intent].append(user_input)
    
    def _precompute_embeddings(self):
        """Precompute embeddings for all intent examples"""
        if not self.use_transformers:
            return
        
        for intent, examples in self.intent_examples.items():
            # Add user patterns
            all_examples = examples + self.user_patterns.get(intent, [])
            embeddings = self.model.encode(all_examples, convert_to_tensor=True)
            self.intent_embeddings[intent] = embeddings
    
    def classify(self, user_input: str) -> Intent:
        """Classify user intent"""
        if self.use_transformers:
            return self._classify_with_transformers(user_input)
        else:
            return self._classify_with_keywords(user_input)
    
    def classify_intent(self, text: str, context: dict):
        """Wrapper for compatibility - returns tuple of (intent, confidence, entities)"""
        result = self.classify(text)
        return result.intent_name, result.confidence, result.entities
    
    def _classify_with_transformers(self, user_input: str) -> Intent:
        """Classify using sentence transformers"""
        # Encode user input
        input_embedding = self.model.encode(user_input, convert_to_tensor=True)
        
        # Find most similar intent
        best_intent = None
        best_score = -1.0
        
        for intent, embeddings in self.intent_embeddings.items():
            # Compute cosine similarity with all examples
            similarities = util.cos_sim(input_embedding, embeddings)
            max_similarity = similarities.max().item()
            
            if max_similarity > best_score:
                best_score = max_similarity
                best_intent = intent
        
        # Extract entities
        entities = self._extract_entities(user_input, best_intent)
        
        return Intent(
            intent_name=best_intent or 'conversational',
            confidence=best_score,
            entities=entities,
            slot_values={}
        )
    
    def _classify_with_keywords(self, user_input: str) -> Intent:
        """Fallback keyword-based classification"""
        user_lower = user_input.lower()
        
        # Keyword patterns for each intent
        patterns = {
            'open_application': ['open', 'launch', 'start', 'run'],
            'close_application': ['close', 'quit', 'exit', 'kill', 'shutdown'],
            'search_web': ['search', 'google', 'look up', 'find'],
            'file_operation': ['create', 'delete', 'move', 'rename', 'copy', 'organize'],
            'system_control': ['volume', 'lock', 'shut down', 'restart', 'sleep'],
            'information_query': ['what', 'when', 'where', 'how', 'show me'],
            'task_automation': ['remind', 'schedule', 'set timer', 'send email'],
        }
        
        best_intent = 'conversational'
        best_score = 0.0
        
        for intent, keywords in patterns.items():
            score = sum(keyword in user_lower for keyword in keywords) / len(keywords)
            if score > best_score:
                best_score = score
                best_intent = intent
        
        entities = self._extract_entities(user_input, best_intent)
        
        return Intent(
            intent_name=best_intent,
            confidence=best_score,
            entities=entities,
            slot_values={}
        )
    
    def _extract_entities(self, text: str, intent: str) -> Dict[str, List[str]]:
        """Extract named entities from text"""
        entities = defaultdict(list)
        
        # Application names (capitalized words or quoted)
        if intent in ['open_application', 'close_application']:
            # Find capitalized words
            caps_words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
            entities['application'].extend(caps_words)
            
            # Common app names (lowercase)
            common_apps = ['chrome', 'firefox', 'spotify', 'notepad', 'excel', 
                          'word', 'vscode', 'calculator', 'outlook']
            for app in common_apps:
                if app in text.lower():
                    entities['application'].append(app.title())
        
        # File paths
        if intent == 'file_operation':
            # Simple path detection
            paths = re.findall(r'[A-Za-z]:\\[\\a-zA-Z0-9_\-.]+', text)
            entities['file_path'].extend(paths)
        
        # URLs
        urls = re.findall(r'https?://[^\s]+', text)
        entities['url'].extend(urls)
        
        # Numbers
        numbers = re.findall(r'\b\d+\b', text)
        entities['number'].extend(numbers)
        
        # Email addresses
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        entities['email'].extend(emails)
        
        return dict(entities)
    
    def correct_intent(self, user_input: str, predicted_intent: str, 
                      correct_intent: str, confidence: float):
        """Learn from user correction"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO intent_corrections
                (user_input, predicted_intent, corrected_intent, confidence, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user_input, predicted_intent, correct_intent, confidence, 
                  datetime.now().isoformat()))
        
        # Add to user patterns
        self.user_patterns[correct_intent].append(user_input)
        
        # Recompute embeddings
        if self.use_transformers:
            self._precompute_embeddings()
    
    def add_user_vocabulary(self, user_term: str, standard_term: str, intent: str):
        """Learn user's personal vocabulary"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if exists
            cursor = conn.execute("""
                SELECT frequency FROM user_vocabulary
                WHERE user_term = ? AND standard_term = ?
            """, (user_term, standard_term))
            
            row = cursor.fetchone()
            if row:
                # Update frequency
                conn.execute("""
                    UPDATE user_vocabulary
                    SET frequency = frequency + 1, last_used = ?
                    WHERE user_term = ? AND standard_term = ?
                """, (datetime.now().isoformat(), user_term, standard_term))
            else:
                # Insert new
                conn.execute("""
                    INSERT INTO user_vocabulary
                    (original_term, user_term, intent, last_used)
                    VALUES (?, ?, ?, ?)
                """, (standard_term, user_term, intent, datetime.now().isoformat()))
    
    def get_learning_stats(self) -> Dict:
        """Get learning statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM intent_corrections")
            corrections_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM user_vocabulary")
            vocab_count = cursor.fetchone()[0]
        
        return {
            'total_corrections': corrections_count,
            'user_vocabulary_size': vocab_count,
            'learned_patterns_per_intent': {
                intent: len(patterns) 
                for intent, patterns in self.user_patterns.items()
            },
            'transformer_enabled': self.use_transformers,
        }


class NamedEntityRecognizer:
    """
    Named Entity Recognition for extracting structured information
    Learns user-specific entities (custom app names, contact nicknames, etc.)
    """
    
    def __init__(self, db_path: str = "data/ner.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Entity patterns
        self.entity_patterns = self._init_patterns()
        self.custom_entities = defaultdict(set)
        
        self._init_database()
        self._load_custom_entities()
    
    def _init_patterns(self) -> Dict[str, List]:
        """Initialize regex patterns for entity extraction"""
        return {
            'date': [
                r'\d{1,2}/\d{1,2}/\d{2,4}',
                r'\d{4}-\d{2}-\d{2}',
                r'(today|tomorrow|yesterday)',
                r'(next|last) (week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            ],
            'time': [
                r'\d{1,2}:\d{2}\s*(am|pm|AM|PM)?',
                r'at \d{1,2}',
                r'(morning|afternoon|evening|night)',
            ],
            'duration': [
                r'\d+\s*(second|minute|hour|day|week|month|year)s?',
                r'for \d+ (second|minute|hour)s?',
            ],
            'email': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            ],
            'phone': [
                r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                r'\+\d{1,3}\s?\d{1,14}',
            ],
            'url': [
                r'https?://[^\s]+',
                r'www\.[^\s]+',
            ],
            'file_path': [
                r'[A-Za-z]:\\[\\a-zA-Z0-9_\-. ]+',
                r'/[/a-zA-Z0-9_\-. ]+',
            ],
        }
    
    def _init_database(self):
        """Initialize database for custom entities"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_text TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    canonical_form TEXT,
                    frequency INTEGER DEFAULT 1,
                    last_seen TEXT NOT NULL
                )
            """)
    
    def _load_custom_entities(self):
        """Load user-defined entities"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT entity_text, entity_type, canonical_form
                FROM custom_entities
                WHERE last_seen > datetime('now', '-60 days')
            """)
            
            for text, etype, canonical in cursor.fetchall():
                self.custom_entities[etype].add((text, canonical or text))
    
    def extract_entities(self, text: str) -> List[Entity]:
        """Extract all entities from text"""
        entities = []
        
        # Extract using patterns
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    entity = Entity(
                        text=match.group(),
                        type=entity_type,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.9
                    )
                    entities.append(entity)
        
        # Extract custom entities
        for entity_type, entity_set in self.custom_entities.items():
            for entity_text, canonical in entity_set:
                if entity_text.lower() in text.lower():
                    pos = text.lower().find(entity_text.lower())
                    entity = Entity(
                        text=entity_text,
                        type=f"custom_{entity_type}",
                        start=pos,
                        end=pos + len(entity_text),
                        confidence=1.0
                    )
                    entities.append(entity)
        
        # Remove overlapping entities (keep highest confidence)
        entities = self._remove_overlaps(entities)
        
        return entities
    
    def _remove_overlaps(self, entities: List[Entity]) -> List[Entity]:
        """Remove overlapping entities, keeping highest confidence"""
        if not entities:
            return []
        
        # Sort by start position
        entities.sort(key=lambda e: (e.start, -e.confidence))
        
        result = [entities[0]]
        for entity in entities[1:]:
            if entity.start >= result[-1].end:
                result.append(entity)
            elif entity.confidence > result[-1].confidence:
                result[-1] = entity
        
        return result
    
    def add_custom_entity(self, text: str, entity_type: str, canonical_form: Optional[str] = None):
        """Add custom entity to knowledge base"""
        canonical = canonical_form or text
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT frequency FROM custom_entities
                WHERE entity_text = ? AND entity_type = ?
            """, (text, entity_type))
            
            row = cursor.fetchone()
            if row:
                conn.execute("""
                    UPDATE custom_entities
                    SET frequency = frequency + 1, last_seen = ?
                    WHERE entity_text = ? AND entity_type = ?
                """, (datetime.now().isoformat(), text, entity_type))
            else:
                conn.execute("""
                    INSERT INTO custom_entities
                    (entity_text, entity_type, canonical_form, last_seen)
                    VALUES (?, ?, ?, ?)
                """, (text, entity_type, canonical, datetime.now().isoformat()))
        
        self.custom_entities[entity_type].add((text, canonical))


# Example usage
def example_usage():
    """Demonstrate intent classification and NER"""
    
    # Initialize
    classifier = IntentClassifier()
    ner = NamedEntityRecognizer()
    
    # Test cases
    test_inputs = [
        "Open Chrome browser",
        "Search for best restaurants in New York",
        "Remind me to call John tomorrow at 3pm",
        "Delete old files from Downloads folder",
        "What's the weather like today?",
    ]
    
    print("Intent Classification & NER Demo\n" + "="*50)
    
    for user_input in test_inputs:
        print(f"\nInput: '{user_input}'")
        
        # Classify intent
        intent = classifier.classify(user_input)
        print(f"Intent: {intent.intent_name} (confidence: {intent.confidence:.3f})")
        print(f"Entities: {intent.entities}")
        
        # Extract named entities
        entities = ner.extract_entities(user_input)
        if entities:
            print("Named Entities:")
            for entity in entities:
                print(f"  - {entity.text} ({entity.type})")
    
    # Show learning stats
    print("\n" + "="*50)
    print("\nLearning Statistics:")
    stats = classifier.get_learning_stats()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    example_usage()
