"""
Unit and integration tests for:
1. Generalized Closed-Loop Intent Penalty Gatekeeper
2. Multi-Turn Generalized Follow-Up Query Resolution
3. Speculative Pre-Fetching Engine (~0ms perceived latency)
4. Developer-Grade Deep Research Agent (Mode C)
"""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core_ai.ai.intent_penalty_gatekeeper import IntentPenaltyGatekeeper
from core_ai.ai.intent_router import IntentRouter
from core_ai.integrations.web_intelligence.micro_router import FollowUpContextResolver, NeuralMicroRouter
from core_ai.integrations.web_intelligence.models import WebQueryMode
from core_ai.integrations.web_intelligence.service import get_web_intelligence


class TestGeneralizedIntentAndWebIntel(unittest.TestCase):
    """Full verification suite for generalized routing, learning, and web intel."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_penalties.db")
        self.gatekeeper = IntentPenaltyGatekeeper(db_path=self.db_path)

    def tearDown(self):
        self.tmp_dir.cleanup()

    # =========================================================================
    # PART 1: INTENT PENALTY GATEKEEPER & ACTIVE CLOSED LOOP
    # =========================================================================

    def test_pattern_tokenization_and_generalization(self):
        """Test canonical token extraction across variations."""
        tokens1 = self.gatekeeper.extract_pattern_tokens("ek chutkula sunao bhai please")
        tokens2 = self.gatekeeper.extract_pattern_tokens("chutkula sunao na")
        # Both should share core semantic tokens 'chutkula' and 'sunao'
        self.assertIn("chutkula", tokens1)
        self.assertIn("sunao", tokens1)
        self.assertIn("chutkula", tokens2)
        self.assertIn("sunao", tokens2)

        key1 = self.gatekeeper.generate_pattern_key("ek chutkula sunao bhai")
        key2 = self.gatekeeper.generate_pattern_key("chutkula sunao please")
        self.assertEqual(key1, key2, "Phrasing variations must map to the same canonical key")

    def test_gatekeeper_negative_and_positive_feedback(self):
        """Test active penalty escalation and reward decrement."""
        query = "volume badha do please"
        intent = "volume_control"

        self.assertFalse(self.gatekeeper.is_penalized(query, intent))

        # Record negative feedback (e.g. user says 'nahi galat hai' or aborts)
        new_score = self.gatekeeper.record_negative_feedback(query, intent, penalty_delta=1.0)
        self.assertGreaterEqual(new_score, 1.0)
        self.assertTrue(self.gatekeeper.is_penalized(query, intent))

        # Generalized variation check: "ek volume badha do" should also be penalized
        self.assertTrue(
            self.gatekeeper.is_penalized("volume badha do", intent),
            "Variant of penalized pattern must also be detected as penalized"
        )

        # Unrelated intent must NOT be penalized
        self.assertFalse(self.gatekeeper.is_penalized(query, "tell_joke"))

        # Reward with positive feedback
        self.gatekeeper.record_positive_feedback(query, intent, reward_delta=0.5)
        self.gatekeeper.record_positive_feedback(query, intent, reward_delta=0.5)
        self.assertFalse(self.gatekeeper.is_penalized(query, intent))

    def test_intent_router_gatekeeper_bypass(self):
        """Test that IntentRouter Tier 1 bypasses a penalized regex match."""
        router = IntentRouter()
        # Inject our isolated gatekeeper into the router
        router._gatekeeper = self.gatekeeper

        query = "volume badhao"
        intent = "volume_control"
        # 1. Normal state: should route to volume_control via Tier 1 regex
        res1 = router._fast_match(query)
        self.assertIsNotNone(res1, f"Should match {intent} by default")
        self.assertEqual(res1.intent_name, intent)

        # 2. User complains / negative feedback: penalize intent for this query
        router.record_intent_feedback(query, intent, success=False, reason="User requested silence")

        # 3. Post-penalty state: Tier 1 regex must be BYPASSED!
        res2 = router._fast_match(query)
        self.assertIsNone(res2, f"Penalized intent {intent} MUST be bypassed by Tier 1 fast match")

        # 4. Clear penalty: normal routing restored
        router.clear_intent_penalty(intent)
        res3 = router._fast_match(query)
        self.assertIsNotNone(res3, "Clearing penalty must restore routing")
        self.assertEqual(res3.intent_name, intent)

    # =========================================================================
    # PART 2: GENERALIZED MULTI-TURN FOLLOW-UP RESOLUTION
    # =========================================================================

    def test_followup_detection(self):
        """Test detection of elliptical follow-up queries."""
        self.assertTrue(FollowUpContextResolver.is_followup("aur python me?"))
        self.assertTrue(FollowUpContextResolver.is_followup("and for windows?"))
        self.assertTrue(FollowUpContextResolver.is_followup("what about rust?"))
        self.assertTrue(FollowUpContextResolver.is_followup("usme error kya tha?"))
        self.assertTrue(FollowUpContextResolver.is_followup("how to fix it?"))
        self.assertTrue(FollowUpContextResolver.is_followup("docker ke andar?"))

        # Standalone queries must NOT be classified as follow-up
        self.assertFalse(FollowUpContextResolver.is_followup("what is the memory limit in Node.js?"))
        self.assertFalse(FollowUpContextResolver.is_followup("install postgresql on ubuntu"))

    def test_followup_resolution_target_swap(self):
        """Test target swap: e.g. Node.js -> Python, Golang -> Rust."""
        prior_turn = "What is the memory limit in Node.js v20?"
        current_turn = "aur python me?"

        resolved = FollowUpContextResolver.resolve(current_turn, last_user_turn=prior_turn)
        self.assertIn("memory limit", resolved.lower())
        self.assertIn("python", resolved.lower())

    def test_followup_resolution_aspect_and_constraint(self):
        """Test aspect queries (how to fix, benchmark) and environmental constraints."""
        prior = "TypeError cannot read properties of undefined in React 18"

        # Aspect: how to fix
        resolved_fix = FollowUpContextResolver.resolve("how to fix it?", last_user_turn=prior)
        self.assertIn("how to fix", resolved_fix.lower())
        self.assertIn("react 18", resolved_fix.lower())

        # Constraint: inside docker
        resolved_env = FollowUpContextResolver.resolve("docker container ke andar?", last_user_turn="how to run redis")
        self.assertIn("run redis", resolved_env.lower())
        self.assertIn("docker", resolved_env.lower())

    # =========================================================================
    # PART 3: SPECULATIVE PRE-FETCHING ENGINE
    # =========================================================================

    def test_speculative_prefetch_execution(self):
        """Test that speculative pre-fetch launches background future and speeds up ground_prompt."""
        service = get_web_intelligence()
        query = "Python 3.13 free threaded GIL removal release date"

        # 1. Speculative prefetch triggers background search
        launched_query = service.speculative_prefetch(query)
        self.assertIsNotNone(launched_query)
        self.assertEqual(launched_query.lower(), query.lower())

        # Check future exists in service
        with service._speculative_lock:
            self.assertIn(launched_query, service._speculative_futures)

        # 2. Execute ground_prompt: should grab speculative future
        grounding = service.ground_prompt(query, timeout=4.0)
        self.assertIsNotNone(grounding)
        self.assertIn(grounding.mode, (WebQueryMode.BACKGROUND_GROUNDING, WebQueryMode.DEEP_RESEARCH))
        # Verify speculative cache hit flag was set
        self.assertTrue(grounding.cache_hit)

    # =========================================================================
    # PART 4: DEVELOPER-GRADE DEEP RESEARCH AGENT (MODE C)
    # =========================================================================

    def test_deep_research_dossier_synthesis(self):
        """Test that deep_research generates multi-vector technical dossier."""
        service = get_web_intelligence()
        topic = "uvloop vs standard asyncio event loop performance"

        result = service.deep_research(topic, max_sources=3, timeout=5.0)
        self.assertIsNotNone(result)
        self.assertEqual(result.mode, WebQueryMode.DEEP_RESEARCH)
        self.assertIn("[DEEP RESEARCH DOSSIER", result.context_block)
        self.assertIn("Technical Insights", result.context_block)
        self.assertIn("Synthesis Directive", result.context_block)


if __name__ == "__main__":
    unittest.main()
