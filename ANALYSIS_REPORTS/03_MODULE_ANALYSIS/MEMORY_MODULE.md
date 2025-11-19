# 🧠 Memory Module Analysis

**File:** `modules/memory.py`  
**Lines of Code:** 338  
**Status:** ⚠️ **PARTIALLY WORKING**  
**Last Updated:** November 17, 2025

---

## 📋 Functionality Overview

The Memory module provides conversation memory and knowledge management:

- ✅ Database initialization (SQLite)
- ✅ Save conversations to memory
- ✅ Retrieve conversation history
- ✅ Search through conversations
- ⚠️ Generate conversation summaries (basic)
- ⚠️ Knowledge base management (basic)
- ❌ Connection pooling (not implemented)
- ❌ Semantic search (basic string matching only)

---

## 🐛 Issues Found

### Issue #1: Database Connection Management - No Pooling 🟡
**Lines:** Throughout the module  
**Severity:** MODERATE

```python
def save_to_memory(speaker: str, content: str):
    """Saves a line of dialogue to both memory tables."""
    try:
        conn = sqlite3.connect('memory.db')  # ❌ New connection every call
        c = conn.cursor()
        # ... operations ...
        conn.commit()
        conn.close()  # ❌ Connection closed immediately
    except Exception as e:
        print(f"Error saving to memory: {e}")
```

**Problem:** Every function opens and closes a new database connection.

**Impact:**
- Performance degradation with frequent calls
- Potential for database locks in concurrent scenarios
- Resource waste (connection overhead)
- Possible "database is locked" errors

**Fix - Implement Connection Pooling:**

```python
import sqlite3
from contextlib import contextmanager
import threading

# Global connection pool
_connection_pool = threading.local()

@contextmanager
def get_db_connection():
    """Context manager for database connections with pooling"""
    # Check if thread already has a connection
    if not hasattr(_connection_pool, 'connection'):
        _connection_pool.connection = sqlite3.connect(
            'memory.db',
            check_same_thread=False,
            timeout=10.0
        )
        # Enable WAL mode for better concurrency
        _connection_pool.connection.execute('PRAGMA journal_mode=WAL')
    
    try:
        yield _connection_pool.connection
    except Exception as e:
        _connection_pool.connection.rollback()
        raise e
    else:
        _connection_pool.connection.commit()

def save_to_memory(speaker: str, content: str):
    """Saves a line of dialogue - IMPROVED VERSION"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Save to original memory table
            c.execute("INSERT INTO memory (speaker, content) VALUES (?,?)", 
                     (speaker, content))
            
            # Save to enhanced memory with deduplication
            content_hash = hashlib.md5(content.encode()).hexdigest()
            importance = determine_importance(content)
            category = categorize_content(content)
            summary = generate_summary(content)
            
            try:
                c.execute("""
                    INSERT INTO enhanced_memory 
                    (speaker, content, content_hash, importance_level, category, summary)
                    VALUES (?,?,?,?,?,?)
                """, (speaker, content, content_hash, importance, category, summary))
            except sqlite3.IntegrityError:
                # Content already exists, update timestamp
                c.execute("""
                    UPDATE enhanced_memory 
                    SET timestamp = CURRENT_TIMESTAMP 
                    WHERE content_hash = ?
                """, (content_hash,))
    except Exception as e:
        logging.error(f"Error saving to memory: {e}")
```

---

### Issue #2: No Database Indexes - Slow Searches 🟡
**Lines:** 21-66 (setup_memory)  
**Severity:** MODERATE

```python
def setup_memory() -> str:
    """Creates the memory databases and tables if they don't exist."""
    try:
        conn = sqlite3.connect('memory.db')
        c = conn.cursor()
        
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
             summary TEXT)
        ''')
        # ❌ NO INDEXES CREATED
```

**Problem:** Searching large amounts of conversation data is slow without indexes.

**Impact:**
- Slow `search_memory()` function as data grows
- Full table scans on every search
- Poor performance with 1000+ conversations

**Fix - Add Indexes:**

```python
def setup_memory() -> str:
    """Creates the memory databases with proper indexes"""
    try:
        conn = sqlite3.connect('memory.db')
        c = conn.cursor()
        
        # Create tables (existing code)
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
             summary TEXT)
        ''')
        
        # ✅ Add indexes for better search performance
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON enhanced_memory(timestamp DESC)
        ''')
        
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_category 
            ON enhanced_memory(category)
        ''')
        
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_importance 
            ON enhanced_memory(importance_level DESC)
        ''')
        
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_speaker 
            ON enhanced_memory(speaker)
        ''')
        
        # Full-text search index (if SQLite supports FTS5)
        try:
            c.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts 
                USING fts5(content, summary, content='enhanced_memory', content_rowid='id')
            ''')
            
            # Trigger to keep FTS index updated
            c.execute('''
                CREATE TRIGGER IF NOT EXISTS memory_fts_insert 
                AFTER INSERT ON enhanced_memory BEGIN
                    INSERT INTO memory_fts(rowid, content, summary) 
                    VALUES (new.id, new.content, new.summary);
                END
            ''')
            
            c.execute('''
                CREATE TRIGGER IF NOT EXISTS memory_fts_update 
                AFTER UPDATE ON enhanced_memory BEGIN
                    UPDATE memory_fts SET content=new.content, summary=new.summary 
                    WHERE rowid=new.id;
                END
            ''')
        except Exception as e:
            print(f"⚠️ FTS5 not available: {e}")
        
        conn.commit()
        conn.close()
        return "✅ Memory database initialized with indexes"
    except Exception as e:
        return f"Error setting up memory: {e}"
```

---

### Issue #3: Search Function - Basic String Matching Only 🟡
**Lines:** 118-157  
**Severity:** MODERATE

```python
def search_memory(query: str, limit: int = 10) -> str:
    """Searches through conversation history"""
    # ❌ Basic LIKE query - not semantic search
    search_term = f"%{query}%"
    c.execute("""
        SELECT speaker, content, timestamp, importance_level, category 
        FROM enhanced_memory 
        WHERE content LIKE ? OR summary LIKE ? OR category LIKE ?
        ORDER BY importance_level DESC, timestamp DESC 
        LIMIT ?
    """, (search_term, search_term, search_term, limit))
```

**Problem:** Only finds exact substring matches, not semantic meaning.

**Fix - Implement Better Search:**

```python
def search_memory(query: str, limit: int = 10, use_fts: bool = True) -> str:
    """Enhanced search with FTS and semantic matching"""
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Try FTS5 full-text search first
            if use_fts:
                try:
                    c.execute("""
                        SELECT m.speaker, m.content, m.timestamp, 
                               m.importance_level, m.category,
                               bm25(memory_fts) as rank
                        FROM memory_fts
                        JOIN enhanced_memory m ON memory_fts.rowid = m.id
                        WHERE memory_fts MATCH ?
                        ORDER BY rank, m.importance_level DESC
                        LIMIT ?
                    """, (query, limit))
                    
                    results = c.fetchall()
                    if results:
                        return format_search_results(results, query, "FTS")
                except Exception as e:
                    print(f"FTS search failed, falling back: {e}")
            
            # Fallback to LIKE search with better ranking
            search_term = f"%{query}%"
            c.execute("""
                SELECT speaker, content, timestamp, importance_level, category,
                    CASE 
                        WHEN content LIKE ? THEN 3
                        WHEN summary LIKE ? THEN 2
                        WHEN category LIKE ? THEN 1
                        ELSE 0
                    END as relevance
                FROM enhanced_memory 
                WHERE content LIKE ? OR summary LIKE ? OR category LIKE ?
                ORDER BY relevance DESC, importance_level DESC, timestamp DESC 
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%",
                  search_term, search_term, search_term, limit))
            
            results = c.fetchall()
            return format_search_results(results, query, "LIKE")
            
    except Exception as e:
        return f"Error searching memory: {e}"

def format_search_results(results, query, method):
    """Format search results nicely"""
    if not results:
        return f"No conversations found containing '{query}'."
    
    report = f"🔍 MEMORY SEARCH RESULTS for '{query}' ({method} search)\n"
    report += "━" * 80 + "\n"
    
    for row in results:
        speaker, content, timestamp, importance, category = row[:5]
        
        # Format timestamp
        dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        formatted_time = dt.strftime("%m/%d %I:%M %p")
        
        # Importance indicator
        importance_icon = "🔴" if importance >= 4 else "🟡" if importance >= 3 else "🟢"
        
        # Truncate long content
        display_content = content[:100] + "..." if len(content) > 100 else content
        
        report += f"{importance_icon} [{formatted_time}] {speaker}: {display_content}\n"
    
    return report
```

---

### Issue #4: Summary Generation - Basic Implementation 🟡
**Lines:** 159-237  
**Severity:** LOW

```python
def get_conversation_summary(date: str = "") -> str:
    """Gets a summary of conversations"""
    # ... loads conversations ...
    
    # ❌ Very basic summary generation
    summary = "Conversation summary coming soon!"
    topics = ", ".join(set([conv[0] for conv in conversations[:5]]))
    events = "No major events"
```

**Problem:** Summary generation is stubbed out.

**Fix - Implement Proper Summarization:**

```python
def get_conversation_summary(date: str = "", use_ai: bool = False) -> str:
    """Generate intelligent conversation summary"""
    if not date:
        date = datetime.date.today().strftime("%Y-%m-%d")
    
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # Check for existing summary
            c.execute("""
                SELECT summary, key_topics, important_events 
                FROM daily_summaries WHERE date = ?
            """, (date,))
            
            existing = c.fetchone()
            if existing:
                summary, topics, events = existing
                return format_summary(date, summary, topics, events)
            
            # Get conversations for the day
            c.execute("""
                SELECT speaker, content, category, importance_level 
                FROM enhanced_memory 
                WHERE DATE(timestamp) = ? 
                ORDER BY timestamp
            """, (date,))
            
            conversations = c.fetchall()
            
            if not conversations:
                return f"No conversations found for {date}."
            
            # Generate summary
            if use_ai:
                summary = generate_ai_summary(conversations)
            else:
                summary = generate_basic_summary(conversations)
            
            # Extract topics and events
            topics = extract_topics(conversations)
            events = extract_events(conversations)
            
            # Save summary
            c.execute("""
                INSERT OR REPLACE INTO daily_summaries 
                (date, summary, key_topics, important_events)
                VALUES (?, ?, ?, ?)
            """, (date, summary, topics, events))
            
            return format_summary(date, summary, topics, events)
            
    except Exception as e:
        return f"Error generating summary: {e}"

def generate_basic_summary(conversations: list) -> str:
    """Generate summary from conversation statistics"""
    total = len(conversations)
    speakers = set(conv[0] for conv in conversations)
    categories = {}
    
    for conv in conversations:
        category = conv[2]
        categories[category] = categories.get(category, 0) + 1
    
    summary = f"Had {total} conversations with {len(speakers)} participants. "
    summary += f"Main topics: {', '.join(sorted(categories.keys()))}. "
    
    # Important messages
    important = [c for c in conversations if c[3] >= 4]
    if important:
        summary += f"Included {len(important)} important messages."
    
    return summary

def extract_topics(conversations: list) -> str:
    """Extract key topics from conversations"""
    categories = {}
    for conv in conversations:
        category = conv[2]
        categories[category] = categories.get(category, 0) + 1
    
    # Get top 5 topics
    top_topics = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:5]
    return ", ".join([f"{topic} ({count})" for topic, count in top_topics])

def extract_events(conversations: list) -> str:
    """Extract important events"""
    events = []
    for conv in conversations:
        if conv[3] >= 4:  # High importance
            content = conv[1][:100]
            events.append(content)
    
    return " | ".join(events[:3]) if events else "No major events"

def format_summary(date, summary, topics, events):
    """Format summary for display"""
    return f"""📋 CONVERSATION SUMMARY for {date}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{summary}

🏷️ Key Topics: {topics}
📌 Important Events: {events}
"""
```

---

### Issue #5: Content Categorization - Hardcoded Categories 🟢
**Lines:** 310-325  
**Severity:** LOW

```python
def categorize_content(content: str) -> str:
    """Categorize conversation content"""
    content_lower = content.lower()
    
    # ❌ Very basic keyword matching
    if any(word in content_lower for word in ['meeting', 'schedule', 'calendar']):
        return 'scheduling'
    elif any(word in content_lower for word in ['task', 'todo', 'work', 'project']):
        return 'tasks'
    # ... more hardcoded rules
```

**Improvement - Make Configurable:**

```python
# Configuration file or dict
CATEGORY_RULES = {
    'scheduling': ['meeting', 'schedule', 'calendar', 'appointment', 'tomorrow', 'next week'],
    'tasks': ['task', 'todo', 'work', 'project', 'deadline', 'complete', 'finish'],
    'questions': ['what', 'how', 'why', 'when', 'where', 'who', '?'],
    'commands': ['open', 'close', 'search', 'play', 'stop', 'run'],
    'personal': ['remember', 'note', 'save', 'remind', 'important'],
    'technical': ['error', 'bug', 'issue', 'problem', 'fix', 'code'],
    'general': []  # Default
}

def categorize_content(content: str, custom_rules: dict = None) -> str:
    """Categorize content with configurable rules"""
    rules = custom_rules or CATEGORY_RULES
    content_lower = content.lower()
    
    # Score each category
    scores = {}
    for category, keywords in rules.items():
        if category == 'general':
            continue
        score = sum(1 for keyword in keywords if keyword in content_lower)
        if score > 0:
            scores[category] = score
    
    # Return highest scoring category or general
    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]
    return 'general'
```

---

## 📊 Database Schema Analysis

### Current Tables

**1. memory** (Original)
```sql
CREATE TABLE memory (
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    speaker TEXT,
    content TEXT
)
```
✅ Simple, works  
❌ No primary key  
❌ No indexes

**2. enhanced_memory**
```sql
CREATE TABLE enhanced_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    speaker TEXT,
    content TEXT,
    content_hash TEXT UNIQUE,
    importance_level INTEGER DEFAULT 3,
    category TEXT DEFAULT 'general',
    tags TEXT,
    summary TEXT
)
```
✅ Good schema  
⚠️ Missing indexes  
⚠️ tags stored as TEXT (should be separate table)

**3. daily_summaries**
```sql
CREATE TABLE daily_summaries (
    date TEXT PRIMARY KEY,
    summary TEXT,
    key_topics TEXT,
    important_events TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
```
✅ Good for daily summaries

**4. knowledge_base**
```sql
CREATE TABLE knowledge_base (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT,
    content TEXT,
    source TEXT,
    confidence REAL DEFAULT 0.8,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP
)
```
✅ Good structure  
❌ Not being used effectively

---

## ⚠️ Concurrency Issues

**Problem:** SQLite default locking can cause "database is locked" errors.

**Solution:**

```python
import sqlite3
import time

def get_db_connection_with_retry(max_retries=3, retry_delay=0.1):
    """Connect with retry logic"""
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(
                'memory.db',
                timeout=10.0,
                isolation_level='DEFERRED'  # Better for reads
            )
            # Enable WAL mode for better concurrency
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA busy_timeout=10000')  # 10 second timeout
            return conn
        except sqlite3.OperationalError as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            raise e
```

---

## 🧪 Testing Requirements

**Current Tests:** 0  
**Required Tests:** 15+

```python
# test_memory.py
import pytest
from modules.memory import *

def test_setup_memory():
    """Test database initialization"""
    result = setup_memory()
    assert "initialized" in result.lower()
    assert os.path.exists('memory.db')

def test_save_and_retrieve():
    """Test saving and retrieving memory"""
    setup_memory()
    save_to_memory("User", "Test message")
    result = get_memory(1)
    assert "Test message" in result

def test_search_memory():
    """Test search functionality"""
    setup_memory()
    save_to_memory("User", "Find this specific message")
    result = search_memory("specific")
    assert "specific message" in result.lower()

def test_duplicate_prevention():
    """Test content deduplication"""
    setup_memory()
    save_to_memory("User", "Duplicate content")
    save_to_memory("User", "Duplicate content")
    # Should not create duplicate

def test_categorization():
    """Test content categorization"""
    assert categorize_content("Let's schedule a meeting") == "scheduling"
    assert categorize_content("Complete this task") == "tasks"

def test_importance_detection():
    """Test importance level detection"""
    assert determine_importance("URGENT: Critical issue") >= 4
    assert determine_importance("Just a note") <= 2

def test_conversation_summary():
    """Test summary generation"""
    setup_memory()
    save_to_memory("User", "Test conversation")
    summary = get_conversation_summary()
    assert summary is not None

def test_concurrent_writes():
    """Test concurrent database writes"""
    import threading
    
    def write_memory(id):
        for i in range(10):
            save_to_memory(f"User{id}", f"Message {i}")
    
    threads = [threading.Thread(target=write_memory, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Should not have "database is locked" errors
```

---

## 🔧 Fix Priority

### P0 - Critical (This Week)
- [ ] Implement connection pooling (2 hours)
- [ ] Add database indexes (1 hour)
- [ ] Enable WAL mode (30 min)
- [ ] Add retry logic (1 hour)

### P1 - High (Next Week)
- [ ] Improve search with FTS5 (3 hours)
- [ ] Better summary generation (3 hours)
- [ ] Add transaction management (2 hours)
- [ ] Write comprehensive tests (4 hours)

### P2 - Medium (This Month)
- [ ] Implement semantic search (6 hours)
- [ ] Add tags system (3 hours)
- [ ] Optimize queries (2 hours)
- [ ] Add memory export/import (2 hours)

---

## ✨ Enhancement Opportunities

### 1. Semantic Search
```python
# Using sentence-transformers
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

def semantic_search(query: str, limit: int = 10):
    """Search using semantic similarity"""
    query_embedding = model.encode(query)
    
    # Get all messages with embeddings
    # Compare cosine similarity
    # Return most similar
```

### 2. Memory Cleanup
```python
def cleanup_old_memories(days_old: int = 90):
    """Archive or delete old, unimportant memories"""
    cutoff = datetime.now() - timedelta(days=days_old)
    # Keep important memories, archive low-importance ones
```

### 3. Memory Analytics
```python
def get_memory_stats():
    """Get statistics about memory usage"""
    return {
        'total_conversations': count_all(),
        'topics': count_by_category(),
        'most_active_day': get_most_active_day(),
        'database_size': get_db_size()
    }
```

---

**Priority:** 🟡 P1  
**Estimated Fix Time:** 8-12 hours  
**Impact:** Moderate - Performance and reliability

**Next Module:** [Multilingual Module →](MULTILINGUAL_MODULE.md)
