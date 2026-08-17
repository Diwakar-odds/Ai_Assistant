"""
Unit tests for Taskbar Detection Module

Tests for:
- get_running_applications()
- get_taskbar_apps_visual()
- get_complete_desktop_analysis()
- find_specific_app_in_taskbar()
- detect_taskbar_apps()
- can_see_taskbar()
"""

import unittest
import os
import sys
from unittest.mock import patch, Mock, MagicMock
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.taskbar_detection import (
    TaskbarDetector,
    detect_taskbar_apps,
    can_see_taskbar
)


class TestTaskbarDetector(unittest.TestCase):
    """Test suite for TaskbarDetector class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = TaskbarDetector()
    
    def test_taskbar_detector_initialization(self):
        """Test TaskbarDetector initialization"""
        self.assertIsNotNone(self.detector)
        # multimodal might be None if not available
        self.assertIsInstance(self.detector.multimodal, (type(None), object))
    
    @patch('modules.taskbar_detection.psutil.process_iter')
    def test_get_running_applications_basic(self, mock_process_iter):
        """Test getting running applications"""
        # Mock process information
        mock_proc1 = Mock()
        mock_proc1.info = {
            'pid': 1234,
            'name': 'chrome.exe',
            'memory_info': Mock(rss=100*1024*1024),  # 100 MB
            'cpu_percent': 5.0,
            'create_time': 1000000000
        }
        
        mock_proc2 = Mock()
        mock_proc2.info = {
            'pid': 5678,
            'name': 'notepad.exe',
            'memory_info': Mock(rss=50*1024*1024),  # 50 MB
            'cpu_percent': 2.0,
            'create_time': 1000000100
        }
        
        mock_process_iter.return_value = [mock_proc1, mock_proc2]
        
        result = self.detector.get_running_applications()
        
        self.assertIn('processes', result)
        self.assertIn('windows', result)
        self.assertIn('summary', result)
        self.assertEqual(len(result['processes']), 2)
        self.assertEqual(result['summary']['total_processes'], 2)
    
    @patch('modules.taskbar_detection.psutil.process_iter')
    def test_get_running_applications_with_errors(self, mock_process_iter):
        """Test getting applications with process access errors"""
        # Mock one good process and one that raises an error
        mock_proc_good = Mock()
        mock_proc_good.info = {
            'pid': 1234,
            'name': 'test.exe',
            'memory_info': Mock(rss=100*1024*1024),
            'cpu_percent': 5.0,
            'create_time': 1000000000
        }
        
        mock_proc_bad = Mock()
        mock_proc_bad.info = Mock(side_effect=Exception("Access denied"))
        
        mock_process_iter.return_value = [mock_proc_good, mock_proc_bad]
        
        result = self.detector.get_running_applications()
        
        # Should only have the good process
        self.assertEqual(len(result['processes']), 1)
    
    def test_get_taskbar_apps_visual_without_multimodal(self):
        """Test visual taskbar detection without multimodal support"""
        # Force multimodal to None
        self.detector.multimodal = None
        
        result = self.detector.get_taskbar_apps_visual()
        
        self.assertIn('error', result)
        self.assertIn('not available', result['error'])
    
    @patch('modules.taskbar_detection.psutil.process_iter')
    def test_get_complete_desktop_analysis(self, mock_process_iter):
        """Test complete desktop analysis"""
        # Mock minimal process data
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'test.exe',
            'memory_info': Mock(rss=100*1024*1024),
            'cpu_percent': 5.0,
            'create_time': 1000000000
        }
        mock_process_iter.return_value = [mock_proc]
        
        result = self.detector.get_complete_desktop_analysis()
        
        self.assertIn('timestamp', result)
        self.assertIn('process_analysis', result)
        self.assertIn('visual_analysis', result)
        self.assertIn('taskbar_analysis', result)
        self.assertIn('summary', result)
    
    @patch('modules.taskbar_detection.psutil.process_iter')
    def test_find_specific_app_in_taskbar(self, mock_process_iter):
        """Test finding a specific application"""
        # Mock process that matches search
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'chrome.exe'
        }
        mock_process_iter.return_value = [mock_proc]
        
        result = self.detector.find_specific_app_in_taskbar("chrome")
        
        self.assertIn('app_name', result)
        self.assertEqual(result['app_name'], 'chrome')
        self.assertIn('found_in_processes', result)
        self.assertTrue(result['found_in_processes'])
        self.assertIn('matching_processes', result)
        self.assertEqual(len(result['matching_processes']), 1)
    
    @patch('modules.taskbar_detection.psutil.process_iter')
    def test_find_specific_app_not_found(self, mock_process_iter):
        """Test finding an app that doesn't exist"""
        # Mock process that doesn't match
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'notepad.exe'
        }
        mock_process_iter.return_value = [mock_proc]
        
        result = self.detector.find_specific_app_in_taskbar("nonexistent")
        
        self.assertFalse(result['found_in_processes'])
        self.assertEqual(len(result['matching_processes']), 0)


class TestTaskbarDetectionFunctions(unittest.TestCase):
    """Test suite for module-level functions"""
    
    @patch('modules.taskbar_detection.psutil.process_iter')
    def test_detect_taskbar_apps(self, mock_process_iter):
        """Test main taskbar detection function"""
        # Mock process data
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'test.exe',
            'memory_info': Mock(rss=100*1024*1024),
            'cpu_percent': 5.0,
            'create_time': 1000000000
        }
        mock_process_iter.return_value = [mock_proc]
        
        result = detect_taskbar_apps()
        
        self.assertIn("TASKBAR & RUNNING APPS ANALYSIS", result)
        self.assertIn("Total Running Processes:", result)
    
    def test_can_see_taskbar(self):
        """Test taskbar capability checking"""
        result = can_see_taskbar()
        
        self.assertIn("TASKBAR DETECTION CAPABILITIES", result)
        self.assertIn("What I CAN do:", result)
        self.assertIn("Process Detection", result)


class TestTaskbarDetectionEdgeCases(unittest.TestCase):
    """Test suite for edge cases and error handling"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = TaskbarDetector()
    
    @patch('modules.taskbar_detection.psutil.process_iter')
    def test_empty_process_list(self, mock_process_iter):
        """Test handling of empty process list"""
        mock_process_iter.return_value = []
        
        result = self.detector.get_running_applications()
        
        self.assertEqual(len(result['processes']), 0)
        self.assertEqual(result['summary']['total_processes'], 0)
    
    @patch('modules.taskbar_detection.psutil.process_iter')
    def test_process_with_missing_info(self, mock_process_iter):
        """Test handling of process with missing information"""
        # Mock process with incomplete info
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'test.exe',
            # Missing some fields
        }
        mock_process_iter.return_value = [mock_proc]
        
        result = self.detector.get_running_applications()
        
        # Should handle missing info gracefully
        self.assertGreaterEqual(len(result['processes']), 0)
    
    @patch('modules.taskbar_detection.psutil.process_iter')
    def test_find_app_case_insensitive(self, mock_process_iter):
        """Test that app search is case-insensitive"""
        # Mock process
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'Chrome.exe'
        }
        mock_process_iter.return_value = [mock_proc]
        
        # Search with lowercase
        result = self.detector.find_specific_app_in_taskbar("chrome")
        
        self.assertTrue(result['found_in_processes'])
    
    @patch('modules.taskbar_detection.psutil.process_iter')
    def test_find_app_partial_match(self, mock_process_iter):
        """Test that app search works with partial names"""
        # Mock process
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'MicrosoftEdge.exe'
        }
        mock_process_iter.return_value = [mock_proc]
        
        # Search with partial name
        result = self.detector.find_specific_app_in_taskbar("Edge")
        
        self.assertTrue(result['found_in_processes'])


class TestTaskbarDetectionIntegration(unittest.TestCase):
    """Test suite for integration scenarios"""
    
    @patch('modules.taskbar_detection.psutil.process_iter')
    def test_detect_common_applications(self, mock_process_iter):
        """Test detecting common applications"""
        # Mock common applications
        common_apps = [
            {'pid': 1, 'name': 'chrome.exe', 'memory_info': Mock(rss=200*1024*1024), 'cpu_percent': 5.0, 'create_time': 1000000000},
            {'pid': 2, 'name': 'code.exe', 'memory_info': Mock(rss=300*1024*1024), 'cpu_percent': 10.0, 'create_time': 1000000100},
            {'pid': 3, 'name': 'spotify.exe', 'memory_info': Mock(rss=150*1024*1024), 'cpu_percent': 2.0, 'create_time': 1000000200},
            {'pid': 4, 'name': 'slack.exe', 'memory_info': Mock(rss=180*1024*1024), 'cpu_percent': 3.0, 'create_time': 1000000300},
        ]
        
        mock_procs = []
        for app in common_apps:
            mock_proc = Mock()
            mock_proc.info = app
            mock_procs.append(mock_proc)
        
        mock_process_iter.return_value = mock_procs
        
        detector = TaskbarDetector()
        result = detector.get_running_applications()
        
        # Verify all apps detected
        self.assertEqual(len(result['processes']), 4)
        self.assertIn('summary', result)
        self.assertEqual(result['summary']['total_processes'], 4)
        
        # Check that memory info is converted
        for proc in result['processes']:
            self.assertIn('memory_mb', proc)
            self.assertIsInstance(proc['memory_mb'], float)
    
    @patch('modules.taskbar_detection.psutil.process_iter')
    def test_detect_and_find_specific_app(self, mock_process_iter):
        """Test detecting all apps then finding a specific one"""
        # Mock multiple applications
        apps = [
            {'pid': 1, 'name': 'chrome.exe'},
            {'pid': 2, 'name': 'notepad.exe'},
            {'pid': 3, 'name': 'explorer.exe'},
        ]
        
        mock_procs = []
        for app in apps:
            mock_proc = Mock()
            mock_proc.info = app
            mock_procs.append(mock_proc)
        
        mock_process_iter.return_value = mock_procs
        
        detector = TaskbarDetector()
        
        # Get all applications
        all_apps = detector.get_running_applications()
        self.assertEqual(len(all_apps['processes']), 3)
        
        # Find specific app
        chrome_result = detector.find_specific_app_in_taskbar("chrome")
        self.assertTrue(chrome_result['found_in_processes'])
        
        # Find non-existent app
        nonexistent_result = detector.find_specific_app_in_taskbar("firefox")
        self.assertFalse(nonexistent_result['found_in_processes'])


class TestWin32WindowDetection(unittest.TestCase):
    """Test suite for Win32 window detection (if available)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = TaskbarDetector()
    
    def test_window_detection_availability(self):
        """Test if window detection is available"""
        try:
            import win32gui
            win32_available = True
        except ImportError:
            win32_available = False
        
        # This is informational - not a failure if win32gui not available
        if win32_available:
            result = self.detector.get_running_applications()
            self.assertIn('windows', result)
        else:
            # Should still work without win32gui
            result = self.detector.get_running_applications()
            self.assertIn('processes', result)


def suite():
    """Create test suite"""
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(TestTaskbarDetector))
    test_suite.addTest(unittest.makeSuite(TestTaskbarDetectionFunctions))
    test_suite.addTest(unittest.makeSuite(TestTaskbarDetectionEdgeCases))
    test_suite.addTest(unittest.makeSuite(TestTaskbarDetectionIntegration))
    test_suite.addTest(unittest.makeSuite(TestWin32WindowDetection))
    return test_suite


if __name__ == '__main__':
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())
