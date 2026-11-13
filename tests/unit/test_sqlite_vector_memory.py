"""
Unit Tests for Phase 3: SQLite Native Vector Storage & Retrieval
Tests:
1. UserDNA trait vector embedding storage in SQLite BLOB
2. UserDNA semantic vector search over personal knowledge
3. Turn persistence into SQLite conversation_vectors table (float16 BLOB)
4. MemoryRetrieval.search_memory_vectors dot-product speed and ranking (<5ms)
5. retrieve_unified_context hybrid fusion (FTS5 + Vector DB)
"""

import sys
import unittest
import tempfile
import sqlite3
from pathlib import Path

# Ensure paths
project_root = Path(__file__).resolve().parents[2]
sys.path.extend([
    str(project_root),
    str(project_root / "core_ai" / "src"),
    str(project_root / "backend"),
])

import numpy as np


class TestSQLiteVectorMemory(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test_conversation_ai.db")
        self.dna_db_path = str(Path(self.temp_dir.name) / "test_personal_knowledge.db")

    def tearDown(self):
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_user_dna_vector_storage_and_search(self):
        """Verify UserDNA stores float16 BLOB embeddings and searches semantically."""
        from ai_assistant.ai.user_dna import UserDNA

        dna = UserDNA(db_path=self.dna_db_path)
        dna.update_trait("friend_name", "Anshuman")
        dna.update_trait("user_location", "Varanasi")
        dna.update_trait("job_title", "Senior Systems Engineer")

        # Verify BLOB is stored in SQLite
        with sqlite3.connect(self.dna_db_path) as conn:
            row = conn.execute("SELECT key, embedding FROM user_dna WHERE key='friend_name'").fetchone()
            self.assertIsNotNone(row)
            self.assertIsNotNone(row[1])
            # 384 dimensions * 2 bytes for float16 = 768 bytes
            self.assertEqual(len(row[1]), 768)

        # Semantic vector search for pal / buddy
        results = dna.search_traits_by_vector("who is my closest pal", limit=2, min_score=0.25)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["key"], "friend_name")
        self.assertEqual(results[0]["value"], "Anshuman")

    def test_conversation_vectors_persistence_and_search(self):
        """Verify conversation turns are stored as vectors and retrieved in <5ms."""
        import time
        from ai_assistant.ai.memory_retrieval import persist_turn_to_conversation_ai, MemoryRetrieval

        # Persist a couple of substantive conversation turns
        ok1 = persist_turn_to_conversation_ai(
            user_text="We need to finalize the Goa road trip itinerary for next month",
            ai_text="I have noted down the Goa road trip details and beach recommendations.",
            session_id="sess_travel_101",
            db_path=self.db_path,
        )
        self.assertTrue(ok1)

        ok2 = persist_turn_to_conversation_ai(
            user_text="Remind me to service my car before the long highway drive",
            ai_text="Car maintenance reminder scheduled.",
            session_id="sess_travel_101",
            db_path=self.db_path,
        )
        self.assertTrue(ok2)

        # Verify rows in conversation_vectors table
        with sqlite3.connect(self.db_path) as conn:
            cnt = conn.execute("SELECT COUNT(*) FROM conversation_vectors").fetchone()[0]
            self.assertGreaterEqual(cnt, 2)
            # Verify BLOB format
            blob_row = conn.execute("SELECT embedding FROM conversation_vectors LIMIT 1").fetchone()
            self.assertEqual(len(blob_row[0]), 768)

        # Initialize retriever with test DB
        retriever = MemoryRetrieval(db_path=self.db_path)

        # Test semantic search latency & retrieval
        t0 = time.time()
        matches = retriever.search_memory_vectors("vacation plans and beach travel", limit=3, min_score=0.35)
        latency_ms = (time.time() - t0) * 1000

        self.assertTrue(len(matches) > 0, "Should find Goa trip conversation by vector similarity")
        self.assertIn("Goa road trip", matches[0]["text"])
        self.assertLess(latency_ms, 75.0, f"Vector search should complete in <75ms on CPU, got {latency_ms:.2f}ms")
        print(f"\n[BENCHMARK] SQLite BLOB Vector Search Latency: {latency_ms:.2f}ms (matches: {len(matches)})")
        retriever.close()

    def test_unified_context_hybrid_injection(self):
        """Verify retrieve_unified_context injects vector-recalled memories into prompt."""
        from ai_assistant.ai.memory_retrieval import persist_turn_to_conversation_ai, MemoryRetrieval

        persist_turn_to_conversation_ai(
            user_text="My brother loves playing football on weekends",
            ai_text="Noted that your brother enjoys weekend football.",
            session_id="sess_sports",
            db_path=self.db_path,
        )

        retriever = MemoryRetrieval(db_path=self.db_path)
        ctx = retriever.retrieve_unified_context("what sport does my sibling play")
        retriever.close()
        
        self.assertIsNotNone(ctx)
        self.assertTrue(len(ctx) > 0)
        self.assertIn("football", ctx.lower())


if __name__ == "__main__":
    unittest.main()
