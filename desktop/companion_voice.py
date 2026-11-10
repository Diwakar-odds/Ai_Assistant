#!/usr/bin/env python3
"""
Pulsar AI Assistant - Companion Voice Subsystem
================================================
Always-on lightweight voice listener running in the companion process:
- Offline wake word detection via Vosk ("hey pulsar", "ok pulsar", "pulsar")
- Automatic speech endpointing (VAD / Energy-based silence detection)
- Speech recognition via AdvancedSpeechRecognizer (Whisper / Local)
- Visual feedback hooks (triggering scanning/listening animations on the robot)
"""

import sys
import os
import time
import threading
from pathlib import Path
from typing import Callable, Optional

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root / "core_ai" / "src"))

from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")


class CompanionVoiceListener:
    """Always-on voice capture and wake-word listener for the floating companion"""

    def __init__(self, on_wake: Optional[Callable] = None, on_command: Optional[Callable[[str], None]] = None, on_partial: Optional[Callable[[str], None]] = None):
        self.on_wake = on_wake
        self.on_command = on_command
        self.on_partial = on_partial
        self.is_running = False
        self.is_listening_for_command = False

        self.wake_detector = None
        self.speech_recognizer = None
        self._init_thread = threading.Thread(target=self._init_models, daemon=True)
        self._init_thread.start()

    def _init_models(self):
        """Asynchronously warm up speech recognition and wake-word detector"""
        try:
            from ai_assistant.voice.wake_word_detector import SmartWakeWordDetector
            self.wake_detector = SmartWakeWordDetector()
            logger.info("✅ Companion voice: SmartWakeWordDetector loaded")
        except Exception as e:
            logger.warning(f"Could not load SmartWakeWordDetector: {e}")

        try:
            from ai_assistant.voice.advanced_speech_recognizer import AdvancedSpeechRecognizer
            self.speech_recognizer = AdvancedSpeechRecognizer()
            logger.info("✅ Companion voice: AdvancedSpeechRecognizer loaded")
        except Exception as e:
            logger.warning(f"Could not load AdvancedSpeechRecognizer: {e}")

    def start(self):
        """Starts continuous background voice listening loop"""
        if self.is_running:
            return
        self.is_running = True
        threading.Thread(target=self._loop, daemon=True).start()
        logger.info("🎤 Companion Voice Listener started")

    def stop(self):
        self.is_running = False

    def _loop(self):
        """Main listening loop with wake word and command capture"""
        time.sleep(2.0)  # Wait for models to warm up

        while self.is_running:
            try:
                # 1. Listen for wake word if detector is available
                if self.wake_detector and hasattr(self.wake_detector, "listen_chunk"):
                    # Use wake detector chunk processing
                    hit, keyword = self.wake_detector.listen_chunk()
                    if hit:
                        self._handle_wake_event()
                else:
                    # Sleep briefly if detector is passive
                    time.sleep(0.2)
            except Exception as e:
                time.sleep(1.0)

    def _handle_wake_event(self):
        """Triggered when user says 'Hey Pulsar'"""
        if self.is_listening_for_command:
            return
        self.is_listening_for_command = True
        logger.info("🎯 Wake word detected by companion!")

        # Visual feedback: eyes turn glowing cyan
        if self.on_wake:
            try:
                self.on_wake()
            except Exception:
                pass

        # Capture command audio and transcribe
        command_text = self._record_and_transcribe(timeout=6.0)
        self.is_listening_for_command = False

        if command_text and self.on_command:
            logger.info(f"🗣️ Transcribed command: '{command_text}'")
            try:
                self.on_command(command_text)
            except Exception as e:
                logger.error(f"Error in on_command callback: {e}")

    def trigger_manual_listen(self):
        """Called when user clicks robot icon or presses hotkey to speak directly"""
        def _worker():
            if self.is_listening_for_command:
                return
            self.is_listening_for_command = True
            if self.on_wake:
                try:
                    self.on_wake()
                except Exception:
                    pass

            command_text = self._record_and_transcribe(timeout=7.0)
            self.is_listening_for_command = False

            if command_text and self.on_command:
                self.on_command(command_text)

        threading.Thread(target=_worker, daemon=True).start()

    def _record_and_transcribe(self, timeout: float = 6.0) -> Optional[str]:
        """Records microphone until pause, then runs STT with partial visual cues"""
        if self.on_partial:
            self.on_partial("🎙️ Listening...")

        try:
            if self.speech_recognizer:
                # Use AdvancedSpeechRecognizer audio capture
                text, conf, lang = self.speech_recognizer.recognize_from_microphone(timeout=timeout)
                if self.on_partial and text:
                    self.on_partial(f"🧠 \"{text.strip()}\"")
                return text.strip() if text else None
        except Exception as e:
            logger.debug(f"Direct mic capture notice: {e}")

        # Fallback using Google Speech API via SpeechRecognition if available
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.4)
                if self.on_partial:
                    self.on_partial("🎙️ Listening to command...")
                audio = r.listen(source, timeout=timeout, phrase_time_limit=timeout)
                if self.on_partial:
                    self.on_partial("🧠 Analyzing speech...")
                text = r.recognize_google(audio)
                if self.on_partial and text:
                    self.on_partial(f"🧠 \"{text.strip()}\"")
                return text
        except Exception:
            return None

