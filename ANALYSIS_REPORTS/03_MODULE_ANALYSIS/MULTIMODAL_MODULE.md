# 🎥 Multimodal Module Analysis

**File:** `modules/multimodal.py`, `setup_multimodal.py`  
**Lines of Code:** 612  
**Status:** ⚠️ **PARTIALLY WORKING**  
**Test Coverage:** 0%  
**Last Updated:** November 17, 2025

---

## 📋 Functionality Overview

### Purpose
Provides multimodal AI capabilities using Google Gemini:
- Image analysis and understanding
- Screen capture and analysis
- Vision-based queries
- Multimodal conversation

### Features
- ✅ Screen capture
- ✅ Image file analysis
- ⚠️ Video analysis (basic)
- ❌ Audio analysis (not implemented)
- ⚠️ Multimodal conversation context

---

## 🐛 Critical Issues

### Issue #1: API Key Hardcoded 🔴
**File:** `modules/multimodal.py`  
**Line:** 23  
**Severity:** CRITICAL SECURITY

```python
GOOGLE_API_KEY = "AIzaSyBqN0ooaSDpL8wOh9pv_X9nC7aVpXzZgHQ"  # ❌ HARDCODED
```

**Already documented in Critical Issues & Security Reports**

---

### Issue #2: No Error Handling for API Calls 🔴
**Lines:** 156-180  
**Severity:** HIGH

```python
def analyze_image(self, image_path, prompt="Describe this image"):
    """Analyze image using Gemini Vision"""
    try:
        img = PIL.Image.open(image_path)
        # ❌ No API error handling
        # ❌ No rate limiting
        # ❌ No retry logic
        response = self.model.generate_content([prompt, img])
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"  # ❌ Generic error, no logging
```

**Fix - Add Proper Error Handling:**

```python
import time
import logging
from google.api_core.exceptions import GoogleAPIError, ResourceExhausted
from PIL import Image

class MultimodalModule:
    def __init__(self):
        # ...
        self.api_call_count = 0
        self.last_api_call = 0
        self.rate_limit_delay = 1  # seconds between calls
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def analyze_image(self, image_path, prompt="Describe this image", max_retries=3):
        """Analyze image using Gemini Vision with error handling"""
        
        # Validate image path
        if not os.path.exists(image_path):
            self.logger.error(f"Image not found: {image_path}")
            return {"success": False, "error": "Image file not found"}
        
        # Rate limiting
        self._rate_limit()
        
        for attempt in range(max_retries):
            try:
                # Load and validate image
                img = Image.open(image_path)
                
                # Check image size
                max_size = 10 * 1024 * 1024  # 10MB
                if os.path.getsize(image_path) > max_size:
                    self.logger.warning(f"Image too large: {os.path.getsize(image_path)} bytes")
                    img = self._resize_image(img)
                
                # Make API call
                self.logger.info(f"Analyzing image: {image_path}")
                response = self.model.generate_content([prompt, img])
                
                # Check if response was blocked
                if not response.text:
                    self.logger.warning("Response was blocked by safety filters")
                    return {
                        "success": False,
                        "error": "Content blocked by safety filters",
                        "safety_ratings": response.prompt_feedback.safety_ratings
                    }
                
                self.api_call_count += 1
                self.last_api_call = time.time()
                
                return {
                    "success": True,
                    "text": response.text,
                    "image_path": image_path,
                    "prompt": prompt
                }
                
            except ResourceExhausted as e:
                self.logger.error(f"API quota exceeded: {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    return {
                        "success": False,
                        "error": "API quota exceeded. Please try again later."
                    }
            
            except GoogleAPIError as e:
                self.logger.error(f"Google API error: {e}")
                return {
                    "success": False,
                    "error": f"API error: {str(e)}"
                }
            
            except Exception as e:
                self.logger.error(f"Unexpected error analyzing image: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": f"Failed to analyze image: {str(e)}"
                }
        
        return {
            "success": False,
            "error": "Max retries exceeded"
        }
    
    def _rate_limit(self):
        """Implement rate limiting for API calls"""
        elapsed = time.time() - self.last_api_call
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
    
    def _resize_image(self, img, max_dimension=2048):
        """Resize image if too large"""
        if max(img.size) > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        return img
```

---

### Issue #3: Screen Capture Has No Cleanup 🟡
**Lines:** 89-110  
**Severity:** MODERATE

```python
def capture_screen(self):
    """Capture screenshot"""
    try:
        screenshot = pyautogui.screenshot()
        temp_path = "temp_screenshot.png"
        screenshot.save(temp_path)
        # ❌ File never deleted
        # ❌ Overwrites same file repeatedly
        # ❌ No timestamp in filename
        return temp_path
    except Exception as e:
        return None
```

**Fix - Better Screen Capture:**

```python
import pyautogui
import tempfile
from datetime import datetime
from pathlib import Path

class MultimodalModule:
    def __init__(self):
        # ...
        self.temp_dir = Path(tempfile.gettempdir()) / "yourdaddy_screenshots"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Track temp files for cleanup
        self.temp_files = []
        
    def capture_screen(self, region=None):
        """Capture screenshot with automatic cleanup"""
        try:
            # Generate unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"screenshot_{timestamp}.png"
            filepath = self.temp_dir / filename
            
            # Capture screenshot
            if region:
                # Capture specific region (x, y, width, height)
                screenshot = pyautogui.screenshot(region=region)
            else:
                # Capture full screen
                screenshot = pyautogui.screenshot()
            
            # Save
            screenshot.save(filepath)
            
            # Track for cleanup
            self.temp_files.append(filepath)
            
            self.logger.info(f"Screenshot saved: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Screenshot capture failed: {e}")
            return None
    
    def analyze_screen(self, prompt="What do you see on the screen?"):
        """Capture and analyze current screen"""
        screenshot_path = self.capture_screen()
        
        if not screenshot_path:
            return {"success": False, "error": "Failed to capture screenshot"}
        
        result = self.analyze_image(screenshot_path, prompt)
        
        # Clean up after analysis
        self._cleanup_temp_file(screenshot_path)
        
        return result
    
    def _cleanup_temp_file(self, filepath):
        """Delete temporary file"""
        try:
            path = Path(filepath)
            if path.exists():
                path.unlink()
                if path in self.temp_files:
                    self.temp_files.remove(path)
                self.logger.debug(f"Cleaned up: {filepath}")
        except Exception as e:
            self.logger.warning(f"Failed to cleanup {filepath}: {e}")
    
    def cleanup_all_temp_files(self):
        """Clean up all temporary files"""
        for filepath in list(self.temp_files):
            self._cleanup_temp_file(filepath)
        
        # Remove old screenshots (older than 1 hour)
        import time
        current_time = time.time()
        
        for file in self.temp_dir.glob("screenshot_*.png"):
            file_age = current_time - file.stat().st_mtime
            if file_age > 3600:  # 1 hour
                try:
                    file.unlink()
                    self.logger.debug(f"Deleted old screenshot: {file}")
                except Exception as e:
                    self.logger.warning(f"Failed to delete {file}: {e}")
    
    def __del__(self):
        """Cleanup on object destruction"""
        self.cleanup_all_temp_files()
```

---

### Issue #4: Video Analysis Not Implemented 🔴
**Lines:** 285-295  
**Severity:** HIGH

```python
def analyze_video(self, video_path, prompt="Describe this video"):
    """Analyze video using Gemini"""
    # ❌ NOT IMPLEMENTED
    return "Video analysis not yet implemented"
```

**Fix - Implement Video Analysis:**

```python
import cv2
from pathlib import Path

class MultimodalModule:
    def analyze_video(self, video_path, prompt="Describe this video", 
                      frame_interval=30, max_frames=10):
        """Analyze video by extracting and analyzing key frames"""
        
        if not os.path.exists(video_path):
            return {"success": False, "error": "Video file not found"}
        
        try:
            # Open video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"success": False, "error": "Failed to open video"}
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            
            self.logger.info(f"Video: {duration:.2f}s, {frame_count} frames, {fps} fps")
            
            # Extract key frames
            frames = []
            frame_num = 0
            
            while len(frames) < max_frames and frame_num < frame_count:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    frames.append(pil_image)
                
                frame_num += frame_interval
            
            cap.release()
            
            if not frames:
                return {"success": False, "error": "No frames extracted"}
            
            # Analyze each frame
            frame_analyses = []
            for i, frame in enumerate(frames):
                # Save frame temporarily
                temp_frame_path = self.temp_dir / f"frame_{i}.jpg"
                frame.save(temp_frame_path)
                
                # Analyze
                result = self.analyze_image(
                    str(temp_frame_path),
                    f"{prompt} (Frame {i+1}/{len(frames)})"
                )
                
                if result["success"]:
                    frame_analyses.append(result["text"])
                
                # Cleanup
                self._cleanup_temp_file(temp_frame_path)
            
            # Generate summary
            summary_prompt = f"""
            Based on these frame descriptions from a video:
            {chr(10).join(f"{i+1}. {desc}" for i, desc in enumerate(frame_analyses))}
            
            Provide a cohesive summary of the video content.
            """
            
            summary_response = self.model.generate_content(summary_prompt)
            
            return {
                "success": True,
                "video_path": video_path,
                "duration": duration,
                "frames_analyzed": len(frames),
                "frame_descriptions": frame_analyses,
                "summary": summary_response.text
            }
            
        except Exception as e:
            self.logger.error(f"Video analysis failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Video analysis error: {str(e)}"
            }
```

---

### Issue #5: No Conversation Context Management 🟡
**Lines:** 340-360  
**Severity:** MODERATE

```python
def multimodal_conversation(self, user_input, image_path=None):
    """Handle multimodal conversation"""
    # ❌ No conversation history
    # ❌ No context retention
    # ❌ Each message is isolated
    
    if image_path:
        img = PIL.Image.open(image_path)
        response = self.model.generate_content([user_input, img])
    else:
        response = self.model.generate_content(user_input)
    
    return response.text
```

**Fix - Add Conversation Context:**

```python
class MultimodalModule:
    def __init__(self):
        # ...
        self.conversation_history = []
        self.max_history_length = 10
        self.conversation_context = []  # For images/media
    
    def multimodal_conversation(self, user_input, image_path=None, 
                                video_path=None, clear_context=False):
        """Handle multimodal conversation with context"""
        
        if clear_context:
            self.conversation_history = []
            self.conversation_context = []
            return {"success": True, "message": "Context cleared"}
        
        try:
            # Build conversation context
            conversation_parts = []
            
            # Add relevant history
            for item in self.conversation_history[-5:]:  # Last 5 messages
                conversation_parts.append(f"User: {item['user']}")
                conversation_parts.append(f"Assistant: {item['assistant']}")
            
            # Add current input
            conversation_parts.append(f"User: {user_input}")
            
            # Prepare content for API
            content_parts = ["\n".join(conversation_parts)]
            
            # Add media if provided
            if image_path and os.path.exists(image_path):
                img = Image.open(image_path)
                content_parts.append(img)
                self.conversation_context.append({
                    "type": "image",
                    "path": image_path
                })
            
            if video_path:
                # For video, analyze first then include summary
                video_result = self.analyze_video(video_path)
                if video_result["success"]:
                    content_parts.append(f"Video context: {video_result['summary']}")
            
            # Generate response
            response = self.model.generate_content(content_parts)
            
            # Store in history
            self.conversation_history.append({
                "user": user_input,
                "assistant": response.text,
                "timestamp": datetime.now().isoformat(),
                "media": {
                    "image": image_path,
                    "video": video_path
                }
            })
            
            # Trim history
            if len(self.conversation_history) > self.max_history_length:
                self.conversation_history = self.conversation_history[-self.max_history_length:]
            
            return {
                "success": True,
                "response": response.text,
                "conversation_length": len(self.conversation_history)
            }
            
        except Exception as e:
            self.logger.error(f"Conversation error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_conversation_history(self):
        """Get conversation history"""
        return self.conversation_history
    
    def clear_conversation_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.conversation_context = []
```

---

## 🧪 Testing Requirements

```python
# test_multimodal.py
import pytest
import os
from modules.multimodal import MultimodalModule
from PIL import Image

@pytest.fixture
def mm_module():
    return MultimodalModule()

@pytest.fixture
def test_image(tmp_path):
    """Create a test image"""
    img = Image.new('RGB', (100, 100), color='red')
    img_path = tmp_path / "test.png"
    img.save(img_path)
    return str(img_path)

def test_image_analysis(mm_module, test_image):
    """Test image analysis"""
    result = mm_module.analyze_image(test_image, "What color is this?")
    
    assert result["success"] == True
    assert "text" in result
    assert len(result["text"]) > 0

def test_screen_capture(mm_module):
    """Test screen capture"""
    screenshot_path = mm_module.capture_screen()
    
    assert screenshot_path is not None
    assert os.path.exists(screenshot_path)
    
    # Cleanup
    mm_module._cleanup_temp_file(screenshot_path)

def test_temp_file_cleanup(mm_module, test_image):
    """Test temporary file cleanup"""
    # Analyze image
    mm_module.analyze_image(test_image)
    
    # Cleanup
    mm_module.cleanup_all_temp_files()
    
    # Check all temp files are deleted
    assert len(mm_module.temp_files) == 0

def test_conversation_context(mm_module):
    """Test conversation context management"""
    # First message
    result1 = mm_module.multimodal_conversation("Hello")
    assert result1["success"] == True
    
    # Second message (should have context)
    result2 = mm_module.multimodal_conversation("What did I just say?")
    assert result2["success"] == True
    
    # Check history
    history = mm_module.get_conversation_history()
    assert len(history) == 2

def test_error_handling_invalid_image(mm_module):
    """Test error handling for invalid image"""
    result = mm_module.analyze_image("nonexistent.png")
    
    assert result["success"] == False
    assert "error" in result

def test_rate_limiting(mm_module, test_image):
    """Test rate limiting between API calls"""
    import time
    
    start = time.time()
    mm_module.analyze_image(test_image)
    mm_module.analyze_image(test_image)
    elapsed = time.time() - start
    
    # Should take at least rate_limit_delay seconds
    assert elapsed >= mm_module.rate_limit_delay
```

---

## 🔧 Fix Priority

### P0 - Critical (Week 1)
- [ ] Move API key to .env (5 min)
- [ ] Add proper error handling (3 hours)
- [ ] Add rate limiting (1 hour)
- [ ] Fix screen capture cleanup (1 hour)

### P1 - High (Week 2)
- [ ] Implement video analysis (4 hours)
- [ ] Add conversation context (3 hours)
- [ ] Add retry logic (1 hour)
- [ ] Write tests (4 hours)

### P2 - Medium (Week 3)
- [ ] Add audio analysis (4 hours)
- [ ] Optimize image processing (2 hours)
- [ ] Add progress callbacks (2 hours)
- [ ] Performance monitoring (2 hours)

**Total Effort:** 18-25 hours

---

**Priority:** 🟡 P1  
**Status:** Core working, needs robustness  
**Impact:** Medium - affects AI capabilities

**Next Report:** [Calendar Module →](CALENDAR_MODULE.md)
