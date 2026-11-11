#!/usr/bin/env python3
"""
Comprehensive automated unit and regression test suite for Section B fixes:
1. ContextManager / TaskChainOrchestrator / CommandBrain state leak & false override guard
2. ChatSessionStore session isolation & stale-write suppression
3. Barge-in stop expansion (Hinglish/Hindi/English profanity & stop heads)
4. Jarvis feminine Hinglish persona & multiline report formatting
5. Bare media controls + Win32 VK media keys + IntentRouter media_control
6. Chrome profile semantic resolution ("college" -> Profile 5) & filler extraction
7. Multi-step conversational preamble filtering & duplicate step collapse
8. Taskbar open GUI windows filtering & newline formatting
9. Memory database bugfixes & unified cross-session historical RAG
"""

import json
import os
import sqlite3
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

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

# Core imports
from ai_assistant.ai.intent_router import IntentRouter
from ai_assistant.ai.memory import search_memory, get_conversation_summary
from ai_assistant.ai.memory_retrieval import (
    MemoryRetrieval,
    retrieve_unified_historical_context,
    persist_turn_to_conversation_ai,
)
from ai_assistant.ai.multi_step_parser import MultiStepCommandParser
from ai_assistant.automation.browser_profiles import (
    extract_profile_from_text,
    resolve_chrome_profile,
)
from ai_assistant.automation.taskbar_detection import TaskbarDetector
from ai_assistant.core.command_brain import CommandBrain, CommandClassification
from ai_assistant.core.conversation_context import (
    ContextManager,
    ExecutionState,
)
from ai_assistant.core.jarvis_persona import (
    build_persona_system_prompt,
    format_post_task_report,
)
from ai_assistant.core.local_command_normalizer import (
    is_barge_in_stop_command,
    parse_voice_control_command,
    execute_voice_control_command,
)
from ai_assistant.core.task_chain_orchestrator import TaskChainOrchestrator
from ai_assistant.integrations.music import control_media_player
from backend.utils.chat_session_store import ChatSessionStore


class TestFix1ContextAndOrchestrator(unittest.TestCase):
    """Fix 1: ContextManager normalization, override detection, and orchestrator state cleanup."""

    def test_transient_executing_state_normalized_to_idle(self):
        import tempfile
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tf:
            tf.write(json.dumps({
                "context_vars": {},
                "execution_state": "executing",
                "current_task_chain": [{"step": 1, "intent": "test"}],
                "current_step": 1,
                "command_history": [],
            }))
            tf_path = Path(tf.name)

        try:
            cm = ContextManager(storage_path=str(tf_path))
            self.assertEqual(cm.get_state(), ExecutionState.IDLE)
            self.assertEqual(cm.get_task_chain(), [])
        finally:
            if tf_path.exists():
                tf_path.unlink()

    def test_is_override_strict_boundary_and_state(self):
        cm = ContextManager()
        # Idle state should NOT trigger override on plain commands
        cm.set_state(ExecutionState.IDLE)
        self.assertFalse(cm.is_override("Stop spotify"))
        self.assertFalse(cm.is_override("open notepad"))
        self.assertFalse(cm.is_override("no problem"))
        self.assertFalse(cm.is_override("stop"))
        self.assertFalse(cm.is_override("cancel"))

        # Executing state triggers override on explicit cancel/stop
        cm.set_state(ExecutionState.EXECUTING)
        self.assertTrue(cm.is_override("stop"))
        self.assertTrue(cm.is_override("cancel"))
        self.assertTrue(cm.is_override("ruko"))
        self.assertTrue(cm.is_override("abort"))
        # But not commands containing substrings like 'stopwatch'
        self.assertFalse(cm.is_override("open stopwatch"))

    def test_command_brain_pause_resume_classification(self):
        brain = CommandBrain()
        # When no active brain chains exist:
        # Bare "pause" / "resume" must NOT hijack executive pause
        c_pause_song = brain._classify_command("pause song")
        self.assertEqual(c_pause_song, CommandClassification.TASK_NEW)
        c_resume_song = brain._classify_command("resume song")
        self.assertEqual(c_resume_song, CommandClassification.TASK_NEW)
        c_bare_pause = brain._classify_command("pause")
        self.assertEqual(c_bare_pause, CommandClassification.TASK_NEW)

        # When active chains exist, bare "pause" can trigger executive pause
        brain._active_chains["test_chain"] = MagicMock()
        try:
            c_active_pause = brain._classify_command("pause")
            self.assertEqual(c_active_pause, CommandClassification.EXECUTIVE_PAUSE)
            c_active_resume = brain._classify_command("resume")
            self.assertEqual(c_active_resume, CommandClassification.EXECUTIVE_RESUME)
            # But targeted commands still stay TASK_NEW
            c_active_pause_song = brain._classify_command("pause song")
            self.assertEqual(c_active_pause_song, CommandClassification.TASK_NEW)
        finally:
            brain._active_chains.clear()


class TestFix2ChatSessionStoreIsolation(unittest.TestCase):
    """Fix 2: ChatSessionStore session isolation & stale write guard."""

    def test_stale_session_write_is_suppressed(self):
        import tempfile
        import shutil
        tmp_dir = Path(tempfile.mkdtemp(prefix="pulsar_store_test_"))
        try:
            store = ChatSessionStore(storage_dir=tmp_dir)
            s1 = store.get_current_session()
            s1_id = s1["id"]

            store.record_message("user", "Message 1 in S1", expected_session_id=s1_id)
            self.assertEqual(len(store.get_current_session()["messages"]), 1)

            # Start a brand new session
            s2 = store.start_new_session()
            s2_id = s2["id"]
            self.assertNotEqual(s1_id, s2_id)
            self.assertEqual(len(s2["messages"]), 0)

            # Now an asynchronous lingering task attempts to write to s1
            stale_written = store.record_message("ai", "Late AI reply for S1", expected_session_id=s1_id)
            self.assertIsNone(stale_written)
            self.assertEqual(len(store.get_current_session()["messages"]), 0, "Stale message should NOT appear in S2")

            # Activity record for stale session should also be suppressed (only the 1 initial startup activity remains)
            stale_act = store.record_activity("response", "Late act", expected_session_id=s1_id)
            self.assertIsNone(stale_act)
            self.assertEqual(len(store.get_current_session()["activities"]), 1, "Stale activity must not be appended to S2")

            # Valid activity for s2 should succeed
            valid_act = store.record_activity("response", "Valid act in S2", expected_session_id=s2_id)
            self.assertIsNotNone(valid_act)
            self.assertEqual(len(store.get_current_session()["activities"]), 2)

            # Legitimate write for s2 should succeed
            valid_written = store.record_message("user", "Message 1 in S2", expected_session_id=s2_id)
            self.assertIsNotNone(valid_written)
            self.assertEqual(len(store.get_current_session()["messages"]), 1)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


class TestFix3BargeInStopExpansion(unittest.TestCase):
    """Fix 3: Barge-in stop expansion and voice control command execution."""

    def test_barge_in_profanity_and_phrases(self):
        stop_phrases = [
            "chup madarchod",
            "chup ho ja saale",
            "shut up idiot",
            "Hey Pulsar chup",
            "बोलना बंद करो",
            "chup kar",
            "bas karo",
            "shhh",
            "shut up please",
            "stop talking",
            "shaant ho ja",
            "ruk ja",
        ]
        for phrase in stop_phrases:
            with self.subTest(phrase=phrase):
                self.assertTrue(is_barge_in_stop_command(phrase), f"Expected '{phrase}' to be detected as stop")

    def test_non_barge_in_commands_preserved(self):
        normal_commands = [
            "stop spotify",
            "open chrome",
            "play arijit singh",
            "stop the timer",
            "stop song",
            "pause video",
            "cancel meeting",
            "what is the time",
        ]
        for cmd in normal_commands:
            with self.subTest(cmd=cmd):
                self.assertFalse(is_barge_in_stop_command(cmd), f"Expected '{cmd}' NOT to be detected as stop")

    def test_parse_and_execute_voice_control_command(self):
        parsed = parse_voice_control_command("chup ho ja")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.get("action"), "stop_speaking")

        # Execute voice control command without raising
        result = execute_voice_control_command(parsed)
        self.assertIsInstance(result, dict)
        self.assertTrue(result.get("success"))


class TestFix4JarvisPersonaAndFormatting(unittest.TestCase):
    """Fix 4: Jarvis feminine Hinglish persona guidance and multiline formatting."""

    def test_persona_system_prompt_contains_feminine_guidance(self):
        prompt = build_persona_system_prompt()
        self.assertIn("PERSONA GENDER", prompt)
        self.assertIn("kar rahi hoon", prompt)
        self.assertIn("bata rahi hoon", prompt)

    def test_multiline_post_task_formatting(self):
        output = "1. Chrome (active)\n2. VS Code\n3. Spotify"
        formatted = format_post_task_report("check taskbar", output, success=True, intent="list_running_apps")
        self.assertIn("1. Chrome (active)\n2. VS Code\n3. Spotify", formatted)
        # Verify no weird trailing period after newline
        self.assertNotIn("\n.", formatted)


class TestFix5MediaControlAndWin32Keys(unittest.TestCase):
    """Fix 5: Bare media controls + IntentRouter + Win32 keys."""

    def setUp(self):
        self.router = IntentRouter()

    def test_media_control_intent_routing(self):
        cases = [
            ("next song", "next"),
            ("previous song", "previous"),
            ("pause song", "pause"),
            ("resume music", "resume"),
        ]
        for text, expected_action in cases:
            with self.subTest(text=text):
                res = self.router.route(text)
                self.assertEqual(res.intent_name, "media_control")
                self.assertEqual(res.parameters.get("action"), expected_action)

        # Mute is a volume_control intent
        res_mute = self.router.route("mute")
        self.assertEqual(res_mute.intent_name, "volume_control")
        self.assertEqual(res_mute.parameters.get("action"), "mute")

    @patch("ctypes.windll.user32.keybd_event")
    def test_control_media_player_win32_vk(self, mock_keybd):
        for act in ("next", "previous", "pause", "resume", "play_pause", "mute"):
            res = control_media_player(act)
            self.assertIsInstance(res, str)
            self.assertNotIn("❌", res)
        self.assertTrue(mock_keybd.called)


class TestFix6BrowserProfilesResolution(unittest.TestCase):
    """Fix 6: Chrome profile semantic resolution and filler stripping."""

    def test_college_profile_resolution(self):
        resolved = resolve_chrome_profile("mere college ki chrome profile kholo")
        self.assertEqual(resolved, "Profile 5")

    def test_extract_profile_from_text(self):
        profile, action = extract_profile_from_text("Open Rancho profile")
        self.assertEqual(profile.lower(), "rancho")

        profile2, _ = extract_profile_from_text("mere college ki chrome profile kholo")
        self.assertEqual(profile2.lower(), "college")


class TestFix7MultiStepPreambleFiltering(unittest.TestCase):
    """Fix 7: Multi-step parser preamble removal and step collapsing."""

    def setUp(self):
        self.parser = MultiStepCommandParser()

    def test_preamble_removal_with_comma(self):
        cmd = "i want to research on smtg , open rancho chrome profile"
        steps = self.parser.parse_command(cmd)
        self.assertGreater(len(steps), 0)
        # First step should NOT be an unknown dummy step
        self.assertEqual(steps[0].intent, "open_app")
        self.assertIn("rancho", str(steps[0].params.get("profile", "")).lower())

    def test_collapse_duplicate_taskbar_queries(self):
        cmd = "check taskbar and tell me which apps are currently open"
        steps = self.parser.parse_command(cmd)
        # Should collapse to 1 step instead of 2 identical list_running_apps
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].intent, "list_running_apps")


class TestFix8TaskbarDetection(unittest.TestCase):
    """Fix 8: Taskbar open GUI windows vs kernel process dump."""

    def test_taskbar_formatting_filters_invalid_windows(self):
        detector = TaskbarDetector()
        mock_windows = [
            {"title": "Google Chrome", "process_name": "chrome.exe", "class_name": "Chrome_WidgetWin_1", "position": {"width": 1200, "height": 800}, "pid": 100},
            {"title": "Visual Studio Code", "process_name": "Code.exe", "class_name": "Chrome_WidgetWin_1", "position": {"width": 1400, "height": 900}, "pid": 101},
            {"title": "Program Manager", "process_name": "explorer.exe", "class_name": "Progman", "position": {"width": 1920, "height": 1080}, "pid": 102},  # Helper
            {"title": "Default IME", "process_name": "csrss.exe", "class_name": "IME", "position": {"width": 0, "height": 0}, "pid": 103},         # Helper
            {"title": "", "process_name": "helper.exe", "class_name": "Helper", "position": {"width": 50, "height": 50}, "pid": 104},                     # Empty
            {"title": "Hidden 0x0 Helper", "process_name": "notepad.exe", "class_name": "Notepad", "position": {"width": 0, "height": 0}, "pid": 105},   # 0x0
        ]
        with patch.object(detector, "_get_window_information", return_value=mock_windows):
            formatted = detector.format_taskbar_open_apps()
            apps_info = detector.get_taskbar_open_apps()

        app_names = [a["app"].lower() for a in apps_info["apps"]]
        self.assertIn("google chrome", app_names)
        self.assertIn("vs code", app_names)
        self.assertNotIn("program manager", app_names)
        self.assertNotIn("default ime", app_names)

        self.assertIn("Google Chrome", formatted)
        self.assertIn("VS Code", formatted)
        self.assertNotIn("Program Manager", formatted)
        self.assertNotIn("Default IME", formatted)
        # Verify lines use real newlines
        lines = formatted.strip().split("\n")
        self.assertGreaterEqual(len(lines), 2)

    def test_system_py_has_no_double_escaped_newlines(self):
        system_file = PROJECT_ROOT / "core_ai" / "src" / "ai_assistant" / "core" / "system.py"
        content = system_file.read_text(encoding="utf-8")
        # Ensure there are no literal double-escaped '\\n' sequences inside string literals
        self.assertNotIn('\\\\n', content)


class TestFix9MemoryAndUnifiedRAG(unittest.TestCase):
    """Fix 9: Memory database queries, enc: filtering, and unified historical RAG."""

    def test_memory_db_path_and_enc_filtering(self):
        import tempfile
        import shutil
        tmp_dir = Path(tempfile.mkdtemp(prefix="pulsar_rag_test_"))
        try:
            core_dir = tmp_dir / "core"
            core_dir.mkdir(parents=True, exist_ok=True)
            db_path = core_dir / "conversation_ai.db"

            # Persist turns using the official thread-safe helper
            ok1 = persist_turn_to_conversation_ai(
                "who is abhishek?",
                "Abhishek is a software engineer and good friend.",
                session_id="s_old",
                db_path=str(db_path),
            )
            self.assertTrue(ok1)

            ok2 = persist_turn_to_conversation_ai(
                "kl mera science exam hai",
                "Noted! Science exam ki taiyari shuru karte hain.",
                session_id="s_old",
                db_path=str(db_path),
            )
            self.assertTrue(ok2)

            # Initialize MemoryRetrieval on this test DB and isolated data_dir
            retriever = MemoryRetrieval(db_path=str(db_path), data_dir=tmp_dir)

            # Query who is abhishek
            res = retriever.search_memory("who is abhishek", limit=3)
            self.assertGreater(len(res), 0)
            flattened = retriever._flatten_messages(res[0].get("messages", []))
            self.assertIn("Abhishek", flattened)

            # Persist another turn and verify immediate searchability
            persist_turn_to_conversation_ai(
                "where do I live?",
                "You live in Bhopal.",
                session_id="s_new",
                db_path=str(db_path),
            )
            res2 = retriever.search_memory("Bhopal", limit=3)
            self.assertGreater(len(res2), 0)
            self.assertIn("Bhopal", retriever._flatten_messages(res2[0].get("messages", [])))

            # Unified context retrieval
            unified = retriever.retrieve_unified_context("who is abhishek?", max_chars=1000, current_session_id="s_curr")
            self.assertIn("Abhishek", unified)

            # Module-level wrapper
            mod_unified = retrieve_unified_historical_context("who is abhishek?", db_path=str(db_path), max_chars=1000)
            self.assertIn("Abhishek", mod_unified)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_broad_multimonth_date_filter(self):
        mr = MemoryRetrieval()
        df = mr._extract_date_filter("what did we talk about in the past 4 or 5 months?")
        self.assertIsNotNone(df)
        self.assertTrue(df.get("broad", False))
        # Should be a date roughly 120-160 days in the past
        past_date = datetime.strptime(df["start"], "%Y-%m-%d")
        diff = (datetime.now() - past_date).days
        self.assertGreaterEqual(diff, 110)
        self.assertLessEqual(diff, 170)


if __name__ == "__main__":
    unittest.main()
