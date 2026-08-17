"""
Advanced Features Activation Script
Initializes and activates all enhancement features

Features activated:
- Semantic response cache
- Intelligent model router
- Streaming responses
- Emotion detection
- Visual automation verification
- Usage pattern analysis
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import logging
import asyncio
from typing import Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def check_dependencies() -> Dict[str, bool]:
    """Check if required dependencies are installed"""
    dependencies = {}
    
    # Core dependencies
    try:
        import diskcache
        dependencies['diskcache'] = True
    except ImportError:
        dependencies['diskcache'] = False
    
    try:
        from sentence_transformers import SentenceTransformer
        dependencies['sentence_transformers'] = True
    except ImportError:
        dependencies['sentence_transformers'] = False
    
    try:
        import librosa
        dependencies['librosa'] = True
    except ImportError:
        dependencies['librosa'] = False
    
    try:
        from PIL import Image
        dependencies['Pillow'] = True
    except ImportError:
        dependencies['Pillow'] = False
    
    try:
        import cv2
        dependencies['opencv'] = True
    except ImportError:
        dependencies['opencv'] = False
    
    try:
        import sklearn
        dependencies['scikit-learn'] = True
    except ImportError:
        dependencies['scikit-learn'] = False
    
    return dependencies


def create_directories():
    """Create necessary directories"""
    directories = [
        "data/response_cache",
        "data/automation/screenshots",
        "data/training",
        "data/voice_cache",
        "logs/enhanced"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Created directory: {directory}")


def initialize_cache():
    """Initialize semantic cache"""
    try:
        from ai_assistant.ai.semantic_cache import get_response_cache
        
        cache = get_response_cache()
        stats = cache.get_stats()
        
        logger.info(f"✅ Semantic cache initialized")
        logger.info(f"   Cache entries: {stats.get('cache_size_entries', 0)}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Cache initialization failed: {e}")
        return False


def initialize_router():
    """Initialize model router"""
    try:
        from ai_assistant.ai.model_router import get_model_router
        
        router = get_model_router()
        stats = router.get_stats()
        
        logger.info(f"✅ Model router initialized")
        logger.info(f"   Available models: {len(router.models)}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Router initialization failed: {e}")
        return False


def initialize_streaming():
    """Initialize streaming handler"""
    try:
        from ai_assistant.ai.streaming_handler import get_streaming_handler
        
        handler = get_streaming_handler()
        
        logger.info(f"✅ Streaming handler initialized")
        logger.info(f"   Providers available: {len(handler.providers)}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Streaming initialization failed: {e}")
        return False


def initialize_emotion_detection():
    """Initialize emotion detector"""
    try:
        from ai_assistant.voice.emotion_detection import get_emotion_detector
        
        detector = get_emotion_detector()
        
        logger.info(f"✅ Emotion detector initialized")
        
        return True
    except Exception as e:
        logger.error(f"❌ Emotion detection initialization failed: {e}")
        return False


def initialize_visual_verification():
    """Initialize visual verifier"""
    try:
        from ai_assistant.automation.visual_verification import get_visual_verifier
        
        verifier = get_visual_verifier()
        
        logger.info(f"✅ Visual verifier initialized")
        
        return True
    except Exception as e:
        logger.error(f"❌ Visual verification initialization failed: {e}")
        return False


async def test_enhanced_ai():
    """Test the integrated enhanced AI"""
    try:
        from ai_assistant.core.enhanced_integration import get_enhanced_ai
        
        ai = get_enhanced_ai()
        
        # Test query
        logger.info("\n🧪 Testing enhanced AI with sample query...")
        
        result = await ai.process_query(
            "What is 2 + 2?",
            enable_cache=True,
            enable_streaming=False  # Disable for test
        )
        
        logger.info(f"✅ Enhanced AI test passed")
        logger.info(f"   Response: {result['text'][:50]}...")
        logger.info(f"   Model: {result['model']}")
        logger.info(f"   Time: {result['time_ms']:.0f}ms")
        
        return True
    except Exception as e:
        logger.error(f"❌ Enhanced AI test failed: {e}")
        return False


def run_usage_analysis():
    """Run usage pattern analysis"""
    try:
        from ai_assistant.ai.usage_pattern_analyzer import UsagePatternAnalyzer
        
        analyzer = UsagePatternAnalyzer()
        
        logger.info("\n📊 Running usage pattern analysis...")
        results = analyzer.analyze_all(days_back=30)
        
        # Generate report
        report = analyzer.generate_report("data/training/usage_analysis_report.txt")
        
        logger.info(f"✅ Usage analysis complete")
        logger.info(f"   Common commands: {len(results.get('common_commands', []))}")
        logger.info(f"   Training examples: {len(results.get('training_data', []))}")
        logger.info(f"   Report saved to: data/training/usage_analysis_report.txt")
        
        return True
    except Exception as e:
        logger.error(f"❌ Usage analysis failed: {e}")
        return False


def main():
    """Main activation function"""
    print("=" * 80)
    print("ADVANCED FEATURES ACTIVATION")
    print("=" * 80)
    print()
    
    # Check dependencies
    logger.info("📦 Checking dependencies...")
    deps = check_dependencies()
    
    missing_deps = [name for name, installed in deps.items() if not installed]
    
    if missing_deps:
        logger.warning(f"⚠️  Missing optional dependencies: {', '.join(missing_deps)}")
        logger.warning(f"   Some features may not work without them")
        logger.warning(f"   Install with: pip install {' '.join(missing_deps)}")
        print()
    else:
        logger.info("✅ All dependencies available")
        print()
    
    # Create directories
    logger.info("📁 Creating directories...")
    create_directories()
    print()
    
    # Initialize components
    results = {}
    
    logger.info("🔧 Initializing components...")
    print()
    
    results['cache'] = initialize_cache()
    results['router'] = initialize_router()
    results['streaming'] = initialize_streaming()
    results['emotion'] = initialize_emotion_detection()
    results['verification'] = initialize_visual_verification()
    
    print()
    
    # Test enhanced AI
    logger.info("🧪 Testing integrated system...")
    results['enhanced_ai'] = asyncio.run(test_enhanced_ai())
    
    print()
    
    # Run usage analysis
    results['analysis'] = run_usage_analysis()
    
    print()
    
    # Summary
    print("=" * 80)
    print("ACTIVATION SUMMARY")
    print("=" * 80)
    
    successful = sum(1 for v in results.values() if v)
    total = len(results)
    
    for component, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {component.replace('_', ' ').title()}")
    
    print()
    print(f"Success Rate: {successful}/{total} ({(successful/total)*100:.0f}%)")
    
    if successful == total:
        print("\n🎉 ALL FEATURES ACTIVATED SUCCESSFULLY!")
        print("\n📚 Next Steps:")
        print("   1. Install missing dependencies if any: pip install -r requirements.txt")
        print("   2. Test streaming: python -m ai_assistant.ai.streaming_handler")
        print("   3. Test caching: python -m ai_assistant.ai.semantic_cache")
        print("   4. View usage report: data/training/usage_analysis_report.txt")
        print("   5. Integrate into your assistant: from ai_assistant.core.enhanced_integration import get_enhanced_ai")
    else:
        print("\n⚠️  Some features failed to activate")
        print("   Check logs above for details")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
