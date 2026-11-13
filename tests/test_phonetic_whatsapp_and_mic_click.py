"""
Tests for manual mic push-to-talk contract and phonetic WhatsApp routing.
"""

import unittest
import sys
from pathlib import Path

# Ensure paths
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "core_ai" / "src"))
sys.path.insert(0, str(root / "backend"))

from ai_assistant.core.local_command_normalizer import normalize_hinglish_devanagari
from ai_assistant.voice.vocabulary_registry import get_vocabulary_registry
from ai_assistant.ai.intent_router import IntentRouter


class TestPhoneticWhatsAppAndMic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = get_vocabulary_registry()
        cls.router = IntentRouter()

    def test_whisper_phonetic_whatsapp_routing(self):
        variations = [
            "वाट्सब प्वलो",
            "वाटसब प्वलो",
            "वाट्सप खोलो",
            "व्हाट्सएप प्वलो",
            "व्हाट्सब खोलो",
            "whatsapp kholo",
            "open whatsapp",
            "व्हाट्सएप खोलो",
        ]
        for q in variations:
            res = self.router.route(q)
            self.assertIsNotNone(res, f"Failed to route '{q}'")
            self.assertEqual(res.intent_name, "open_app", f"Wrong intent for '{q}': {res.intent_name}")
            self.assertEqual(res.parameters.get("target"), "whatsapp", f"Wrong target for '{q}': {res.parameters}")
            self.assertEqual(res.tier, 1, f"Expected Tier 1 fast match for '{q}', got Tier {res.tier}")

    def test_stt_corrections_map(self):
        self.assertEqual(self.registry.normalize_stt_transcript("वाट्सब प्वलो").lower(), "whatsapp खोलो")
        self.assertEqual(self.registry.normalize_stt_transcript("व्हाट्सब").lower(), "whatsapp")

    def test_hinglish_normalization(self):
        self.assertEqual(normalize_hinglish_devanagari("वाट्सब प्वलो"), "open whatsapp")
        self.assertEqual(normalize_hinglish_devanagari("वाट्सप खोलो"), "open whatsapp")


if __name__ == "__main__":
    unittest.main()
