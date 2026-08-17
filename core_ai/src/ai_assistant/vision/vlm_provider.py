"""
Abstract VLM Provider Interface

Provides a unified interface for different Vision Language Model providers
(Gemini Vision, OpenAI GPT-4V, Claude Vision, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    PIL_AVAILABLE = False
import json


@dataclass
class VLMResponse:
    """Standardized response from VLM providers."""
    
    text: str
    """Main text response from the VLM"""
    
    structured_data: Optional[Dict[str, Any]] = None
    """Structured data if JSON parsing was requested"""
    
    confidence: Optional[float] = None
    """Confidence score if available (0.0 - 1.0)"""
    
    provider: str = "unknown"
    """Name of the VLM provider used"""
    
    model: str = "unknown"
    """Specific model used"""
    
    timestamp: datetime = field(default_factory=datetime.now)
    """When this response was generated"""
    
    cached: bool = False
    """Whether this response came from cache"""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional provider-specific metadata"""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "text": self.text,
            "structured_data": self.structured_data,
            "confidence": self.confidence,
            "provider": self.provider,
            "model": self.model,
            "timestamp": self.timestamp.isoformat(),
            "cached": self.cached,
            "metadata": self.metadata
        }
    
    def extract_json(self) -> Optional[Dict[str, Any]]:
        """Attempt to extract JSON from text response."""
        if self.structured_data:
            return self.structured_data
        
        try:
            # Try to find JSON in the text
            import re
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, self.text, re.DOTALL)
            
            if matches:
                # Try to parse the first valid JSON
                for match in matches:
                    try:
                        parsed = json.loads(match)
                        self.structured_data = parsed
                        return parsed
                    except json.JSONDecodeError:
                        continue
            
            return None
        except Exception as e:
            print(f"Error extracting JSON: {e}")
            return None


class VLMProvider(ABC):
    """Abstract base class for Vision Language Model providers."""
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        """
        Initialize the VLM provider.
        
        Args:
            api_key: API key for the provider
            **kwargs: Additional provider-specific configuration
        """
        self.api_key = api_key
        self.config = kwargs
        self._cache = {}
        self._cache_enabled = kwargs.get('enable_cache', True)
        self._cache_ttl = kwargs.get('cache_ttl', 300)  # 5 minutes default
    
    @abstractmethod
    def analyze_image(
        self,
        image: Union[Image.Image, str],
        prompt: str,
        **kwargs
    ) -> VLMResponse:
        """
        Analyze an image with a text prompt.
        
        Args:
            image: PIL Image object or path to image file
            prompt: Text prompt describing what to analyze
            **kwargs: Provider-specific parameters
            
        Returns:
            VLMResponse with analysis results
        """
        pass
    
    @abstractmethod
    def extract_text(
        self,
        image: Union[Image.Image, str],
        **kwargs
    ) -> VLMResponse:
        """
        Extract text from an image (OCR).
        
        Args:
            image: PIL Image object or path to image file
            **kwargs: Provider-specific parameters
            
        Returns:
            VLMResponse with extracted text
        """
        pass
    
    @abstractmethod
    def detect_objects(
        self,
        image: Union[Image.Image, str],
        **kwargs
    ) -> VLMResponse:
        """
        Detect objects in an image.
        
        Args:
            image: PIL Image object or path to image file
            **kwargs: Provider-specific parameters
            
        Returns:
            VLMResponse with detected objects
        """
        pass
    
    def extract_ui_elements(
        self,
        image: Union[Image.Image, str],
        element_type: Optional[str] = None,
        **kwargs
    ) -> VLMResponse:
        """
        Extract UI elements from a screenshot.
        
        Args:
            image: Screenshot image
            element_type: Type of element to find (button, input, menu, etc.)
            **kwargs: Provider-specific parameters
            
        Returns:
            VLMResponse with UI element information
        """
        if element_type:
            prompt = f"""Analyze this screenshot and find all {element_type} elements.
            
For each element, provide:
1. Element type
2. Text/label
3. Approximate location (top-left, center, etc.)
4. Whether it's clickable/interactive

Return as JSON array:
[{{"type": "...", "text": "...", "location": "...", "clickable": true/false}}]
"""
        else:
            prompt = """Analyze this screenshot and identify all interactive UI elements.

For each element, provide:
1. Element type (button, input, menu, link, etc.)
2. Text/label
3. Approximate location
4. Whether it's clickable/interactive

Return as JSON array.
"""
        
        return self.analyze_image(image, prompt, **kwargs)
    
    def find_element_coordinates(
        self,
        image: Union[Image.Image, str],
        element_description: str,
        **kwargs
    ) -> VLMResponse:
        """
        Find pixel coordinates of a specific UI element.
        
        Args:
            image: Screenshot image
            element_description: Description of element to find
            **kwargs: Provider-specific parameters
            
        Returns:
            VLMResponse with coordinate information
        """
        prompt = f"""Find this UI element: "{element_description}"

Return ONLY a JSON object with this structure:
{{
    "found": true/false,
    "element_type": "button/input/menu/etc",
    "text": "element text if any",
    "location": "top-left/center/bottom-right/etc",
    "coordinates": {{"x": estimated_pixel_x, "y": estimated_pixel_y}},
    "clickable": true/false,
    "confidence": "high/medium/low"
}}

If not found, set found to false and explain why in a "reason" field.
"""
        
        response = self.analyze_image(image, prompt, **kwargs)
        
        # Try to extract structured coordinates
        coords = response.extract_json()
        if coords:
            response.structured_data = coords
        
        return response
    
    def compare_images(
        self,
        image1: Union[Image.Image, str],
        image2: Union[Image.Image, str],
        **kwargs
    ) -> VLMResponse:
        """
        Compare two images and describe differences.
        
        Args:
            image1: First image
            image2: Second image
            **kwargs: Provider-specific parameters
            
        Returns:
            VLMResponse with comparison results
        """
        # Most VLMs don't support multi-image input yet
        # Implement in subclass if available
        raise NotImplementedError("Multi-image comparison not supported by this provider")
    
    def _get_cache_key(self, image: Any, prompt: str) -> str:
        """Generate cache key for image + prompt combination."""
        import hashlib
        
        # Create hash from prompt
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:16]
        
        # Create hash from image
        if isinstance(image, Image.Image):
            import io
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_hash = hashlib.md5(buffer.getvalue()).hexdigest()[:16]
        elif isinstance(image, str):
            image_hash = hashlib.md5(image.encode()).hexdigest()[:16]
        else:
            image_hash = "unknown"
        
        return f"{image_hash}_{prompt_hash}"
    
    def _check_cache(self, cache_key: str) -> Optional[VLMResponse]:
        """Check if response is in cache and still valid."""
        if not self._cache_enabled:
            return None
        
        if cache_key in self._cache:
            cached_response, timestamp = self._cache[cache_key]
            
            # Check if cache is still valid
            age = (datetime.now() - timestamp).total_seconds()
            if age < self._cache_ttl:
                cached_response.cached = True
                return cached_response
            else:
                # Remove expired cache entry
                del self._cache[cache_key]
        
        return None
    
    def _add_to_cache(self, cache_key: str, response: VLMResponse):
        """Add response to cache."""
        if self._cache_enabled:
            self._cache[cache_key] = (response, datetime.now())
    
    def clear_cache(self):
        """Clear the response cache."""
        self._cache.clear()
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider."""
        pass
    
    @property
    @abstractmethod
    def supported_features(self) -> List[str]:
        """Return list of supported features."""
        pass
