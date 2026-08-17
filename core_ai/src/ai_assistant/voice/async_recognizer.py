"""
Async Voice Recognition Module

Provides non-blocking voice recognition using ThreadPoolExecutor
for concurrent processing of multiple recognition requests.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Tuple, Dict
import time

# Import the synchronous recognizer
try:
    from ai_assistant.voice.advanced_speech_recognizer import get_advanced_speech_recognizer
    RECOGNIZER_AVAILABLE = True
except ImportError:
    RECOGNIZER_AVAILABLE = False
    logging.warning("Advanced speech recognizer not available")

# Global thread pool for async operations
executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="voice_async")

# Global recognizer instance
_recognizer = None

def init_async_recognizer():
    """Initialize the async recognizer singleton"""
    global _recognizer
    if RECOGNIZER_AVAILABLE and _recognizer is None:
        _recognizer = get_advanced_speech_recognizer()
        logging.info("✅ Async voice recognizer initialized")
    return _recognizer

async def recognize_async(
    audio_input,
    language: str = "en",
    context: Optional[str] = None
) -> Tuple[str, float, str]:
    """
    Recognize speech asynchronously without blocking
    
    Args:
        audio_input: Audio file path or audio data
        language: Language code (default: 'en')
        context: Optional context for better accuracy
        
    Returns:
        Tuple of (recognized_text, confidence, model_used)
    """
    if not _recognizer:
        init_async_recognizer()
    
    if not _recognizer:
        raise RuntimeError("Voice recognizer not available")
    
    # Run recognition in thread pool
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        executor,
        _recognizer.recognize,
        audio_input,
        language,
        context
    )
    
    return result

async def batch_recognize_async(
    audio_inputs: list,
    language: str = "en"
) -> list:
    """
    Recognize multiple audio inputs concurrently
    
    Args:
        audio_inputs: List of audio file paths or audio data
        language: Language code
        
    Returns:
        List of (text, confidence, model) tuples
    """
    tasks = [
        recognize_async(audio, language)
        for audio in audio_inputs
    ]
    
    return await asyncio.gather(*tasks)

def recognize_background(
    audio_input,
    callback=None,
    language: str = "en",
    context: Optional[str] = None
) -> asyncio.Future:
    """
    Start recognition in background and return Future
    
    Args:
        audio_input: Audio to recognize
        callback: Optional callback(result) when complete
        language: Language code
        context: Optional context
        
    Returns:
        Future object that resolves to recognition result
    """
    async def _recognize_with_callback():
        result = await recognize_async(audio_input, language, context)
        if callback:
            callback(result)
        return result
    
    # Schedule the coroutine
    loop = asyncio.get_event_loop()
    return asyncio.ensure_future(_recognize_with_callback())

# Metrics tracking
class RecognitionMetrics:
    """Track async recognition performance metrics"""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_time = 0.0
        self.avg_latency = 0.0
    
    def record_success(self, latency: float):
        self.total_requests += 1
        self.successful_requests += 1
        self.total_time += latency
        self.avg_latency = self.total_time / self.successful_requests
    
    def record_failure(self):
        self.total_requests += 1
        self.failed_requests += 1
    
    def get_stats(self) -> Dict:
        success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        return {
            "total_requests": self.total_requests,
            "successful": self.successful_requests,
            "failed": self.failed_requests,
            "success_rate": f"{success_rate:.1f}%",
            "avg_latency_ms": f"{self.avg_latency * 1000:.0f}"
        }

metrics = RecognitionMetrics()

async def recognize_with_metrics(audio_input, language: str = "en") -> Tuple[str, float, str]:
    """Recognize with automatic metrics tracking"""
    start = time.time()
    try:
        result = await recognize_async(audio_input, language)
        latency = time.time() - start
        metrics.record_success(latency)
        return result
    except Exception as e:
        metrics.record_failure()
        raise e

def get_recognition_stats() -> Dict:
    """Get recognition performance statistics"""
    return metrics.get_stats()

# Cleanup on shutdown
def shutdown_async_recognizer():
    """Shutdown thread pool gracefully"""
    executor.shutdown(wait=True)
    logging.info("Async voice recognizer shutdown complete")
