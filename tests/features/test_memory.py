"""
Unit tests for the Memory Management Module.
Tests connection pooling, transaction management, semantic search, and knowledge base.
"""

import unittest
import os
import sqlite3
import tempfile
import shutil
from modules import memory


class TestMemoryModule(unittest.TestCase):
    """Test suite for memory management functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        cls.test_db = "test_memory.db"
        # Backup original database path if it exists
        if os.path.exists("memory.db"):
            shutil.copy("memory.db", "memory.db.backup")
    
    def setUp(self):
        """Set up before each test."""
        # Remove test database if it exists
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        
        # Update the memory pool to use test database
        memory._memory_pool = memory.ConnectionPool(self.test_db, max_connections=5)
        
        # Initialize test database
        memory.setup_memory()
    
    def tearDown(self):
        """Clean up after each test."""
        memory._memory_pool.close_all()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    @classmethod
    def tearDownClass(cls):
        """Restore original database after all tests."""
        if os.path.exists("memory.db.backup"):
            shutil.move("memory.db.backup", "memory.db")
    
    def test_setup_memory(self):
        """Test database setup."""
        result = memory.setup_memory()
        self.assertIn("initialized", result.lower())
        
        # Verify tables exist
        with memory.get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in c.fetchall()]
            
            self.assertIn("memory", tables)
            self.assertIn("enhanced_memory", tables)
            self.assertIn("daily_summaries", tables)
            self.assertIn("knowledge_base", tables)
    
    def test_connection_pooling(self):
        """Test connection pool functionality."""
        # Get multiple connections
        connections = []
        for _ in range(3):
            conn = memory._memory_pool.get_connection()
            connections.append(conn)
        
        # Return connections
        for conn in connections:
            memory._memory_pool.return_connection(conn)
        
        # Verify pool has connections
        self.assertGreater(len(memory._memory_pool._connections), 0)
    
    def test_save_to_memory(self):
        """Test saving conversations to memory."""
        memory.save_to_memory("User", "Hello, how are you?")
        memory.save_to_memory("YourDaddy", "I'm doing well, thank you!")
        
        # Verify data was saved
        with memory.get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM memory")
            count = c.fetchone()[0]
            self.assertEqual(count, 2)
    
    def test_transaction_rollback(self):
        """Test transaction rollback on error."""
        try:
            with memory.get_db_transaction() as conn:
                c = conn.cursor()
                c.execute("INSERT INTO memory (speaker, content) VALUES (?, ?)", ("User", "Test"))
                # Force an error
                raise Exception("Test error")
        except Exception:
            pass
        
        # Verify transaction was rolled back
        with memory.get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM memory WHERE content = 'Test'")
            count = c.fetchone()[0]
            self.assertEqual(count, 0)
    
    def test_get_memory(self):
        """Test retrieving conversation history."""
        memory.save_to_memory("User", "First message")
        memory.save_to_memory("YourDaddy", "First response")
        memory.save_to_memory("User", "Second message")
        
        result = memory.get_memory(last_n_messages=2)
        self.assertIn("Second message", result)
        self.assertIn("First response", result)
    
    def test_search_memory(self):
        """Test searching through memory."""
        memory.save_to_memory("User", "Can you help me with Python?")
        memory.save_to_memory("YourDaddy", "Sure! What do you need help with?")
        memory.save_to_memory("User", "I need to learn about lists")
        
        result = memory.search_memory("Python", limit=5)
        self.assertIn("Python", result)
    
    def test_semantic_search_memory(self):
        """Test semantic search functionality."""
        memory.save_to_memory("User", "I want to schedule a meeting for tomorrow")
        memory.save_to_memory("User", "Can you send an email to John?")
        memory.save_to_memory("User", "What's my calendar like next week?")
        
        result = memory.semantic_search_memory("calendar appointment", limit=3)
        self.assertIn("meeting", result.lower() or "calendar" in result.lower())
    
    def test_save_and_get_knowledge(self):
        """Test knowledge base functionality."""
        # Save knowledge
        result = memory.save_knowledge("Python", "Python is a programming language", "user")
        self.assertIn("saved", result.lower())
        
        # Retrieve knowledge
        result = memory.get_knowledge("Python")
        self.assertIn("programming language", result)
    
    def test_importance_determination(self):
        """Test importance level calculation."""
        # High importance
        high_importance = memory.determine_importance("This is important and urgent!")
        self.assertGreaterEqual(high_importance, 4)
        
        # Low importance
        low_importance = memory.determine_importance("Hello")
        self.assertLessEqual(low_importance, 3)
    
    def test_content_categorization(self):
        """Test content categorization."""
        self.assertEqual(memory.categorize_content("Schedule a meeting"), "scheduling")
        self.assertEqual(memory.categorize_content("Open Notepad"), "applications")
        self.assertEqual(memory.categorize_content("Check CPU usage"), "system")
        self.assertEqual(memory.categorize_content("Search Google"), "web")
    
    def test_deduplication(self):
        """Test duplicate content handling."""
        memory.save_to_memory("User", "Duplicate message")
        memory.save_to_memory("User", "Duplicate message")
        
        # Should only have one entry in enhanced_memory
        with memory.get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM enhanced_memory WHERE content = 'Duplicate message'")
            count = c.fetchone()[0]
            self.assertEqual(count, 1)
    
    def test_conversation_summary(self):
        """Test daily conversation summary."""
        import datetime
        today = datetime.date.today().strftime("%Y-%m-%d")
        
        memory.save_to_memory("User", "Test message 1")
        memory.save_to_memory("YourDaddy", "Test response 1")
        
        result = memory.get_conversation_summary(today)
        self.assertIn("SUMMARY", result)
        self.assertIn(today, result)


class TestMemoryPerformance(unittest.TestCase):
    """Test suite for memory module performance."""
    
    def setUp(self):
        """Set up test database."""
        self.test_db = "test_memory_perf.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        
        memory._memory_pool = memory.ConnectionPool(self.test_db, max_connections=5)
        memory.setup_memory()
    
    def tearDown(self):
        """Clean up."""
        memory._memory_pool.close_all()
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_bulk_insert_performance(self):
        """Test performance with many inserts."""
        import time
        
        start_time = time.time()
        
        for i in range(100):
            memory.save_to_memory("User", f"Test message {i}")
        
        elapsed_time = time.time() - start_time
        
        # Should complete in reasonable time (< 5 seconds for 100 inserts)
        self.assertLess(elapsed_time, 5.0)
        
        # Verify all were saved
        with memory.get_db_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM memory")
            count = c.fetchone()[0]
            self.assertEqual(count, 100)
    
    def test_search_performance(self):
        """Test search performance with many records."""
        import time
        
        # Insert many records
        for i in range(200):
            memory.save_to_memory("User", f"Message about topic {i % 10}")
        
        start_time = time.time()
        result = memory.search_memory("topic 5", limit=10)
        elapsed_time = time.time() - start_time
        
        # Search should be fast (< 1 second)
        self.assertLess(elapsed_time, 1.0)
        self.assertIn("topic", result.lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)
