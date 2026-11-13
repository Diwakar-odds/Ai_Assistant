#!/usr/bin/env python3
"""
Unit and Integration Tests for Single-Process In-Process Audio & Wake Word Pipeline
===================================================================================
Verifies:
1. In-process voice manager initialization and lifecycle
2. Wake detection, acknowledgment generation, and silence handling
3. Manual mic click bypassing wake word requirement (require_wake_word=False)
4. Screen query routing and noise fragment dropping in execute_companion_voice_command
5. Mutual exclusion when WebUI mic is active (zero contention)
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (project_root, os.path.join(project_root, "backend"), os.path.join(project_root, "core_ai", "src")):
    if p not in sys.path:
        sys.path.insert(0, p)


class TestSingleProcessAudioFixes(unittest.TestCase):

    def setUp(self):
        from backend.inprocess_voice import InProcessVoiceManager
        InProcessVoiceManager._instance = None
        self.mock_socketio = MagicMock()

    def test_inprocess_voice_manager_singleton(self):
        """Verify InProcessVoiceManager singleton instance creation."""
        from backend.inprocess_voice import InProcessVoiceManager
        mgr1 = InProcessVoiceManager.get_instance(self.mock_socketio)
        mgr2 = InProcessVoiceManager.get_instance()
        self.assertIs(mgr1, mgr2)
        self.assertEqual(mgr1.socketio, self.mock_socketio)

    def test_on_wake_emits_socket_and_wakes_orb(self):
        """Verify _on_wake fires companion_wake and wake_word_detected socket events."""
        from backend.inprocess_voice import InProcessVoiceManager
        mgr = InProcessVoiceManager.get_instance(self.mock_socketio)
        
        with patch("ai_assistant.voice.tts_output_service.get_tts_service") as mock_tts_getter:
            mock_tts = MagicMock()
            mock_tts_getter.return_value = mock_tts
            
            mgr._on_wake("hey pulsar")
            
            mock_tts.stop.assert_called_once_with(reason="inprocess_voice_wake")
            
            # Check socketio emits
            emitted_events = [call[0][0] for call in self.mock_socketio.emit.call_args_list]
            self.assertIn("companion_wake", emitted_events)
            self.assertIn("wake_word_detected", emitted_events)

    def test_on_wake_ack_speaks_feminine_hindi(self):
        """Verify _on_wake_ack generates natural Hindi acknowledgment and queues TTS."""
        from backend.inprocess_voice import InProcessVoiceManager
        mgr = InProcessVoiceManager.get_instance(self.mock_socketio)
        
        with patch("ai_assistant.voice.tts_output_service.get_tts_service") as mock_tts_getter:
            mock_tts = MagicMock()
            mock_tts_getter.return_value = mock_tts
            
            mgr._on_wake_ack("hey pulsar")
            
            # Verify TTS was called with an acknowledgment
            mock_tts.speak.assert_called_once()
            spoken_text = mock_tts.speak.call_args[0][0]
            self.assertTrue(len(spoken_text) > 0)
            # Verify feminine Hindi grammar (e.g. हूँ, बताओ, बोलिए)
            self.assertTrue(any(marker in spoken_text for marker in ("हूँ", "बताओ", "बोलिए", "रेडी", "सुन")))

    def test_manual_mic_click_accepts_command_without_wake_word(self):
        """Verify that when manual_click=True / require_wake_word=False, speech without wake word is accepted."""
        from ai_assistant.core.speech_text_crisper import filter_and_crisp_speech_transcript
        
        # User manually clicks mic and says "what is running on screen?" (no wake word)
        res = filter_and_crisp_speech_transcript(
            "what is running on screen",
            require_wake_word=False,
            check_echo=False
        )
        self.assertTrue(res["valid"])
        self.assertEqual(res["crisped_text"].lower(), "what is running on screen")
        self.assertIsNone(res["matched_wake"])

    def test_manual_mic_click_accepts_hindi_command_without_wake_word(self):
        """Verify Hindi command spoken directly after mic click is accepted."""
        from ai_assistant.core.speech_text_crisper import filter_and_crisp_speech_transcript
        
        res = filter_and_crisp_speech_transcript(
            "स्क्रीन पर क्या चल रहा है",
            require_wake_word=False,
            check_echo=False
        )
        self.assertTrue(res["valid"])
        self.assertEqual(res["crisped_text"], "स्क्रीन पर क्या चल रहा है")

    def test_manual_mic_click_strips_wake_word_if_user_spoke_it(self):
        """Verify that if user says 'Hey Pulsar open chrome' after mic click, wake word is stripped and command passes."""
        from ai_assistant.core.speech_text_crisper import filter_and_crisp_speech_transcript
        
        res = filter_and_crisp_speech_transcript(
            "hey pulsar open chrome",
            require_wake_word=False,
            check_echo=False
        )
        self.assertTrue(res["valid"])
        self.assertEqual(res["matched_wake"].lower(), "hey pulsar")
        self.assertEqual(res["crisped_text"].lower(), "open chrome")

    def test_execute_companion_voice_command_drops_noise(self):
        """Verify execute_companion_voice_command drops single-syllable noise."""
        from backend.routes.system_routes import execute_companion_voice_command
        
        res = execute_companion_voice_command({"command": "आई", "source": "companion_voice"})
        self.assertTrue(res.get("dropped_noise"))
        self.assertTrue(res.get("silent"))
        self.assertEqual(res.get("response"), "")

    def test_screen_request_phrase_detection(self):
        """Verify command_requests_screen identifies both English and Hindi screen queries."""
        from backend.inprocess_voice import command_requests_screen
        
        self.assertTrue(command_requests_screen("what is on screen"))
        self.assertTrue(command_requests_screen("स्क्रीन पर क्या चल रहा है"))
        self.assertTrue(command_requests_screen("look at my screen"))
        self.assertFalse(command_requests_screen("play saiyaara song"))
        self.assertFalse(command_requests_screen("open whatsapp"))

    def test_is_paused_during_webui_mic_recording(self):
        """Verify in-process listener pauses when WebUI microphone is recording."""
        from backend.inprocess_voice import InProcessVoiceManager
        mgr = InProcessVoiceManager.get_instance(self.mock_socketio)
        
        with patch("backend.voice_service.get_overlay_state") as mock_ov:
            mock_ov.return_value = {"webui_mic_active": True}
            self.assertTrue(mgr._is_paused())
            self.assertTrue(mgr._is_capture_aborted())
            
            mock_ov.return_value = {"webui_mic_active": False}
            with patch("backend.voice_service.is_wake_word_enabled", return_value=True):
                self.assertFalse(mgr._is_paused())
                self.assertFalse(mgr._is_capture_aborted())


if __name__ == "__main__":
    unittest.main()
