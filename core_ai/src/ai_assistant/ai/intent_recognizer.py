"""
Intent Recognizer Module (Alias / Wrapper for IntentClassifier)
Forwards to intent_classification.py for unified NLU intent recognition.
"""

from ai_assistant.ai.intent_classification import IntentClassifier

IntentRecognizer = IntentClassifier

__all__ = ['IntentRecognizer', 'IntentClassifier']
