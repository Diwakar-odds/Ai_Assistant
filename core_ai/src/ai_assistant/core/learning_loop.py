import logging
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)


class LearningLoop:
    """
    The Grand Orchestrator for post-interaction learning.
    After every chat interaction, this fires off updates to:
      - EmotionalIntelligence (detect mood from the user's prompt)
      - UserDNA (evolve the user profile with implicit traits)
      - RelationshipManager (increment trust)
      - Memory (store the semantic embedding via save_to_memory)
    
    All updates are fire-and-forget on a background thread to avoid
    blocking the main chat response latency.
    """

    def __init__(self):
        self.emotional_intelligence = None
        self.dna = None
        self.relationship = None

        try:
            from ai_assistant.ai.emotional_intelligence import EmotionalIntelligence
            self.emotional_intelligence = EmotionalIntelligence()
            from ai_assistant.ai.personality_engine import PersonalityEngine
            self.personality_engine = PersonalityEngine()
        except ImportError as e:
            logger.warning(f"EmotionalIntelligence unavailable: {e}")

        try:
            from ai_assistant.ai.user_dna import UserDNA
            self.dna = UserDNA()
        except ImportError as e:
            logger.warning(f"UserDNA unavailable: {e}")

        try:
            from ai_assistant.core.relationship_manager import RelationshipManager
            self.relationship = RelationshipManager()
        except ImportError as e:
            logger.warning(f"RelationshipManager unavailable: {e}")

        logger.info("LearningLoop initialized: EI=%s, DNA=%s, Relationship=%s",
                     self.emotional_intelligence is not None,
                     self.dna is not None,
                     self.relationship is not None)

    def process_interaction(self, prompt: str, response: str, context: Dict[str, Any]):
        """
        Called asynchronously after every chat interaction.
        Runs all learning updates in a background thread.
        """
        thread = threading.Thread(
            target=self._process_async,
            args=(prompt, response, context),
            daemon=True
        )
        thread.start()

    def _process_async(self, prompt: str, response: str, context: Dict[str, Any]):
        """Internal: runs all learning hooks off the main thread."""
        logger.info("Executing post-interaction learning loop...")

        # 1. Emotional Intelligence — detect the user's mood from the prompt
        mood = context.get("mood", "neutral")
        if self.emotional_intelligence and prompt:
            try:
                emotion_result = self.emotional_intelligence.analyze_sentiment(prompt)
                mood = emotion_result.get("emotion", "neutral")
                context["mood"] = mood
                context["sentiment"] = emotion_result.get("sentiment", "neutral")
                context["emotion_confidence"] = emotion_result.get("confidence", 0.5)
                logger.info(f"EI detected emotion: {mood} (conf={emotion_result.get('confidence')})")
            except Exception as e:
                logger.error(f"EI analysis failed: {e}")

        # 2. User DNA — evolve profile with implicit traits
        if self.dna:
            try:
                self.dna.update_trait("recent_mood", mood)

                # Track communication style hints
                if len(prompt) > 200:
                    self.dna.update_trait("verbosity_preference", "detailed")
                elif len(prompt) < 30:
                    self.dna.update_trait("verbosity_preference", "concise")

                # Track active hours
                from datetime import datetime
                current_hour = datetime.now().hour
                self.dna.update_trait("last_active_hour", current_hour)
            except Exception as e:
                logger.error(f"DNA update failed: {e}")

        # 3. Relationship Manager — build trust
        if self.relationship:
            try:
                self.relationship.increment_interaction()
            except Exception as e:
                logger.error(f"Relationship update failed: {e}")

        # 4. Save to semantic memory (embeddings auto-computed by memory.py)
        try:
            from ai_assistant.ai.memory import save_to_memory
            save_to_memory("User", prompt)
            save_to_memory("Pulsar", response)
        except Exception as e:
            logger.error(f"Memory save in learning loop failed: {e}")

    def get_emotion_context(self, prompt: str) -> Dict[str, Any]:
        """
        Quick synchronous call to get the emotional context for a prompt.
        Used by the assistant to inject emotion-aware prompt modifiers
        BEFORE sending to the LLM.
        """
        if not self.emotional_intelligence:
            return {"mood": "neutral", "prompt_modifier": ""}

        try:
            result = self.emotional_intelligence.analyze_sentiment(prompt)
            modifier = self.emotional_intelligence.get_prompt_modifier(result)
            if modifier:
                prompt = f"[{modifier}] {prompt}"
                
            # Inject Personality modifier based on trust
            personality_modifier = ""
            if hasattr(self, 'personality_engine') and self.relationship:
                trust_score = self.relationship.trust_score
                personality_modifier = self.personality_engine.get_personality_modifier(trust_score)
                if personality_modifier:
                    prompt = f"[{personality_modifier}] {prompt}"

            combined_modifier = modifier
            if personality_modifier:
                combined_modifier = f"{modifier} {personality_modifier}".strip()
                
            mood_str = result.get("emotion", "neutral")
            if combined_modifier:
                combined_modifier = f"[System Context: The user's current mood is {mood_str}. {combined_modifier}]"
            else:
                combined_modifier = f"[System Context: The user's current mood is {mood_str}.]"

            return {
                "mood": result.get("emotion", "neutral"),
                "sentiment": result.get("sentiment", "neutral"),
                "confidence": result.get("confidence", 0.5),
                "prompt_modifier": combined_modifier
            }
        except Exception as e:
            logger.error(f"get_emotion_context failed: {e}")
            return {"mood": "neutral", "prompt_modifier": ""}

    def get_relationship_stage(self) -> str:
        """Returns the current relationship stage string."""
        if self.relationship:
            try:
                return self.relationship.get_relationship_stage()
            except Exception:
                pass
        return "Formal"

    def get_user_profile_summary(self) -> Dict[str, Any]:
        """Returns a snapshot of the user's DNA profile for context injection."""
        if self.dna:
            try:
                return self.dna.get_full_profile()
            except Exception:
                pass
        return {}
