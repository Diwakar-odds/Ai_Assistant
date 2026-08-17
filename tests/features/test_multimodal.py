"""
Unit tests for the Multimodal AI Module.
Tests image analysis, screen capture, caching, and API integration.
"""

import unittest
import os
import time
from unittest.mock import Mock, patch, MagicMock
from PIL import Image
from modules import multimodal


class TestMultiModalAI(unittest.TestCase):
    """Test suite for multi-modal AI functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Mock the Gemini API to avoid actual API calls
        self.mock_api_key = "AIza" + "S" * 30  # Valid format for testing
        os.environ["GEMINI_API_KEY"] = self.mock_api_key
    
    def tearDown(self):
        """Clean up after tests."""
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
    
    @patch('modules.multimodal.genai')
    def test_initialization_with_valid_key(self, mock_genai):
        """Test initialization with valid API key."""
        mock_genai.GenerativeModel.return_value = Mock()
        
        ai = multimodal.MultiModalAI(self.mock_api_key)
        
        self.assertIsNotNone(ai)
        self.assertEqual(ai.api_key, self.mock_api_key)
        mock_genai.configure.assert_called_once()
    
    def test_initialization_without_key(self):
        """Test initialization fails without API key."""
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        
        with self.assertRaises(ValueError) as context:
            multimodal.MultiModalAI()
        
        self.assertIn("API_KEY", str(context.exception))
    
    @patch('modules.multimodal.genai')
    def test_initialization_with_invalid_key_format(self, mock_genai):
        """Test initialization fails with invalid key format."""
        with self.assertRaises(ValueError) as context:
            multimodal.MultiModalAI("invalid_key_format")
        
        self.assertIn("Invalid", str(context.exception))
    
    @patch('modules.multimodal.ImageGrab')
    @patch('modules.multimodal.genai')
    def test_capture_screen(self, mock_genai, mock_imagegrab):
        """Test screen capture functionality."""
        mock_genai.GenerativeModel.return_value = Mock()
        mock_image = Image.new('RGB', (100, 100), color='red')
        mock_imagegrab.grab.return_value = mock_image
        
        ai = multimodal.MultiModalAI(self.mock_api_key)
        screenshot = ai.capture_screen()
        
        self.assertIsNotNone(screenshot)
        self.assertEqual(screenshot.size, (100, 100))
        mock_imagegrab.grab.assert_called()
    
    @patch('modules.multimodal.ImageGrab')
    @patch('modules.multimodal.genai')
    def test_capture_screen_with_region(self, mock_genai, mock_imagegrab):
        """Test screen capture with specific region."""
        mock_genai.GenerativeModel.return_value = Mock()
        mock_image = Image.new('RGB', (50, 50), color='blue')
        mock_imagegrab.grab.return_value = mock_image
        
        ai = multimodal.MultiModalAI(self.mock_api_key)
        region = (0, 0, 100, 100)
        screenshot = ai.capture_screen(region=region)
        
        self.assertIsNotNone(screenshot)
        mock_imagegrab.grab.assert_called_with(bbox=region)
    
    @patch('modules.multimodal.genai')
    def test_capture_screen_with_invalid_region(self, mock_genai):
        """Test screen capture with invalid region coordinates."""
        mock_genai.GenerativeModel.return_value = Mock()
        
        ai = multimodal.MultiModalAI(self.mock_api_key)
        
        # Invalid region (left >= right)
        with self.assertRaises(ValueError):
            ai.capture_screen(region=(100, 0, 50, 100))
    
    @patch('modules.multimodal.genai')
    def test_image_to_base64(self, mock_genai):
        """Test image to base64 conversion."""
        mock_genai.GenerativeModel.return_value = Mock()
        
        ai = multimodal.MultiModalAI(self.mock_api_key)
        test_image = Image.new('RGB', (10, 10), color='green')
        
        base64_str = ai.image_to_base64(test_image)
        
        self.assertIsInstance(base64_str, str)
        self.assertGreater(len(base64_str), 0)
    
    @patch('modules.multimodal.genai')
    def test_image_hashing(self, mock_genai):
        """Test image hashing for cache lookup."""
        mock_genai.GenerativeModel.return_value = Mock()
        
        ai = multimodal.MultiModalAI(self.mock_api_key)
        test_image = Image.new('RGB', (100, 100), color='red')
        
        hash1 = ai._image_hash(test_image)
        hash2 = ai._image_hash(test_image)
        
        # Same image should produce same hash
        self.assertEqual(hash1, hash2)
        
        # Different image should produce different hash
        different_image = Image.new('RGB', (100, 100), color='blue')
        hash3 = ai._image_hash(different_image)
        self.assertNotEqual(hash1, hash3)
    
    @patch('modules.multimodal.genai')
    def test_screenshot_caching(self, mock_genai):
        """Test screenshot caching mechanism."""
        mock_genai.GenerativeModel.return_value = Mock()
        mock_imagegrab = Mock()
        mock_image = Image.new('RGB', (100, 100), color='red')
        
        with patch('modules.multimodal.ImageGrab.grab', return_value=mock_image):
            ai = multimodal.MultiModalAI(self.mock_api_key)
            
            # First capture
            ai.capture_screen(use_cache=True)
            first_time = ai.last_screenshot_time
            
            # Second capture immediately (should use cache)
            time.sleep(0.1)
            ai.capture_screen(use_cache=True)
            second_time = ai.last_screenshot_time
            
            # Should be same (cached)
            self.assertEqual(first_time, second_time)
    
    @patch('modules.multimodal.genai')
    def test_cache_cleanup(self, mock_genai):
        """Test cache cleanup mechanism."""
        mock_genai.GenerativeModel.return_value = Mock()
        
        ai = multimodal.MultiModalAI(self.mock_api_key)
        
        # Add multiple items to cache
        test_image = Image.new('RGB', (10, 10), color='red')
        for i in range(15):
            cache_key = f"test_key_{i}"
            ai.screenshot_cache[cache_key] = (test_image, {"test": "data"}, time.time())
        
        # Trigger cleanup
        ai._cleanup_old_cache()
        
        # Cache should be limited to max_size (10)
        self.assertLessEqual(len(ai.screenshot_cache), ai.cache_max_size)
    
    @patch('modules.multimodal.genai')
    def test_analyze_image_with_caching(self, mock_genai):
        """Test image analysis with caching."""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Test analysis result"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        ai = multimodal.MultiModalAI(self.mock_api_key)
        test_image = Image.new('RGB', (100, 100), color='blue')
        
        # First analysis (should call API)
        result1 = ai.analyze_image(test_image, "Describe this image", use_cache=True)
        self.assertIn("analysis", result1)
        self.assertEqual(result1["cached"], False)
        
        # Second analysis (should use cache)
        result2 = ai.analyze_image(test_image, "Describe this image", use_cache=True)
        self.assertIn("analysis", result2)
    
    @patch('modules.multimodal.genai')
    def test_image_optimization(self, mock_genai):
        """Test image optimization for API calls."""
        mock_genai.GenerativeModel.return_value = Mock()
        
        ai = multimodal.MultiModalAI(self.mock_api_key)
        
        # Create large image
        large_image = Image.new('RGB', (3000, 2000), color='red')
        
        # Optimize
        optimized = ai._optimize_image(large_image)
        
        # Should be smaller than original
        self.assertLessEqual(optimized.size[0], 1920)
        self.assertLessEqual(optimized.size[1], 1080)
    
    @patch('modules.multimodal.genai')
    def test_clear_cache(self, mock_genai):
        """Test cache clearing."""
        mock_genai.GenerativeModel.return_value = Mock()
        
        ai = multimodal.MultiModalAI(self.mock_api_key)
        
        # Add items to cache
        test_image = Image.new('RGB', (10, 10), color='red')
        ai.screenshot_cache["test"] = (test_image, {"data": "test"}, time.time())
        ai.last_screenshot = test_image
        
        # Clear cache
        result = ai.clear_cache()
        
        self.assertEqual(len(ai.screenshot_cache), 0)
        self.assertIsNone(ai.last_screenshot)
        self.assertIn("cleared", result.lower())
    
    @patch('modules.multimodal.genai')
    def test_analysis_history(self, mock_genai):
        """Test analysis history tracking."""
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = "Analysis result"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        
        ai = multimodal.MultiModalAI(self.mock_api_key)
        test_image = Image.new('RGB', (10, 10), color='red')
        
        # Perform analyses
        ai.analyze_image(test_image, "Test 1", use_cache=False)
        ai.analyze_image(test_image, "Test 2", use_cache=False)
        
        # Check history
        history = ai.get_analysis_history(limit=10)
        self.assertEqual(len(history), 2)
        
        # Clear history
        ai.clear_analysis_history()
        self.assertEqual(len(ai.analysis_history), 0)


class TestMultiModalConvenienceFunctions(unittest.TestCase):
    """Test convenience functions."""
    
    @patch('modules.multimodal.MultiModalAI')
    def test_analyze_current_screen(self, mock_ai_class):
        """Test quick screen analysis function."""
        mock_ai = Mock()
        mock_ai.analyze_screen.return_value = {"analysis": "Test result"}
        mock_ai_class.return_value = mock_ai
        
        result = multimodal.analyze_current_screen("What's on screen?")
        
        self.assertIn("Test result", result)
    
    @patch('modules.multimodal.MultiModalAI')
    def test_answer_visual_question_quick(self, mock_ai_class):
        """Test quick visual question answering."""
        mock_ai = Mock()
        mock_ai.answer_visual_question.return_value = "Answer text"
        mock_ai_class.return_value = mock_ai
        
        result = multimodal.answer_visual_question_quick("What is this?")
        
        self.assertEqual(result, "Answer text")


if __name__ == '__main__':
    unittest.main(verbosity=2)
