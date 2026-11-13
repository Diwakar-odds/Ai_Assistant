#!/usr/bin/env python3
"""
Unit and regression test suite for:
1. STT Whisper normalization of garbled Hindi queries ("अगी स्क्रीन पर क्या जर लाई?")
2. Whisper noise/hallucination fragment rejection (single tokens like "आई", "आ", "the")
3. Silencing spammy pre-task filler reports for Q&A, chat, app launches, and media
4. Elimination of repetitive post-task boilerplate ("बताओ अगला क्या मूव है?", "लीजिए, काम डन — ")
5. Multimodal vision description extraction and screen query recognition in Agent Brain
6. Clean, peer-to-peer single-clause wake acknowledgments
"""

import sys
import unittest
from pathlib import Path

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

from ai_assistant.voice.vocabulary_registry import get_vocabulary_registry
from ai_assistant.core.local_command_normalizer import is_noise_fragment
from ai_assistant.core.jarvis_persona import (
    generate_wake_acknowledgment,
    generate_pre_task_report,
    format_post_task_report,
    _infer_action_category,
)
from backend.agent_brain import AgentBrain


class TestSTTHindiPhonetics(unittest.TestCase):
    def setUp(self):
        self.vocab = get_vocabulary_registry()

    def test_garbled_screen_query_normalized(self):
        raw = "अगी स्क्रीन पर क्या जर लाई?"
        norm = self.vocab.normalize_stt_transcript(raw)
        self.assertIn("स्क्रीन पर क्या चल रहा है", norm)

    def test_misheard_words(self):
        self.assertEqual(self.vocab.normalize_stt_transcript("अगी"), "अभी")
        self.assertEqual(self.vocab.normalize_stt_transcript("पल्सर"), "Pulsar")


class TestNoiseFragmentRejection(unittest.TestCase):
    def test_single_noise_tokens_rejected(self):
        for token in ("आई", "आ", "ओ", "है", "हैं", "हाँ", "ना", "the", "um", "uh", "you"):
            self.assertTrue(is_noise_fragment(token), f"Expected token '{token}' to be rejected as noise")

    def test_valid_commands_accepted(self):
        for cmd in ("open whatsapp", "play saiyaara", "what is on screen", "stop", "volume up", "स्क्रीन पर क्या चल रहा है"):
            self.assertFalse(is_noise_fragment(cmd), f"Expected command '{cmd}' to be accepted as valid")


class TestPreTaskReportSilencing(unittest.TestCase):
    def test_app_launch_silent_pre_report(self):
        # "open whatsapp" should be classified as open_app and have NO pre-report
        cat = _infer_action_category("open whatsapp")
        self.assertEqual(cat, "open_app")
        pre = generate_pre_task_report("open whatsapp")
        self.assertIsNone(pre, "Direct app launch should NOT emit pre-report text")

    def test_media_silent_pre_report(self):
        cat = _infer_action_category("play saiyaara song")
        self.assertEqual(cat, "media")
        pre = generate_pre_task_report("play saiyaara song")
        self.assertIsNone(pre, "Media commands should NOT emit pre-report text")

    def test_general_think_silent_pre_report(self):
        cat = _infer_action_category("what is running on screen?")
        self.assertEqual(cat, "screen_vision")
        # Direct screen vision inquiry should be quiet
        pre = generate_pre_task_report("what is running on screen?")
        self.assertIsNone(pre)

        cat_qa = _infer_action_category("who was Albert Einstein?")
        self.assertEqual(cat_qa, "general_think")
        pre_qa = generate_pre_task_report("who was Albert Einstein?")
        self.assertIsNone(pre_qa, "Q&A queries should NOT emit filler pre-report text")


class TestPostTaskReportFormatting(unittest.TestCase):
    def test_screen_action_unwrapped(self):
        desc = "Personal 2 - Microsoft Edge is open with 8 tabs visible."
        formatted = format_post_task_report(
            command="what is running on screen?",
            raw_result=desc,
            success=True,
            intent="screen_action"
        )
        self.assertEqual(formatted, desc, "Screen vision descriptions must NOT be wrapped with action boilerplate")
        self.assertNotIn("लीजिए, काम डन", formatted)

    def test_no_next_move_spam(self):
        result = "WhatsApp khol diya hai"
        formatted = format_post_task_report(
            command="open whatsapp",
            raw_result=result,
            success=True,
            intent="open_app"
        )
        self.assertNotIn("बताओ अगला क्या मूव है?", formatted)


class TestAgentBrainScreenHandling(unittest.TestCase):
    def test_explicit_screen_request_hindi(self):
        self.assertTrue(AgentBrain._explicit_screen_request("स्क्रीन पर क्या चल रहा है?"))
        self.assertTrue(AgentBrain._explicit_screen_request("अगी स्क्रीन पर क्या जर लाई?"))
        self.assertTrue(AgentBrain._explicit_screen_request("what is running on screen?"))

    def test_extract_analysis_text(self):
        self.assertEqual(
            AgentBrain._extract_analysis_text({"analysis": "Edge browser is open"}),
            "Edge browser is open"
        )
        self.assertEqual(
            AgentBrain._extract_analysis_text({"description": "VS Code editor"}),
            "VS Code editor"
        )
        self.assertEqual(
            AgentBrain._extract_analysis_text({}, fallback="Default screen text"),
            "Default screen text"
        )


class TestWakeAcknowledgmentTone(unittest.TestCase):
    def test_wake_ack_concise_single_thought(self):
        for _ in range(10):
            ack = generate_wake_acknowledgment(wake_word="pulsar", language_hint="hindi")
            self.assertTrue(len(ack.split()) <= 10, f"Wake ack too long: {ack}")
            self.assertNotIn("बताओ — बताओ", ack, f"Wake ack has stuttering repetition: {ack}")


if __name__ == "__main__":
    unittest.main()
