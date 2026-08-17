import logging
from typing import Dict, Any, Optional
from ai_assistant.nlp.intent_extractor import IntentExtractor, IntentResult

# Optional dependencies for existing intent routing systems
try:
    from ai_assistant.workflow.intent_router import IntentRouter
    INTENT_ROUTER_AVAILABLE = True
except ImportError:
    INTENT_ROUTER_AVAILABLE = False

try:
    from ai_assistant.nlp.predict_command import OfflineCommandPredictor
    OFFLINE_PREDICTOR_AVAILABLE = True
except ImportError:
    OFFLINE_PREDICTOR_AVAILABLE = False

logger = logging.getLogger(__name__)

class UnifiedIntentClassifier:
    """
    Unifies the 3 intent classification systems:
    1. Semantic Router (IntentRouter)
    2. ML Predictor (OfflineCommandPredictor)
    3. Regex Patterns (IntentExtractor)
    
    Uses a waterfall approach to determine the most likely intent.
    """
    
    def __init__(self):
        self.extractor = IntentExtractor()
        
        self.router = None
        if INTENT_ROUTER_AVAILABLE:
            try:
                self.router = IntentRouter(threshold=0.6)
            except Exception as e:
                logger.warning(f"Failed to initialize IntentRouter: {e}")
                
        self.predictor = None
        if OFFLINE_PREDICTOR_AVAILABLE:
            try:
                self.predictor = OfflineCommandPredictor()
            except Exception as e:
                logger.warning(f"Failed to initialize OfflineCommandPredictor: {e}")
                
        logger.info("UnifiedIntentClassifier initialized")
        
    def classify(self, text: str) -> IntentResult:
        """
        Classifies the text and returns an IntentResult.
        Tries Semantic Router, then ML Predictor, then Regex Extractor.
        """
        if not text or not text.strip():
            return IntentResult(intent="unknown", entities={}, confidence=0.0)
            
        best_intent = None
        best_confidence = 0.0
        source = "none"
        
        # 1. Try Semantic Router first (often best for complex phrasing)
        if self.router:
            try:
                route_name, score = self.router.determine_intent(text)
                if route_name and score >= self.router.threshold:
                    # Found a strong semantic match
                    best_intent = route_name
                    best_confidence = score
                    source = "semantic_router"
            except Exception as e:
                logger.error(f"Semantic Router error: {e}")
                
        # 2. If Semantic Router didn't find a strong match, try ML Predictor (good for multilingual)
        if (not best_intent or best_confidence < 0.7) and self.predictor:
            try:
                pred_intent = self.predictor.predict(text)
                if pred_intent:
                    # In absence of confidence score from predictor, assume 0.8
                    if 0.8 > best_confidence:
                        best_intent = pred_intent
                        best_confidence = 0.8
                        source = "ml_predictor"
            except Exception as e:
                logger.error(f"ML Predictor error: {e}")
                
        # 3. Always run Regex Extractor to get entities, and use its intent if it's very confident
        regex_result = self.extractor.extract(text)
        
        if regex_result.confidence > best_confidence and regex_result.intent != "unknown":
            best_intent = regex_result.intent
            best_confidence = regex_result.confidence
            source = "regex_extractor"
            
        if not best_intent:
            best_intent = regex_result.intent
            best_confidence = regex_result.confidence
            source = "regex_fallback"
            
        # Compile final result
        return IntentResult(
            intent=best_intent,
            entities=regex_result.entities, # Always use regex for entity extraction
            confidence=best_confidence
        )
