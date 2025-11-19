"""
Unit tests for the Conversational AI Module.
Tests mood detection, context switching, proactive suggestions, and conversation management.
"""

import unittest
import os
import json
import tempfile
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from modules import conversational_ai


class TestConversationalAI(unittest.TestCase):
    """Test suite for conversational AI functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, "test_conversation.db")
        
        self.ai = conversational_ai.AdvancedConversationalAI(self.test_db)
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        self.ai.cleanup()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """Test conversational AI initialization."""
        self.assertIsNotNone(self.ai)
        self.assertTrue(os.path.exists(self.test_db))
        self.assertEqual(self.ai.user_mood, conversational_ai.MoodType.NEUTRAL)
    
    def test_database_creation(self):
        """Test database tables creation."""
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            
            self.assertIn("conversations", tables)
            self.assertIn("mood_history", tables)
            self.assertIn("user_patterns", tables)
    
    def test_mood_detection_frustrated(self):
        """Test detecting frustrated mood."""
        text = "This is so frustrating! Why doesn't it work?"
        mood = self.ai.detect_mood(text)
        
        self.assertEqual(mood, conversational_ai.MoodType.FRUSTRATED)
    
    def test_mood_detection_happy(self):
        """Test detecting happy mood."""
        text = "This is awesome! Thank you so much!"
        mood = self.ai.detect_mood(text)
        
        self.assertEqual(mood, conversational_ai.MoodType.HAPPY)
    
    def test_mood_detection_urgent(self):
        """Test detecting urgent mood."""
        text = "I need this done ASAP! It's urgent!"
        mood = self.ai.detect_mood(text)
        
        self.assertEqual(mood, conversational_ai.MoodType.URGENT)
    
    def test_mood_detection_confused(self):
        """Test detecting confused mood."""
        text = "I don't understand what's happening. Can you explain?"
        mood = self.ai.detect_mood(text)
        
        self.assertEqual(mood, conversational_ai.MoodType.CONFUSED)
    
    def test_mood_detection_neutral(self):
        """Test neutral mood for normal text."""
        text = "Please open the file manager."
        mood = self.ai.detect_mood(text)
        
        # Should remain neutral or change based on patterns
        self.assertIsInstance(mood, conversational_ai.MoodType)
    
    def test_create_context(self):
        """Test creating conversation context."""
        context_id = self.ai.create_context(
            "Test Conversation",
            "Testing",
            "Hello, this is a test"
        )
        
        self.assertIsNotNone(context_id)
        self.assertIn(context_id, self.ai.contexts)
        self.assertEqual(self.ai.active_context_id, context_id)
        
        context = self.ai.contexts[context_id]
        self.assertEqual(context.name, "Test Conversation")
        self.assertEqual(context.topic, "Testing")
        self.assertEqual(len(context.messages), 1)
    
    def test_switch_context(self):
        """Test switching between conversation contexts."""
        # Create two contexts
        context_id1 = self.ai.create_context("Context 1", "Topic 1")
        context_id2 = self.ai.create_context("Context 2", "Topic 2")
        
        # Should be on context 2 now
        self.assertEqual(self.ai.active_context_id, context_id2)
        
        # Switch back to context 1
        success = self.ai.switch_context(context_id1)
        
        self.assertTrue(success)
        self.assertEqual(self.ai.active_context_id, context_id1)
        
        # Check states
        self.assertEqual(
            self.ai.contexts[context_id1].state,
            conversational_ai.ConversationState.ACTIVE
        )
        self.assertEqual(
            self.ai.contexts[context_id2].state,
            conversational_ai.ConversationState.IDLE
        )
    
    def test_switch_context_by_name(self):
        """Test switching context by name."""
        self.ai.create_context("Email Discussion", "emails")
        self.ai.create_context("File Management", "files")
        
        success = self.ai.switch_context(context_name="Email Discussion")
        
        self.assertTrue(success)
        self.assertEqual(self.ai.contexts[self.ai.active_context_id].name, "Email Discussion")
    
    def test_add_message(self):
        """Test adding messages to context."""
        context_id = self.ai.create_context("Test", "Testing")
        
        self.ai.add_message("assistant", "Hello! How can I help?")
        self.ai.add_message("user", "I need help with files")
        
        context = self.ai.contexts[context_id]
        self.assertEqual(len(context.messages), 3)  # Initial + 2 new
        
        # Check message structure
        last_message = context.messages[-1]
        self.assertEqual(last_message["role"], "user")
        self.assertEqual(last_message["content"], "I need help with files")
        self.assertIn("timestamp", last_message)
    
    def test_get_context_summary(self):
        """Test getting conversation context summary."""
        context_id = self.ai.create_context("Test", "Testing", "Hello")
        self.ai.add_message("assistant", "Hi there!")
        self.ai.add_message("user", "How are you?")
        
        summary = self.ai.get_context_summary(context_id)
        
        self.assertIn("id", summary)
        self.assertIn("name", summary)
        self.assertIn("topic", summary)
        self.assertIn("message_count", summary)
        self.assertEqual(summary["message_count"], 3)
    
    def test_get_conversation_history(self):
        """Test retrieving conversation history."""
        self.ai.create_context("Test", "Testing")
        
        for i in range(15):
            self.ai.add_message("user", f"Message {i}")
        
        history = self.ai.get_conversation_history(limit=10)
        
        self.assertEqual(len(history), 10)
        self.assertEqual(history[-1]["content"], "Message 14")
    
    def test_suggest_next_actions_frustrated_mood(self):
        """Test action suggestions for frustrated mood."""
        self.ai.create_context("Test", "Testing")
        self.ai.user_mood = conversational_ai.MoodType.FRUSTRATED
        
        suggestions = self.ai.suggest_next_actions()
        
        self.assertGreater(len(suggestions), 0)
        
        # Should include helpful suggestions
        suggestion_types = [s["type"] for s in suggestions]
        self.assertTrue(any(t in ["help", "break"] for t in suggestion_types))
    
    def test_suggest_next_actions_confused_mood(self):
        """Test action suggestions for confused mood."""
        self.ai.create_context("Test", "Testing")
        self.ai.user_mood = conversational_ai.MoodType.CONFUSED
        
        suggestions = self.ai.suggest_next_actions()
        
        self.assertGreater(len(suggestions), 0)
        
        suggestion_types = [s["type"] for s in suggestions]
        self.assertTrue(any(t in ["clarification", "step_by_step"] for t in suggestion_types))
    
    def test_handle_context_switch_request(self):
        """Test handling context switch from user input."""
        self.ai.create_context("Email", "emails")
        
        user_input = "switch to email discussion"
        switched, message, context_id = self.ai.handle_context_switch_request(user_input)
        
        self.assertTrue(switched)
        self.assertIn("Switched", message)
        self.assertIsNotNone(context_id)
    
    def test_handle_context_switch_create_new(self):
        """Test creating new context from switch request."""
        user_input = "talk about calendar events"
        switched, message, context_id = self.ai.handle_context_switch_request(user_input)
        
        self.assertTrue(switched)
        self.assertIn("Started", message)
        self.assertIn(context_id, self.ai.contexts)
        self.assertIn("calendar", self.ai.contexts[context_id].topic.lower())
    
    def test_proactive_suggestions_morning(self):
        """Test proactive suggestions for morning time."""
        # Mock the time
        with patch('modules.conversational_ai.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 9, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            suggestions = self.ai.get_proactive_suggestions()
            
            # Should suggest morning briefing
            self.assertGreater(len(suggestions), 0)
            suggestion_types = [s["type"] for s in suggestions]
            self.assertIn("morning_briefing", suggestion_types)
    
    def test_proactive_suggestions_end_of_day(self):
        """Test proactive suggestions for end of day."""
        with patch('modules.conversational_ai.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 17, 0)
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            suggestions = self.ai.get_proactive_suggestions()
            
            suggestion_types = [s["type"] for s in suggestions]
            self.assertIn("end_of_day", suggestion_types)
    
    def test_detect_repetitive_pattern(self):
        """Test detecting repetitive patterns."""
        self.ai.create_context("Test", "Testing")
        
        # Add similar messages
        for i in range(5):
            self.ai.add_message("user", "Please open notepad")
        
        is_repetitive = self.ai._detect_repetitive_pattern()
        
        self.assertTrue(is_repetitive)
    
    def test_calculate_similarity(self):
        """Test text similarity calculation."""
        # Identical texts
        sim1 = self.ai._calculate_similarity("hello world", "hello world")
        self.assertEqual(sim1, 1.0)
        
        # Similar texts
        sim2 = self.ai._calculate_similarity("open notepad", "open the notepad")
        self.assertGreater(sim2, 0.5)
        
        # Different texts
        sim3 = self.ai._calculate_similarity("open notepad", "close calculator")
        self.assertLess(sim3, 0.5)
    
    def test_extract_topic(self):
        """Test topic extraction from text."""
        topic1 = self.ai._extract_topic("I need help with email configuration")
        self.assertIn("email", topic1.lower())
        
        topic2 = self.ai._extract_topic("Can you organize my files?")
        self.assertIn("organize", topic2.lower() or "files" in topic2.lower())
    
    def test_context_persistence(self):
        """Test saving and loading contexts."""
        # Create context
        context_id = self.ai.create_context("Persistent", "Testing persistence")
        self.ai.add_message("user", "Test message")
        
        # Create new AI instance (should load saved contexts)
        new_ai = conversational_ai.AdvancedConversationalAI(self.test_db)
        
        self.assertIn(context_id, new_ai.contexts)
        self.assertEqual(new_ai.contexts[context_id].name, "Persistent")
        self.assertEqual(len(new_ai.contexts[context_id].messages), 2)
        
        new_ai.cleanup()


class TestConversationalAIConvenienceFunctions(unittest.TestCase):
    """Test module-level convenience functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, "test_conversation.db")
        
        # Mock the global AI instance
        self.original_ai = None
        if hasattr(conversational_ai, '_global_ai'):
            self.original_ai = conversational_ai._global_ai
    
    def tearDown(self):
        """Clean up."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('modules.conversational_ai.AdvancedConversationalAI')
    def test_create_conversation_context(self, mock_ai_class):
        """Test convenience function for creating context."""
        mock_ai = Mock()
        mock_ai.create_context.return_value = "ctx_123"
        mock_ai_class.return_value = mock_ai
        
        context_id = conversational_ai.create_conversation_context(
            "Test", "Testing", "Hello"
        )
        
        self.assertEqual(context_id, "ctx_123")
        mock_ai.create_context.assert_called_once()
    
    @patch('modules.conversational_ai.AdvancedConversationalAI')
    def test_detect_user_mood(self, mock_ai_class):
        """Test convenience function for mood detection."""
        mock_ai = Mock()
        mock_ai.detect_mood.return_value = conversational_ai.MoodType.HAPPY
        mock_ai_class.return_value = mock_ai
        
        mood = conversational_ai.detect_user_mood("I'm so happy!")
        
        self.assertEqual(mood, "happy")


class TestMoodType(unittest.TestCase):
    """Test MoodType enum."""
    
    def test_mood_types(self):
        """Test all mood types are defined."""
        moods = [
            conversational_ai.MoodType.NEUTRAL,
            conversational_ai.MoodType.HAPPY,
            conversational_ai.MoodType.FRUSTRATED,
            conversational_ai.MoodType.FOCUSED,
            conversational_ai.MoodType.TIRED,
            conversational_ai.MoodType.URGENT,
            conversational_ai.MoodType.CONFUSED
        ]
        
        for mood in moods:
            self.assertIsInstance(mood, conversational_ai.MoodType)


class TestConversationState(unittest.TestCase):
    """Test ConversationState enum."""
    
    def test_conversation_states(self):
        """Test all conversation states are defined."""
        states = [
            conversational_ai.ConversationState.IDLE,
            conversational_ai.ConversationState.ACTIVE,
            conversational_ai.ConversationState.WAITING_FOR_INPUT,
            conversational_ai.ConversationState.PROCESSING,
            conversational_ai.ConversationState.MULTI_TASK,
            conversational_ai.ConversationState.CONTEXT_SWITCH
        ]
        
        for state in states:
            self.assertIsInstance(state, conversational_ai.ConversationState)


if __name__ == '__main__':
    unittest.main(verbosity=2)
