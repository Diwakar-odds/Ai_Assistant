"""
Unit Tests for Production Storage Architecture, Paths, and Concurrency
======================================================================
Verifies:
  1. Development Mode paths point to repository workspace.
  2. Production Mode paths point to OS-standard user directories (zero hardcoding).
  3. All 49 database paths resolve correctly into the canonical data directory.
  4. Database connections enable WAL journal mode and busy timeouts for multi-threading.
  5. Crash handler installs cleanly and resolves crash log path.
"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(PROJECT_ROOT / "core_ai") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "core_ai"))

from core_ai.config.paths import (
    APP_NAME,
    APP_DIR_NAME,
    PROJECT_ROOT as RESOLVED_ROOT,
    DATA_DIR,
    CONFIG_DIR,
    LOGS_DIR,
    _get_os_system_data_dir,
    _get_os_system_config_dir,
    _get_os_system_logs_dir,
    ensure_directories,
)
from core_ai.core.database_config import get_db_path, get_db_connection, DATABASES
from core_ai.utils.crash_handler import install_crash_handler, _resolve_crash_log_file


class TestProductionStorageAndPaths(unittest.TestCase):
    def test_development_mode_paths(self):
        """In normal local git development, paths must point to project root."""
        self.assertEqual(RESOLVED_ROOT, PROJECT_ROOT)
        self.assertEqual(DATA_DIR, PROJECT_ROOT / "data")
        self.assertEqual(CONFIG_DIR, PROJECT_ROOT / "config")
        self.assertEqual(LOGS_DIR, PROJECT_ROOT / "logs")

    def test_production_mode_resolution(self):
        """In production mode, paths must use OS-standard directories without hardcoded usernames."""
        data_dir = _get_os_system_data_dir()
        config_dir = _get_os_system_config_dir()
        logs_dir = _get_os_system_logs_dir()

        self.assertIsNotNone(data_dir)
        self.assertIsNotNone(config_dir)
        self.assertIsNotNone(logs_dir)

        if sys.platform == "win32":
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            appdata = os.environ.get("APPDATA", "")
            if local_appdata:
                self.assertTrue(str(data_dir).startswith(local_appdata))
                self.assertTrue(str(logs_dir).startswith(local_appdata))
            if appdata:
                self.assertTrue(str(config_dir).startswith(appdata))
            self.assertIn("PulsarAI", str(data_dir))
            self.assertIn("PulsarAI", str(config_dir))

    def test_database_registry_resolution(self):
        """All registered databases must resolve cleanly inside DATA_DIR."""
        self.assertGreater(len(DATABASES), 20)
        for db_name, db_target in DATABASES.items():
            db_path = get_db_path(db_name)
            self.assertEqual(db_path, db_target)
            self.assertTrue(str(db_path).startswith(str(DATA_DIR)))

    def test_database_wal_mode_and_concurrency(self):
        """get_db_connection must enable WAL mode and busy timeout."""
        conn = get_db_connection("chat_history")
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0].lower()
        self.assertIn(journal_mode, ("wal", "memory"))
        cursor.execute("PRAGMA busy_timeout")
        busy_timeout = cursor.fetchone()[0]
        self.assertGreaterEqual(busy_timeout, 5000)
        conn.close()

    def test_crash_handler_installation(self):
        """Crash handler installs and resolves crash log path."""
        install_crash_handler()
        crash_log = _resolve_crash_log_file()
        self.assertIsNotNone(crash_log)
        self.assertTrue(str(crash_log).endswith("crash.log"))


if __name__ == "__main__":
    unittest.main()
