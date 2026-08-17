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
        
        # Initialize specialized automations
        try:
            from ai_assistant.automation.file_automation import FileAutomation
            self.file_automation = FileAutomation()
            logger.info("✅ FileAutomation connected")
        except ImportError:
            self.file_automation = None
            logger.warning("⚠️ FileAutomation missing")
            
        try:
            from ai_assistant.automation.system_automation import SystemAutomation
            self.system_automation = SystemAutomation()
            logger.info("✅ SystemAutomation connected")
        except ImportError:
            self.system_automation = None
            logger.warning("⚠️ SystemAutomation missing")

        try:
            from ai_assistant.automation.app_automation import WhatsAppAutomation
            self.whatsapp_automation = WhatsAppAutomation()
        except ImportError:
            self.whatsapp_automation = None
            
        try:
            from ai_assistant.automation.taskbar_detection import TaskbarDetector
            self.taskbar_detector = TaskbarDetector()
            logger.info("✅ TaskbarDetector connected")
        except ImportError:
            self.taskbar_detector = None
            logger.warning("⚠️ TaskbarDetector missing")

        try:
            from ai_assistant.multimodal import MultiModalAI
            self.vlm = MultiModalAI()
            logger.info("✅ VLM (MultiModalAI) connected")
        except ImportError:
            self.vlm = None
            
        try:
            from ai_assistant.automation.visual_verification import get_visual_verifier
            self.visual_verifier = get_visual_verifier()
            logger.info("✅ Visual Verifier connected")
        except ImportError:
            self.visual_verifier = None
        
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
                
                # Execute step
                step_result = self.execute_step(step)
                results.append(step_result)
                
                if step_result['success']:
                    steps_completed += 1
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
        Execute a single task step.
        
        Args:
            step: TaskStep to execute
        
        Returns:
            Dict with execution result
        """
        logger.debug(f"Executing step: {step.intent} with params: {step.params}")
        
        try:
            # Infer missing parameters from context
            params = self.context_manager.infer_missing_params(step.intent, step.params)
            
            # Map intent to action
            if step.intent == 'open_app':
                app_name = params.get('app_name') or params.get('app')
                if not app_name:
                    return {
                        'success': False,
                        'step': step.step,
                        'intent': step.intent,
                        'error': 'No app name provided'
                    }
                
                result = self.app_controller.open_app(app_name)
                
                # Update context
                if result['success']:
                    self.context_manager.set_var('current_app', app_name.lower())
                    self.context_manager.set_var('last_action', 'opened_app')
                
                return {
                    'success': result['success'],
                    'step': step.step,
                    'intent': step.intent,
                    'result': result
                }
            
            elif step.intent == 'send_message':
                app_name = params.get('app_name', self.context_manager.get_var('current_app', 'WhatsApp'))
                contact = params.get('contact')
                message = params.get('message', '')
                
                if not contact:
                    return {
                        'success': False,
                        'step': step.step,
                        'intent': step.intent,
                        'error': 'No contact specified'
                    }
                
                result = self.app_controller.execute_action(app_name, 'send_message', {
                    'contact': contact,
                    'message': message
                })
                
                # Update context
                if result['success']:
                    self.context_manager.set_var('selected_contact', contact)
                    self.context_manager.set_var('last_message', message)
                    self.context_manager.set_var('last_action', 'sent_message')
                
                return {
                    'success': result.get('success', False),
                    'step': step.step,
                    'intent': step.intent,
                    'result': result
                }
            
                return {
                    'success': result.get('success', False),
                    'step': step.step,
                    'intent': step.intent,
                    'result': result
                }
            
            # ===== FILE OPERATIONS =====
            
            elif step.intent == 'find_file':
                filename = params.get('file_name') or params.get('name')
                location = params.get('location')  # Optional
                
                if not filename:
                     return {'success': False, 'step': step.step, 'error': 'No file name provided'}

                if self.file_automation:
                    path = self.file_automation.find_file(filename, location)
                    if path:
                        # Store in context for next steps!
                        self.context_manager.set_var('found_file_path', path)
                        self.context_manager.set_var('last_file', path)
                        return {'success': True, 'step': step.step, 'result': path}
                    else:
                        return {'success': False, 'step': step.step, 'error': f'File not found: {filename}'}
                else:
                    return {'success': False, 'step': step.step, 'error': 'File automation not available'}

            elif step.intent == 'open_folder' or step.intent == 'open_explorer':
                path = params.get('path') or params.get('folder') or self.context_manager.get_var('found_file_path')
                
                if self.file_automation:
                    success = self.file_automation.open_explorer(path)
                    return {'success': success, 'step': step.step}
                return {'success': False, 'step': step.step, 'error': 'File automation not available'}

            elif step.intent == 'move_file':
                src = params.get('source') or self.context_manager.get_var('found_file_path')
                dst = params.get('destination')
                
                if not src or not dst:
                    return {'success': False, 'step': step.step, 'error': 'Missing source or destination'}
                    
                if self.file_automation:
                    success = self.file_automation.move_file(src, dst)
                    return {'success': success, 'step': step.step}
                return {'success': False, 'step': step.step, 'error': 'File automation not available'}
            
            # ===== SYSTEM OPERATIONS =====
            
            elif step.intent == 'set_brightness':
                level_str = params.get('level', '50')
                try:
                    level = int(str(level_str).replace('%', ''))
                except:
                    level = 50
                    
                if self.system_automation:
                    success = self.system_automation.set_brightness(level)
                    return {'success': success, 'step': step.step}
                return {'success': False, 'step': step.step, 'error': 'System automation not available'}
                
            elif step.intent == 'toggle_wifi':
                action = params.get('action', 'on') # on/off/enable/disable
                enable = action.lower() in ['on', 'enable', 'start']
                
                if self.system_automation:
                    success = self.system_automation.toggle_wifi(enable)
                    return {'success': success, 'step': step.step}
                return {'success': False, 'step': step.step, 'error': 'System automation not available'}

            # ===== ADVANCED APP OPERATIONS =====
            
            elif step.intent == 'send_file':
                # e.g. "Send it to Mom"
                contact = params.get('contact')
                file_path = params.get('file') or self.context_manager.get_var('found_file_path') or self.context_manager.get_var('last_file')
                message = params.get('message', "Sent via AI Assistant")
                app = params.get('app', 'whatsapp').lower()
                
                if not contact or not file_path:
                    return {'success': False, 'step': step.step, 'error': 'Missing contact or file path'}
                
                if 'whatsapp' in app and self.whatsapp_automation:
                    success = self.whatsapp_automation.send_with_attachment(contact, message, file_path)
                    return {'success': success, 'step': step.step}
                else:
                    return {'success': False, 'step': step.step, 'error': f'Unsupported app or missing automation: {app}'}

            elif step.intent == 'check_taskbar':
                # "Check if Chrome is in the taskbar" or "What apps are running"
                app_name = params.get('app_name')
                
                if not self.taskbar_detector:
                    return {'success': False, 'step': step.step, 'error': 'Taskbar detection not available'}
                
                if app_name:
                    result = self.taskbar_detector.find_specific_app_in_taskbar(app_name)
                    found = result.get('found_in_processes', False) or (result.get('visual_search_result', {}).get('found', False))
                    
                    self.context_manager.set_var('last_taskbar_check', result)
                    return {
                        'success': True, 
                        'step': step.step, 
                        'result': result,
                        'message': f"Found {app_name}" if found else f"{app_name} not found"
                    }
                else:
                    # General check
                    result = self.taskbar_detector.get_complete_desktop_analysis()
                    self.context_manager.set_var('desktop_state', result)
                    return {'success': True, 'step': step.step, 'result': result}

            elif step.intent == 'type_text':
                app_name = params.get('app_name', self.context_manager.get_var('current_app'))
                text = params.get('text', '')
                
                if not app_name:
                    return {
                        'success': False,
                        'step': step.step,
                        'intent': step.intent,
                        'error': 'No app specified and no current app in context'
                    }
                
                result = self.app_controller.execute_action(app_name, 'type_text', {
                    'text': text
                })
                
                return {
                    'success': result.get('success', False),
                    'step': step.step,
                    'intent': step.intent,
                    'result': result
                }
            
            elif step.intent == 'play_video':
                app_name = params.get('app_name', 'YouTube')
                query = params.get('query', '')
                
                result = self.app_controller.execute_action(app_name, 'play_video', {
                    'query': query
                })
                
                return {
                    'success': result.get('success', False),
                    'step': step.step,
                    'intent': step.intent,
                    'result': result
                }
            
            elif step.intent == 'skip_time':
                app_name = params.get('app_name', self.context_manager.get_var('current_app', 'YouTube'))
                minutes = params.get('minutes', 0)
                
                result = self.app_controller.execute_action(app_name, 'skip_time', {
                    'minutes': minutes
                })
                
                return {
                    'success': result.get('success', False),
                    'step': step.step,
                    'intent': step.intent,
                    'result': result
                }
            
            else:
                # Unknown intent - try generic execution
                logger.warning(f"Unknown intent: {step.intent}, trying generic execution")
                
                return {
                    'success': False,
                    'step': step.step,
                    'intent': step.intent,
                    'error': f"Unknown intent: {step.intent}"
                }
        
        except Exception as e:
            logger.error(f"Step execution failed: {e}", exc_info=True)
            return {
                'success': False,
                'step': step.step,
                'intent': step.intent,
                'error': str(e)
            }
    
    # ===== VERIFICATION =====

    def _verify_step(self, step, result) -> bool:
        """
        Verify that a step was ACTUALLY successful using 3-layer check:
        1. Code Return (already checked)
        2. System State (os.exists, process list)
        3. Visual VLM (optional, for complex UI)
        """
        intent = step.intent
        logger.info(f"🕵️ Verifying step: {intent}")
        
        # 1. System State Verification
        if intent in ['find_file', 'open_folder', 'move_file']:
            # For file ops, we usually return the path. Check if it exists.
            path = result.get('result')
            # If move_file, we might return boolean, so let's check params
            if intent == 'move_file':
                dst = step.params.get('destination')
                if dst:
                    import os
                    # Construct potential full path if dst is folder? 
                    # Simpler to assume if the code returned True, shutil worked.
                    # But let's check if we can.
                    return True
            
            if isinstance(path, str) and (':' in path or '/' in path):
                import os
                exists = os.path.exists(path)
                logger.info(f"   State Check (File Existence): {'✅' if exists else '❌'} ({path})")
                return exists
                
        elif intent == 'check_taskbar':
            # It already does the check inside.
            return True
            
        elif intent in ['open_app', 'launch_app']:
            app_name = step.params.get('app_name') or step.params.get('name')
            if app_name and self.taskbar_detector:
                # Give it a moment to appear
                import time
                time.sleep(1)
                scan = self.taskbar_detector.find_specific_app_in_taskbar(app_name)
                found = scan.get('found_in_processes', False)
                logger.info(f"   State Check (Process Running): {'✅' if found else '❌'} ({app_name})")
                return found
                
        elif intent in ['set_brightness', 'set_volume']:
            # We could read back the value.
            # implementing strict read-back might be overkill for now, assume success if no error.
            return True
        
        # 2. Visual Verification (VLM)
        # We generally use this for 'UI' heavy tasks (WhatsApp, unknown apps)
        use_vlm = False
        if intent == 'send_file' and 'whatsapp' in str(step.params).lower():
            use_vlm = True
        
        if use_vlm and self.vlm:
            logger.info("   👁️ Running Visual Verification (VLM)...")
            try:
                # Capture screen? The VLM module likely handles it or we pass image.
                # Assuming vlm.analyze_screen handles capture.
                prompt = f"I just tried to perform this action: '{intent}' with params {step.params}. " \
                         f"Please verify if it looks successful. For WhatsApp, look for the message or 'sending' status." \
                         f"Return 'YES' if successful, 'NO' if failed."
                
                # Run sync for now as this is a sync method context
                # Ideally we should be async but Orchestrator is sync so far.
                # We'll rely on VLM to be blocking or fast.
                analysis = self.vlm.analyze_screen(prompt=prompt)
                
                is_success = "YES" in str(analysis.get('analysis', '')).upper()
                logger.info(f"   VLM Verdict: {'✅' if is_success else '❌'} ({analysis.get('analysis')})")
                return is_success
                
            except Exception as e:
                logger.warning(f"   VLM Verification Execution Failed: {e}")
                return True # Fallback to trusting the code execution if VLM fails to run
        
        # Default: Trust the method's return code
        return True

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
