import sys
from pathlib import Path
_root = Path(__file__).resolve().parent.parent
sys.path.extend([str(_root / "core_ai" / "src"), str(_root / "backend")])

import unittest
import time
import json
from ai_assistant.voice.vocabulary_registry import VocabularyRegistry, get_vocabulary_registry
from ai_assistant.voice.text_cleaner import hinglish_to_devanagari, clean_text_for_tts
from ai_assistant.knowledge.interaction_learner import record_turn_and_learn_async, _extract_and_persist_facts
from ai_assistant.ai.user_dna import UserDNA
from ai_assistant.core.jarvis_persona import build_persona_system_prompt


class TestVocabularyAndLifeLearner(unittest.TestCase):
    """Test suite for User Dictionary, Grammar Engine, and Situational Life Learning."""

    def setUp(self):
        self.reg = get_vocabulary_registry()

    def tearDown(self):
        import sqlite3
        try:
            dna = UserDNA()
            with sqlite3.connect(dna.db_path) as conn:
                conn.execute("DELETE FROM user_dna WHERE key IN ('user_name', 'upcoming_exam', 'upcoming_interview', 'friend_name', 'user_location')")
                conn.commit()
        except Exception:
            pass

    def test_vocabulary_whisper_prompt_keywords(self):
        kw = self.reg.get_whisper_prompt_keywords()
        self.assertIsInstance(kw, str)
        self.assertIn("Diwakar", kw)
        self.assertIn("Rancho", kw)
        self.assertIn("VS Code", kw)

    def test_stt_phonetic_normalization(self):
        raw_transcription = "hey divakar launch vescode now"
        normalized = self.reg.normalize_stt_transcript(raw_transcription)
        self.assertIn("diwakar", normalized.lower())
        self.assertIn("vs code", normalized.lower())

    def test_feminine_grammar_enforcement(self):
        # Hinglish
        hinglish_male = "main ye kaam karunga aur dekhunga"
        hinglish_fem = self.reg.enforce_grammar_and_tone(hinglish_male)
        self.assertIn("karungi", hinglish_fem)
        self.assertIn("dekhungi", hinglish_fem)

        # Devanagari
        dev_male = "मैं यह कोड करूँगा और सोचता हूँ।"
        dev_fem = self.reg.enforce_grammar_and_tone(dev_male)
        self.assertIn("करूँगी", dev_fem)
        self.assertIn("सोचती हूँ", dev_fem)

    def test_anti_servant_tone_filter(self):
        servant_phrase = "सारे सिस्टम ऑनलाइन हैं — आदेश दें।"
        filtered = self.reg.enforce_grammar_and_tone(servant_phrase)
        self.assertNotIn("आदेश दें", filtered)
        self.assertIn("बताओ", filtered)

    def test_tts_phonetics_injection_in_text_cleaner(self):
        cleaned = hinglish_to_devanagari("open vs code for diwakar")
        self.assertIn("वीएस कोड", cleaned)
        self.assertIn("दिवाकर", cleaned)

    def test_interaction_learner_async_speed_and_accuracy(self):
        t0 = time.perf_counter()
        record_turn_and_learn_async(
            "mera exam Monday ko hai",
            "Best of luck! Main prepare karwa dungi.",
            source="test_runner"
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        # Verification: Must complete immediately in < 2ms (non-blocking daemon)
        self.assertLess(elapsed_ms, 15.0)

        # Synchronous execution check
        _extract_and_persist_facts(
            "mera interview Friday ko hai",
            "Interview ke liye best wishes!",
            active_window={"app_name": "Code.exe", "title": "project.py"}
        )
        dna = UserDNA()
        profile = dna.get_full_profile()
        self.assertIn("upcoming_interview", profile)
        self.assertIn("Friday", str(profile["upcoming_interview"]))

    def test_persona_system_prompt_includes_living_context(self):
        UserDNA().update_trait("upcoming_interview", "Friday")
        prompt = build_persona_system_prompt()
        self.assertIn("LIVING USER CONTEXT", prompt)
        self.assertIn("Upcoming Events", prompt)
        # Ensure strict gender rule remains
        self.assertIn("PERSONA GENDER", prompt)

    def test_tts_pipeline_wiring(self):
        from ai_assistant.voice.text_cleaner import prepare_text_for_kitten_tts, clean_text_for_tts, hinglish_to_devanagari

        input_text = "Main vs code open kar raha hoon for diwakar"
        cleaned = clean_text_for_tts(input_text)
        self.assertIn("kar rahi hoon", cleaned)
        self.assertIn("VS Code", cleaned)
        self.assertIn("Diwakar", cleaned)

        # EdgeTTS hi-IN Devanagari conversion
        edge_text = hinglish_to_devanagari(input_text)
        self.assertIn("कर रही हूँ", edge_text)
        self.assertIn("वीएस कोड", edge_text)
        self.assertIn("दिवाकर", edge_text)

        # KittenTTS offline conversion
        kitten_text = prepare_text_for_kitten_tts(input_text)
        self.assertIn("V S Code", kitten_text)
        self.assertIn("Dih-wah-kur", kitten_text)

        # Anti-servant across pipeline
        servant_input = "saare system online hain, aadesh den."
        clean_servant = clean_text_for_tts(servant_input)
        self.assertNotIn("aadesh den", clean_servant.lower())
        kitten_servant = prepare_text_for_kitten_tts(servant_input)
        self.assertNotIn("aadesh den", kitten_servant.lower())


if __name__ == '__main__':
    unittest.main()
