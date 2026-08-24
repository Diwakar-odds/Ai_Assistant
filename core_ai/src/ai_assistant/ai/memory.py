# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

# Memory Management Module
"""
Enhanced memory system with semantic search, conversation summaries,
and knowledge management for the Pulsar AI Assistant.

Now includes encryption for sensitive conversation data.
"""

import sqlite3
import hashlib
import datetime
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager
import threading
from pathlib import Path

_embedding_model = None

def get_embedding_model():
    """Lazily load the SentenceTransformer model to avoid blocking startup."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("Loading Semantic Memory Embeddings Model...")
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            logger.warning("WARNING: sentence-transformers not found. Semantic memory degraded.")
            _embedding_model = None
    return _embedding_model

# Import encryption support
try:
    from ai_assistant.core.encrypted_database import create_encrypted_memory_db
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    # logger.warning("WARNING: Encryption not available - sensitive data will not be encrypted")
    pass

# Import database configuration
try:
    from database_config import get_db_path_str
    DB_PATH = get_db_path_str('memory')
except ImportError:
    DB_PATH = 'memory.db'

# Connection pool for SQLite
class ConnectionPool:
    """Simple connection pool for SQLite to reuse connections."""
    def __init__(self, database: str, max_connections: int = 5):
        self.database = database
        self.max_connections = max_connections
        self._connections = []
        self._lock = threading.Lock()
    
    def get_connection(self):
        """Get a connection from the pool or create a new one."""
        with self._lock:
            if self._connections:
                return self._connections.pop()
            return sqlite3.connect(self.database, check_same_thread=False)
    
    def return_connection(self, conn):
        """Return a connection to the pool."""
        with self._lock:
            if len(self._connections) < self.max_connections:
                self._connections.append(conn)
            else:
                conn.close()
    
    def close_all(self):
        """Close all connections in the pool."""
        with self._lock:
            for conn in self._connections:
                conn.close()
            self._connections.clear()

# Global connection pool and encrypted database
_memory_pool = ConnectionPool(DB_PATH, max_connections=5)
_encrypted_db = None

def get_encrypted_db():
    """Get encrypted database instance"""
    global _encrypted_db
    if _encrypted_db is None and ENCRYPTION_AVAILABLE:
        _encrypted_db = create_encrypted_memory_db(DB_PATH)
    return _encrypted_db

@contextmanager
def get_db_connection():
    """Context manager for database connections with automatic cleanup."""
    conn = _memory_pool.get_connection()
    try:
        yield conn
    finally:
        _memory_pool.return_connection(conn)

@contextmanager
def get_db_transaction():
    """Context manager for database transactions with automatic commit/rollback."""
    conn = _memory_pool.get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        _memory_pool.return_connection(conn)

def setup_memory() -> str:
    """Creates the memory databases and tables if they don't exist."""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Original conversation memory
            c.execute('''
                CREATE TABLE IF NOT EXISTS memory
                (timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                 speaker TEXT, 
                 content TEXT)
            ''')
            
            # Enhanced memory with categorization and embeddings
            c.execute('''
                CREATE TABLE IF NOT EXISTS enhanced_memory
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                 speaker TEXT,
                 content TEXT,
                 content_hash TEXT UNIQUE,
                 importance_level INTEGER DEFAULT 3,
                 category TEXT DEFAULT 'general',
                 tags TEXT,
                 summary TEXT,
                 embedding BLOB)
            ''')
            
            # Attempt to add embedding column if table existed before RAG upgrade
            try:
                c.execute("ALTER TABLE enhanced_memory ADD COLUMN embedding BLOB")
            except sqlite3.OperationalError:
                pass # Column already exists
            
            # Create indexes for better query performance
            c.execute('''
                CREATE INDEX IF NOT EXISTS idx_enhanced_memory_timestamp 
                ON enhanced_memory(timestamp DESC)
            ''')
            c.execute('''
                CREATE INDEX IF NOT EXISTS idx_enhanced_memory_category 
                ON enhanced_memory(category)
            ''')
            c.execute('''
                CREATE INDEX IF NOT EXISTS idx_enhanced_memory_importance 
                ON enhanced_memory(importance_level DESC)
            ''')
            
            # Daily conversation summaries
            c.execute('''
                CREATE TABLE IF NOT EXISTS daily_summaries
                (date TEXT PRIMARY KEY,
                 summary TEXT,
                 key_topics TEXT,
                 important_events TEXT,
                 created_at DATETIME DEFAULT CURRENT_TIMESTAMP)
            ''')
            
            # Knowledge base for important facts
            c.execute('''
                CREATE TABLE IF NOT EXISTS knowledge_base
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 topic TEXT,
                 content TEXT,
                 source TEXT,
                 confidence REAL DEFAULT 0.8,
                 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                 last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP)
            ''')
            
            # Create index for knowledge base
            c.execute('''
                CREATE INDEX IF NOT EXISTS idx_knowledge_base_topic 
                ON knowledge_base(topic)
            ''')
            
            conn.commit()
            return "Memory database initialized with connection pooling."
    except Exception as e:
        return f"Error setting up memory: {e}"

def save_to_memory(speaker: str, content: str):
    """Saves a line of dialogue to both memory tables with transaction safety and encryption."""
    try:
        # Compute semantic embedding if available
        embedding_bytes = None
        model = get_embedding_model()
        if model:
            emb = model.encode(content)
            embedding_bytes = emb.astype(np.float32).tobytes()

        # Use encrypted database if available
        encrypted_db = get_encrypted_db()
        
        if encrypted_db:
            # Save to encrypted database
            content_hash = hashlib.md5(content.encode()).hexdigest()
            importance = determine_importance(content)
            category = categorize_content(content)
            summary = generate_summary(content)
            
            # Check for duplicates
            existing = encrypted_db.select("enhanced_memory", "content_hash = ?", (content_hash,))
            
            if existing:
                # Update timestamp for existing content
                encrypted_db.update("enhanced_memory", 
                                  {"timestamp": datetime.datetime.now().isoformat()}, 
                                  "content_hash = ?", (content_hash,))
            else:
                # Insert new content
                data = {
                    "speaker": speaker,
                    "content": content,
                    "content_hash": content_hash,
                    "importance_level": importance,
                    "category": category,
                    "summary": summary,
                    "embedding": embedding_bytes
                }
                encrypted_db.insert("enhanced_memory", data)
                
                # Also save to basic memory table (unencrypted for backward compatibility)
                encrypted_db.insert("memory", {"speaker": speaker, "content": content})
        else:
            # Fallback to regular database
            with get_db_transaction() as conn:
                c = conn.cursor()
                
                # Save to original memory table
                c.execute("INSERT INTO memory (speaker, content) VALUES (?,?)", (speaker, content))
                
                # Save to enhanced memory with deduplication
                content_hash = hashlib.md5(content.encode()).hexdigest()
                importance = determine_importance(content)
                category = categorize_content(content)
                summary = generate_summary(content)
                
                try:
                    c.execute("""
                        INSERT INTO enhanced_memory 
                        (speaker, content, content_hash, importance_level, category, summary, embedding)
                        VALUES (?,?,?,?,?,?,?)
                    """, (speaker, content, content_hash, importance, category, summary, embedding_bytes))
                except sqlite3.IntegrityError:
                    # Content already exists (duplicate), update timestamp instead
                    c.execute("""
                        UPDATE enhanced_memory 
                        SET timestamp = CURRENT_TIMESTAMP 
                        WHERE content_hash = ?
                    """, (content_hash,))
    except Exception as e:
        logger.error(f"Error saving to memory: {e}")

def get_memory(last_n_messages: int = 10) -> str:
    """
    Retrieves the last N messages from the conversation history.
    :param last_n_messages: The number of recent messages to retrieve.
    """
    print(f"--- 'Hands' (get_memory) activated. Retrieving last {last_n_messages} messages. ---")
    try:
        encrypted_db = get_encrypted_db()
        
        if encrypted_db:
            # Use encrypted database
            rows = encrypted_db.select("memory", "", None, last_n_messages)
            # Sort by timestamp descending
            rows = sorted(rows, key=lambda x: x.get('timestamp', ''), reverse=True)
            
            if not rows:
                return "The conversation history is empty."
                
            history = "\n".join([f"{row['speaker']}: {row['content']}" for row in reversed(rows)])
            return f"Here is the recent conversation history:\n{history}"
        else:
            # Fallback to regular database
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT speaker, content FROM memory ORDER BY timestamp DESC LIMIT ?", (last_n_messages,))
                rows = c.fetchall()
            
            if not rows:
                return "The conversation history is empty."
                
            history = "\n".join([f"{speaker}: {content}" for speaker, content in reversed(rows)])
            return f"Here is the recent conversation history:\n{history}"
    except Exception as e:
        return f"Error retrieving memory: {e}"

def search_memory(query: str, limit: int = 10) -> str:
    """
    Searches through conversation history for messages containing the query.
    :param query: Search term to look for
    :param limit: Maximum number of results to return
    """
    print(f"--- 'Hands' (search_memory) activated. Query: {query} ---")
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
        
        # Search in enhanced memory first (better categorization)
        search_term = f"%{query}%"
        c.execute("""
            SELECT speaker, content, timestamp, importance_level, category 
            FROM enhanced_memory 
            WHERE content LIKE ? OR summary LIKE ? OR category LIKE ?
            ORDER BY importance_level DESC, timestamp DESC 
            LIMIT ?
        """, (search_term, search_term, search_term, limit))
        
        results = c.fetchall()
        conn.close()
        
        if not results:
            return f"No conversations found containing '{query}'."
        
        search_report = f"🔍 MEMORY SEARCH RESULTS for '{query}'\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
        
        for speaker, content, timestamp, importance, category in results:
            # Format timestamp
            dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime("%m/%d %I:%M %p")
            
            # Importance indicator
            importance_icon = "🔴" if importance >= 4 else "🟡" if importance >= 3 else "🟢"
            
            search_report += f"{importance_icon} [{formatted_time}] {speaker}: {content[:100]}{'...' if len(content) > 100 else ''}\\n"
        
        return search_report
        
    except Exception as e:
        return f"Error searching memory: {e}"

def get_conversation_summary(date: str = "") -> str:
    """
    Gets a summary of conversations for a specific date or today.
    :param date: Date in YYYY-MM-DD format (optional, defaults to today)
    """
    if not date:
        date = datetime.date.today().strftime("%Y-%m-%d")
    
    print(f"--- 'Hands' (get_conversation_summary) activated. Date: {date} ---")
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
        
        # Check if summary already exists
        c.execute("SELECT summary, key_topics, important_events FROM daily_summaries WHERE date = ?", (date,))
        existing = c.fetchone()
        
        if existing:
            summary, topics, events = existing
            return f"📋 CONVERSATION SUMMARY for {date}\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n{summary}\\n\\n🏷️ Key Topics: {topics}\\n📌 Important Events: {events}"
        
        # Generate new summary from conversations
        c.execute("""
            SELECT speaker, content FROM memory 
            WHERE DATE(timestamp) = ? 
            ORDER BY timestamp
        """, (date,))
        
        conversations = c.fetchall()
        
        if not conversations:
            return f"No conversations found for {date}."
        
        # Generate summary (simplified version)
        total_messages = len(conversations)
        user_messages = len([c for c in conversations if c[0] == "User"])
        assistant_messages = len([c for c in conversations if c[0] == "Pulsar"])
        
        summary = f"Total messages: {total_messages} (User: {user_messages}, Assistant: {assistant_messages})"
        topics = "General conversation, assistance requests"
        events = "Daily interaction with AI assistant"
        
        # Save the generated summary
        c.execute("""
            INSERT OR REPLACE INTO daily_summaries (date, summary, key_topics, important_events)
            VALUES (?, ?, ?, ?)
        """, (date, summary, topics, events))
        
        conn.commit()
        conn.close()
        
        return f"📋 CONVERSATION SUMMARY for {date}\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n{summary}\\n\\n🏷️ Key Topics: {topics}\\n📌 Important Events: {events}"
        
    except Exception as e:
        return f"Error getting conversation summary: {e}"

def save_knowledge(topic: str, content: str, source: str = "user") -> str:
    """
    Saves important knowledge/facts to the knowledge base.
    :param topic: The topic or category of the knowledge
    :param content: The actual knowledge content
    :param source: Source of the information (default: user)
    """
    print(f"--- 'Hands' (save_knowledge) activated. Topic: {topic} ---")
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            c.execute("""
                INSERT INTO knowledge_base (topic, content, source)
                VALUES (?, ?, ?)
            """, (topic, content, source))
            
            conn.commit()
        
        return f"✅ Knowledge saved successfully: '{topic}' - {content[:50]}{'...' if len(content) > 50 else ''}"
        
    except Exception as e:
        return f"Error saving knowledge: {e}"

def get_knowledge(topic: str) -> str:
    """
    Retrieves knowledge from the knowledge base by topic.
    :param topic: The topic to search for
    """
    print(f"--- 'Hands' (get_knowledge) activated. Topic: {topic} ---")
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            search_term = f"%{topic}%"
            c.execute("""
                SELECT topic, content, source, confidence, created_at
                FROM knowledge_base 
                WHERE topic LIKE ? OR content LIKE ?
                ORDER BY confidence DESC, created_at DESC
                LIMIT 10
            """, (search_term, search_term))
            
            results = c.fetchall()
            
            # Update last accessed time
            c.execute("""
                UPDATE knowledge_base 
                SET last_accessed = CURRENT_TIMESTAMP 
                WHERE topic LIKE ? OR content LIKE ?
            """, (search_term, search_term))
            
            conn.commit()
        
        if not results:
            return f"No knowledge found for topic: '{topic}'"
        
        knowledge_report = f"📚 KNOWLEDGE BASE RESULTS for '{topic}'\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
        
        for topic_name, content, source, confidence, created_at in results:
            dt = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            formatted_date = dt.strftime("%m/%d/%Y")
            confidence_icon = "🟢" if confidence >= 0.8 else "🟡" if confidence >= 0.6 else "🔴"
            
            knowledge_report += f"{confidence_icon} **{topic_name}** (Source: {source}, {formatted_date})\\n   {content}\\n\\n"
        
        return knowledge_report
        
    except Exception as e:
        return f"Error retrieving knowledge: {e}"

# Helper functions
def determine_importance(content: str) -> int:
    """Determines importance level (1-5) based on content analysis."""
    content_lower = content.lower()
    
    # High importance keywords
    high_importance = ['important', 'urgent', 'critical', 'remember', 'password', 'appointment', 'meeting', 'deadline']
    medium_importance = ['task', 'todo', 'schedule', 'plan', 'idea', 'note']
    
    if any(word in content_lower for word in high_importance):
        return 5
    elif any(word in content_lower for word in medium_importance):
        return 4
    elif len(content) > 100:  # Longer messages might be more important
        return 3
    else:
        return 2

def categorize_content(content: str) -> str:
    """Categorizes content based on keywords and context."""
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['schedule', 'meeting', 'appointment', 'calendar']):
        return 'scheduling'
    elif any(word in content_lower for word in ['task', 'todo', 'work', 'project']):
        return 'tasks'
    elif any(word in content_lower for word in ['system', 'computer', 'cpu', 'memory', 'disk']):
        return 'system'
    elif any(word in content_lower for word in ['search', 'google', 'youtube', 'web']):
        return 'web'
    elif any(word in content_lower for word in ['open', 'close', 'application', 'app']):
        return 'applications'
    else:
        return 'general'

def generate_summary(content: str) -> str:
    """Generates a brief summary of the content."""
    if len(content) <= 50:
        return content
    else:
        # Simple truncation for now (could be enhanced with NLP)
        return content[:47] + "..."

def semantic_search_memory(query: str, limit: int = 5, threshold: float = 0.3) -> str:
    """
    Perform semantic search on conversation history using SentenceTransformers.
    :param query: Search query
    :param limit: Maximum number of results
    :param threshold: Minimum cosine similarity threshold (0-1)
    """
    print(f"--- 'Hands' (semantic_search_memory) activated. Query: {query} ---")
    model = get_embedding_model()
    
    if not model:
        # Fallback to simple keyword search if model failed to load
        return search_memory(query, limit)
        
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        
        # 1. Compute embedding for the user's query
        query_embedding = model.encode([query]).astype(np.float32)
        
        encrypted_db = get_encrypted_db()
        all_convs = []
        
        if encrypted_db:
            rows = encrypted_db.select("enhanced_memory", "embedding IS NOT NULL", limit=1000)
            for row in rows:
                all_convs.append((
                    row.get("id"),
                    row.get("speaker"),
                    row.get("content"),
                    row.get("timestamp"),
                    row.get("importance_level", 3),
                    row.get("category", "general"),
                    row.get("embedding")
                ))
        else:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT id, speaker, content, timestamp, importance_level, category, embedding
                    FROM enhanced_memory
                    WHERE embedding IS NOT NULL
                    ORDER BY timestamp DESC
                    LIMIT 1000
                """)
                all_convs = c.fetchall()
            
        if not all_convs:
            return "No semantic memories found (database might be initializing or empty)."
            
        scored_results = []
        for conv_id, speaker, content, timestamp, importance, category, embedding_bytes in all_convs:
            # Reconstruct numpy array from BLOB
            emb_array = np.frombuffer(embedding_bytes, dtype=np.float32).reshape(1, -1)
            # Calculate Cosine Similarity
            score = cosine_similarity(query_embedding, emb_array)[0][0]
            
            # Bonus factor for highly important memories
            adjusted_score = score + (importance * 0.02)
            
            if adjusted_score >= threshold:
                scored_results.append((adjusted_score, speaker, content, timestamp, importance, category))
                
        # Sort by best score descending
        scored_results.sort(reverse=True, key=lambda x: x[0])
        top_results = scored_results[:limit]
        
        if not top_results:
            return f"No semantically relevant conversations found for: '{query}'"
            
        search_report = f"🔍 SEMANTIC RAG RESULTS for '{query}'\\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\\n"
        for score, speaker, content, timestamp, importance, category in top_results:
            dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime("%m/%d %I:%M %p")
            importance_icon = "🔴" if importance >= 4 else "🟡" if importance >= 3 else "🟢"
            
            search_report += f"{importance_icon} [{formatted_time}] {speaker} (Sim: {score:.2f}, {category}): {content}\\n\\n"
            
        return search_report
        
    except Exception as e:
        print(f"Semantic search error: {e}")
        return f"Error in semantic search: {e}"