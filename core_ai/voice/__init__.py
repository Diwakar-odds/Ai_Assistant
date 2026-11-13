"""
Voice processing modules for the AI Assistant.

This package contains modules for speech recognition, text-to-speech,
wake word detection, echo cancellation, and other voice-related functionality.
"""

__version__ = "1.0.0"

from .advanced_speech_recognizer import *
from .advanced_voice import *
from .neural_voice_engine import *
from .wake_word_detector import *
from .echo_guard import EchoGuard, get_echo_guard, reset_echo_guard