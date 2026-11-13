import unittest
import os
import sys

# Ensure import paths
sys.path.insert(0, os.path.abspath("core_ai/src"))
sys.path.insert(0, os.path.abspath("backend"))

from ai_assistant.ai.multi_step_parser import MultiStepCommandParser
from ai_assistant.ai.intent_router import IntentRouter
from ai_assistant.automation.file_automation import FileAutomation
from ai_assistant.core.chain_recovery_manager import get_chain_recovery_manager, ChainRecoveryManager
from ai_assistant.core.command_brain import get_executive_brain
from ai_assistant.integrations.orchestrator_integration import should_use_orchestrator
from ai_assistant.core.intent_executor import get_intent_executor


class TestChainHinglishAndRecovery(unittest.TestCase):

    def setUp(self):
        self.parser = MultiStepCommandParser()
        self.router = IntentRouter()
        self.file_auto = FileAutomation()
        self.recovery_mgr = get_chain_recovery_manager()
        self.recovery_mgr.clear()

    def tearDown(self):
        self.recovery_mgr.clear()

    def test_01_hinglish_conjunction_detection(self):
        """Test that Hinglish conjunctions (krke, karke, etc.) trigger orchestrator detection."""
        self.assertTrue(should_use_orchestrator("yutube music open krke behja song bjao"))
        self.assertTrue(should_use_orchestrator("open file app and locate to resume folder in disk d"))
        self.assertTrue(should_use_orchestrator("chrome open karke python search karo"))
        self.assertTrue(should_use_orchestrator("whatsapp kholo aur mom ko message bhejo"))

    def test_02_parse_yutube_music_and_play_media(self):
        """Test splitting 'yutube music open krke behja song bjao' into 2 actionable steps."""
        steps = self.parser.parse_command("yutube music open krke behja song bjao")
        self.assertEqual(len(steps), 2, f"Expected 2 steps, got: {[s.intent for s in steps]}")
        self.assertEqual(steps[0].intent, "open_app")
        self.assertIn("youtube music", steps[0].params.get("target", "").lower())
        self.assertEqual(steps[1].intent, "play_media")
        self.assertIn("behja", steps[1].params.get("query", "").lower())

    def test_03_parse_file_app_and_locate_folder(self):
        """Test splitting 'open file app and locate to resume folder in disk d'."""
        steps = self.parser.parse_command("open file app and locate to resume folder in disk d")
        self.assertEqual(len(steps), 2, f"Expected 2 steps, got: {[s.intent for s in steps]}")
        self.assertEqual(steps[0].intent, "open_app")
        self.assertEqual(steps[1].intent, "open_folder")
        self.assertIn("resume", steps[1].params.get("folder", "").lower())

    def test_04_drive_and_folder_resolution(self):
        """Test colloquial Windows drive and folder resolution."""
        # Drive resolution
        d_root = self.file_auto.resolve_folder_path("disk d")
        self.assertIsNotNone(d_root)
        self.assertTrue(d_root.upper().startswith("D:"))

        # Compound expression resolution
        resume_path = self.file_auto.resolve_folder_path("resume folder in disk d")
        self.assertIsNotNone(resume_path)
        self.assertTrue(os.path.exists(resume_path))
        self.assertIn("resume", resume_path.lower())

        # Bare folder name search
        bare_resume = self.file_auto.resolve_folder_path("resume")
        self.assertIsNotNone(bare_resume)
        self.assertTrue(os.path.exists(bare_resume))

    def test_05_real_filesystem_contents_no_hallucination(self):
        """Test that list_folder_contents returns REAL disk items without hallucination."""
        resume_path = self.file_auto.resolve_folder_path("resume folder in disk d")
        self.assertTrue(os.path.exists(resume_path))
        contents = self.file_auto.list_folder_contents(resume_path)
        
        # Real items verified on disk: AI resume, Frontend Developer, ML, Python Developer, Software eng
        self.assertIn("AI resume", contents)
        self.assertIn("ML", contents)
        self.assertIn("Python Developer", contents)
        # Verify hallucinated items are NOT present
        self.assertNotIn("Experience.docx", contents)
        self.assertNotIn("Education.pdf", contents)

    def test_06_intent_executor_open_folder_returns_real_contents(self):
        """Test IntentExecutor._open_folder returns verified path and real contents."""
        executor = get_intent_executor()
        res = executor.execute("open_folder", {"folder": "resume folder in disk d"})
        self.assertTrue(res.get("success"))
        self.assertIn("resume", str(res.get("path", "")).lower())
        self.assertTrue(isinstance(res.get("contents"), list))
        self.assertIn("AI resume", res.get("contents", []))

    def test_07_recovery_manager_affirmative_interception(self):
        """Test affirmative interception when user replies 'hn' to a failed step prompt."""
        self.recovery_mgr.record_failure(
            chain_id="chain_rec_test",
            failed_step={
                "step": 2,
                "intent": "open_folder",
                "params": {"folder": "resume folder in disk d"},
                "original_text": "locate to resume folder in disk d",
            },
            prompt_message="Step 2 (open_folder) failed: Verification failed। दूसरा तरीका आज़माऊँ?",
        )

        self.assertTrue(self.recovery_mgr.has_pending_recovery())
        self.assertTrue(self.recovery_mgr.is_affirmative("hn"))
        self.assertTrue(self.recovery_mgr.is_affirmative("haan"))
        self.assertTrue(self.recovery_mgr.is_affirmative("yes"))
        self.assertTrue(self.recovery_mgr.is_affirmative("karo"))
        self.assertTrue(self.recovery_mgr.is_affirmative("dusra tarika"))

        # Execute recovery
        rec_res = self.recovery_mgr.execute_recovery()
        self.assertTrue(rec_res.get("success"))
        self.assertTrue(rec_res.get("recovered"))
        self.assertIn("AI resume", rec_res.get("response", ""))
        self.assertFalse(self.recovery_mgr.has_pending_recovery())

    def test_08_recovery_manager_negative_rejection(self):
        """Test rejection when user replies 'nahi' or 'cancel'."""
        self.recovery_mgr.record_failure(
            chain_id="chain_rec_test2",
            failed_step={"step": 1, "intent": "open_app", "params": {"target": "unknown_app"}},
            prompt_message="Step 1 failed",
        )
        self.assertTrue(self.recovery_mgr.has_pending_recovery())
        self.assertTrue(self.recovery_mgr.is_negative("nahi"))
        self.assertTrue(self.recovery_mgr.is_negative("no"))
        self.assertTrue(self.recovery_mgr.is_negative("cancel"))
        self.assertTrue(self.recovery_mgr.is_negative("mat karo"))

    def test_09_executive_brain_intercepts_hn_without_llm_hallucination(self):
        """Test that ExecutiveBrain intercepts 'hn' and runs recovery with 0 LLM hallucination."""
        self.recovery_mgr.record_failure(
            chain_id="chain_rec_test3",
            failed_step={
                "step": 2,
                "intent": "open_folder",
                "params": {"folder": "resume folder in disk d"},
                "original_text": "locate to resume folder in disk d",
            },
            prompt_message="Step 2 failed",
        )

        brain = get_executive_brain()
        resp = brain.receive_command("hn", source="chat")
        self.assertEqual(resp.action_taken, "completed")
        self.assertTrue(resp.success)
        self.assertIn("AI resume", resp.message)
        self.assertFalse(self.recovery_mgr.has_pending_recovery())


if __name__ == "__main__":
    unittest.main()
