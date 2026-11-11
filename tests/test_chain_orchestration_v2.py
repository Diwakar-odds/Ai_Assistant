"""
Comprehensive verification test suite for Chain Orchestration V2,
Multi-Step Command Parsing, Parameter Interpolation, Pause/Resume/Cancel,
and ExecutiveBrain routing.
"""

import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = REPO_ROOT / "core_ai" / "src"
BACKEND_DIR = REPO_ROOT / "backend"
for p in (str(REPO_ROOT), str(CORE_SRC), str(BACKEND_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from ai_assistant.ai.multi_step_parser import MultiStepCommandParser, TaskStep
from ai_assistant.core.action_chain_models import ActionChain, Action, ActionType, ChainStatus
from ai_assistant.core.chain_of_actions_manager import ChainOfActionsManager, get_chain_manager
from ai_assistant.core.task_chain_orchestrator import (
    ChainExecutionContext,
    TaskChainOrchestrator,
    get_orchestrator,
)
from ai_assistant.core.command_brain import (
    ExecutiveBrain,
    get_executive_brain,
    EXECUTIVE_STOP_KEYWORDS,
    EXECUTIVE_PAUSE_KEYWORDS,
    EXECUTIVE_RESUME_KEYWORDS,
)


class TestMultiStepParserV2(unittest.TestCase):
    def setUp(self):
        self.parser = MultiStepCommandParser()

    def test_01_quote_and_url_preservation(self):
        cmd = 'type "hello, and welcome; to our world" and open https://example.com/search?q=a&&b'
        segments = self.parser.split_with_relations(cmd)
        self.assertEqual(len(segments), 2)
        self.assertIn('"hello, and welcome; to our world"', segments[0]["text"])
        self.assertIn("https://example.com/search?q=a&&b", segments[1]["text"])

    def test_02_symbolic_delimiters(self):
        cmd1 = "open chrome && search python && wait 2 seconds"
        steps1 = self.parser.parse_command(cmd1)
        self.assertEqual(len(steps1), 3)

        cmd2 = "open spotify; play music; set volume to 50"
        steps2 = self.parser.parse_command(cmd2)
        self.assertEqual(len(steps2), 3)

        cmd3 = "open notepad -> type hello -> save file"
        steps3 = self.parser.parse_command(cmd3)
        self.assertEqual(len(steps3), 3)

    def test_03_hindi_and_hinglish_chain(self):
        cmd = "chrome kholo aur phir python search karo uske baad 2 second ruko"
        steps = self.parser.parse_command(cmd)
        self.assertEqual(len(steps), 3)
        self.assertEqual(steps[0].step, 1)
        self.assertEqual(steps[1].step, 2)
        self.assertEqual(steps[2].step, 3)

    def test_04_numbered_lists(self):
        cmd = "1. open chrome\n2. search machine learning\n3. wait 3 seconds"
        steps = self.parser.parse_command(cmd)
        self.assertEqual(len(steps), 3)

    def test_05_parallel_connectors(self):
        cmd = "play music in parallel search wikipedia for quantum physics"
        segments = self.parser.split_with_relations(cmd)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[1]["relation"], "parallel")

    def test_06_conversational_and_noun_protection(self):
        # Noun conjunction should NOT split
        self.assertFalse(self.parser.is_multi_step("I like fish and chips"))
        self.assertFalse(self.parser.is_multi_step("Buy apples, oranges and bananas"))
        self.assertFalse(self.parser.is_multi_step("Hello Pulsar, how are you today?"))


class TestVariableInterpolation(unittest.TestCase):
    def test_01_placeholder_resolution(self):
        ctx = ChainExecutionContext(None, chain_id="test_chain")
        step1 = TaskStep(step=1, intent="search", params={}, step_id="step_1")
        ctx.record_step_output(step1, {"output": "quantum computing breakthroughs", "output_path": "C:\\out.txt"})

        resolved = ctx.resolve_placeholders("Summarize {prev.output} from {step_1.output_path}")
        self.assertEqual(resolved, "Summarize quantum computing breakthroughs from C:\\out.txt")

        # Nested dict resolution
        payload = {
            "query": "{prev.output}",
            "nested": ["File at {step_1.path}", 42],
        }
        res_dict = ctx.resolve_placeholders(payload)
        self.assertEqual(res_dict["query"], "quantum computing breakthroughs")
        self.assertEqual(res_dict["nested"][0], "File at C:\\out.txt")


class TestChainOfActionsManagerLifecycle(unittest.TestCase):
    def test_01_create_chain_and_dto(self):
        mgr = ChainOfActionsManager()
        chain = asyncio.run(mgr.create_chain("open notepad && type test message", source="unit_test"))
        self.assertTrue(chain.chain_id.startswith("chain_"))
        self.assertEqual(chain.status, ChainStatus.PENDING)
        self.assertEqual(len(chain.actions), 2)

        dto = chain.to_dict()
        self.assertEqual(dto["chain_id"], chain.chain_id)
        self.assertEqual(dto["status"], "pending")
        self.assertEqual(dto["total_actions"], 2)
        self.assertEqual(dto["actions_completed"], 0)
        self.assertEqual(len(dto["actions"]), 2)

    def test_02_pause_resume_cancel(self):
        mgr = ChainOfActionsManager()
        chain = asyncio.run(mgr.create_chain("wait 5 seconds && wait 5 seconds"))
        cid = chain.chain_id

        # Pause
        ok_pause = mgr.pause_chain(cid)
        self.assertTrue(ok_pause)
        self.assertEqual(chain.status, ChainStatus.PAUSED)

        # Resume
        ok_resume = mgr.resume_chain(cid)
        self.assertTrue(ok_resume)
        self.assertIn(chain.status, (ChainStatus.EXECUTING, ChainStatus.PENDING))

        # Cancel
        ok_cancel = mgr.cancel_chain(cid, reason="Test cancellation")
        self.assertTrue(ok_cancel)
        self.assertEqual(chain.status, ChainStatus.CANCELLED)
        dto = chain.to_dict()
        self.assertEqual(dto["status"], "cancelled")


class TestExecutiveBrainRouting(unittest.TestCase):
    def test_01_executive_stop_keywords(self):
        brain = get_executive_brain()
        # Verify classification for stop phrases
        for phrase in ("stop", "emergency stop", "halt all actions", "cancel chain"):
            resp = brain.receive_command(phrase, source="unit_test")
            self.assertTrue(resp.success)
            self.assertEqual(resp.action_taken, "stop")

    def test_02_executive_pause_and_resume_keywords(self):
        brain = get_executive_brain()
        resp_pause = brain.receive_command("pause chain", source="unit_test")
        self.assertTrue(resp_pause.success)
        self.assertEqual(resp_pause.action_taken, "pause")

        resp_resume = brain.receive_command("resume chain", source="unit_test")
        self.assertTrue(resp_resume.success)
        self.assertEqual(resp_resume.action_taken, "resume")


if __name__ == "__main__":
    unittest.main()
