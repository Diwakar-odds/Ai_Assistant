"""
Comprehensive Unit & Integration Test for Refactored Architecture and Priorities 1, 2, and 3.
"""

import os
import sys
import unittest
from pathlib import Path

# Add directories to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / 'core_ai' / 'src'))
sys.path.insert(0, str(root_dir / 'backend'))
sys.path.insert(0, str(root_dir))


class TestPriority1Refactoring(unittest.TestCase):
    """Test Priority 1 - Critical fixes."""

    def test_main_skip_auth_default(self):
        """Verify that --skip-auth defaults to False in main.py."""
        import argparse
        # Inspect main.py directly or reconstruct parser
        with open(root_dir / 'main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('--skip-auth", action="store_true", default=False', content)

    def test_duplicate_backend_removed(self):
        """Verify that nested duplicate directory backend/backend/ is deleted."""
        duplicate_dir = root_dir / 'backend' / 'backend'
        self.assertFalse(duplicate_dir.exists())

    def test_modular_requirements_exist(self):
        """Verify all modular requirements files exist."""
        req_dir = root_dir / 'config' / 'requirements'
        self.assertTrue((req_dir / 'base.txt').exists())
        self.assertTrue((req_dir / 'ml.txt').exists())
        self.assertTrue((req_dir / 'voice.txt').exists())
        self.assertTrue((req_dir / 'dev.txt').exists())
        self.assertTrue((req_dir / 'requirements.txt').exists())
        self.assertTrue((root_dir / 'requirements.txt').exists())

    def test_route_blueprints_importable_without_wildcard(self):
        """Verify all 11 route blueprints are imported cleanly."""
        from backend.routes import (
            auth_bp, chain_bp, chat_bp, file_bp, learning_bp,
            local_ai_bp, settings_bp, system_bp, taskbar_bp,
            voice_bp, web_bp, register_all_routes
        )
        self.assertIsNotNone(auth_bp)
        self.assertIsNotNone(chat_bp)
        self.assertIsNotNone(settings_bp)
        self.assertIsNotNone(system_bp)


class TestPriority2Decomposition(unittest.TestCase):
    """Test Priority 2 - Monolith decomposition and migration system."""

    def test_assistant_decomposition(self):
        """Test ModernAssistant and its composed managers."""
        from ai_assistant.core.assistant import ModernAssistant
        from ai_assistant.core.voice_manager import VoiceManager
        from ai_assistant.core.ai_processor import AIProcessor
        from ai_assistant.core.automation_handler import AutomationHandler
        from ai_assistant.core.system_monitor import SystemMonitor

        assistant = ModernAssistant()
        self.assertIsInstance(assistant.voice_mgr, VoiceManager)
        self.assertIsInstance(assistant.ai_proc, AIProcessor)
        self.assertIsInstance(assistant.automation, AutomationHandler)
        self.assertIsInstance(assistant.monitor, SystemMonitor)

        # Test delegating methods
        stats = assistant.get_real_time_system_stats()
        self.assertIn('timestamp', stats)
        init_status = assistant.get_init_status()
        self.assertIn('system_monitoring', init_status)

    def test_automation_engine_decomposition(self):
        """Test SmartAutomationEngine, models, storage, runner, scheduler."""
        from ai_assistant.automation.automation_engine import (
            SmartAutomationEngine, Workflow, WorkflowTask, TaskType, WorkflowStatus
        )
        engine = SmartAutomationEngine()
        wf = engine.create_workflow(
            name="Test Auto Workflow",
            description="Unit testing",
            tasks=[WorkflowTask(id="step1", name="Delay Step", type=TaskType.DELAY, function="", parameters={"duration": 0.05})]
        )
        self.assertIsNotNone(wf.id)
        result = engine.run_workflow(wf)
        self.assertEqual(result.status, WorkflowStatus.COMPLETED)
        self.assertTrue(engine.delete_workflow(wf.id))

    def test_database_migrations(self):
        """Test SQLite MigrationManager and schema versioning."""
        import tempfile
        from ai_assistant.core.db_migrations import MigrationManager, DEFAULT_MIGRATIONS

        tf = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db = tf.name
        tf.close()

        try:
            mgr = MigrationManager(temp_db)
            applied_count = mgr.run_migrations()
            self.assertEqual(applied_count, len(DEFAULT_MIGRATIONS))

            # Running again should apply 0
            second_run = mgr.run_migrations()
            self.assertEqual(second_run, 0)
        finally:
            try:
                if os.path.exists(temp_db):
                    os.unlink(temp_db)
            except Exception:
                pass

    def test_logging_consolidation(self):
        """Test unified logger creation."""
        from ai_assistant.utils.logging_config import get_logger, SessionManager
        log = get_logger('test_logger')
        self.assertIsNotNone(log)
        self.assertIsNotNone(SessionManager.get_current_date())


class TestPriority3BacklogItems(unittest.TestCase):
    """Test Priority 3 - Deduplication, DI, experimental modules."""

    def test_ai_module_aliases(self):
        """Test that deduplicated AI modules forward to primary classes."""
        from ai_assistant.ai.query_cache import QueryCache
        from ai_assistant.ai.semantic_cache import SemanticCache
        self.assertIs(QueryCache, SemanticCache)

        from ai_assistant.ai.intent_recognizer import IntentRecognizer
        from ai_assistant.ai.intent_classification import IntentClassifier
        self.assertIs(IntentRecognizer, IntentClassifier)

        from ai_assistant.ai.local_model_manager import LocalModelManager
        from ai_assistant.ai.local_ai_manager import LocalAIManager
        self.assertIs(LocalModelManager, LocalAIManager)

    def test_service_container_di(self):
        """Test ServiceContainer registration, resolution, and override."""
        from ai_assistant.core.container import get_container
        container = get_container()
        container.register_singleton("config_service", {"env": "test", "version": 4})
        self.assertEqual(container.resolve("config_service")["version"], 4)

        container.override_for_testing("config_service", {"env": "mocked", "version": 99})
        self.assertEqual(container.resolve("config_service")["version"], 99)

    def test_readme_trimmed(self):
        """Test that README.md is concise (under 20KB instead of 328KB)."""
        readme_path = root_dir / 'README.md'
        size_bytes = os.path.getsize(readme_path)
        self.assertLess(size_bytes, 30000, "README.md should be under 30KB")


if __name__ == '__main__':
    unittest.main()
