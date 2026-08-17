"""
Unit tests for the App Discovery Module.
Tests application scanning, fuzzy search, usage tracking, and shortcut resolution.
"""

import unittest
import os
import json
import tempfile
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from modules import app_discovery


class TestAppDiscovery(unittest.TestCase):
    """Test suite for application discovery functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary files for testing
        self.temp_dir = tempfile.mkdtemp()
        self.test_cache_file = os.path.join(self.temp_dir, "test_apps.json")
        self.test_usage_db = os.path.join(self.temp_dir, "test_usage.db")
        
        # Create test app discovery instance
        self.app_disc = app_discovery.AppDiscovery()
        self.app_disc.apps_cache_file = self.test_cache_file
        self.app_disc.usage_db_file = self.test_usage_db
        self.app_disc._init_usage_database()
    
    def tearDown(self):
        """Clean up test environment."""
        import shutil
        import time
        
        # Close any open database connections
        try:
            # Force close database connections
            import gc
            gc.collect()
            time.sleep(0.1)
        except:
            pass
        
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except PermissionError:
                # Database file may still be locked on Windows
                time.sleep(0.5)
                try:
                    shutil.rmtree(self.temp_dir)
                except:
                    pass  # Best effort cleanup
    
    def test_initialization(self):
        """Test AppDiscovery initialization."""
        self.assertIsNotNone(self.app_disc)
        self.assertIsInstance(self.app_disc.apps_database, dict)
    
    def test_usage_database_creation(self):
        """Test usage database initialization."""
        # Check if database was created
        self.assertTrue(os.path.exists(self.test_usage_db))
        
        # Verify tables exist
        with sqlite3.connect(self.test_usage_db) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row[0] for row in cursor.fetchall()]
            
            self.assertIn("app_launches", tables)
            self.assertIn("app_frequency", tables)
    
    def test_save_and_load_cache(self):
        """Test saving and loading app cache."""
        # Add test apps
        test_apps = {
            "notepad": "C:\\Windows\\notepad.exe",
            "calculator": "C:\\Windows\\calc.exe"
        }
        self.app_disc.apps_database = test_apps
        
        # Save cache
        self.app_disc.save_cache()
        self.assertTrue(os.path.exists(self.test_cache_file))
        
        # Create new instance and load cache
        new_disc = app_discovery.AppDiscovery()
        new_disc.apps_cache_file = self.test_cache_file
        new_disc.load_cache()
        
        self.assertEqual(new_disc.apps_database, test_apps)
    
    def test_track_app_launch(self):
        """Test tracking application launches."""
        self.app_disc.track_app_launch("notepad", "C:\\Windows\\notepad.exe", True)
        self.app_disc.track_app_launch("notepad", "C:\\Windows\\notepad.exe", True)
        self.app_disc.track_app_launch("calculator", "C:\\Windows\\calc.exe", True)
        
        # Check frequency table
        with sqlite3.connect(self.test_usage_db) as conn:
            cursor = conn.execute(
                "SELECT app_name, launch_count FROM app_frequency WHERE app_name = 'notepad'"
            )
            result = cursor.fetchone()
            
            self.assertEqual(result[0], "notepad")
            self.assertEqual(result[1], 2)
    
    def test_get_most_used_apps(self):
        """Test retrieving most used applications."""
        # Track some launches
        self.app_disc.track_app_launch("notepad", "", True)
        self.app_disc.track_app_launch("notepad", "", True)
        self.app_disc.track_app_launch("notepad", "", True)
        self.app_disc.track_app_launch("calculator", "", True)
        
        most_used = self.app_disc.get_most_used_apps(limit=5)
        
        self.assertGreater(len(most_used), 0)
        self.assertEqual(most_used[0][0], "notepad")  # Most used
        self.assertEqual(most_used[0][1], 3)  # Launch count
    
    def test_get_recent_apps(self):
        """Test retrieving recently used applications."""
        import time
        
        self.app_disc.track_app_launch("notepad", "", True)
        time.sleep(0.1)
        self.app_disc.track_app_launch("calculator", "", True)
        
        recent = self.app_disc.get_recent_apps(limit=5)
        
        self.assertGreater(len(recent), 0)
        self.assertEqual(recent[0][0], "calculator")  # Most recent
    
    def test_find_app_exact_match(self):
        """Test finding app with exact name match."""
        self.app_disc.apps_database = {
            "notepad": "C:\\Windows\\notepad.exe",
            "calculator": "C:\\Windows\\calc.exe"
        }
        
        result = self.app_disc.find_app("notepad")
        self.assertEqual(result, "C:\\Windows\\notepad.exe")
    
    def test_find_app_partial_match(self):
        """Test finding app with partial name match."""
        self.app_disc.apps_database = {
            "microsoft word": "C:\\Program Files\\Microsoft Office\\WINWORD.EXE",
            "wordpad": "C:\\Windows\\wordpad.exe"
        }
        
        result = self.app_disc.find_app("word")
        self.assertIn("word", result.lower())
    
    def test_calculate_match_score(self):
        """Test fuzzy match scoring algorithm."""
        # Exact match should have highest score
        exact_score = self.app_disc._calculate_match_score("notepad", "notepad", 0)
        self.assertGreaterEqual(exact_score, 100)
        
        # Substring match should have good score
        substring_score = self.app_disc._calculate_match_score("note", "notepad", 0)
        self.assertGreater(substring_score, 50)
        
        # No match should have zero score
        no_match_score = self.app_disc._calculate_match_score("xyz", "notepad", 0)
        self.assertEqual(no_match_score, 0)
    
    def test_calculate_match_score_with_usage(self):
        """Test match scoring with usage frequency boost."""
        # App with high usage should get boosted score
        score_with_usage = self.app_disc._calculate_match_score("notepad", "notepad", 100)
        score_without_usage = self.app_disc._calculate_match_score("notepad", "notepad", 0)
        
        self.assertGreater(score_with_usage, score_without_usage)
    
    def test_string_similarity(self):
        """Test string similarity calculation."""
        # Identical strings
        sim1 = self.app_disc._string_similarity("notepad", "notepad")
        self.assertEqual(sim1, 1.0)
        
        # Similar strings
        sim2 = self.app_disc._string_similarity("notepad", "notpad")
        self.assertGreater(sim2, 0.5)
        
        # Different strings
        sim3 = self.app_disc._string_similarity("notepad", "calculator")
        self.assertLess(sim3, 0.5)
    
    def test_search_apps(self):
        """Test searching applications with ranking."""
        self.app_disc.apps_database = {
            "notepad": "C:\\Windows\\notepad.exe",
            "notepad++": "C:\\Program Files\\Notepad++\\notepad++.exe",
            "calculator": "C:\\Windows\\calc.exe",
            "paint": "C:\\Windows\\mspaint.exe"
        }
        
        results = self.app_disc.search_apps("note", limit=5)
        
        self.assertGreater(len(results), 0)
        # Results should contain notepad-related apps
        app_names = [name for name, _, _ in results]
        self.assertTrue(any("note" in name for name in app_names))
    
    def test_get_system_utilities(self):
        """Test getting system utilities list."""
        utilities = self.app_disc._get_system_utilities()
        
        self.assertIsInstance(utilities, dict)
        self.assertIn("notepad", utilities)
        self.assertIn("calculator", utilities)
        self.assertIn("paint", utilities)
    
    def test_find_main_executable(self):
        """Test finding main executable from list."""
        exe_files = [
            "C:\\Program Files\\App\\setup.exe",
            "C:\\Program Files\\App\\app.exe",
            "C:\\Program Files\\App\\updater.exe"
        ]
        
        main_exe = self.app_disc._find_main_executable(exe_files, "app")
        self.assertIn("app.exe", main_exe)
    
    @patch('subprocess.run')
    def test_resolve_shortcut_powershell(self, mock_run):
        """Test shortcut resolution using PowerShell."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "C:\\Windows\\notepad.exe"
        mock_run.return_value = mock_result
        
        result = self.app_disc._resolve_shortcut("test.lnk")
        
        self.assertEqual(result, "C:\\Windows\\notepad.exe")


class TestAppDiscoveryFunctions(unittest.TestCase):
    """Test module-level convenience functions."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Temporarily replace global instance
        self.original_app_discovery = app_discovery.app_discovery
        app_discovery.app_discovery = app_discovery.AppDiscovery()
        app_discovery.app_discovery.apps_cache_file = os.path.join(
            self.temp_dir, "test_apps.json"
        )
        app_discovery.app_discovery.usage_db_file = os.path.join(
            self.temp_dir, "test_usage.db"
        )
        app_discovery.app_discovery._init_usage_database()
    
    def tearDown(self):
        """Clean up."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
        
        # Restore original instance
        app_discovery.app_discovery = self.original_app_discovery
    
    @patch('os.startfile')
    def test_smart_open_application_success(self, mock_startfile):
        """Test successfully opening an application."""
        app_discovery.app_discovery.apps_database = {
            "notepad": "C:\\Windows\\notepad.exe"
        }
        
        result = app_discovery.smart_open_application("notepad")
        
        self.assertIn("Successfully", result)
        mock_startfile.assert_called_once()
    
    def test_smart_open_application_not_found(self):
        """Test opening non-existent application."""
        app_discovery.app_discovery.apps_database = {}
        
        result = app_discovery.smart_open_application("nonexistentapp")
        
        self.assertIn("Could not find", result)
    
    def test_smart_open_application_name_too_long(self):
        """Test validation of app name length."""
        long_name = "a" * 300
        
        result = app_discovery.smart_open_application(long_name)
        
        self.assertIn("too long", result)
    
    def test_get_app_usage_stats(self):
        """Test getting usage statistics."""
        # Track some apps
        app_discovery.app_discovery.track_app_launch("notepad", "", True)
        app_discovery.app_discovery.track_app_launch("calculator", "", True)
        
        result = app_discovery.get_app_usage_stats()
        
        self.assertIn("USAGE STATISTICS", result)
        self.assertIn("MOST USED", result)
    
    def test_search_apps_by_name(self):
        """Test searching apps by name."""
        app_discovery.app_discovery.apps_database = {
            "notepad": "C:\\Windows\\notepad.exe",
            "calculator": "C:\\Windows\\calc.exe"
        }
        
        result = app_discovery.search_apps_by_name("note")
        
        self.assertIn("SEARCH RESULTS", result)
        self.assertIn("notepad", result.lower())


class TestAppDiscoveryPerformance(unittest.TestCase):
    """Test performance of app discovery."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.app_disc = app_discovery.AppDiscovery()
        self.app_disc.apps_cache_file = os.path.join(self.temp_dir, "test_apps.json")
        self.app_disc.usage_db_file = os.path.join(self.temp_dir, "test_usage.db")
        self.app_disc._init_usage_database()
    
    def tearDown(self):
        """Clean up."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_search_performance_large_database(self):
        """Test search performance with many apps."""
        import time
        
        # Create large database
        for i in range(1000):
            self.app_disc.apps_database[f"app{i}"] = f"C:\\Apps\\app{i}.exe"
        
        start_time = time.time()
        results = self.app_disc.search_apps("app500", limit=10)
        elapsed_time = time.time() - start_time
        
        # Search should complete quickly (< 1 second)
        self.assertLess(elapsed_time, 1.0)
        self.assertGreater(len(results), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
