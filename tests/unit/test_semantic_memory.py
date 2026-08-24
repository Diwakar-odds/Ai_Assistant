"""
Unit Tests for Semantic Memory (RAG) Upgrade.
Verifies that sentence-transformers properly computes vector embeddings,
stores them as BLOBs in SQLite, and performs cosine similarity search.
"""

import unittest
import os
import tempfile
import shutil
import sqlite3
from unittest.mock import patch

class TestSemanticMemory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, "test_memory.db")
        
        # Patch the DB path to point to our temp DB
        self.patcher = patch('ai_assistant.ai.memory.DB_PATH', self.test_db)
        self.patcher.start()
        
        # Patch get_db_path_str in database_config just in case
        self.patcher_cfg = patch('ai_assistant.core.database_config.get_db_path_str', return_value=self.test_db)
        self.patcher_cfg.start()
        
        # Patch get_encrypted_db to return None so tests use the local test SQLite setup directly
        self.patcher_enc = patch('ai_assistant.ai.memory.get_encrypted_db', return_value=None)
        self.patcher_enc.start()
        
        import ai_assistant.ai.memory as memory
        # Force re-initialization of pool
        memory._memory_pool.database = self.test_db
        memory.setup_memory()
        
        self.memory = memory

    def tearDown(self):
        self.patcher.stop()
        self.patcher_cfg.stop()
        self.patcher_enc.stop()
        
        # Close all connections in the pool so Windows can delete the file
        self.memory._memory_pool.close_all()
        
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_semantic_search_finds_synonyms(self):
        """Test that vector search matches semantically similar sentences without exact keyword overlap."""
        
        # First check if the model is available. If not, skip semantic testing.
        if self.memory.get_embedding_model() is None:
            self.skipTest("sentence-transformers not installed, skipping semantic test")
            
        # 1. Save memories with different semantic meanings
        self.memory.save_to_memory("User", "I have a pet dog named Max.")
        self.memory.save_to_memory("User", "My favorite car brand is Toyota.")
        self.memory.save_to_memory("User", "I love eating pizza with extra cheese.")
        
        # 2. Search using a query that has no overlapping keywords with the target memory,
        # but is semantically identical.
        query = "Do I own a canine?"
        
        result = self.memory.semantic_search_memory(query, limit=1, threshold=0.1)
        
        # It should NOT be the fallback string.
        self.assertFalse(result.startswith("No "), f"Search failed. Result: {result}")
        
        # The result should contain the canine/dog memory.
        self.assertIn("Max", result)
        self.assertNotIn("Toyota", result)
        self.assertNotIn("pizza", result)

    def test_semantic_search_with_empty_db(self):
        """Should handle an empty database gracefully."""
        result = self.memory.semantic_search_memory("Hello?", limit=1)
        self.assertTrue(result.startswith("No "), "Should return 'No memories found' string")

    def test_embedding_column_exists(self):
        """Ensure the setup_memory added the BLOB column."""
        with self.memory.get_db_connection() as conn:
            cursor = conn.execute("PRAGMA table_info(enhanced_memory)")
            columns = [info[1] for info in cursor.fetchall()]
            self.assertIn("embedding", columns)

if __name__ == '__main__':
    unittest.main(verbosity=2)
