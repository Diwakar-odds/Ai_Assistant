# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Intent Recognizer Module (Alias / Wrapper for IntentClassifier)
Forwards to intent_classification.py for unified NLU intent recognition.
"""

from ai_assistant.ai.intent_classification import IntentClassifier

IntentRecognizer = IntentClassifier

__all__ = ['IntentRecognizer', 'IntentClassifier']
