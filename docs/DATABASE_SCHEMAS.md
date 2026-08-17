# Database Schema Documentation

This document describes the database schemas used in the YourDaddy AI Assistant project.

## Database Files

All database files are SQLite databases stored in the `data/` directory:

| Database | File | Purpose | Size (approx) |
|----------|------|---------|---------------|
| App Usage | `app_usage.db` | Track application usage statistics | 28 KB |
| Chat History | `chat_history.db` | Store conversation history | 28 KB |
| Conversation AI | `conversation_ai.db` | AI conversation context and state | 61 KB |
| Enhanced Learning | `enhanced_learning.db` | Machine learning training data | 53 KB |
| Language Data | `language_data.db` | Multilingual language preferences | 28 KB |
| Memory | `memory.db` | Long-term memory and knowledge | 69 KB |
| Personal Knowledge | `personal_knowledge.db` | User-specific knowledge base | Variable |

---

## 1. App Usage Database (`app_usage.db`)

**Purpose:** Track which applications are used and how frequently.

### Tables

#### `app_usage`
Stores application usage statistics.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Unique identifier |
| `app_name` | TEXT NOT NULL | Application name |
| `app_path` | TEXT | Full path to application executable |
| `usage_count` | INTEGER DEFAULT 0 | Number of times app was opened |
| `last_used` | TIMESTAMP | Last time app was used |
| `category` | TEXT | Application category (e.g., "Browser", "Development") |
| `created_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Record creation time |

**Indexes:**
- `idx_app_name` on `app_name`
- `idx_last_used` on `last_used`

---

## 2. Chat History Database (`chat_history.db`)

**Purpose:** Store conversation history for context and retrieval.

### Tables

#### `chat_sessions`
Stores chat session metadata.

| Column | Type | Description |
|--------|------|-------------|
| `session_id` | TEXT PRIMARY KEY | Unique session identifier (UUID) |
| `user_id` | TEXT | User identifier |
| `started_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Session start time |
| `ended_at` | TIMESTAMP | Session end time |
| `message_count` | INTEGER DEFAULT 0 | Number of messages in session |

#### `chat_messages`
Stores individual chat messages.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Unique message identifier |
| `session_id` | TEXT NOT NULL | Foreign key to chat_sessions |
| `role` | TEXT NOT NULL | Message role: 'user' or 'assistant' |
| `content` | TEXT NOT NULL | Message content |
| `timestamp` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Message timestamp |
| `metadata` | JSON | Additional metadata (model used, tokens, etc.) |

**Indexes:**
- `idx_session_id` on `session_id`
- `idx_timestamp` on `timestamp`

---

## 3. Conversation AI Database (`conversation_ai.db`)

**Purpose:** Store AI conversation context, state, and preferences.

### Tables

#### `conversation_context`
Stores conversation context for continuity.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Unique identifier |
| `user_id` | TEXT NOT NULL | User identifier |
| `context_data` | JSON | Serialized context information |
| `last_updated` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Last update time |

#### `ai_preferences`
Stores user preferences for AI behavior.

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | TEXT PRIMARY KEY | User identifier |
| `model_preference` | TEXT | Preferred AI model (e.g., "gemini-pro") |
| `temperature` | REAL DEFAULT 0.7 | AI temperature setting |
| `max_tokens` | INTEGER | Maximum tokens per response |
| `system_prompt` | TEXT | Custom system prompt |
| `updated_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Last update time |

---

## 4. Enhanced Learning Database (`enhanced_learning.db`)

**Purpose:** Store machine learning training data and user feedback.

### Tables

#### `training_data`
Stores training examples and feedback.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Unique identifier |
| `input_text` | TEXT NOT NULL | Input/query text |
| `output_text` | TEXT NOT NULL | Expected/actual output |
| `feedback` | TEXT | User feedback ('positive', 'negative', 'neutral') |
| `category` | TEXT | Data category |
| `created_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Creation time |

#### `learning_metrics`
Stores performance metrics.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Unique identifier |
| `metric_name` | TEXT NOT NULL | Metric name (e.g., "accuracy") |
| `metric_value` | REAL NOT NULL | Metric value |
| `timestamp` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Measurement time |

---

## 5. Language Data Database (`language_data.db`)

**Purpose:** Store multilingual preferences and language detection data.

### Tables

#### `user_language_preferences`
Stores user language preferences.

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | TEXT PRIMARY KEY | User identifier |
| `preferred_language` | TEXT NOT NULL | Preferred language code (e.g., "en", "hi") |
| `tts_language` | TEXT | Text-to-speech language |
| `auto_detect` | BOOLEAN DEFAULT 1 | Enable automatic language detection |
| `updated_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Last update time |

#### `language_detection_history`
Stores language detection history for analysis.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Unique identifier |
| `text_sample` | TEXT NOT NULL | Text that was analyzed |
| `detected_language` | TEXT NOT NULL | Detected language code |
| `confidence` | REAL | Detection confidence (0.0-1.0) |
| `timestamp` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Detection time |

---

## 6. Memory Database (`memory.db`)

**Purpose:** Long-term memory storage for facts, preferences, and knowledge.

### Tables

#### `memories`
Stores individual memory entries.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Unique identifier |
| `user_id` | TEXT NOT NULL | User identifier |
| `memory_type` | TEXT NOT NULL | Type: 'fact', 'preference', 'event', 'knowledge' |
| `key` | TEXT NOT NULL | Memory key/identifier |
| `value` | TEXT NOT NULL | Memory value/content |
| `importance` | INTEGER DEFAULT 5 | Importance score (1-10) |
| `created_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Creation time |
| `last_accessed` | TIMESTAMP | Last access time |
| `access_count` | INTEGER DEFAULT 0 | Number of times accessed |

**Indexes:**
- `idx_user_memory` on `user_id, memory_type`
- `idx_key` on `key`
- `idx_importance` on `importance`

#### `memory_embeddings`
Stores vector embeddings for semantic search.

| Column | Type | Description |
|--------|------|-------------|
| `memory_id` | INTEGER PRIMARY KEY | Foreign key to memories |
| `embedding` | BLOB | Vector embedding (serialized numpy array) |
| `embedding_model` | TEXT | Model used for embedding |
| `created_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Creation time |

---

## 7. Personal Knowledge Database (`personal_knowledge.db`)

**Purpose:** User-specific knowledge base and custom information.

### Tables

#### `knowledge_entries`
Stores knowledge base entries.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Unique identifier |
| `title` | TEXT NOT NULL | Entry title |
| `content` | TEXT NOT NULL | Entry content |
| `category` | TEXT | Category/tag |
| `source` | TEXT | Source of information |
| `created_at` | TIMESTAMP DEFAULT CURRENT_TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | Last update time |

#### `knowledge_tags`
Stores tags for knowledge entries.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Unique identifier |
| `entry_id` | INTEGER NOT NULL | Foreign key to knowledge_entries |
| `tag` | TEXT NOT NULL | Tag name |

**Indexes:**
- `idx_entry_id` on `entry_id`
- `idx_tag` on `tag`

---

## Database Management

### Connection Pooling

The application uses connection pooling for efficient database access:

```python
from ai_assistant.database_config import get_db_path

# Get database path
db_path = get_db_path('memory')

# Use with connection pooling (implemented in memory.py)
```

### Migration

To migrate databases from root directory to `data/` directory:

```python
from ai_assistant.database_config import migrate_legacy_databases

# Run migration
migrated = migrate_legacy_databases()
```

### Backup Recommendations

1. **Regular Backups:** Back up the entire `data/` directory daily
2. **Before Updates:** Create backups before major updates
3. **Version Control:** Do NOT commit `.db` files to git (already in `.gitignore`)

### Performance Optimization

1. **Indexes:** All frequently queried columns have indexes
2. **Connection Pooling:** Reduces connection overhead
3. **Prepared Statements:** Use parameterized queries to prevent SQL injection
4. **Vacuum:** Run `VACUUM` periodically to optimize database files

```sql
-- Optimize database
VACUUM;

-- Analyze for query optimization
ANALYZE;
```

---

## Future Improvements

1. **Migration System:** Implement Alembic or similar for schema migrations
2. **Encryption:** Add encryption for sensitive data
3. **Replication:** Consider database replication for backup
4. **Consolidation:** Evaluate if some databases can be merged
5. **Monitoring:** Add database performance monitoring
6. **Caching:** Implement Redis/Memcached for frequently accessed data

---

## Related Files

- Database Configuration: `ai_assistant/database_config.py`
- Memory Module: `ai_assistant/ai/memory.py`
- Chat System: `ai_assistant/ai/advanced_chat_system.py`
- App Discovery: `ai_assistant/automation/app_discovery.py`
