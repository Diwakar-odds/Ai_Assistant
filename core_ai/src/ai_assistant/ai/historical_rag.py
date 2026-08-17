"""
Historical Retrieval-Augmented Generation (RAG)
Uses past successful interactions to improve responses

Features:
- Semantic search over conversation history
- FAISS integration for fast similarity search
- Context-aware example injection
- Success-weighted retrieval
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import hashlib

try:
    import numpy as np
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("⚠️ FAISS not available - using fallback search")

try:
    from sentence_transformers import SentenceTransformer
    SBERT_AVAILABLE = True
except ImportError:
    SBERT_AVAILABLE = False
    print("⚠️ sentence-transformers not available")


class HistoricalRAG:
    """
    Retrieval-Augmented Generation using historical interactions
    """
    
    def __init__(self, db_path: str = "data/historical_rag.db",
                 model_name: str = "all-MiniLM-L6-v2",
                 embedding_dim: int = 384):
        self.db_path = db_path
        self.embedding_dim = embedding_dim
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model
        if SBERT_AVAILABLE:
            try:
                self.embedder = SentenceTransformer(model_name)
                self.embedding_dim = self.embedder.get_sentence_embedding_dimension()
            except:
                self.embedder = None
        else:
            self.embedder = None
        
        # Initialize FAISS index
        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.index_to_id = []  # Maps FAISS index position to interaction ID
        else:
            self.index = None
            self.index_to_id = []
        
        self._init_database()
        self._load_index()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    context TEXT,
                    user_feedback REAL DEFAULT 0.5,
                    success_score REAL DEFAULT 0.5,
                    embedding BLOB,
                    created_at TEXT NOT NULL,
                    used_count INTEGER DEFAULT 0,
                    last_used TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS retrieval_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    retrieved_ids TEXT NOT NULL,
                    num_retrieved INTEGER NOT NULL,
                    response_quality REAL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            # Create indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_success_score 
                ON interactions(success_score DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at 
                ON interactions(created_at DESC)
            """)
    
    def _load_index(self):
        """Load existing interactions into FAISS index"""
        if not FAISS_AVAILABLE or not self.embedder:
            return
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT id, embedding
                FROM interactions
                WHERE embedding IS NOT NULL
                ORDER BY id
            """)
            
            embeddings = []
            ids = []
            
            for row in cursor.fetchall():
                interaction_id, embedding_blob = row
                if embedding_blob:
                    # Convert blob back to numpy array
                    embedding = np.frombuffer(embedding_blob, dtype=np.float32)
                    embeddings.append(embedding)
                    ids.append(interaction_id)
            
            if embeddings:
                embeddings_array = np.array(embeddings).astype('float32')
                self.index.add(embeddings_array)
                self.index_to_id = ids
    
    def add_interaction(self, query: str, response: str, 
                       context: Optional[Dict] = None,
                       success_score: float = 0.5):
        """Add an interaction to the RAG database"""
        # Generate embedding
        embedding = None
        embedding_blob = None
        
        if self.embedder:
            try:
                embedding = self.embedder.encode(query, convert_to_numpy=True)
                embedding_blob = embedding.astype('float32').tobytes()
            except:
                pass
        
        # Store in database
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO interactions
                (query, response, context, success_score, embedding, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                query,
                response,
                json.dumps(context) if context else None,
                success_score,
                embedding_blob,
                datetime.now().isoformat()
            ))
            
            interaction_id = cursor.lastrowid
        
        # Add to FAISS index
        if FAISS_AVAILABLE and embedding is not None:
            self.index.add(np.array([embedding]).astype('float32'))
            self.index_to_id.append(interaction_id)
        
        return interaction_id
    
    def retrieve_similar(self, query: str, top_k: int = 5,
                        min_success_score: float = 0.6) -> List[Dict]:
        """
        Retrieve similar past interactions
        
        Returns:
            List of dicts with 'query', 'response', 'context', 'similarity', 'success_score'
        """
        if not self.embedder or not FAISS_AVAILABLE:
            return self._retrieve_fallback(query, top_k, min_success_score)
        
        # Encode query
        try:
            query_embedding = self.embedder.encode(query, convert_to_numpy=True)
        except:
            return self._retrieve_fallback(query, top_k, min_success_score)
        
        # Search FAISS index
        if self.index.ntotal == 0:
            return []
        
        k = min(top_k * 2, self.index.ntotal)  # Retrieve more to filter by success score
        distances, indices = self.index.search(
            np.array([query_embedding]).astype('float32'), 
            k
        )
        
        # Get interaction details from database
        results = []
        
        with sqlite3.connect(self.db_path) as conn:
            for idx, distance in zip(indices[0], distances[0]):
                if idx < len(self.index_to_id):
                    interaction_id = self.index_to_id[idx]
                    
                    cursor = conn.execute("""
                        SELECT query, response, context, success_score, used_count
                        FROM interactions
                        WHERE id = ?
                    """, (interaction_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        query_text, response, context_str, success, used_count = row
                        
                        # Filter by success score
                        if success >= min_success_score:
                            # Convert L2 distance to similarity (0-1)
                            similarity = 1 / (1 + float(distance))
                            
                            results.append({
                                'id': interaction_id,
                                'query': query_text,
                                'response': response,
                                'context': json.loads(context_str) if context_str else None,
                                'similarity': similarity,
                                'success_score': success,
                                'used_count': used_count
                            })
                            
                            # Update usage stats
                            conn.execute("""
                                UPDATE interactions
                                SET used_count = used_count + 1,
                                    last_used = ?
                                WHERE id = ?
                            """, (datetime.now().isoformat(), interaction_id))
        
        # Sort by combined score (similarity * success_score)
        results.sort(key=lambda x: x['similarity'] * x['success_score'], reverse=True)
        
        # Record retrieval
        self._record_retrieval(query, [r['id'] for r in results[:top_k]])
        
        return results[:top_k]
    
    def _retrieve_fallback(self, query: str, top_k: int = 5,
                          min_success_score: float = 0.6) -> List[Dict]:
        """Fallback retrieval using SQL LIKE"""
        query_words = set(query.lower().split())
        
        results = []
        
        with sqlite3.connect(self.db_path) as conn:
            # Get recent successful interactions
            cursor = conn.execute("""
                SELECT id, query, response, context, success_score
                FROM interactions
                WHERE success_score >= ?
                ORDER BY created_at DESC
                LIMIT 100
            """, (min_success_score,))
            
            for row in cursor.fetchall():
                interaction_id, q, response, context_str, success = row
                q_words = set(q.lower().split())
                
                # Jaccard similarity
                intersection = len(query_words & q_words)
                union = len(query_words | q_words)
                
                if union > 0:
                    similarity = intersection / union
                    
                    if similarity > 0.3:  # Minimum threshold
                        results.append({
                            'id': interaction_id,
                            'query': q,
                            'response': response,
                            'context': json.loads(context_str) if context_str else None,
                            'similarity': similarity,
                            'success_score': success,
                            'used_count': 0
                        })
            
            # Sort by combined score
            results.sort(key=lambda x: x['similarity'] * x['success_score'], reverse=True)
        
        return results[:top_k]
    
    def _record_retrieval(self, query: str, retrieved_ids: List[int]):
        """Record retrieval statistics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO retrieval_stats
                (query, retrieved_ids, num_retrieved, timestamp)
                VALUES (?, ?, ?, ?)
            """, (
                query,
                json.dumps(retrieved_ids),
                len(retrieved_ids),
                datetime.now().isoformat()
            ))
    
    def augment_prompt(self, query: str, base_prompt: str,
                      max_examples: int = 3) -> str:
        """
        Augment prompt with relevant past examples
        
        Args:
            query: User query
            base_prompt: Base prompt template
            max_examples: Maximum number of examples to inject
        
        Returns:
            Augmented prompt with examples
        """
        similar = self.retrieve_similar(query, top_k=max_examples)
        
        if not similar:
            return base_prompt
        
        # Build examples section
        examples_text = "\nRelevant past interactions:\n\n"
        
        for i, ex in enumerate(similar, 1):
            examples_text += f"Example {i}:\n"
            examples_text += f"Q: {ex['query']}\n"
            examples_text += f"A: {ex['response'][:200]}...\n\n"
        
        # Inject into prompt
        augmented = base_prompt.replace(
            "{query}",
            f"{examples_text}Current query: {{query}}"
        )
        
        return augmented
    
    def update_feedback(self, interaction_id: int, feedback_score: float):
        """Update success score based on user feedback"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE interactions
                SET user_feedback = ?,
                    success_score = (success_score + ?) / 2
                WHERE id = ?
            """, (feedback_score, feedback_score, interaction_id))
    
    def get_stats(self) -> Dict:
        """Get RAG statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    AVG(success_score) as avg_success,
                    SUM(used_count) as total_retrievals,
                    COUNT(CASE WHEN success_score >= 0.7 THEN 1 END) as high_quality
                FROM interactions
            """)
            
            row = cursor.fetchone()
            if row:
                total, avg_success, retrievals, high_quality = row
                
                return {
                    'total_interactions': total or 0,
                    'average_success_score': avg_success or 0.0,
                    'total_retrievals': retrievals or 0,
                    'high_quality_percentage': (high_quality / total * 100) if total else 0,
                    'index_size': self.index.ntotal if FAISS_AVAILABLE else 0
                }
        
        return {}


def example_usage():
    """Demonstrate historical RAG"""
    rag = HistoricalRAG()
    
    # Add some interactions
    print("Adding historical interactions...")
    rag.add_interaction(
        "How do I open Chrome?",
        "To open Chrome, use the command: open_application('chrome')",
        context={'category': 'automation'},
        success_score=0.9
    )
    
    rag.add_interaction(
        "Open Chrome browser",
        "Opening Chrome... [chrome launched successfully]",
        context={'category': 'automation'},
        success_score=0.95
    )
    
    rag.add_interaction(
        "What is machine learning?",
        "Machine learning is a branch of AI that enables systems to learn from data...",
        context={'category': 'explanation'},
        success_score=0.85
    )
    
    # Retrieve similar
    print("\nRetrieving similar to: 'How to launch Chrome?'")
    similar = rag.retrieve_similar("How to launch Chrome?", top_k=3)
    
    for result in similar:
        print(f"\nSimilarity: {result['similarity']:.2f}, Success: {result['success_score']:.2f}")
        print(f"Q: {result['query']}")
        print(f"A: {result['response'][:100]}...")
    
    # Get stats
    stats = rag.get_stats()
    print(f"\nRAG Statistics:")
    print(f"  Total interactions: {stats['total_interactions']}")
    print(f"  Average success: {stats['average_success_score']:.2f}")
    print(f"  Index size: {stats['index_size']}")


if __name__ == "__main__":
    example_usage()
