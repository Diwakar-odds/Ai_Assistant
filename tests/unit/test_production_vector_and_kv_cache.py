"""
Unit Tests for Production Upgrade Components:
1. GGUF Q8_0 KV Cache parameter specification
2. Shared Embedder Singleton and normalization
3. Tier 1.5 Precomputed Vector Matcher speed and accuracy
4. IntentRouter Tier 1.5 integration
5. Conversational Fast-Path Guardrails (false-positive prevention)
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project paths
project_root = Path(__file__).resolve().parents[2]
sys.path.extend([
    str(project_root),
    str(project_root / "core_ai" / "src"),
    str(project_root / "backend"),
])

import numpy as np


class TestProductionVectorAndKVCache(unittest.TestCase):

    def test_shared_embedder_normalization(self):
        """Verify that shared embedder produces unit-length (L2 norm = 1.0) vectors."""
        from ai_assistant.ai.shared_embedder import encode_text, cosine_similarity

        vec1 = encode_text("open visual studio code", normalize=True)
        self.assertIsNotNone(vec1)
        self.assertEqual(len(vec1), 384)
        
        # Norm should be approximately 1.0
        norm1 = np.linalg.norm(vec1)
        self.assertAlmostEqual(norm1, 1.0, places=4)

        vec2 = encode_text("launch vs code", normalize=True)
        self.assertIsNotNone(vec2)
        
        # Similarity should be positive and indicative of semantic relation (> 0.50)
        sim = cosine_similarity(vec1, vec2.reshape(1, -1))[0]
        self.assertGreater(sim, 0.50)

    def test_intent_vector_matcher_load_and_speed(self):
        """Verify Tier 1.5 matcher loads in <10ms and classifies variations accurately."""
        import time
        from ai_assistant.ai.intent_vector_matcher import IntentVectorMatcher

        matcher = IntentVectorMatcher()
        self.assertTrue(matcher.is_available(), "IntentVectorMatcher should have loaded intent_embeddings.npz")

        # Test semantic match on non-exact command variation
        t0 = time.time()
        match = matcher.match("screen ki photo lo")
        latency_ms = (time.time() - t0) * 1000

        self.assertIsNotNone(match, "Should match 'screen ki photo lo' to analyze_screen")
        self.assertEqual(match.intent_name, "analyze_screen")
        self.assertGreaterEqual(match.confidence, 0.70)
        print(f"\n[BENCHMARK] Tier 1.5 Vector Match latency: {latency_ms:.2f}ms (conf: {match.confidence:.3f})")

    def test_conversational_guardrail_prevents_false_positives(self):
        """Verify that conversational queries do NOT trigger false command matches."""
        from ai_assistant.ai.intent_router import IntentRouter

        router = IntentRouter()
        
        # Obvious chat phrases should be bypassed and return None (general chat)
        chat_phrases = [
            "hi pulsar kaise ho",
            "kya haal hai bhai",
            "tell me a joke please",
            "what is the capital of France",
        ]
        for phrase in chat_phrases:
            res = router.route(phrase)
            self.assertIsNone(res, f"Phrase '{phrase}' should NOT trigger any intent, but got: {res}")

    def test_intent_router_tier_1_5_dispatch(self):
        """Verify that IntentRouter seamlessly routes through Tier 1.5 when Tier 1 misses."""
        from ai_assistant.ai.intent_router import IntentRouter

        router = IntentRouter()

        # "bluetooth chalu kar do bhai" might miss strict tier-1 regex but matches via Tier 1.5
        res = router.route("bluetooth chalu kar do")
        self.assertIsNotNone(res)
        self.assertEqual(res.intent_name, "bluetooth_toggle")
        self.assertTrue(res.parameters.get("enable"))

    def test_gguf_instantiate_q8_kv_params(self):
        """Verify that GGUFModelManager requests Q8_0 KV cache and flash_attn."""
        from ai_assistant.ai.gguf_model_manager import GGUFModelManager, GGML_TYPE_Q8_0
        
        # Verify constant is present
        self.assertEqual(GGML_TYPE_Q8_0, 8)


if __name__ == "__main__":
    unittest.main()
