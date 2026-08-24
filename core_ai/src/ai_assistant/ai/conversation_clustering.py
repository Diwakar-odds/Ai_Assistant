# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Conversation Topic Clustering
Clusters conversations by topics to improve retrieval and context

Features:
- TF-IDF + K-Means clustering
- Topic modeling with LDA
- Conversation similarity search
- Cluster-based context retrieval
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import Counter, defaultdict
import re

try:
    from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
    from sklearn.cluster import KMeans
    from sklearn.decomposition import LatentDirichletAllocation
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("⚠️ scikit-learn not available")


class ConversationClusterer:
    """
    Clusters conversations by topics
    """
    
    def __init__(self, db_path: str = "data/analytics/conversation_clustering.db",
                 n_clusters: int = 10,
                 n_topics: int = 10):
        self.db_path = db_path
        self.n_clusters = n_clusters
        self.n_topics = n_topics
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(
                max_features=500,
                stop_words='english',
                ngram_range=(1, 2)
            )
            self.clusterer = KMeans(n_clusters=n_clusters, random_state=42)
            
            # Topic modeling
            self.count_vectorizer = CountVectorizer(
                max_features=200,
                stop_words='english'
            )
            self.lda = LatentDirichletAllocation(
                n_components=n_topics,
                random_state=42
            )
            
            self.trained = False
            self.topic_words = []
        
        self.cluster_topics = {}
        
        self._init_database()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    cluster_id INTEGER,
                    topic_id INTEGER,
                    embedding TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS clusters (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    keywords TEXT NOT NULL,
                    size INTEGER DEFAULT 0,
                    centroid TEXT,
                    last_updated TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS topics (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    top_words TEXT NOT NULL,
                    weight REAL DEFAULT 0.0,
                    last_updated TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cluster 
                ON conversations(cluster_id)
            """)
    
    def preprocess_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Lowercase
        text = text.lower()
        
        # Remove special chars but keep spaces
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        return text
    
    def add_conversation(self, conversation_id: str, user_id: str, 
                        messages: List[Dict]) -> int:
        """Add conversation to database"""
        # Combine all messages into text
        text = ' '.join([
            msg.get('content', '') for msg in messages
            if msg.get('role') == 'user'
        ])
        
        text = self.preprocess_text(text)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO conversations
                (conversation_id, user_id, text, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                conversation_id,
                user_id,
                text,
                datetime.now().isoformat()
            ))
            return cursor.lastrowid
    
    def cluster_conversations(self):
        """Cluster conversations using TF-IDF + K-Means"""
        if not SKLEARN_AVAILABLE:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, text
                FROM conversations
            """)
            
            conv_ids = []
            texts = []
            
            for row in cursor.fetchall():
                conv_id, text = row
                if text and len(text.split()) > 3:  # Min length
                    conv_ids.append(conv_id)
                    texts.append(text)
            
            if len(texts) < self.n_clusters:
                return
            
            # TF-IDF vectorization
            X = self.vectorizer.fit_transform(texts)
            
            # Cluster
            cluster_labels = self.clusterer.fit_predict(X)
            
            # Update database
            for conv_id, cluster_id in zip(conv_ids, cluster_labels):
                # Get TF-IDF vector
                idx = conv_ids.index(conv_id)
                embedding = X[idx].toarray()[0].tolist()
                
                conn.execute("""
                    UPDATE conversations
                    SET cluster_id = ?, embedding = ?
                    WHERE id = ?
                """, (int(cluster_id), json.dumps(embedding), conv_id))
            
            self.trained = True
            
            # Analyze clusters
            self._analyze_clusters(texts, cluster_labels)
    
    def _analyze_clusters(self, texts: List[str], labels: np.ndarray):
        """Analyze cluster topics"""
        with sqlite3.connect(self.db_path) as conn:
            for cluster_id in range(self.n_clusters):
                # Get texts in this cluster
                cluster_texts = [
                    texts[i] for i in range(len(texts))
                    if labels[i] == cluster_id
                ]
                
                if not cluster_texts:
                    continue
                
                # Extract keywords
                keywords = self._extract_keywords(cluster_texts)
                
                # Generate cluster name
                cluster_name = self._generate_cluster_name(keywords)
                
                conn.execute("""
                    INSERT OR REPLACE INTO clusters
                    (id, name, keywords, size, last_updated)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    cluster_id,
                    cluster_name,
                    json.dumps(keywords[:10]),
                    len(cluster_texts),
                    datetime.now().isoformat()
                ))
                
                self.cluster_topics[cluster_id] = {
                    'name': cluster_name,
                    'keywords': keywords[:10],
                    'size': len(cluster_texts)
                }
    
    def _extract_keywords(self, texts: List[str], top_n: int = 10) -> List[str]:
        """Extract top keywords from texts"""
        if not SKLEARN_AVAILABLE:
            # Fallback: word frequency
            words = []
            for text in texts:
                words.extend(text.split())
            return [word for word, _ in Counter(words).most_common(top_n)]
        
        # Use TF-IDF
        try:
            vectorizer = TfidfVectorizer(max_features=top_n, stop_words='english')
            vectorizer.fit(texts)
            return vectorizer.get_feature_names_out().tolist()
        except:
            return []
    
    def _generate_cluster_name(self, keywords: List[str]) -> str:
        """Generate readable cluster name from keywords"""
        if not keywords:
            return "Miscellaneous"
        
        # Take top 2-3 keywords
        name_parts = keywords[:3]
        
        # Capitalize
        name_parts = [word.capitalize() for word in name_parts]
        
        return " & ".join(name_parts)
    
    def discover_topics(self):
        """Discover latent topics using LDA"""
        if not SKLEARN_AVAILABLE:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT text FROM conversations
            """)
            
            texts = [row[0] for row in cursor.fetchall() if row[0]]
            
            if len(texts) < self.n_topics:
                return
            
            # Create document-term matrix
            X = self.count_vectorizer.fit_transform(texts)
            
            # Fit LDA
            self.lda.fit(X)
            
            # Extract topic words
            feature_names = self.count_vectorizer.get_feature_names_out()
            
            for topic_idx, topic in enumerate(self.lda.components_):
                # Get top words for this topic
                top_indices = topic.argsort()[-10:][::-1]
                top_words = [feature_names[i] for i in top_indices]
                
                # Generate topic name
                topic_name = " + ".join(top_words[:3])
                
                conn.execute("""
                    INSERT OR REPLACE INTO topics
                    (id, name, top_words, last_updated)
                    VALUES (?, ?, ?, ?)
                """, (
                    topic_idx,
                    topic_name,
                    json.dumps(top_words),
                    datetime.now().isoformat()
                ))
                
                self.topic_words.append(top_words)
    
    def find_similar_conversations(self, query: str, top_k: int = 5) -> List[Dict]:
        """Find conversations similar to query"""
        query = self.preprocess_text(query)
        
        if not SKLEARN_AVAILABLE or not self.trained:
            # Fallback: keyword matching
            return self._find_similar_fallback(query, top_k)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, conversation_id, text, cluster_id, embedding
                FROM conversations
                WHERE embedding IS NOT NULL
            """)
            
            candidates = []
            
            # Vectorize query
            query_vec = self.vectorizer.transform([query])
            
            for row in cursor.fetchall():
                conv_id, conversation_id, text, cluster_id, embedding_json = row
                
                if embedding_json:
                    embedding = np.array(json.loads(embedding_json))
                    
                    # Cosine similarity
                    similarity = cosine_similarity(
                        query_vec.toarray(),
                        embedding.reshape(1, -1)
                    )[0][0]
                    
                    candidates.append({
                        'id': conv_id,
                        'conversation_id': conversation_id,
                        'text': text[:200],
                        'cluster_id': cluster_id,
                        'similarity': float(similarity)
                    })
            
            # Sort by similarity
            candidates.sort(key=lambda x: x['similarity'], reverse=True)
            
            return candidates[:top_k]
    
    def _find_similar_fallback(self, query: str, top_k: int = 5) -> List[Dict]:
        """Fallback similarity using keyword overlap"""
        query_words = set(query.split())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, conversation_id, text, cluster_id
                FROM conversations
            """)
            
            candidates = []
            
            for row in cursor.fetchall():
                conv_id, conversation_id, text, cluster_id = row
                text_words = set(text.split())
                
                # Jaccard similarity
                overlap = len(query_words & text_words)
                union = len(query_words | text_words)
                similarity = overlap / union if union > 0 else 0
                
                candidates.append({
                    'id': conv_id,
                    'conversation_id': conversation_id,
                    'text': text[:200],
                    'cluster_id': cluster_id,
                    'similarity': similarity
                })
            
            candidates.sort(key=lambda x: x['similarity'], reverse=True)
            return candidates[:top_k]
    
    def get_cluster_summary(self, cluster_id: int) -> Optional[Dict]:
        """Get summary of a cluster"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT name, keywords, size
                FROM clusters
                WHERE id = ?
            """, (cluster_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'cluster_id': cluster_id,
                    'name': row[0],
                    'keywords': json.loads(row[1]) if row[1] else [],
                    'size': row[2]
                }
        
        return None
    
    def get_cluster_conversations(self, cluster_id: int, limit: int = 10) -> List[Dict]:
        """Get conversations in a cluster"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT conversation_id, text, created_at
                FROM conversations
                WHERE cluster_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (cluster_id, limit))
            
            return [
                {
                    'conversation_id': row[0],
                    'text': row[1][:200],
                    'created_at': row[2]
                }
                for row in cursor.fetchall()
            ]
    
    def get_stats(self) -> Dict:
        """Get clustering statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(cluster_id) as clustered,
                    COUNT(DISTINCT cluster_id) as num_clusters
                FROM conversations
            """)
            
            row = cursor.fetchone()
            if row:
                return {
                    'total_conversations': row[0] or 0,
                    'clustered': row[1] or 0,
                    'num_clusters': row[2] or 0,
                    'topics_discovered': len(self.topic_words),
                    'model_trained': self.trained if SKLEARN_AVAILABLE else False
                }
        
        return {}


def example_usage():
    """Demonstrate conversation clustering"""
    clusterer = ConversationClusterer(n_clusters=3)
    
    print("Conversation Clustering Demo\n" + "="*50)
    
    # Add sample conversations
    print("\n1. Adding sample conversations...")
    
    conversations = [
        # Coding topic
        [{'role': 'user', 'content': 'How do I write a Python function?'},
         {'role': 'assistant', 'content': 'Here is how...'}],
        [{'role': 'user', 'content': 'Debug this JavaScript code'},
         {'role': 'assistant', 'content': 'The issue is...'}],
        
        # Weather topic
        [{'role': 'user', 'content': 'What is the weather today?'},
         {'role': 'assistant', 'content': 'The weather is...'}],
        [{'role': 'user', 'content': 'Will it rain tomorrow?'},
         {'role': 'assistant', 'content': 'Yes, expect rain...'}],
        
        # Math topic
        [{'role': 'user', 'content': 'Solve this equation'},
         {'role': 'assistant', 'content': 'The solution is...'}],
        [{'role': 'user', 'content': 'Explain calculus'},
         {'role': 'assistant', 'content': 'Calculus is...'}],
    ]
    
    for i, messages in enumerate(conversations):
        clusterer.add_conversation(f'conv_{i}', 'user_1', messages)
    
    # Cluster conversations
    print("2. Clustering conversations...")
    if SKLEARN_AVAILABLE:
        clusterer.cluster_conversations()
        logger.info("✅ Clustering complete")
    
    # Find similar
    print("\n3. Finding similar conversations to 'python coding'...")
    similar = clusterer.find_similar_conversations('python coding', top_k=3)
    for conv in similar:
        print(f"  {conv['conversation_id']}: {conv['text']} (sim: {conv['similarity']:.2f})")
    
    # Get cluster summaries
    print("\n4. Cluster Summaries:")
    stats = clusterer.get_stats()
    for cluster_id in range(min(stats.get('num_clusters', 0), 3)):
        summary = clusterer.get_cluster_summary(cluster_id)
        if summary:
            print(f"\n  {summary['name']} (Cluster {cluster_id})")
            print(f"    Keywords: {', '.join(summary['keywords'][:5])}")
            print(f"    Size: {summary['size']} conversations")
    
    # Stats
    print(f"\n5. Statistics:")
    print(f"  Total conversations: {stats['total_conversations']}")
    print(f"  Clustered: {stats['clustered']}")
    print(f"  Clusters: {stats['num_clusters']}")


if __name__ == "__main__":
    example_usage()
