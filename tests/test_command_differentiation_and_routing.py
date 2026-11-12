import unittest
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

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

from ai_assistant.ai.intent_router import IntentRouter
from ai_assistant.ai.multi_step_parser import MultiStepCommandParser
from ai_assistant.core.local_command_normalizer import normalize_hinglish_devanagari
from ai_assistant.core.command_brain import CommandBrain, BrainResponse
from ai_assistant.core.emergency_stop import trigger_emergency_stop


class TestCommandDifferentiationAndRouting(unittest.TestCase):
    """
    Verification suite for:
    1. Media Command vs Multi-Step Differentiation ('play next song' is atomic, not compound)
    2. Executive Pause vs Media Pause Differentiation ('pause song' != executive pause)
    3. Whisper Phonetic Devanagari Normalization ('ले नेख सों' -> 'next song')
    4. Emergency Stop Debouncing & Single-Notification Delivery
    """

    def setUp(self):
        self.router = IntentRouter()
        self.parser = MultiStepCommandParser()

    def test_play_next_song_not_multi_step(self):
        """'play next song' must NEVER be split into 'play' and 'song'."""
        cmd = "play next song"
        self.assertFalse(self.parser.is_multi_step(cmd))
        steps = self.parser.parse_command(cmd)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].intent, "media_control")
        self.assertEqual(steps[0].params.get("action"), "next")

    def test_media_control_intent_variants(self):
        """Various English and Hindi phrases for next/prev/pause/resume route directly in Tier 1."""
        test_cases = [
            ("play next song", "next"),
            ("next song", "next"),
            ("play next track", "next"),
            ("skip song", "next"),
            ("agla gaana", "next"),
            ("अगला गाना", "next"),
            ("gaana badlo", "next"),
            ("previous song", "previous"),
            ("play prev song", "previous"),
            ("pichla gaana", "previous"),
            ("पिछला गाना", "previous"),
            ("pause song", "pause"),
            ("pause the song", "pause"),
            ("pause music", "pause"),
            ("stop the music", "pause"),
            ("gaana pause karo", "pause"),
            ("gaana roko", "pause"),
            ("म्यूजिक रोक दो", "pause"),
            ("resume song", "resume"),
            ("resume music", "resume"),
            ("gaana chalao", "resume"),
            ("gaana chalu karo", "resume"),
            ("म्यूजिक चालू करो", "resume"),
        ]
        for cmd, expected_action in test_cases:
            with self.subTest(cmd=cmd, expected=expected_action):
                res = self.router.route(cmd)
                self.assertIsNotNone(res, f"Failed to route '{cmd}'")
                self.assertEqual(res.intent_name, "media_control", f"'{cmd}' routed to '{res.intent_name}', expected 'media_control'")
                self.assertEqual(res.parameters.get("action"), expected_action, f"'{cmd}' gave action '{res.parameters.get('action')}', expected '{expected_action}'")

    def test_whisper_phonetic_normalization(self):
        """Phonetic Whisper slips like 'ले नेख सों' normalize and route directly to next song."""
        slips = [
            ("ले नेख सों", "next"),
            ("नेख सों", "next"),
            ("ले नेक्स सों", "next"),
            ("नेक्स सोंग", "next"),
            ("नेक्स्ट सोंग", "next"),
            ("प्ले नेक्स", "next"),
            ("गाना रोको", "pause"),
            ("गाना रोक दो", "pause"),
            ("गाना चलाओ", "resume"),
        ]
        for slip, expected_action in slips:
            with self.subTest(slip=slip, expected=expected_action):
                norm = normalize_hinglish_devanagari(slip)
                res = self.router.route(norm)
                self.assertIsNotNone(res, f"Failed to route normalized '{slip}' -> '{norm}'")
                self.assertEqual(res.intent_name, "media_control")
                self.assertEqual(res.parameters.get("action"), expected_action)

    def test_executive_brain_does_not_hijack_media_pause(self):
        """'pause song' must NOT return 'Execution paused.' when passed to CommandBrain."""
        brain = CommandBrain()
        brain._active_chains.clear()

        with patch("ai_assistant.core.task_chain_orchestrator.TaskChainOrchestrator.execute_command") as mock_exec:
            mock_exec.return_value = MagicMock(success=True, results=[{"result": "🎵 Paused playback"}], message="Paused playback")
            res = brain.receive_command("pause song")
            self.assertNotEqual(res.message, "Execution paused.")
            self.assertNotEqual(res.action_taken, "pause")

    def test_bare_pause_with_no_active_chains_does_not_fake_pause(self):
        """When no chains are running, bare 'pause' falls through rather than returning 'Execution paused.'"""
        brain = CommandBrain()
        brain._active_chains.clear()

        with patch("ai_assistant.core.task_chain_orchestrator.TaskChainOrchestrator.execute_command") as mock_exec:
            mock_exec.return_value = MagicMock(success=True, results=[], message="OK")
            res = brain.receive_command("pause")
            self.assertNotEqual(res.message, "Execution paused.")

    def test_emergency_stop_debouncing(self):
        """Two rapid emergency stop triggers within 1000ms return the same debounced result without error."""
        trigger_emergency_stop(reason="Warmup")
        time.sleep(1.1)  # wait past warmup debounce
        res1 = trigger_emergency_stop(reason="Test Stop 1")
        res2 = trigger_emergency_stop(reason="Test Stop 2")
        self.assertEqual(res1.get("status"), "stopped")
        self.assertEqual(res2.get("status"), "stopped")
        self.assertEqual(res1.get("reason"), res2.get("reason"))
        self.assertEqual(res1.get("reason"), "Test Stop 1")


if __name__ == '__main__':
    unittest.main()
