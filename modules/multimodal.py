# Multi-Modal AI Integration Module
"""
Advanced multi-modal AI capabilities including computer vision, screen analysis,
image generation, and visual question answering.

Features:
- Screen capture and analysis
- Image understanding and description
- Visual question answering
- Document/image text extraction
- Real-time visual monitoring
- Image generation capabilities
"""

import base64
import io
import os
import json
import time
from typing import Optional, Dict, List, Tuple, Any
from PIL import Image, ImageGrab, ImageDraw, ImageFont
import google.generativeai as genai
from datetime import datetime
import threading
import asyncio

class MultiModalAI:
    """Advanced multi-modal AI system for visual understanding and generation."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the multi-modal AI system with API key validation."""
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")
        
        # Validate API key format (basic check)
        if not self.api_key.startswith(('AI', 'sk-')) or len(self.api_key) < 20:
            raise ValueError("Invalid GEMINI_API_KEY format. Please check your API key.")
        
        # Configure Gemini
        try:
            genai.configure(api_key=self.api_key)
        except Exception as e:
            raise ValueError(f"Failed to configure Gemini API: {e}")
        
        # Initialize models
        try:
            self.vision_model = genai.GenerativeModel('gemini-2.5-flash')
            self.text_model = genai.GenerativeModel('gemini-2.5-flash')
        except Exception as e:
            raise ValueError(f"Failed to initialize Gemini models: {e}")
        
        # Screen monitoring
        self.is_monitoring = False
        self.monitor_thread = None
        self.last_screenshot = None
        self.last_screenshot_time = None
        
        # Enhanced screenshot caching with hash-based deduplication
        self.screenshot_cache = {}  # hash -> (image, analysis, timestamp)
        self.cache_max_size = 10
        self.cache_expiry_seconds = 300  # 5 minutes
        
        # Analysis history
        self.analysis_history = []
        
    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None, use_cache: bool = True) -> Image.Image:
        """
        Capture screenshot of the entire screen or specific region with caching.
        
        Args:
            region: (left, top, right, bottom) coordinates for partial capture
            use_cache: Whether to use cached screenshot if available
            
        Returns:
            PIL Image object
        """
        try:
            # Check if we can use cached screenshot
            if use_cache and self.last_screenshot and self.last_screenshot_time:
                time_diff = time.time() - self.last_screenshot_time
                if time_diff < 2.0:  # Use cache if less than 2 seconds old
                    return self.last_screenshot
            
            # Capture new screenshot
            if region:
                # Validate region coordinates
                if not all(isinstance(x, int) for x in region) or len(region) != 4:
                    raise ValueError("Region must be tuple of 4 integers (left, top, right, bottom)")
                if region[0] >= region[2] or region[1] >= region[3]:
                    raise ValueError("Invalid region coordinates")
                screenshot = ImageGrab.grab(bbox=region)
            else:
                screenshot = ImageGrab.grab()
            
            self.last_screenshot = screenshot
            self.last_screenshot_time = time.time()
            self._cleanup_old_cache()
            return screenshot
            
        except Exception as e:
            print(f"Error capturing screen: {e}")
            return None
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string."""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    
    def _image_hash(self, image: Image.Image) -> str:
        """Generate hash for image to check cache."""
        import hashlib
        buffered = io.BytesIO()
        # Use smaller size for hash to improve performance
        thumb = image.copy()
        thumb.thumbnail((100, 100))
        thumb.save(buffered, format="PNG")
        return hashlib.md5(buffered.getvalue()).hexdigest()
    
    def _cleanup_old_cache(self):
        """Remove expired items from screenshot cache."""
        current_time = time.time()
        to_remove = []
        
        for key, (img, analysis, timestamp) in self.screenshot_cache.items():
            if current_time - timestamp > self.cache_expiry_seconds:
                to_remove.append(key)
        
        for key in to_remove:
            del self.screenshot_cache[key]
        
        # Limit cache size
        if len(self.screenshot_cache) > self.cache_max_size:
            # Remove oldest entries
            sorted_items = sorted(self.screenshot_cache.items(), key=lambda x: x[1][2])
            for key, _ in sorted_items[:len(self.screenshot_cache) - self.cache_max_size]:
                del self.screenshot_cache[key]
    
    def analyze_image(self, image: Image.Image, prompt: str = "Describe what you see in this image", use_cache: bool = True) -> Dict[str, Any]:
        """
        Analyze an image using Gemini Vision with caching support.
        
        Args:
            image: PIL Image object
            prompt: Analysis prompt
            use_cache: Whether to use cached analysis if available
            
        Returns:
            Analysis results dictionary
        """
        try:
            # Check cache first
            if use_cache:
                img_hash = self._image_hash(image)
                cache_key = f"{img_hash}_{prompt}"
                
                if cache_key in self.screenshot_cache:
                    cached_img, cached_analysis, cached_time = self.screenshot_cache[cache_key]
                    if time.time() - cached_time < self.cache_expiry_seconds:
                        print("Using cached analysis")
                        return cached_analysis
            
            # Optimize image size for API
            optimized_image = self._optimize_image(image)
            
            # Prepare the prompt and image
            response = self.vision_model.generate_content([prompt, optimized_image])
            
            result = {
                "timestamp": datetime.now().isoformat(),
                "prompt": prompt,
                "analysis": response.text,
                "confidence": "high",  # Gemini doesn't provide confidence scores
                "image_info": {
                    "size": image.size,
                    "mode": image.mode,
                    "format": getattr(image, 'format', 'Unknown')
                },
                "cached": False
            }
            
            # Cache the result
            if use_cache:
                img_hash = self._image_hash(image)
                cache_key = f"{img_hash}_{prompt}"
                self.screenshot_cache[cache_key] = (image, result, time.time())
            
            # Add to history
            self.analysis_history.append(result)
            
            return result
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "prompt": prompt,
                "analysis": f"Error analyzing image: {str(e)}",
                "confidence": "error",
                "image_info": None
            }
    
    def analyze_screen(self, prompt: str = "What's currently on the screen?", region: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        """
        Analyze current screen content.
        
        Args:
            prompt: Analysis prompt
            region: Optional screen region to analyze
            
        Returns:
            Analysis results
        """
        screenshot = self.capture_screen(region)
        if not screenshot:
            return {"error": "Failed to capture screen"}
        
        return self.analyze_image(screenshot, prompt)
    
    def answer_visual_question(self, question: str, image: Optional[Image.Image] = None) -> str:
        """
        Answer questions about visual content.
        
        Args:
            question: Question about the image/screen
            image: Optional image, if None uses current screen
            
        Returns:
            Answer string
        """
        if image is None:
            image = self.capture_screen()
        
        if not image:
            return "Sorry, I couldn't capture the screen to answer your question."
        
        try:
            prompt = f"Question: {question}\n\nPlease provide a clear, concise answer based on what you see in the image."
            result = self.analyze_image(image, prompt)
            return result.get("analysis", "Sorry, I couldn't analyze the image.")
            
        except Exception as e:
            return f"Error answering visual question: {str(e)}"
    
    def extract_text_from_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Dict[str, Any]:
        """
        Extract text from screen using AI vision.
        
        Args:
            region: Optional screen region
            
        Returns:
            Extracted text and metadata
        """
        screenshot = self.capture_screen(region)
        if not screenshot:
            return {"error": "Failed to capture screen"}
        
        prompt = """Extract all visible text from this image. 
        Return the text in a structured format, preserving any formatting, headers, or organization you can detect.
        If there are UI elements like buttons or menus, include those too."""
        
        result = self.analyze_image(screenshot, prompt)
        
        return {
            "extracted_text": result.get("analysis", ""),
            "timestamp": result.get("timestamp"),
            "region": region,
            "success": "analysis" in result
        }
    
    def describe_ui_elements(self, detailed: bool = False) -> Dict[str, Any]:
        """
        Describe UI elements on the current screen.
        
        Args:
            detailed: Whether to provide detailed descriptions
            
        Returns:
            UI element descriptions
        """
        screenshot = self.capture_screen()
        if not screenshot:
            return {"error": "Failed to capture screen"}
        
        if detailed:
            prompt = """Analyze this screenshot and provide a detailed description of all UI elements including:
            - Windows and applications visible
            - Buttons, menus, and interactive elements
            - Text content and labels
            - Layout and organization
            - Any notable features or states
            
            Format the response in a structured way."""
        else:
            prompt = "Briefly describe the main UI elements and applications visible on this screen."
        
        result = self.analyze_image(screenshot, prompt)
        return {
            "ui_description": result.get("analysis", ""),
            "timestamp": result.get("timestamp"),
            "detailed": detailed
        }
    
    def find_ui_element(self, element_description: str) -> Dict[str, Any]:
        """
        Find and locate specific UI elements on screen.
        
        Args:
            element_description: Description of the element to find
            
        Returns:
            Element location and information
        """
        screenshot = self.capture_screen()
        if not screenshot:
            return {"error": "Failed to capture screen"}
        
        prompt = f"""Look for the following UI element: "{element_description}"
        
        If you find it, describe:
        1. Where it is located (top/bottom/left/right/center of screen)
        2. What it looks like
        3. Its current state (enabled/disabled/selected/etc.)
        4. How to interact with it
        
        If you don't find it, explain what you do see that might be similar."""
        
        result = self.analyze_image(screenshot, prompt)
        return {
            "element_found": "found" in result.get("analysis", "").lower(),
            "description": result.get("analysis", ""),
            "timestamp": result.get("timestamp")
        }
    
    def monitor_screen_changes(self, callback: callable = None, interval: float = 2.0):
        """
        Monitor screen for changes and trigger callback.
        
        Args:
            callback: Function to call when changes detected
            interval: Check interval in seconds
        """
        def monitor_loop():
            previous_analysis = None
            
            while self.is_monitoring:
                try:
                    # Capture and analyze current screen
                    current_analysis = self.analyze_screen("Briefly describe what's on screen")
                    
                    # Compare with previous
                    if previous_analysis and current_analysis != previous_analysis:
                        if callback:
                            callback(current_analysis, previous_analysis)
                    
                    previous_analysis = current_analysis
                    time.sleep(interval)
                    
                except Exception as e:
                    print(f"Monitor error: {e}")
                    time.sleep(interval)
        
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
            self.monitor_thread.start()
            return "Screen monitoring started"
        else:
            return "Screen monitoring already active"
    
    def stop_monitoring(self):
        """Stop screen monitoring."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        return "Screen monitoring stopped"
    
    def generate_image_description(self, detailed: bool = True) -> str:
        """
        Generate a comprehensive description of current screen.
        
        Args:
            detailed: Whether to provide detailed analysis
            
        Returns:
            Description string
        """
        screenshot = self.capture_screen()
        if not screenshot:
            return "Unable to capture screen for description"
        
        if detailed:
            prompt = """Provide a comprehensive description of this screenshot including:
            1. Overall layout and design
            2. Main applications or windows
            3. Text content summary
            4. Interactive elements
            5. Visual hierarchy
            6. Color scheme and styling
            7. Any notable details or anomalies
            
            Write this as a detailed report."""
        else:
            prompt = "Provide a concise description of what's shown in this screenshot."
        
        result = self.analyze_image(screenshot, prompt)
        return result.get("analysis", "Unable to generate description")
    
    def save_screenshot_with_analysis(self, filename: str = None, include_analysis: bool = True) -> str:
        """
        Save current screenshot with optional AI analysis.
        
        Args:
            filename: Optional filename, auto-generated if None
            include_analysis: Whether to save analysis as companion file
            
        Returns:
            Status message
        """
        screenshot = self.capture_screen()
        if not screenshot:
            return "Failed to capture screenshot"
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        try:
            # Save screenshot
            screenshot.save(filename)
            result_message = f"Screenshot saved as {filename}"
            
            # Save analysis if requested
            if include_analysis:
                analysis = self.analyze_image(screenshot, "Analyze this screenshot comprehensively")
                analysis_filename = filename.replace(".png", "_analysis.json")
                
                with open(analysis_filename, 'w', encoding='utf-8') as f:
                    json.dump(analysis, f, indent=2, ensure_ascii=False)
                
                result_message += f"\nAnalysis saved as {analysis_filename}"
            
            return result_message
            
        except Exception as e:
            return f"Error saving screenshot: {str(e)}"
    
    def get_analysis_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent analysis history."""
        return self.analysis_history[-limit:]
    
    def clear_analysis_history(self):
        """Clear analysis history."""
        self.analysis_history.clear()
        return "Analysis history cleared"
    
    def _optimize_image(self, image: Image.Image, max_size: Tuple[int, int] = (1920, 1080)) -> Image.Image:
        """Optimize image size for API processing while maintaining quality."""
        if image.size[0] <= max_size[0] and image.size[1] <= max_size[1]:
            return image
        
        # Calculate aspect ratio
        aspect = image.size[0] / image.size[1]
        
        if aspect > max_size[0] / max_size[1]:
            new_width = max_size[0]
            new_height = int(new_width / aspect)
        else:
            new_height = max_size[1]
            new_width = int(new_height * aspect)
        
        optimized = image.copy()
        optimized.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
        return optimized
    
    def clear_cache(self):
        """Clear screenshot and analysis cache."""
        self.screenshot_cache.clear()
        self.last_screenshot = None
        self.last_screenshot_time = None
        return "Cache cleared successfully"
    
    def analyze_video(self, video_path: str, prompt: str = "Describe this video", 
                      max_frames: int = 10, frame_interval: Optional[int] = None) -> Dict[str, Any]:
        """
        Analyze a video by extracting and analyzing key frames.
        
        Args:
            video_path: Path to the video file
            prompt: Analysis prompt
            max_frames: Maximum number of frames to extract (default: 10)
            frame_interval: Frame interval for extraction (auto-calculated if None)
            
        Returns:
            Dict with video analysis results
        """
        try:
            import cv2
        except ImportError:
            return {
                "success": False,
                "error": "opencv-python not installed. Install with: pip install opencv-python"
            }
        
        if not os.path.exists(video_path):
            return {"success": False, "error": "Video file not found"}
        
        try:
            # Open video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"success": False, "error": "Failed to open video file"}
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            print(f"📹 Video: {duration:.2f}s, {frame_count} frames, {fps:.1f} fps, {width}x{height}")
            
            # Calculate frame interval if not provided
            if frame_interval is None:
                frame_interval = max(1, frame_count // max_frames)
            
            # Extract key frames
            frames = []
            frame_timestamps = []
            frame_num = 0
            
            while len(frames) < max_frames and frame_num < frame_count:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = cap.read()
                
                if ret:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(frame_rgb)
                    frames.append(pil_image)
                    
                    # Calculate timestamp
                    timestamp = frame_num / fps if fps > 0 else 0
                    frame_timestamps.append(timestamp)
                
                frame_num += frame_interval
            
            cap.release()
            
            if not frames:
                return {"success": False, "error": "No frames extracted from video"}
            
            print(f"🎞️ Extracted {len(frames)} frames for analysis")
            
            # Analyze each frame
            frame_analyses = []
            for i, (frame, timestamp) in enumerate(zip(frames, frame_timestamps)):
                print(f"🔍 Analyzing frame {i+1}/{len(frames)} at {timestamp:.1f}s...")
                
                result = self.analyze_image(
                    frame,
                    f"{prompt} (Frame at {timestamp:.1f}s)"
                )
                
                # Check if analysis was successful (has analysis text and no error)
                if result.get("analysis") and result.get("confidence") != "error":
                    frame_analyses.append({
                        "frame_number": i + 1,
                        "timestamp": timestamp,
                        "description": result.get("analysis", "")
                    })
            
            if not frame_analyses:
                return {"success": False, "error": "Failed to analyze any frames"}
            
            # Generate comprehensive summary using all frame descriptions
            print("📝 Generating video summary...")
            summary_prompt = f"""Based on these frame descriptions from a video, provide a comprehensive summary:

Video Duration: {duration:.1f} seconds
Frames Analyzed: {len(frame_analyses)}

Frame Descriptions:
{chr(10).join(f"[{fa['timestamp']:.1f}s] {fa['description']}" for fa in frame_analyses)}

Please provide:
1. Overall summary of the video content
2. Key events or changes that occur
3. Main subjects or objects visible
4. Any notable activities or actions
5. Overall theme or purpose of the video
"""
            
            summary_response = self.vision_model.generate_content(summary_prompt)
            
            return {
                "success": True,
                "video_path": video_path,
                "video_properties": {
                    "duration": duration,
                    "fps": fps,
                    "frame_count": frame_count,
                    "resolution": f"{width}x{height}"
                },
                "frames_analyzed": len(frame_analyses),
                "frame_descriptions": frame_analyses,
                "summary": summary_response.text,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Video analysis error: {str(e)}"
            }

# Convenience functions for easy access
def analyze_current_screen(prompt: str = "What's on the screen?") -> str:
    """Quick function to analyze current screen."""
    try:
        ai = MultiModalAI()
        result = ai.analyze_screen(prompt)
        return result.get("analysis", "Unable to analyze screen")
    except Exception as e:
        return f"Error: {str(e)}"

def answer_visual_question_quick(question: str) -> str:
    """Quick function to answer visual questions about current screen."""
    try:
        ai = MultiModalAI()
        return ai.answer_visual_question(question)
    except Exception as e:
        return f"Error: {str(e)}"

def extract_screen_text() -> str:
    """Quick function to extract text from current screen."""
    try:
        ai = MultiModalAI()
        result = ai.extract_text_from_screen()
        return result.get("extracted_text", "No text found")
    except Exception as e:
        return f"Error: {str(e)}"

def describe_current_screen() -> str:
    """Quick function to describe current screen."""
    try:
        ai = MultiModalAI()
        return ai.generate_image_description()
    except Exception as e:
        return f"Error: {str(e)}"

def analyze_video_file(video_path: str, prompt: str = "Describe this video") -> str:
    """Quick function to analyze a video file."""
    try:
        ai = MultiModalAI()
        result = ai.analyze_video(video_path, prompt)
        if result.get("success"):
            return f"📹 Video Analysis:\n\n{result['summary']}\n\n📊 Details: {result['frames_analyzed']} frames analyzed from {result['video_properties']['duration']:.1f}s video"
        else:
            return f"Error: {result.get('error', 'Unknown error')}"
    except Exception as e:
        return f"Error: {str(e)}"

# Export main functions
__all__ = [
    'MultiModalAI',
    'analyze_current_screen',
    'answer_visual_question_quick',
    'extract_screen_text',
    'describe_current_screen',
    'analyze_video_file'
]