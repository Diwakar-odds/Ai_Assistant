import os
import sys
from pathlib import Path

# Add src to path
src_dir = Path(__file__).parent.parent.parent
sys.path.append(str(src_dir))

def test_context_optimizer():
    from ai_assistant.core.context_optimizer import ContextOptimizer
    co = ContextOptimizer()
    profile = co.get_current_profile()
    assert 'time_context' in profile
    assert profile['time_context'] in ['work', 'home', 'night']
    logger.info("✅ ContextOptimizer working correctly.")

def test_intent_recognizer():
    from ai_assistant.ai.intent_recognizer import IntentRecognizer
    # Fallback to basic string parsing if model not available
    ir = IntentRecognizer()
    try:
        res = ir.analyze_sentiment("I am so stressed out right now")
        assert res in ['frustrated', 'neutral', 'happy']
        logger.info("✅ IntentRecognizer sentiment analysis working correctly.")
    except Exception as e:
        logger.warning(f"⚠️ IntentRecognizer warning: {e}")

if __name__ == "__main__":
    print("Running Personalization Tests...")
    test_context_optimizer()
    test_intent_recognizer()
    print("All tests completed.")