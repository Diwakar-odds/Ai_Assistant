"""
Unit Tests for JARVIS-Level Personalization Modules.

Covers:
  - UserDNA (Pillar 1: Deep Evolving User Profile)
  - EmotionalIntelligence (Pillar 4: Adaptive Personality)
  - SelfHealingEngine (Pillar 3: Self-Healing)
  - HealthMonitor (Pillar 3: Background Health Tracking)
  - RelationshipManager (Pillar 4: Relationship Progression)
  - LearningLoop (Pillar 7: Connected Learning)
  - AutonomousActions (Pillar 6: Autonomous Task Initiation)
"""

import unittest
import os
import tempfile
import shutil
import sqlite3
import json
import time
from unittest.mock import patch, MagicMock


# =========================================================================
# 1. UserDNA Tests
# =========================================================================

class TestUserDNA(unittest.TestCase):
    """Test the evolving user profile system (Pillar 1)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, "test_dna.db")
        # Patch get_db_path so UserDNA uses our temp database
        self.patcher = patch(
            'ai_assistant.ai.user_dna.get_db_path',
            return_value=self.test_db
        )
        self.patcher.start()
        from ai_assistant.ai.user_dna import UserDNA
        self.dna = UserDNA(db_path=self.test_db)

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initialization_creates_table(self):
        """UserDNA should create the user_dna table on init."""
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='user_dna'"
            )
            self.assertIsNotNone(cursor.fetchone())

    def test_update_and_get_trait_string(self):
        """Should store and retrieve a string trait."""
        self.dna.update_trait("favorite_color", "blue")
        result = self.dna.get_trait("favorite_color")
        self.assertEqual(result, "blue")

    def test_update_and_get_trait_dict(self):
        """Should store and retrieve complex dict values via JSON serialization."""
        data = {"morning": 0.9, "afternoon": 0.6, "evening": 0.3}
        self.dna.update_trait("energy_curve", data)
        result = self.dna.get_trait("energy_curve")
        self.assertEqual(result, data)

    def test_update_trait_overwrites(self):
        """Updating an existing key should overwrite the old value."""
        self.dna.update_trait("name", "Alice")
        self.dna.update_trait("name", "Bob")
        self.assertEqual(self.dna.get_trait("name"), "Bob")

    def test_get_nonexistent_trait_returns_none(self):
        """Getting a trait that doesn't exist should return None."""
        self.assertIsNone(self.dna.get_trait("does_not_exist"))

    def test_get_full_profile_empty(self):
        """Full profile should be empty dict when no traits stored."""
        profile = self.dna.get_full_profile()
        self.assertEqual(profile, {})

    def test_get_full_profile_populated(self):
        """Full profile should return all stored traits."""
        self.dna.update_trait("name", "Diwakar")
        self.dna.update_trait("role", "Developer")
        self.dna.update_trait("skills", ["Python", "AI"])

        profile = self.dna.get_full_profile()

        self.assertEqual(len(profile), 3)
        self.assertEqual(profile["name"], "Diwakar")
        self.assertEqual(profile["role"], "Developer")
        self.assertIn("Python", profile["skills"])

    def test_incorporate_onboarding_data(self):
        """Should bulk-import onboarding data into the DNA."""
        onboarding = {
            "work_schedule": "9-to-5",
            "communication_style": "concise",
            "interests": ["AI", "Robotics"]
        }
        self.dna.incorporate_onboarding_data(onboarding)

        self.assertEqual(self.dna.get_trait("work_schedule"), "9-to-5")
        self.assertEqual(self.dna.get_trait("communication_style"), "concise")
        self.assertEqual(self.dna.get_trait("interests"), ["AI", "Robotics"])

    def test_confidence_stored_in_db(self):
        """Should store confidence value alongside the trait."""
        self.dna.update_trait("topic_skill", "expert", confidence=0.95)
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.execute(
                "SELECT confidence FROM user_dna WHERE key='topic_skill'"
            )
            row = cursor.fetchone()
            self.assertAlmostEqual(row[0], 0.95)


# =========================================================================
# 2. EmotionalIntelligence Tests
# =========================================================================

class TestEmotionalIntelligence(unittest.TestCase):
    """Test sentiment analysis and adaptive prompt modifiers (Pillar 4)."""

    def setUp(self):
        from ai_assistant.ai.emotional_intelligence import EmotionalIntelligence
        self.ei = EmotionalIntelligence()

    def test_detect_frustrated(self):
        """Should detect frustrated sentiment from angry text."""
        result = self.ei.analyze_sentiment("This is so stupid and frustrating!")
        self.assertEqual(result["sentiment"], "negative")
        self.assertEqual(result["emotion"], "frustrated")

    def test_detect_happy(self):
        """Should detect happy sentiment from positive text."""
        result = self.ei.analyze_sentiment("Thank you so much, this is awesome!")
        self.assertEqual(result["sentiment"], "positive")
        self.assertEqual(result["emotion"], "happy")

    def test_detect_sad(self):
        """Should detect sad sentiment from down text."""
        result = self.ei.analyze_sentiment("I feel so tired and lonely today")
        self.assertEqual(result["sentiment"], "negative")
        self.assertEqual(result["emotion"], "sad")

    def test_detect_neutral(self):
        """Should return neutral for normal text."""
        result = self.ei.analyze_sentiment("Please open the file manager")
        self.assertEqual(result["sentiment"], "neutral")
        self.assertEqual(result["emotion"], "neutral")

    def test_confidence_is_float(self):
        """Confidence should always be a float between 0 and 1."""
        result = self.ei.analyze_sentiment("I'm so happy!")
        self.assertIsInstance(result["confidence"], float)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)

    def test_prompt_modifier_frustrated(self):
        """Should return a calming prompt modifier for frustrated users."""
        modifier = self.ei.get_prompt_modifier({"emotion": "frustrated"})
        self.assertIn("concise", modifier.lower())

    def test_prompt_modifier_sad(self):
        """Should return a warm prompt modifier for sad users."""
        modifier = self.ei.get_prompt_modifier({"emotion": "sad"})
        self.assertIn("empathetic", modifier.lower())

    def test_prompt_modifier_happy(self):
        """Should return an upbeat prompt modifier for happy users."""
        modifier = self.ei.get_prompt_modifier({"emotion": "happy"})
        self.assertIn("cheerful", modifier.lower())

    def test_prompt_modifier_neutral_is_empty(self):
        """Should return empty string for neutral emotion."""
        modifier = self.ei.get_prompt_modifier({"emotion": "neutral"})
        self.assertEqual(modifier, "")

    def test_prompt_modifier_missing_key(self):
        """Should handle missing emotion key gracefully."""
        modifier = self.ei.get_prompt_modifier({})
        self.assertEqual(modifier, "")


# =========================================================================
# 3. SelfHealingEngine Tests
# =========================================================================

class TestSelfHealingEngine(unittest.TestCase):
    """Test autonomous diagnostics and healing (Pillar 3)."""

    def setUp(self):
        from ai_assistant.core.self_healing_engine import SelfHealingEngine
        self.engine = SelfHealingEngine()

    def tearDown(self):
        self.engine.stop()

    def test_initial_health_all_healthy(self):
        """All services should report healthy on startup."""
        status = self.engine.get_status()
        for service, is_healthy in status.items():
            self.assertTrue(is_healthy, f"{service} should be healthy initially")

    def test_get_status_returns_copy(self):
        """get_status should return a copy, not a reference."""
        status = self.engine.get_status()
        status["llm_api"] = False  # mutate the copy
        self.assertTrue(self.engine.get_status()["llm_api"])  # original unchanged

    def test_report_failure_marks_service_down(self):
        """report_failure should mark a service as unhealthy."""
        self.engine.report_failure("database")
        self.assertFalse(self.engine.get_status()["database"])

    def test_report_failure_unknown_service(self):
        """report_failure for an unknown service should not crash."""
        try:
            self.engine.report_failure("unknown_service")
        except Exception:
            self.fail("report_failure should not raise for unknown services")

    def test_callback_fires_on_status_change(self):
        """Registered callbacks should fire when status changes."""
        callback_log = []
        self.engine.register_callback(
            lambda service, status: callback_log.append((service, status))
        )
        self.engine.report_failure("tts_engine")
        self.assertEqual(len(callback_log), 1)
        self.assertEqual(callback_log[0], ("tts_engine", False))

    def test_callback_does_not_fire_on_same_status(self):
        """Callback should NOT fire if status didn't actually change."""
        callback_log = []
        self.engine.register_callback(
            lambda service, status: callback_log.append((service, status))
        )
        # llm_api starts as True; "updating" to True is no change
        self.engine._update_status("llm_api", True)
        self.assertEqual(len(callback_log), 0)

    def test_start_stop_lifecycle(self):
        """Engine should start and stop without errors."""
        self.engine.start()
        self.assertTrue(self.engine.running)
        self.assertIsNotNone(self.engine.thread)
        self.engine.stop()
        self.assertFalse(self.engine.running)

    def test_multiple_callbacks(self):
        """Multiple callbacks should all fire."""
        calls_a = []
        calls_b = []
        self.engine.register_callback(lambda s, st: calls_a.append(s))
        self.engine.register_callback(lambda s, st: calls_b.append(s))
        self.engine.report_failure("network")
        self.assertGreaterEqual(len(calls_a), 1)  # at least network fires
        self.assertGreaterEqual(len(calls_b), 1)

    @patch('socket.create_connection')
    def test_check_network_success(self, mock_socket):
        """_check_network should mark network healthy on success."""
        mock_socket.return_value = MagicMock()
        self.engine._update_status("network", False)  # start unhealthy
        self.engine._check_network()
        self.assertTrue(self.engine.get_status()["network"])

    @patch('socket.create_connection', side_effect=OSError("no route"))
    def test_check_network_failure(self, mock_socket):
        """_check_network should mark network unhealthy on failure."""
        self.engine._check_network()
        self.assertFalse(self.engine.get_status()["network"])
        self.assertFalse(self.engine.get_status()["llm_api"])  # cascade


# =========================================================================
# 4. HealthMonitor Tests
# =========================================================================

class TestHealthMonitor(unittest.TestCase):
    """Test the background health monitoring daemon (Pillar 3)."""

    def setUp(self):
        from ai_assistant.core.self_healing_engine import SelfHealingEngine
        from ai_assistant.core.health_monitor import HealthMonitor
        self.engine = SelfHealingEngine()
        self.monitor = HealthMonitor(self.engine)

    def tearDown(self):
        self.monitor.stop()
        self.engine.stop()

    def test_initialization(self):
        """Monitor should initialize with engine reference."""
        self.assertFalse(self.monitor.running)
        self.assertIsNone(self.monitor.thread)
        self.assertEqual(self.monitor.engine, self.engine)

    def test_start_creates_daemon_thread(self):
        """start() should create a daemon thread."""
        self.monitor.start()
        self.assertTrue(self.monitor.running)
        self.assertIsNotNone(self.monitor.thread)
        self.assertTrue(self.monitor.thread.daemon)

    def test_stop_graceful(self):
        """stop() should terminate the monitor cleanly."""
        self.monitor.start()
        self.monitor.stop()
        self.assertFalse(self.monitor.running)

    def test_double_start_is_safe(self):
        """Calling start() twice should not create duplicate threads."""
        self.monitor.start()
        thread1 = self.monitor.thread
        self.monitor.start()
        thread2 = self.monitor.thread
        self.assertEqual(thread1, thread2)


# =========================================================================
# 5. RelationshipManager Tests
# =========================================================================

class TestRelationshipManager(unittest.TestCase):
    """Test the trust and relationship progression system (Pillar 4)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, "test_relationship.db")
        self.patcher = patch(
            'ai_assistant.core.relationship_manager.get_db_path',
            return_value=self.test_db
        )
        self.patcher.start()
        from ai_assistant.core.relationship_manager import RelationshipManager
        self.rm = RelationshipManager()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_initial_trust_is_zero(self):
        """Trust score should start at 0.0."""
        self.assertAlmostEqual(self.rm.get_trust_level(), 0.0)

    def test_initial_stage_is_formal(self):
        """Relationship stage should be 'Formal' at trust 0."""
        self.assertEqual(self.rm.get_relationship_stage(), "Formal")

    def test_increment_interaction_increases_trust(self):
        """Each interaction should increase trust by 0.1."""
        self.rm.increment_interaction()
        self.assertAlmostEqual(self.rm.get_trust_level(), 0.1)

    def test_multiple_increments(self):
        """100 interactions should yield trust = 10.0."""
        for _ in range(100):
            self.rm.increment_interaction()
        self.assertAlmostEqual(self.rm.get_trust_level(), 10.0)

    def test_trust_capped_at_100(self):
        """Trust should never exceed 100.0."""
        for _ in range(1500):
            self.rm.increment_interaction()
        self.assertLessEqual(self.rm.get_trust_level(), 100.0)

    def test_stage_progression_friendly(self):
        """After enough interactions to pass trust 10, stage should be 'Friendly'."""
        for _ in range(110):
            self.rm.increment_interaction()
        self.assertEqual(self.rm.get_relationship_stage(), "Friendly")

    def test_stage_progression_trusted(self):
        """After 500 interactions (trust=50), stage should be 'Trusted Companion'."""
        for _ in range(500):
            self.rm.increment_interaction()
        self.assertEqual(self.rm.get_relationship_stage(), "Trusted Companion")

    def test_persistence_across_instances(self):
        """Trust should persist across new RelationshipManager instances."""
        for _ in range(50):
            self.rm.increment_interaction()
        expected_trust = self.rm.get_trust_level()

        from ai_assistant.core.relationship_manager import RelationshipManager
        rm2 = RelationshipManager()
        self.assertAlmostEqual(rm2.get_trust_level(), expected_trust)


# =========================================================================
# 6. LearningLoop Tests
# =========================================================================

class TestLearningLoop(unittest.TestCase):
    """Test the unified post-interaction learning orchestrator (Pillar 7)."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_db = os.path.join(self.temp_dir, "test_learning.db")

        # Patch both get_db_path calls that LearningLoop's dependencies use
        self.patcher_dna = patch(
            'ai_assistant.ai.user_dna.get_db_path',
            return_value=self.test_db
        )
        self.patcher_rm = patch(
            'ai_assistant.core.relationship_manager.get_db_path',
            return_value=self.test_db
        )
        self.patcher_dna.start()
        self.patcher_rm.start()

        from ai_assistant.core.learning_loop import LearningLoop
        self.loop = LearningLoop()

    def tearDown(self):
        self.patcher_dna.stop()
        self.patcher_rm.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_dependencies_loaded(self):
        """LearningLoop should successfully load UserDNA and RelationshipManager."""
        self.assertIsNotNone(self.loop.dna)
        self.assertIsNotNone(self.loop.relationship)

    def test_process_interaction_increments_trust(self):
        """process_interaction should call relationship.increment_interaction."""
        initial_trust = self.loop.relationship.get_trust_level()
        self.loop._process_async(
            prompt="hello",
            response="hi sir",
            context={"mood": "neutral"}
        )
        new_trust = self.loop.relationship.get_trust_level()
        self.assertGreater(new_trust, initial_trust)

    def test_process_interaction_stores_mood(self):
        """process_interaction should store mood into UserDNA."""
        self.loop._process_async(
            prompt="I'm frustrated",
            response="I understand",
            context={"mood": "frustrated"}
        )
        stored_mood = self.loop.dna.get_trait("recent_mood")
        self.assertEqual(stored_mood, "frustrated")

    def test_process_interaction_no_mood(self):
        """process_interaction should not crash if context has no mood."""
        try:
            self.loop._process_async(
                prompt="what's the time?",
                response="It's 3 PM",
                context={}
            )
        except Exception:
            self.fail("process_interaction should handle missing mood gracefully")

    def test_process_interaction_updates_dna_cumulatively(self):
        """Multiple interactions should update DNA sequentially."""
        self.loop._process_async("hi", "hello", {"mood": "happy"})
        self.loop._process_async("bye", "goodbye", {"mood": "neutral"})

        # Last mood should be the most recent one
        self.assertEqual(self.loop.dna.get_trait("recent_mood"), "neutral")


# =========================================================================
# 7. AutonomousActions Tests
# =========================================================================

class TestAutonomousActions(unittest.TestCase):
    """Test background autonomous task execution (Pillar 6)."""

    def setUp(self):
        from ai_assistant.core.autonomous_actions import AutonomousActions
        self.actions = AutonomousActions()

    def test_initialization(self):
        """AutonomousActions should initialize without errors."""
        self.assertIsNotNone(self.actions)

    @patch('glob.glob', return_value=[])
    def test_clear_temp_files_empty(self, mock_glob):
        """clear_temp_files should handle zero files gracefully."""
        try:
            self.actions.clear_temp_files()
        except Exception:
            self.fail("clear_temp_files should not raise when no files found")

    @patch('os.remove')
    @patch('glob.glob', return_value=[
        '/tmp/ai_assistant_cache1.tmp',
        '/tmp/ai_assistant_cache2.tmp'
    ])
    def test_clear_temp_files_removes_files(self, mock_glob, mock_remove):
        """clear_temp_files should call os.remove for each matching file."""
        self.actions.clear_temp_files()
        self.assertEqual(mock_remove.call_count, 2)

    @patch('os.remove', side_effect=OSError("Permission denied"))
    @patch('glob.glob', return_value=['/tmp/ai_assistant_locked.tmp'])
    def test_clear_temp_files_handles_permission_error(self, mock_glob, mock_remove):
        """clear_temp_files should not crash on permission errors."""
        try:
            self.actions.clear_temp_files()
        except Exception:
            self.fail("clear_temp_files should handle OSError gracefully")

    def test_prepare_data_does_not_crash(self):
        """prepare_data should execute without errors (stub implementation)."""
        try:
            self.actions.prepare_data()
        except Exception:
            self.fail("prepare_data should not raise")


if __name__ == '__main__':
    unittest.main(verbosity=2)
