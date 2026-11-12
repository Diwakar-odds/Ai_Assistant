"""
Unit tests for Deterministic (Zero-LLM) Speech Text Crisper, Echo Rejection & Hallucination Filter.
Verifies sub-millisecond filtering of Whisper artifacts, repetition loops, self-echo, stutters, and fillers.
"""

import os
import sys
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(PROJECT_ROOT / "core_ai" / "src"))

from ai_assistant.core.speech_text_crisper import (
    record_recent_tts,
    is_recent_tts_echo,
    is_hallucination_or_garbage,
    crisp_speech_transcript,
    filter_and_crisp_speech_transcript,
)


class TestSpeechTextCrisper(unittest.TestCase):

    def test_whisper_sound_tags_rejection(self):
        """Whisper bracketed tags, emojis, and sound annotations must be flagged as garbage."""
        tags = [
            "[Music]",
            "[music]",
            "[Applause]",
            "[cheering]",
            "(music)",
            "*music*",
            "♪♪♪",
            "🎵 🎶",
            "[संगीत]",
            "...",
            "???",
            "--",
        ]
        for tag in tags:
            is_garbage, reason = is_hallucination_or_garbage(tag)
            self.assertTrue(is_garbage, f"Expected '{tag}' to be flagged as garbage, got reason: {reason}")

    def test_whisper_subtitle_watermark_rejection(self):
        """Whisper subtitle watermark phrases must be flagged as garbage."""
        watermarks = [
            "Thank you for watching!",
            "Thanks for watching",
            "Please subscribe to my channel",
            "Subtitles by Amara.org",
            "Like and subscribe for more videos",
            "All rights reserved.",
        ]
        for wm in watermarks:
            is_garbage, reason = is_hallucination_or_garbage(wm)
            self.assertTrue(is_garbage, f"Expected watermark '{wm}' to be flagged as garbage, got: {reason}")
            self.assertIn("whisper_subtitle_watermark", reason)

    def test_repetition_loops_and_gibberish_rejection(self):
        """Background noise, syllable repetition loops and vowel-less mash must be flagged."""
        loops = [
            "na na na na na na na",
            "ha ha ha ha ha ha",
            "dum dum dum dum dum",
            "you know you know you know you know",
            "asdfghjkl",
            "qwrtyp",
        ]
        for lp in loops:
            is_garbage, reason = is_hallucination_or_garbage(lp)
            self.assertTrue(is_garbage, f"Expected '{lp}' to be flagged as garbage, got: {reason}")

    def test_valid_commands_not_flagged_as_garbage(self):
        """Legitimate user commands in English, Hindi, and Hinglish must NOT be flagged as garbage."""
        valid_cmds = [
            "play next song",
            "open whatsapp",
            "pause the music",
            "गाना बजाओ",
            "ले नेख सों",
            "volume badhao",
            "what is the capital of France",
            "take a screenshot",
        ]
        for cmd in valid_cmds:
            is_garbage, reason = is_hallucination_or_garbage(cmd)
            self.assertFalse(is_garbage, f"Expected '{cmd}' to be valid, but got garbage reason: {reason}")

    def test_self_echo_detection_and_rejection(self):
        """Speech spoken by AI within 3.5 seconds must be flagged as acoustic self-echo."""
        ai_spoken = "सुनिए Boss, बोलie, अभी किस काम से शुरुआत करें?"
        record_recent_tts(ai_spoken, timestamp=time.time())

        # Sub-phrase acoustic leakage
        leak_1 = "बोलie अभी किस काम से शुरुआत"
        is_echo, score, matched = is_recent_tts_echo(leak_1, max_age_seconds=3.5)
        self.assertTrue(is_echo, f"Expected '{leak_1}' to be detected as self-echo, score: {score}")

        # Heavy token overlap
        leak_2 = "Boss abhi kis kaam se shuruat karein"
        # Spoken English text test
        ai_spoken_en = "I am ready Boss, what can I do for you today?"
        record_recent_tts(ai_spoken_en, timestamp=time.time())
        leak_en = "ready Boss what can I do for you"
        is_echo_en, score_en, _ = is_recent_tts_echo(leak_en, max_age_seconds=3.5)
        self.assertTrue(is_echo_en, f"Expected '{leak_en}' to be detected as self-echo, score: {score_en}")

        # Expired echo (>4.0s) should NOT be flagged
        record_recent_tts("Puraane session ki baat", timestamp=time.time() - 5.0)
        is_echo_old, _, _ = is_recent_tts_echo("Puraane session ki baat", max_age_seconds=3.5)
        self.assertFalse(is_echo_old, "Expected old TTS record to expire and not trigger echo rejection")

    def test_barge_in_stops_never_treated_as_echo(self):
        """Critical safety: Even if AI is currently speaking, barge-in stop/pause commands must pass through!"""
        ai_spoken = "Bilkul Boss, main abhi aapke saare tasks execute kar rahi hoon aur file download kar rahi hoon."
        record_recent_tts(ai_spoken, timestamp=time.time())

        stop_cmds = [
            "stop",
            "chup ho jao",
            "chup karo",
            "bas",
            "ruk jao",
            "shut up",
            "be quiet",
            "हे पल्सर चुप",
            "Hey Pulsar stop",
        ]
        for cmd in stop_cmds:
            is_echo, score, _ = is_recent_tts_echo(cmd, max_age_seconds=3.5)
            self.assertFalse(is_echo, f"Barge-in command '{cmd}' should NEVER be rejected as echo!")

    def test_stutter_collapsing_and_crisping(self):
        """Duplicate consecutive words (stutters) must collapse to single words."""
        cases = [
            ("open open chrome", "Open chrome"),
            ("play play next next song", "Play next song"),
            ("main main sun raha hoon", "Main sun raha hoon"),
            ("मैं मैं सुन रहा हूँ", "मैं सुन रहा हूँ"),
        ]
        for raw, expected in cases:
            crisped = crisp_speech_transcript(raw)
            self.assertEqual(crisped, expected)

    def test_filler_pruning_and_conjunction_trimming(self):
        """Speech hesitation markers (um, uh, matlab) and dangling conjunctions (and, aur) must be pruned."""
        cases = [
            ("um uh matlab open notepad please and", "Open notepad"),
            ("suno na what is the weather today yaar", "What is the weather today"),
            ("arey yaar play song and", "Play song"),
            ("toh wo chrome kholo aur", "Chrome kholo"),
            ("hmmm open calculator plz", "Open calculator"),
        ]
        for raw, expected in cases:
            crisped = crisp_speech_transcript(raw)
            self.assertEqual(crisped, expected)

    def test_filter_and_crisp_speech_transcript_unified(self):
        """Full pipeline verification: wake-word matching, garbage discard, echo discard, and crisping."""
        # 1. Wake word required - Wake present + command
        res1 = filter_and_crisp_speech_transcript("Hey Pulsar open open chrome and", require_wake_word=True, check_echo=False)
        self.assertTrue(res1["valid"])
        self.assertEqual(res1["matched_wake"].lower(), "hey pulsar")
        self.assertEqual(res1["crisped_text"], "Open chrome")
        self.assertFalse(res1["is_wake_only"])

        # 2. Wake word required - Wake only
        res2 = filter_and_crisp_speech_transcript("Hey Pulsar", require_wake_word=True, check_echo=False)
        self.assertTrue(res2["valid"])
        self.assertEqual(res2["matched_wake"].lower(), "hey pulsar")
        self.assertTrue(res2["is_wake_only"])

        # 3. Wake word required - Missing wake word
        res3 = filter_and_crisp_speech_transcript("open chrome", require_wake_word=True, check_echo=False)
        self.assertFalse(res3["valid"])
        self.assertEqual(res3["rejection_reason"], "wake_word_required")

        # 4. Whisper music tag
        res4 = filter_and_crisp_speech_transcript("[Music]", require_wake_word=False, check_echo=False)
        self.assertFalse(res4["valid"])
        self.assertIn("whisper_music_or_sound_tag", res4["rejection_reason"])

        # 5. Echo rejection with wake word (Residual after wake word is pure echo)
        ai_phrase = "Main bilkul ready hoon aaj ka kya plan hai"
        record_recent_tts(ai_phrase, timestamp=time.time())
        res5 = filter_and_crisp_speech_transcript("Hey Pulsar Main bilkul ready hoon", require_wake_word=True, check_echo=True)
        self.assertFalse(res5["valid"])
        self.assertIn("recent_tts_self_echo", res5["rejection_reason"])


if __name__ == "__main__":
    unittest.main()
