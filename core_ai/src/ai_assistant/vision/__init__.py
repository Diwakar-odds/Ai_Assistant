"""
Vision module for VLM (Vision Language Model) capabilities.

This module provides:
- Abstract VLM provider interface
- Gemini Vision implementation
- Image processing utilities
- Coordinate extraction for UI automation
- Structured response parsing
"""

from .vlm_provider import VLMProvider, VLMResponse
from .gemini_vision_provider import GeminiVisionProvider
from .image_utils import ImageProcessor

__all__ = [
    'VLMProvider',
    'VLMResponse',
    'GeminiVisionProvider',
    'ImageProcessor'
]
