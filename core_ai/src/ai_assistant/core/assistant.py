"""
YourDaddy AI Assistant - ModernAssistant (Coordinator)

Decomposed, clean coordinator class composing:
- VoiceManager: Voice input, STT, TTS, and wake words
- AIProcessor: LLMs, Multimodal vision, conversational AI, and multilingual
- AutomationHandler: OS and App automation commands
- SystemMonitor: Real-time hardware and network telemetry
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from ai_assistant.core.voice_manager import VoiceManager
from ai_assistant.core.ai_processor import AIProcessor
from ai_assistant.core.automation_handler import AutomationHandler
from ai_assistant.core.system_monitor import SystemMonitor

logger = logging.getLogger(__name__)

# Global SocketIO holder
socketio = None

def set_socketio(sio):
    """Set the SocketIO instance for system monitoring"""
    global socketio
    socketio = sio


class ModernAssistant:
    """Modern Assistant coordinator composing specialized domain managers."""
    
    def __init__(self):
        # Feature toggles
        enable_voice = os.getenv('ENABLE_VOICE', 'true').lower() == 'true'
        enable_multimodal = os.getenv('ENABLE_MULTIMODAL', 'true').lower() == 'true'
        enable_conversational = os.getenv('ENABLE_CONVERSATIONAL_AI', 'true').lower() == 'true'
        enable_multilingual = os.getenv('ENABLE_MULTILINGUAL', 'true').lower() == 'true'
        
        # Domain managers
        self.voice_mgr = VoiceManager(enable_voice=enable_voice)
        self.ai_proc = AIProcessor(
            enable_multimodal=enable_multimodal,
            enable_conversational=enable_conversational,
            enable_multilingual=enable_multilingual
        )
        self.automation = AutomationHandler()
        self.monitor = SystemMonitor()
        
        self.current_language = "hinglish"
        logger.info("✅ ModernAssistant initialized (modular coordinator architecture)")

    # ----------------- Voice Properties (Backward Compatibility) -----------------
    @property
    def voice_listening(self) -> bool:
        return self.voice_mgr.voice_listening

    @voice_listening.setter
    def voice_listening(self, value: bool):
        self.voice_mgr.voice_listening = value

    @property
    def voice_recognizer(self):
        return self.voice_mgr.voice_recognizer

    @property
    def tts_engine(self):
        return self.voice_mgr.tts_engine

    @property
    def wake_word_detector(self):
        return self.voice_mgr.wake_word_detector

    def start_voice_listening(self) -> Dict[str, Any]:
        return self.voice_mgr.start_voice_listening()

    def stop_voice_listening(self) -> Dict[str, Any]:
        return self.voice_mgr.stop_voice_listening()

    def speak_text(self, text: str) -> bool:
        return self.voice_mgr.speak_text(text)

    def process_voice_audio(self, audio_data: str) -> Dict[str, Any]:
        return self.voice_mgr.process_voice_audio(audio_data)

    # ----------------- AI & Multimodal Properties (Backward Compatibility) -----------------
    @property
    def multimodal_ai(self):
        return self.ai_proc.multimodal_ai

    @property
    def conversational_ai(self):
        return self.ai_proc.conversational_ai

    @property
    def multilingual(self):
        return self.ai_proc.multilingual

    @property
    def llm_chat(self):
        return self.ai_proc.llm_chat

    def get_init_status(self) -> Dict[str, str]:
        status = self.ai_proc.get_init_status()
        status['voice_system'] = "ready" if self.voice_mgr.enabled else "disabled"
        status['system_monitoring'] = "ready"
        return status

    def analyze_screen(self, prompt: str = "Describe what you see on the screen") -> str:
        return self.ai_proc.analyze_screen(prompt)

    def answer_visual_question(self, question: str, image_path: Optional[str] = None) -> str:
        return self.ai_proc.answer_visual_question(question, image_path)

    # ----------------- Automation & Commands -----------------
    def process_command(self, command: str) -> str:
        """Process incoming user command through automation or NLP."""
        return self.automation.execute_command(command)

    # ----------------- System Telemetry -----------------
    def get_real_time_system_stats(self) -> Dict[str, Any]:
        return self.monitor.get_real_time_stats()
