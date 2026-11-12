#!/usr/bin/env python3
"""
Regression test suite for Pulsar desktop companion & voice UX fixes:
1. Wake-word hallucination stripping & bare vs inline command separation
2. Multilingual English/Hinglish/Hindi voice barge-in stop detection
3. Whisper segment quality filtering & noise-floor resistance
4. CompanionVoiceListener active-TTS barge-in without echo leakage
5. Strict screen-capture opt-in gating & no ambient Antigravity prompt leak
6. Compact, highly transparent ParticleOrbRenderer dimensions & alpha transparency
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for p in (
    PROJECT_ROOT,
    PROJECT_ROOT / "backend",
    PROJECT_ROOT / "core_ai" / "src",
    PROJECT_ROOT / "shared",
    PROJECT_ROOT / "desktop",
):
    sp = str(p)
    if sp not in sys.path:
        sys.path.insert(0, sp)

from ai_assistant.core.local_command_normalizer import (
    is_barge_in_stop_command,
    match_and_strip_wake_phrase,
    parse_voice_control_command,
)
from companion_voice import CompanionVoiceListener, filter_whisper_segments


class TestWakeHallucinationAndStripping(unittest.TestCase):
    def test_tail_hallucination_loops_rejected(self):
        for hallucination in (
            "बले में यह वे पल्सरे पल्सर",
            "भ़ो अभार पल्सर, बपल्सर, पल्सर, पल्सर,",
            "प्र्स पल्स पल्सर, पल्सर, पल्सर,",
        ):
            with self.subTest(hallucination=hallucination):
                matched, _ = match_and_strip_wake_phrase(hallucination)
                self.assertIsNone(matched)

    def test_leading_repeated_wake_strips_cleanly(self):
        matched, rem = match_and_strip_wake_phrase("हे पल्सर, पल्सर")
        self.assertIsNotNone(matched)
        self.assertEqual(rem, "")

        matched2, rem2 = match_and_strip_wake_phrase("Pulsar, Pulsar!")
        self.assertIsNotNone(matched2)
        self.assertEqual(rem2, "")

        _, rem3 = match_and_strip_wake_phrase("पल्सर, पल्सर, व़र,")
        self.assertEqual(rem3, "")

    def test_valid_wake_commands_preserved(self):
        m1, c1 = match_and_strip_wake_phrase("Hey Pulsar open Chrome")
        self.assertEqual(m1, "hey pulsar")
        self.assertEqual(c1, "open Chrome")

        m2, c2 = match_and_strip_wake_phrase("पल्सर यूट्यूब खोलो")
        self.assertEqual(m2, "पल्सर")
        self.assertEqual(c2, "यूट्यूब खोलो")

        m3, c3 = match_and_strip_wake_phrase("Hey Pulsar")
        self.assertEqual(m3, "hey pulsar")
        self.assertEqual(c3, "")

        m4, c4 = match_and_strip_wake_phrase("Open YouTube hey pulsar")
        self.assertEqual(m4, "hey pulsar")
        self.assertEqual(c4, "Open YouTube")

        m5, c5 = match_and_strip_wake_phrase("Hey Pulsar, Pulsar, mute")
        self.assertEqual(m5, "hey pulsar")
        self.assertEqual(c5, "mute")


class TestBargeInAndVoiceControl(unittest.TestCase):
    def test_barge_in_stop_phrases_matched(self):
        for phrase in (
            "chup",
            "chup ho jao",
            "chup raho",
            "bas karo",
            "ruk jao",
            "ruko",
            "roko",
            "band karo",
            "bolna band karo",
            "stop",
            "stop speaking",
            "stop talking",
            "quiet",
            "be quiet",
            "shut up",
            "cancel",
            "चुप हो जाओ",
            "बस करो",
            "रुक जाओ",
            "बोलना बंद करो",
            "hey pulsar chup ho jao",
            "पल्सर रुक जाओ",
            "chup ho jao please",
        ):
            with self.subTest(phrase=phrase):
                self.assertTrue(is_barge_in_stop_command(phrase))

    def test_normal_commands_not_misclassified_as_barge_in(self):
        for phrase in (
            "stop spotify",
            "open chrome",
            "hey pulsar",
            "cancel my 5pm meeting",
            "what time is it",
            "Antigravity X overview",
        ):
            with self.subTest(phrase=phrase):
                self.assertFalse(is_barge_in_stop_command(phrase))

    def test_transient_stop_does_not_disable_persistent_tts(self):
        parsed_stop = parse_voice_control_command("stop speaking")
        self.assertIsNotNone(parsed_stop)
        self.assertEqual(parsed_stop["action"], "stop_speaking")

        parsed_hindi = parse_voice_control_command("chup ho jao")
        self.assertIsNotNone(parsed_hindi)
        self.assertEqual(parsed_hindi["action"], "stop_speaking")

        parsed_off = parse_voice_control_command("tts off")
        self.assertEqual(parsed_off, {"action": "toggle_tts", "enabled": False, "raw": "tts off"})


class TestWhisperFilteringAndBargeInListener(unittest.TestCase):
    def test_filter_whisper_segments_drops_hallucinations(self):
        segments = [
            SimpleNamespace(text="पल्सर, पल्सर, पल्सर", no_speech_prob=0.82, avg_logprob=-1.5, compression_ratio=3.1),
            SimpleNamespace(text="weak noise", no_speech_prob=0.70, avg_logprob=-0.4, compression_ratio=1.1),
            SimpleNamespace(text="garbled", no_speech_prob=0.10, avg_logprob=-1.6, compression_ratio=1.1),
            SimpleNamespace(text="hey pulsar open chrome", no_speech_prob=0.05, avg_logprob=-0.25, compression_ratio=1.15),
        ]
        self.assertEqual(filter_whisper_segments(segments), "hey pulsar open chrome")

    def test_listener_barge_in_behavior_during_tts(self):
        barge_calls = []
        cmd_calls = []
        wake_calls = []

        with patch.object(CompanionVoiceListener, "_init_models", lambda self: None):
            listener = CompanionVoiceListener(
                on_wake=lambda w=None: wake_calls.append(w),
                on_command=lambda c: cmd_calls.append(c),
                is_tts_speaking_fn=lambda: True,
                on_barge_in=lambda t="": barge_calls.append(t),
                get_wake_phrases_fn=lambda: ["hey pulsar", "pulsar"],
            )

        pcm = np.ones(16000, dtype=np.float32) * 0.2

        # 1. Explicit Hinglish stop during TTS -> barge-in only, no command/LLM
        with patch.object(listener, "_transcribe_pcm", return_value="chup ho jao"):
            listener._process_barge_in_candidate(None, pcm, 0.008)
        self.assertEqual(barge_calls, ["chup ho jao"])
        self.assertEqual(cmd_calls, [])

        barge_calls.clear()

        # 2. Speaker bleed containing random commentary or bare "Pulsar" -> ignored
        with patch.object(listener, "_transcribe_pcm", return_value="Antigravity screen pulsar details"):
            listener._process_barge_in_candidate(None, pcm, 0.008)
        self.assertEqual(barge_calls, [])
        self.assertEqual(cmd_calls, [])

        # 3. Multi-word wake + inline command during TTS -> stops TTS AND dispatches command
        with patch.object(listener, "_transcribe_pcm", return_value="hey pulsar open notepad"):
            listener._process_barge_in_candidate(None, pcm, 0.008)
        self.assertEqual(barge_calls, ["hey pulsar open notepad"])
        self.assertEqual(cmd_calls, ["open notepad"])


class TestScreenOptInAndAgentBrainIsolation(unittest.TestCase):
    def test_command_requests_screen_opt_in(self):
        from companion_app import command_requests_screen

        self.assertFalse(command_requests_screen("hello how are you"))
        self.assertFalse(command_requests_screen("open chrome"))
        self.assertFalse(command_requests_screen("write python code for sorting"))
        self.assertFalse(command_requests_screen("call rahul"))
        self.assertTrue(command_requests_screen("mere screen pe kya hai"))
        self.assertTrue(command_requests_screen("take a screenshot"))
        self.assertTrue(command_requests_screen("check email grammar"))

    def test_agent_brain_does_not_capture_screen_or_leak_window_when_false(self):
        from agent_brain import AgentBrain

        brain = AgentBrain()
        with patch.object(
            brain,
            "get_active_window_info",
            return_value={"title": "Antigravity Secret Window", "app_name": "Antigravity.exe", "rect": (0, 0, 100, 100)},
        ), patch.object(
            brain, "capture_screen", side_effect=AssertionError("capture_screen should NOT be called!")
        ), patch.object(
            brain, "_get_active_provider_name", return_value="gguf"
        ), patch(
            "ai_assistant.core.jarvis_persona.build_persona_system_prompt", return_value="sys"
        ) as mock_prompt, patch(
            "ai_assistant.ai.llm_provider.UnifiedChatInterface"
        ) as mock_uci:
            mock_uci.return_value.chat.return_value = "Hello Boss!"
            res = brain.process_command("how to write python code", include_screen=False, source="companion_voice")
            self.assertTrue(res["success"])
            self.assertTrue(mock_prompt.called)
            self.assertIsNone(mock_prompt.call_args.kwargs.get("active_window"))


class TestCompactTransparentOrbRenderer(unittest.TestCase):
    def test_orb_size_position_and_center_transparency(self):
        from companion_app import (
            DEFAULT_ORB_SIZE,
            ParticleOrbRenderer,
            get_workarea_bottom_center_coords,
        )

        self.assertGreaterEqual(DEFAULT_ORB_SIZE, 96)
        self.assertLessEqual(DEFAULT_ORB_SIZE, 180)
        renderer = ParticleOrbRenderer(size=DEFAULT_ORB_SIZE)
        frame = renderer.render_frame(state="idle", audio_level=0.0, dt=0.03)
        self.assertEqual(frame.size, (DEFAULT_ORB_SIZE, DEFAULT_ORB_SIZE))

        rgba = np.asarray(frame)
        alpha = rgba[:, :, 3]

        # Corners must be 100% transparent (alpha == 0)
        self.assertEqual(int(alpha[0, 0]), 0)
        self.assertEqual(int(alpha[0, -1]), 0)
        self.assertEqual(int(alpha[-1, 0]), 0)
        self.assertEqual(int(alpha[-1, -1]), 0)

        # Center region backdrop median alpha must stay very transparent (< 45/255 = <18% opacity)
        c = DEFAULT_ORB_SIZE // 2
        center_patch = alpha[c - 16 : c + 16, c - 16 : c + 16]
        self.assertLess(float(np.median(center_patch)), 45.0)
        # Speaking state must also remain clearly see-through (< 60/255)
        for _ in range(10):
            sp_frame = renderer.render_frame(state="speaking", audio_level=75.0, dt=0.03)
        sp_alpha = np.asarray(sp_frame)[:, :, 3]
        self.assertLess(float(np.median(sp_alpha[c - 16 : c + 16, c - 16 : c + 16])), 60.0)
        # Glowing wireframe/particles must still be visibly lit
        self.assertGreaterEqual(int(alpha.max()), 150)

        # Positioning sits cleanly above taskbar without negative margin clipping below work area
        x, y = get_workarea_bottom_center_coords(DEFAULT_ORB_SIZE, DEFAULT_ORB_SIZE)
        self.assertGreaterEqual(x, 0)
        self.assertGreaterEqual(y, 0)


class TestScreenShareStealthAffinity(unittest.TestCase):
    def test_stealth_constants_and_win32_affinity(self):
        import ctypes
        import ctypes.wintypes as wt
        import win32gui
        import win32con
        from companion_app import WDA_EXCLUDEFROMCAPTURE, WDA_NONE, WDA_MONITOR

        self.assertEqual(WDA_EXCLUDEFROMCAPTURE, 0x00000011)
        self.assertEqual(WDA_NONE, 0x00000000)
        self.assertEqual(WDA_MONITOR, 0x00000001)

        user32 = ctypes.windll.user32
        self.assertTrue(hasattr(user32, "SetWindowDisplayAffinity"))

        # Create temporary layered test window to verify OS accepts WDA_EXCLUDEFROMCAPTURE
        hwnd = win32gui.CreateWindowEx(
            win32con.WS_EX_LAYERED,
            "STATIC",
            "PulsarStealthTest",
            win32con.WS_POPUP,
            0,
            0,
            16,
            16,
            0,
            0,
            0,
            None,
        )
        try:
            ok = user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE)
            self.assertTrue(bool(ok))
            if hasattr(user32, "GetWindowDisplayAffinity"):
                val = wt.DWORD()
                get_ok = user32.GetWindowDisplayAffinity(hwnd, ctypes.byref(val))
                if get_ok:
                    self.assertEqual(val.value, WDA_EXCLUDEFROMCAPTURE)
        finally:
            win32gui.DestroyWindow(hwnd)

    def test_settings_and_voice_stealth_commands(self):
        from settings_manager import is_screen_share_stealth_enabled

        # Default is stealth enabled (True) like Parakeet AI
        self.assertTrue(is_screen_share_stealth_enabled())

        # Voice command parsing for stealth toggle
        for phrase, expected in (
            ("screen share stealth on", True),
            ("stealth mode on", True),
            ("screen share me chupao", True),
            ("hide in screen share", True),
            ("screen share stealth off", False),
            ("stealth mode off", False),
            ("screen share me visible karo", False),
        ):
            with self.subTest(phrase=phrase):
                res = parse_voice_control_command(phrase)
                self.assertIsNotNone(res)
                self.assertEqual(res["action"], "toggle_screen_share_stealth")
                self.assertEqual(res["enabled"], expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
