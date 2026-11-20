import os
import sys
import unittest

# Ensure project root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestClosedLoopLearning(unittest.TestCase):
    def test_learning_router_initialization_and_routing(self):
        from core_ai.ai.auto_learning_router import LearningDataRouter
        router = LearningDataRouter()
        self.assertIsNotNone(router)

        # Test user turn routing
        test_user_msg = "test command open notepad"
        router.route_conversation(speaker='user', content=test_user_msg, category='command', input_mode='test')

        # Test assistant turn routing
        test_ai_msg = "Opening Notepad for you."
        router.route_conversation(speaker='assistant', content=test_ai_msg, category='command', input_mode='test')

        # Check conversation history tracking
        self.assertGreaterEqual(len(router.conversation_history), 2)
        self.assertEqual(router.conversation_history[-2]['speaker'], 'user')
        self.assertEqual(router.conversation_history[-1]['speaker'], 'assistant')

    def test_knowledge_graph_stats(self):
        from core_ai.ai.enhanced_learning import PersonalKnowledgeGraph
        from core_ai.core.database_config import get_db_path_str
        pkg = PersonalKnowledgeGraph(db_path=get_db_path_str("personal_knowledge"))
        stats = pkg.get_stats()
        self.assertIn('total_nodes', stats)
        self.assertIn('total_edges', stats)
        self.assertEqual(stats['status'], 'active')

    def test_voice_service_grounding_injection(self):
        # Verify that voice_service imports and runs cleanly
        from backend.services.voice_service import _get_chat_store
        store = _get_chat_store()
        self.assertIsNotNone(store)

    def test_intent_router_media_disambiguation(self):
        from core_ai.ai.intent_router import IntentRouter
        router = IntentRouter()

        # Song query should route to play_media
        res_song = router.route("kesariya gaana chalao")
        self.assertEqual(res_song.intent_name, "play_media")

        # Joke query should NOT route to play_media
        res_joke = router.route("bhai ek mast chutkula sunao")
        self.assertNotEqual(res_joke.intent_name if res_joke else None, "play_media")

        # App close should NOT route to play_media
        res_close = router.route("chrome band kar do")
        self.assertNotEqual(res_close.intent_name if res_close else None, "play_media")

if __name__ == '__main__':
    unittest.main()
