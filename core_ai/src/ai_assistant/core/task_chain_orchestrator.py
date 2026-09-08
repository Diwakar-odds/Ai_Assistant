"""
Task Chain Orchestrator
Executes multi-step task chains with state management, error handling, and context awareness.
"""

import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ai_assistant.ai.multi_step_parser import TaskStep, MultiStepCommandParser
from ai_assistant.core.conversation_context import ContextManager, ExecutionState, get_context_manager
from ai_assistant.core.universal_app_controller import UniversalAppController, get_universal_controller

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of task chain execution."""
    success: bool
    steps_completed: int
    total_steps: int
    results: List[Dict[str, Any]]
    error: Optional[str] = None
    message: str = ""


class TaskChainOrchestrator:
    """
    Orchestrates execution of multi-step task chains.
    
    Features:
    - State machine (IDLE → PARSING → EXECUTING → COMPLETE)
    - Dependency resolution
    - Context passing between steps
    - Error handling and rollback
    - Mid-task override support
    
    Usage:
        orchestrator = TaskChainOrchestrator()
        
        result = orchestrator.execute_command(
            "WhatsApp खोलो, मॉम को message करो कि hello"
        )
    """
    
    def __init__(self,
                 context_manager: ContextManager = None,
                 app_controller: UniversalAppController = None,
                 parser: MultiStepCommandParser = None):
        """
        Initialize orchestrator.
        
        Args:
            context_manager: Context manager (optional, will create default)
            app_controller: App controller (optional, will create default)
            parser: Command parser (optional, will create default)
        """
        self.context_manager = context_manager or get_context_manager()
        self.app_controller = app_controller or get_universal_controller()
        self.parser = parser or MultiStepCommandParser()
        
        # Initialization of automations is now handled by IntentExecutor
        
        logger.info("Job Chain Orchestrator initialized")
    
    # ===== MAIN EXECUTION METHODS =====
    
    def execute_command(self, command: str) -> ExecutionResult:
        """
        Execute a command (single or multi-step).
        
        This is the MAIN entry point for command execution.
        
        Args:
            command: User command
        
        Returns:
            ExecutionResult with status and details
        """
        logger.info(f"Executing command: {command}")
        
        try:
            # Check for override
            if self.context_manager.is_override(command):
                self.context_manager.handle_override(command)
                logger.info("Override detected, handling...")
            
            # Parse command
            self.context_manager.set_state(ExecutionState.PARSING)
            steps = self.parser.parse_command(command)
            
            logger.info(f"Parsed {len(steps)} steps")
            
            # Execute task chain
            result = self.execute_chain(steps)
            
            # Add to history
            self.context_manager.add_command(
                command,
                intent=steps[0].intent if steps else 'unknown',
                completed=result.success
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Command execution failed: {e}", exc_info=True)
            self.context_manager.set_state(ExecutionState.ERROR)
            
            return ExecutionResult(
                success=False,
                steps_completed=0,
                total_steps=0,
                results=[],
                error=str(e),
                message=f"Failed to execute command: {e}"
            )
    
    def execute_chain(self, steps: List[TaskStep]) -> ExecutionResult:
        """
        Execute a chain of task steps.
        
        Args:
            steps: List of TaskStep objects
        
        Returns:
            ExecutionResult
        """
        logger.info(f"Executing chain of {len(steps)} steps")
        
        # Save task chain to context
        self.context_manager.set_task_chain([
            {
                'step': s.step,
                'intent': s.intent,
                'params': s.params,
                'dependencies': s.dependencies
            }
            for s in steps
        ])
        
        self.context_manager.set_state(ExecutionState.EXECUTING)
        
        results = []
        steps_completed = 0
        
        try:
            for step in steps:
                # Check for cancellation/pause between steps
                current_state = self.context_manager.get_state()
                if current_state in [ExecutionState.PAUSED, ExecutionState.IDLE]:
                    logger.warning(f"⏹️ Execution interrupted (state: {current_state.value}). Stopping at step {step.step}.")
                    return ExecutionResult(
                        success=steps_completed > 0,
                        steps_completed=steps_completed,
                        total_steps=len(steps),
                        results=results,
                        message=f"Execution interrupted after {steps_completed} steps."
                    )
                
                logger.info(f"Executing step {step.step}/{len(steps)}: {step.intent}")
                
                # Check dependencies
                if not self._check_dependencies(step, results):
                    error_msg = f"Dependencies not met for step {step.step}"
                    logger.error(error_msg)
                    return ExecutionResult(
                        success=False,
                        steps_completed=steps_completed,
                        total_steps=len(steps),
                        results=results,
                        error=error_msg
                    )
                
                # Execute step with retry
                step_success = False
                step_result = None
                max_retries = 2
                
                for attempt in range(max_retries + 1):
                    try:
                        logger.info(f"▶️ Executing Step {step.step} (Attempt {attempt+1}/{max_retries+1})")
                        step_result = self.execute_step(step)
                        
                        # Check basic execution success
                        if step_result.get('success', False):
                            # PERFORM VERIFICATION
                            if self._verify_step(step, step_result):
                                step_success = True
                                break # Success!
                            else:
                                logger.warning(f"⚠️ Verification failed for Step {step.step}")
                        else:
                            logger.warning(f"⚠️ Execution failed for Step {step.step}: {step_result.get('error')}")
                            
                    except Exception as e:
                        logger.error(f"❌ Exception in step {step.step}: {e}")
                        step_result = {'success': False, 'error': str(e)}
                    
                    # If we are here, it failed. Wait before retry.
                    if not step_success and attempt < max_retries:
                        logger.info(f"⏳ Waiting 2s before retry...")
                        import time
                        time.sleep(2)
                
                if not step_success:
                    logger.error(f"❌ Step {step.step} failed after {max_retries+1} attempts")
                    # Try to rollback
                    self._rollback_steps(results) # Rollback all completed steps
                    return ExecutionResult(
                        success=False,
                        steps_completed=steps_completed,
                        total_steps=len(steps),
                        results=results,
                        error=f"Step {step.step} ({step.intent}) failed: {step_result.get('error') or 'Verification failed'}",
                        message="Task chain halted due to failure."
                    )
                
                # Step Successful
                logger.info(f"✅ Step {step.step} Completed & Verified")
                results.append(step_result)
                steps_completed += 1
                self.context_manager.advance_step()
            
            # All steps completed successfully
            self.context_manager.set_state(ExecutionState.COMPLETE)
            self.context_manager.clear_task_chain()
            
            return ExecutionResult(
                success=True,
                steps_completed=steps_completed,
                total_steps=len(steps),
                results=results,
                message=f"Successfully completed {steps_completed} steps!"
            )
        
        except Exception as e:
            logger.error(f"Chain execution failed: {e}", exc_info=True)
            self.context_manager.set_state(ExecutionState.ERROR)
            
            return ExecutionResult(
                success=False,
                steps_completed=steps_completed,
                total_steps=len(steps),
                results=results,
                error=str(e)
            )
    
    def execute_step(self, step: TaskStep) -> Dict[str, Any]:
        """
        Execute a single task step using the shared IntentExecutor.
        
        Args:
            step: TaskStep to execute
        
        Returns:
            Dict with execution result
        """
        try:
            from ai_assistant.core.intent_executor import get_intent_executor
            executor = get_intent_executor()
            return executor.execute(step.intent, step.params, self.context_manager)
        except ImportError:
            logger.error("IntentExecutor not available")
            return {
                'success': False,
                'step': step.step,
                'intent': step.intent,
                'error': 'IntentExecutor not found'
            }

    # ===== VERIFICATION =====

    def _verify_step(self, step, result) -> bool:
        """
        Verify that a step was ACTUALLY successful using 3-layer check:
        1. Code Return (already checked)
        2. System State (os.exists, process list)
        3. Visual VLM (optional, for complex UI)
        """
        try:
            from ai_assistant.core.intent_executor import get_intent_executor
            executor = get_intent_executor()
            return executor.verify(step.intent, result, step.params)
        except ImportError:
            logger.error("IntentExecutor not available for verification")
            return True # Fallback to trusting the method's return code

    # ===== DEPENDENCY MANAGEMENT =====
    
    def _check_dependencies(self, step: TaskStep, previous_results: List[Dict]) -> bool:
        """
        Check if step dependencies are met.
        
        Args:
            step: Step to check
            previous_results: Results from previous steps
        
        Returns:
            True if dependencies met, False otherwise
        """
        if not step.dependencies:
            return True
        
        for dep_step_num in step.dependencies:
            # Find result for this dependency
            dep_result = next((r for r in previous_results if r.get('step') == dep_step_num), None)
            
            if not dep_result or not dep_result.get('success'):
                logger.warning(f"Dependency step {dep_step_num} not successful")
                return False
        
        return True
    
    # ===== ERROR HANDLING =====
    
    def _rollback_steps(self, results: List[Dict]):
        """
        Attempt to rollback executed steps.
        
        Currently just logs - full rollback would require action-specific undo logic.
        """
        logger.info(f"Attempting rollback of {len(results)} steps")
        
        # For now, just clear context
        # Full rollback would require each action to support undo
        self.context_manager.set_var('last_action', 'rolled_back')
    
    # ===== OVERRIDE HANDLING =====
    
    def handle_override(self, new_command: str) -> ExecutionResult:
        """
        Handle a command override during execution.
        
        Args:
            new_command: New command that overrides current execution
        
        Returns:
            ExecutionResult for new command
        """
        logger.warning(f"Handling override: {new_command}")
        
        # Context manager already handled the override detection
        # Just execute the new command
        return self.execute_command(new_command)
    
    # ===== STATUS & MONITORING =====
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current execution status."""
        context_summary = self.context_manager.get_summary()
        
        return {
            'state': context_summary['state'],
            'current_step': context_summary['current_step'],
            'active_apps': self.app_controller.get_active_apps(),
            'context_vars': context_summary['key_vars'],
        }
    
    def pause(self):
        """Pause current execution."""
        self.context_manager.set_state(ExecutionState.PAUSED)
        logger.info("Execution paused")
    
    def resume(self):
        """Resume paused execution."""
        if self.context_manager.get_state() == ExecutionState.PAUSED:
            self.context_manager.set_state(ExecutionState.EXECUTING)
            logger.info("Execution resumed")
    
    def cancel(self):
        """Cancel current execution."""
        self.context_manager.clear_task_chain()
        self.context_manager.set_state(ExecutionState.IDLE)
        logger.info("Execution cancelled")


# Singleton instance
_orchestrator = None

def get_orchestrator() -> TaskChainOrchestrator:
    """Get singleton orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TaskChainOrchestrator()
    return _orchestrator
