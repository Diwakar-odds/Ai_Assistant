"""
Integration Tests for System Orchestration, Global Emergency Stop, and Compound Chains
"""

import sys
import unittest
from pathlib import Path

# Setup paths
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / 'backend'))
sys.path.insert(0, str(repo_root / 'core_ai' / 'src'))

from ai_assistant.core.command_brain import CommandBrain, get_executive_brain, CommandClassification, BrainState
from ai_assistant.core.task_chain_orchestrator import TaskChainOrchestrator, get_orchestrator, ExecutionResult
from ai_assistant.core.conversation_context import get_context_manager, ExecutionState
from ai_assistant.ai.multi_step_parser import MultiStepCommandParser, TaskStep
from ai_assistant.core.emergency_stop import trigger_emergency_stop, is_emergency_stop_listener_active


class TestSystemOrchestrationAndEmergencyStop(unittest.TestCase):

    def setUp(self):
        self.brain = get_executive_brain()
        self.orchestrator = get_orchestrator()
        self.ctx = get_context_manager()
        self.parser = MultiStepCommandParser()

    def test_01_global_emergency_stop_via_command_brain(self):
        """Test CommandBrain.handle_executive(CommandClassification.EXECUTIVE_STOP)"""
        # Trigger stop directly through CommandBrain class interface
        response = CommandBrain.handle_executive(CommandClassification.EXECUTIVE_STOP, "Unit Test Emergency Stop")
        
        self.assertEqual(response.action_taken, 'cancelled')
        self.assertEqual(self.brain.state, BrainState.IDLE)
        self.assertTrue(self.orchestrator.is_stopped())
        self.assertEqual(self.ctx.get_state(), ExecutionState.IDLE)

    def test_02_task_chain_orchestrator_halts_on_emergency_stop(self):
        """Test that TaskChainOrchestrator halts its loop when emergency stop is signaled"""
        # Trigger emergency stop
        self.orchestrator.emergency_stop("Direct test stop")
        self.assertTrue(self.orchestrator.is_stopped())
        
        # Now attempting to execute steps should be halted immediately
        steps = [
            TaskStep(step=1, intent='open_app', params={'app_name': 'notepad'}),
            TaskStep(step=2, intent='type_text', params={'text': 'hello'}, dependencies=[1])
        ]
        res = self.orchestrator.execute_chain(steps)
        self.assertFalse(res.success)
        self.assertIn("Emergency stop", res.message)

    def test_03_compound_chain_parsing_rancho_youtube(self):
        """Verify compound command: 'Open Rancho profile and search YouTube for Coke Studio'"""
        cmd = "Open Rancho profile and search YouTube for Coke Studio"
        steps = self.parser.parse_command(cmd)
        
        self.assertEqual(len(steps), 2)
        
        # Step 1: open_app with target Rancho
        step1 = steps[0]
        self.assertEqual(step1.step, 1)
        self.assertEqual(step1.intent, 'open_app')
        self.assertIn(step1.params.get('target').lower(), ['rancho', 'rancho profile'])
        self.assertEqual(step1.params.get('profile'), 'rancho')
        self.assertEqual(step1.dependencies, [])
        
        # Step 2: youtube_search with query Coke Studio and inherited profile
        step2 = steps[1]
        self.assertEqual(step2.step, 2)
        self.assertIn(step2.intent, ['youtube_search', 'search_web'])
        self.assertEqual(step2.params.get('query').lower(), 'coke studio')
        self.assertEqual(step2.params.get('profile'), 'rancho')
        self.assertEqual(step2.dependencies, [1])

    def test_04_context_profile_inheritance(self):
        """Verify that Step 2 inherits Rancho profile from context established by Step 1"""
        self.ctx.set_var('current_app', 'chrome')
        self.ctx.set_var('current_browser_profile', 'Profile 9')
        
        params = {'query': 'coke studio'}
        inferred = self.ctx.infer_missing_params('youtube_search', params)
        self.assertEqual(inferred.get('profile'), 'Profile 9')
        self.assertEqual(inferred.get('query'), 'coke studio')

    def test_05_programmatic_trigger_emergency_stop(self):
        """Verify trigger_emergency_stop helper executes cleanly"""
        res = trigger_emergency_stop("Testing trigger helper")
        self.assertEqual(res['status'], 'stopped')
        self.assertTrue(self.orchestrator.is_stopped())


if __name__ == '__main__':
    unittest.main()
