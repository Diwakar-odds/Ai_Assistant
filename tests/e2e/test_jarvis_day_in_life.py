import os
import sys
import time
import logging
import base64

# Ensure core_ai is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../core_ai/src')))

from ai_assistant.core.assistant import ModernAssistant
from ai_assistant.core.learning_loop import LearningLoop
from ai_assistant.core.situation_awareness import SituationAwareness

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("JARVIS_E2E")

def run_simulation():
    logger.info("=== STARTING JARVIS DAY-IN-THE-LIFE SIMULATION ===")
    
    # 1. Initialization
    logger.info("1. Initializing JARVIS Core...")
    assistant = ModernAssistant()
    
    # We must ensure the components are correctly instantiated since some are lazy-loaded
    if not hasattr(assistant, '_learning_loop') or assistant._learning_loop is None:
        assistant._learning_loop = LearningLoop()
        
    learning_loop = assistant._learning_loop
    
    # 2. Morning Routine (Voice Emotion & Low Trust)
    logger.info("\n2. Morning Routine: Voice Emotion Check")
    # Simulate a frustrated/loud voice command (high RMS energy via lots of 0xFF bytes)
    loud_audio_bytes = b'\xFF' * 50000 
    loud_audio_b64 = f"data:audio/webm;base64,{base64.b64encode(loud_audio_bytes).decode('utf-8')}"
    
    logger.info("   -> User sends loud/frustrated audio command.")
    # We bypass process_voice_audio's whisper call and directly test the emotion piece
    if learning_loop.emotional_intelligence:
        emotion = learning_loop.emotional_intelligence.detect_emotion_from_voice(loud_audio_b64)
        logger.info(f"   -> Detected Emotion: {emotion}")
        
    # Check low trust prompt modifier
    if learning_loop.relationship:
        learning_loop.relationship.trust_score = 10
        context = learning_loop.get_emotion_context("What's on my schedule?")
        logger.info(f"   -> AI Prompt Modifier (Trust 10): {context.get('prompt_modifier')}")
        
    # 3. System Stress (Self-Healing)
    logger.info("\n3. System Stress Check: Hardware Failure")
    # Instead of monkey-patching psutil, we will directly call the HealthMonitor loop's internals
    # or report a failure manually to the SelfHealingEngine to see its reaction.
    if hasattr(assistant, '_self_healing_engine') and assistant._self_healing_engine:
        logger.info("   -> Simulating critical memory failure.")
        assistant._self_healing_engine.report_failure("memory")
        status = assistant._self_healing_engine.get_status()
        logger.info(f"   -> Self-Healing Engine Status: {status}")
        
    # 4. Context Switch (Proactive)
    logger.info("\n4. Context Switch Detection")
    # Setup SituationAwareness
    sa = SituationAwareness()
    
    # Manually seed the first context
    sa._last_context = "Coding/Development"
    
    # Mock the get_active_context method for this test to simulate a change
    original_get = sa.get_active_context
    sa.get_active_context = lambda: "Web Browsing"
    
    switched, old_ctx, new_ctx = sa.detect_context_switch()
    logger.info(f"   -> Switched: {switched}, Old: {old_ctx}, New: {new_ctx}")
    if switched:
        logger.info("   -> Triggering proactive suggestion: 'You switched to Web Browsing. Save workspace?'")
        
    sa.get_active_context = original_get # Restore
    
    # 5. Evening Routine (High Trust & Personality)
    logger.info("\n5. Evening Routine: Personality Engine Check")
    if learning_loop.relationship:
        learning_loop.relationship.trust_score = 100
        context = learning_loop.get_emotion_context("Shut down the lab for the night.")
        logger.info(f"   -> AI Prompt Modifier (Trust 100): {context.get('prompt_modifier')}")
        
    logger.info("\n=== JARVIS DAY-IN-THE-LIFE SIMULATION COMPLETE ===")

if __name__ == "__main__":
    run_simulation()
