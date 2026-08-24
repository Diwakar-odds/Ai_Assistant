# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Enhanced AI Integration Layer
Integrates all advanced features: caching, routing, streaming, emotion detection, visual verification

Usage:
    from ai_assistant.core.enhanced_integration import EnhancedAI
    
    ai = EnhancedAI()
    response = await ai.process_query("What's the weather?", enable_cache=True)
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
import time

logger = logging.getLogger(__name__)

# Import all enhancement components
try:
    from ai_assistant.ai.semantic_cache import get_response_cache, cache_response, get_cached_response
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    logger.warning("Semantic cache not available")

try:
    from ai_assistant.ai.model_router import get_model_router, ModelTier
    ROUTER_AVAILABLE = True
except ImportError:
    ROUTER_AVAILABLE = False
    logger.warning("Model router not available")

try:
    from ai_assistant.ai.streaming_handler import get_streaming_handler, StreamProvider
    STREAMING_AVAILABLE = True
except ImportError:
    STREAMING_AVAILABLE = False
    logger.warning("Streaming handler not available")

try:
    from ai_assistant.voice.emotion_detection import get_emotion_detector, Emotion
    EMOTION_AVAILABLE = True
except ImportError:
    EMOTION_AVAILABLE = False
    logger.warning("Emotion detection not available")

try:
    from ai_assistant.automation.visual_verification import get_visual_verifier
    VERIFICATION_AVAILABLE = True
except ImportError:
    VERIFICATION_AVAILABLE = False
    logger.warning("Visual verification not available")


class EnhancedAI:
    """
    Enhanced AI with all optimizations integrated
    
    Features:
    - Semantic response caching
    - Intelligent model routing
    - Streaming responses
    - Emotion-aware responses
    - Visual automation verification
    """
    
    def __init__(self):
        """Initialize enhanced AI"""
        self.cache = get_response_cache() if CACHE_AVAILABLE else None
        self.router = get_model_router() if ROUTER_AVAILABLE else None
        self.streaming = get_streaming_handler() if STREAMING_AVAILABLE else None
        self.emotion_detector = get_emotion_detector() if EMOTION_AVAILABLE else None
        self.verifier = get_visual_verifier() if VERIFICATION_AVAILABLE else None
        
        # Statistics
        self.stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_time_ms': 0,
            'total_cost_usd': 0.0
        }
        
        logger.info("🚀 Enhanced AI initialized with all features")
        self._log_available_features()
    
    def _log_available_features(self):
        """Log which features are available"""
        features = {
            'Semantic Caching': CACHE_AVAILABLE,
            'Model Routing': ROUTER_AVAILABLE,
            'Streaming': STREAMING_AVAILABLE,
            'Emotion Detection': EMOTION_AVAILABLE,
            'Visual Verification': VERIFICATION_AVAILABLE
        }
        
        logger.info("Available features:")
        for feature, available in features.items():
            status = "✅" if available else "❌"
            logger.info(f"  {status} {feature}")
    
    async def process_query(self,
                          query: str,
                          context: Dict[str, Any] = None,
                          enable_cache: bool = True,
                          enable_streaming: bool = True,
                          audio_path: Optional[str] = None,
                          on_chunk: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """
        Process a query with all enhancements
        
        Args:
            query: User query
            context: Optional context
            enable_cache: Whether to use cache
            enable_streaming: Whether to stream response
            audio_path: Optional audio file for emotion detection
            on_chunk: Optional callback for streaming chunks
            
        Returns:
            Response dict with text, metadata, and stats
        """
        start_time = time.time()
        self.stats['total_queries'] += 1
        
        context = context or {}
        
        # 1. Check emotion if audio provided
        emotion = None
        if audio_path and self.emotion_detector:
            emotion_result = self.emotion_detector.analyze_audio(audio_path)
            emotion = emotion_result.primary_emotion
            context['detected_emotion'] = emotion.value
            context['emotion_confidence'] = emotion_result.confidence
            
            # Get response adaptation
            adaptation = self.emotion_detector.adapt_response_style(emotion)
            context['response_style'] = adaptation
            
            logger.info(f"🎭 Emotion: {emotion.value} (confidence: {emotion_result.confidence:.2f})")
        
        # 2. Check cache
        cached_response = None
        if enable_cache and self.cache:
            cached_response = self.cache.get(query, context)
            if cached_response:
                self.stats['cache_hits'] += 1
                elapsed_ms = (time.time() - start_time) * 1000
                
                return {
                    'text': cached_response,
                    'cached': True,
                    'emotion': emotion.value if emotion else None,
                    'time_ms': round(elapsed_ms, 2),
                    'model': 'cache'
                }
        
        self.stats['cache_misses'] += 1
        
        # 3. Route to best model
        selected_model = None
        analysis = None
        
        if self.router:
            selected_model, analysis = self.router.route(query, context)
            logger.info(f"🎯 Routed to: {selected_model.name} "
                       f"(complexity: {analysis.complexity_score:.2f})")
        else:
            # Fallback to default
            from ai_assistant.ai.model_router import ModelConfig, ModelTier
            selected_model = ModelConfig(
                name="gemini-2.0-flash-exp",
                tier=ModelTier.FAST,
                max_tokens=8192,
                cost_per_1k_tokens=0.0001,
                avg_latency_ms=500,
                capabilities=['general'],
                priority=10
            )
        
        # 4. Generate response
        response_text = ""
        
        if enable_streaming and self.streaming:
            # Stream response
            provider_map = {
                'gemini': StreamProvider.GOOGLE,
                'gpt': StreamProvider.OPENAI
            }
            
            # Determine provider from model name
            if 'gemini' in selected_model.name.lower():
                provider = StreamProvider.GOOGLE
            elif 'gpt' in selected_model.name.lower():
                provider = StreamProvider.OPENAI
            else:
                provider = StreamProvider.GOOGLE  # Default
            
            try:
                response_text = await self.streaming.stream(
                    provider=provider,
                    prompt=query,
                    model=selected_model.name,
                    on_chunk=on_chunk
                )
            except Exception as e:
                logger.error(f"Streaming failed: {e}, falling back to non-streaming")
                response_text = await self._generate_non_streaming(query, selected_model)
        else:
            # Non-streaming response
            response_text = await self._generate_non_streaming(query, selected_model)
        
        # 5. Cache the response
        if enable_cache and self.cache and response_text:
            metadata = {
                'model': selected_model.name,
                'emotion': emotion.value if emotion else None,
                'complexity': analysis.complexity_score if analysis else 0.0
            }
            self.cache.set(query, response_text, context, metadata)
        
        # 6. Track stats
        elapsed_ms = (time.time() - start_time) * 1000
        self.stats['total_time_ms'] += elapsed_ms
        
        # Estimate tokens and cost
        estimated_tokens = len(query.split()) + len(response_text.split())
        cost = (estimated_tokens / 1000) * selected_model.cost_per_1k_tokens
        self.stats['total_cost_usd'] += cost
        
        if self.router:
            self.router.record_usage(selected_model, estimated_tokens, elapsed_ms)
        
        return {
            'text': response_text,
            'cached': False,
            'model': selected_model.name,
            'emotion': emotion.value if emotion else None,
            'complexity': analysis.complexity_score if analysis else 0.0,
            'time_ms': round(elapsed_ms, 2),
            'tokens': estimated_tokens,
            'cost_usd': round(cost, 6)
        }
    
    async def _generate_non_streaming(self, query: str, model) -> str:
        """Generate response without streaming (fallback)"""
        # This would call your existing LLM integration
        # For now, return placeholder
        return f"Response to: {query} (model: {model.name})"
    
    async def verify_automation(self, action_name: str, app_name: str = None) -> Dict[str, Any]:
        """
        Verify automation action succeeded
        
        Args:
            action_name: Name of action performed
            app_name: Name of app (for launch verification)
            
        Returns:
            Verification result
        """
        if not self.verifier:
            return {'success': False, 'reason': 'Visual verification not available'}
        
        if app_name:
            result = self.verifier.verify_app_launched(app_name)
        else:
            # General verification
            before = self.verifier.capture_screenshot("before")
            await asyncio.sleep(2)  # Wait for action
            after = self.verifier.capture_screenshot("after")
            result = self.verifier.verify_action(before, after)
        
        return {
            'success': result.success,
            'confidence': result.confidence,
            'changes_detected': result.changes_detected,
            'change_percentage': result.change_percentage
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        stats = {
            'enhanced_ai': self.stats.copy()
        }
        
        if self.cache:
            stats['cache'] = self.cache.get_stats()
        
        if self.router:
            stats['routing'] = self.router.get_stats()
        
        if self.streaming:
            stats['streaming'] = self.streaming.get_stats()
        
        if self.verifier:
            stats['verification'] = self.verifier.get_success_rate()
        
        # Calculate cache hit rate
        total_queries = self.stats['total_queries']
        if total_queries > 0:
            stats['enhanced_ai']['cache_hit_rate'] = round(
                (self.stats['cache_hits'] / total_queries) * 100, 2
            )
        
        return stats
    
    def optimize(self):
        """Run optimization on all components"""
        if self.cache:
            self.cache.optimize()
            logger.info("✅ Cache optimized")


# Global instance
_enhanced_ai = None

def get_enhanced_ai() -> EnhancedAI:
    """Get global enhanced AI instance"""
    global _enhanced_ai
    if _enhanced_ai is None:
        _enhanced_ai = EnhancedAI()
    return _enhanced_ai


# Demo
async def demo():
    """Demo enhanced AI"""
    print("🚀 Enhanced AI Demo\n")
    
    ai = EnhancedAI()
    
    # Test query
    print("Query: What is machine learning?\n")
    
    def print_chunk(text: str):
        print(text, end='', flush=True)
    
    result = await ai.process_query(
        "Explain machine learning in one sentence",
        enable_cache=True,
        enable_streaming=True,
        on_chunk=print_chunk
    )
    
    print("\n\n📊 Result:")
    print(f"  Model: {result['model']}")
    print(f"  Time: {result['time_ms']:.0f}ms")
    print(f"  Cached: {result['cached']}")
    
    # Stats
    print("\n📈 Overall Stats:")
    stats = ai.get_stats()
    for category, data in stats.items():
        print(f"\n{category.upper()}:")
        for key, value in data.items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(demo())
