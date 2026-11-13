import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
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

from ai_assistant.ai.user_dna import UserDNA
from ai_assistant.ai.memory_retrieval import MemoryRetrieval, is_memory_query
from ai_assistant.core.local_command_normalizer import normalize_hinglish_devanagari
from ai_assistant.ai.intent_router import IntentRouter
from ai_assistant.core.jarvis_persona import build_persona_system_prompt
from ai_assistant.ai.llm_provider import GGUFProvider


class TestMemoryAndRoutingFixes(unittest.TestCase):
    def setUp(self):
        self.router = IntentRouter()

    def tearDown(self):
        import sqlite3
        try:
            dna = UserDNA()
            with sqlite3.connect(dna.db_path) as conn:
                conn.execute("DELETE FROM user_dna WHERE key IN ('user_name', 'upcoming_exam', 'upcoming_interview', 'friend_name', 'user_location')")
                conn.commit()
        except Exception:
            pass

    def test_dna_fact_extraction(self):
        dna = UserDNA()
        test_cases = [
            ("mera exam Friday ko hai", "upcoming_exam", "Friday"),
            ("mera paper Monday ko hai", "upcoming_exam", "Monday"),
            ("mere dost ka naam Rohan hai", "friend_name", "Rohan"),
            ("mai Bhopal me rehta hu", "user_location", "Bhopal"),
            ("mera naam Amit hai", "user_name", "Amit"),
        ]
        for text, key, expected_val in test_cases:
            updated = dna.extract_facts_from_text(text)
            self.assertTrue(updated, f"Failed to extract from: {text}")
            trait_val = dna.get_trait(key)
            self.assertIn(expected_val.lower(), str(trait_val or "").lower())

    def test_memory_query_detection_and_retrieval(self):
        dna = UserDNA()
        dna.update_trait("friend_name", "Anshuman", confidence=0.95)
        dna.update_trait("upcoming_exam", "Exam (Monday)", confidence=0.95)

        queries = [
            "mera paper kb hai?",
            "check in old conversation , when is my exam?",
            "konsa paper tha?",
            "mere dost ka naam kya hai ?",
            "tmhe kl batya tha maine , chat history me dekho naam aaur mujhe btao",
        ]
        for q in queries:
            self.assertTrue(is_memory_query(q), f"Failed memory query trigger: {q}")

        retriever = MemoryRetrieval()
        friend_res = retriever.retrieve_unified_context("mere dost ka naam kya hai")
        self.assertIn("Anshuman", str(friend_res))

        exam_res = retriever.retrieve_unified_context("mera paper kb hai")
        self.assertIn("Monday", str(exam_res))

    def test_typo_normalization(self):
        cases = [
            ("msh hi to mom on whtsap", "msg hi to mom on whatsapp"),
            ("mom ko hi likh kr bhejo whtsp pr", "mom ko hi likh kr bhejo whatsapp par"),
            ("screnshot lo", "screenshot lo"),
        ]
        for inp, expected in cases:
            norm = normalize_hinglish_devanagari(inp)
            self.assertEqual(norm, expected)

    def test_intent_routing_with_typos_and_queries(self):
        r1 = self.router.route("msh hi to mom on whtsap")
        self.assertEqual(r1.intent_name, "send_message")
        self.assertEqual(r1.parameters.get("contact"), "mom")
        self.assertEqual(r1.parameters.get("message"), "hi")

        r2 = self.router.route("mom ko hi likh kr bhejo whtsp pr")
        self.assertEqual(r2.intent_name, "send_message")
        self.assertEqual(r2.parameters.get("contact"), "mom")
        self.assertEqual(r2.parameters.get("message"), "hi")

        r3 = self.router.route("screnshot lo")
        self.assertEqual(r3.intent_name, "analyze_screen")

        r4 = self.router.route("gold price kitna hai abhi aaj ka")
        self.assertEqual(r4.intent_name, "search_web")

        r5 = self.router.route("web pr check kro , ye tmne galat btaya hai")
        self.assertEqual(r5.intent_name, "search_web")

    def test_prompt_memory_preservation(self):
        retrieved_memory = "[VERIFIED FACT: User's friend is Anshuman. Upcoming exam is Monday.]"
        dna = UserDNA()
        dna.update_trait("friend_name", "Anshuman", confidence=0.95)

        prompt = build_persona_system_prompt(
            extra_context=retrieved_memory,
        )
        # Check memory fact is placed at the top of the prompt
        self.assertIn("Anshuman", prompt)
        anshuman_pos = prompt.find("Anshuman")
        self.assertLess(anshuman_pos, 800, "Memory must be near top of prompt to prevent token clamping truncation")

        # Simulate GGUF limit calculation without loading 4GB weights
        from unittest.mock import MagicMock
        fake_llm = MagicMock()
        fake_llm.n_ctx.return_value = 2048
        fake_llm.tokenize.side_effect = lambda b, **kwargs: [1] * (len(b) // 3 + 2)

        gguf = GGUFProvider.__new__(GGUFProvider)
        prepared_msgs, safe_max = gguf._prepare_messages_and_limits(
            fake_llm,
            [{"role": "system", "content": prompt}, {"role": "user", "content": "mere dost ka naam kya hai?"}],
            256
        )
        sys_content = prepared_msgs[0]["content"]
        self.assertIn("Anshuman", sys_content, "Memory must survive GGUF prompt clamping")


if __name__ == "__main__":
    unittest.main()
