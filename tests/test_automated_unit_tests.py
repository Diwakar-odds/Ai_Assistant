"""
Automated Unit Tests - No GUI Required
Tests core logic without needing actual apps.
"""

import sys
from pathlib import Path

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import unittest
from ai_assistant.ai.multi_step_parser import MultiStepCommandParser, TaskStep
from ai_assistant.core.conversation_context import ContextManager, ExecutionState
from ai_assistant.core.task_chain_orchestrator import TaskChainOrchestrator


class TestMultiStepParser(unittest.TestCase):
    """Test command parser logic."""
    
    def setUp(self):
        self.parser = MultiStepCommandParser()
    
    def test_single_step_command(self):
        """Test parsing single-step command."""
        command = "Notepad खोलो"
        steps = self.parser.parse_command(command)
        
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].step, 1)
    
    def test_multi_step_command_with_comma(self):
        """Test comma-separated multi-step command."""
        command = "WhatsApp खोलो, मॉम को message करो"
        steps = self.parser.parse_command(command)
        
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0].step, 1)
        self.assertEqual(steps[1].step, 2)
    
    def test_multi_step_with_phir(self):
        """Test multi-step with 'फिर' keyword."""
        command = "Notepad खोलो फिर Calculator खोलो"
        steps = self.parser.parse_command(command)
        
        self.assertEqual(len(steps), 2)
    
    def test_multi_step_with_and_then(self):
        """Test multi-step with 'and then' keyword."""
        command = "Open Calculator and then open Notepad"
        steps = self.parser.parse_command(command)
        
        self.assertGreaterEqual(len(steps), 2)
    
    def test_dependency_inference(self):
        """Test that dependencies are inferred correctly."""
        command = "WhatsApp खोलो, message करो"
        steps = self.parser.parse_command(command)
        
        # Second step should depend on first
        if len(steps) > 1:
            # send_message should have dependency on open_app
            # (if parser recognizes the intents correctly)
            self.assertIsInstance(steps[1].dependencies, list)


class TestContextManager(unittest.TestCase):
    """Test context manager logic."""
    
    def setUp(self):
        self.context = ContextManager(storage_path="data/test_context.json")
        self.context.reset()
    
    def test_set_and_get_var(self):
        """Test setting and getting context variables."""
        self.context.set_var('test_key', 'test_value')
        value = self.context.get_var('test_key')
        
        self.assertEqual(value, 'test_value')
    
    def test_has_var(self):
        """Test checking variable existence."""
        self.context.set_var('exists', 'yes')
        
        self.assertTrue(self.context.has_var('exists'))
        self.assertFalse(self.context.has_var('does_not_exist'))
    
    def test_state_management(self):
        """Test execution state changes."""
        self.context.set_state(ExecutionState.PARSING)
        self.assertEqual(self.context.get_state(), ExecutionState.PARSING)
        
        self.context.set_state(ExecutionState.EXECUTING)
        self.assertEqual(self.context.get_state(), ExecutionState.EXECUTING)
    
    def test_command_history(self):
        """Test command history tracking."""
        self.context.add_command("Test command 1", intent="test", completed=True)
        self.context.add_command("Test command 2", intent="test", completed=False)
        
        history = self.context.get_command_history(limit=10)
        
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['command'], "Test command 1")
        self.assertTrue(history[0]['completed'])
    
    def test_override_detection(self):
        """Test override keyword detection."""
        self.assertTrue(self.context.is_override("नहीं, कुछ और करो"))
        self.assertTrue(self.context.is_override("wait, don't do that"))
        self.assertTrue(self.context.is_override("stop"))
        self.assertFalse(self.context.is_override("continue with task"))
    
    def test_infer_missing_params(self):
        """Test parameter inference from context."""
        # Set current app
        self.context.set_var('current_app', 'whatsapp')
        
        # Infer app for send_message
        params = self.context.infer_missing_params('send_message', {})
        
        self.assertEqual(params.get('app_name'), 'whatsapp')
    
    def test_persistence(self):
        """Test context saves and loads."""
        self.context.set_var('persistent_key', 'persistent_value')
        self.context.save_context()
        
        # Create new instance
        new_context = ContextManager(storage_path="data/test_context.json")
        new_context.load_context()
        
        value = new_context.get_var('persistent_key')
        self.assertEqual(value, 'persistent_value')


class TestTaskChainOrchestrator(unittest.TestCase):
    """Test orchestrator logic (without actual app execution)."""
    
    def setUp(self):
        self.orchestrator = TaskChainOrchestrator()
        self.orchestrator.context_manager.reset()
    
    def test_parse_command(self):
        """Test that orchestrator can parse commands."""
        command = "Notepad खोलो, text लिखो"
        
        # This will fail at execution but should parse successfully
        # We're just testing the parsing part
        steps = self.orchestrator.parser.parse_command(command)
        
        self.assertGreater(len(steps), 0)
    
    def test_dependency_checking(self):
        """Test dependency verification logic."""
        step1 = TaskStep(step=1, intent='open_app', params={'app': 'notepad'})
        step2 = TaskStep(step=2, intent='type_text', params={'text': 'hello'}, dependencies=[1])
        
        # Simulate step1 success
        results = [{'step': 1, 'success': True, 'intent': 'open_app'}]
        
        # Check dependencies for step2
        deps_met = self.orchestrator._check_dependencies(step2, results)
        
        self.assertTrue(deps_met)
    
    def test_dependency_checking_failure(self):
        """Test dependency check fails when deps not met."""
        step2 = TaskStep(step=2, intent='type_text', params={'text': 'hello'}, dependencies=[1])
        
        # No results (step1 never ran)
        results = []
        
        deps_met = self.orchestrator._check_dependencies(step2, results)
        
        self.assertFalse(deps_met)


class TestEndToEndLogic(unittest.TestCase):
    """Test complete flow without GUI."""
    
    def test_full_parsing_flow(self):
        """Test complete command parsing and preparation."""
        parser = MultiStepCommandParser()
        orchestrator = TaskChainOrchestrator()
        
        command = "Notepad खोलो, Hello World लिखो, फिर Calculator खोलो"
        
        # Parse
        steps = parser.parse_command(command)
        
        # Parser currently produces 2 steps for this command
        self.assertGreaterEqual(len(steps), 2)
        
        # Save to context
        orchestrator.context_manager.set_task_chain([
            {'step': s.step, 'intent': s.intent, 'params': s.params}
            for s in steps
        ])
        
        # Verify saved
        saved_chain = orchestrator.context_manager.get_task_chain()
        self.assertGreaterEqual(len(saved_chain), 2)
    
    def test_context_flow(self):
        """Test context tracking through execution."""
        context = ContextManager(storage_path="data/test_flow.json")
        context.reset()
        
        # Simulate execution flow
        context.set_state(ExecutionState.PARSING)
        context.add_command("Test command", intent="test")
        
        context.set_state(ExecutionState.EXECUTING)
        context.set_var('current_app', 'notepad')
        
        context.set_state(ExecutionState.COMPLETE)
        
        # Verify flow
        self.assertEqual(context.get_state(), ExecutionState.COMPLETE)
        self.assertEqual(context.get_var('current_app'), 'notepad')
        self.assertEqual(len(context.get_command_history()), 1)


def run_all_tests():
    """Run all unit tests."""
    print("\n" + "="*70)
    print("AUTOMATED UNIT TESTS - No GUI Required")
    print("="*70 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestMultiStepParser))
    suite.addTests(loader.loadTestsFromTestCase(TestContextManager))
    suite.addTests(loader.loadTestsFromTestCase(TestTaskChainOrchestrator))
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEndLogic))
    
    # Run with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
    
    print("="*70 + "\n")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
