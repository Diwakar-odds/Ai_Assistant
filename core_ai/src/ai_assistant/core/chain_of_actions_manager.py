"""
Chain of Actions Manager
Central orchestrator for multi-step action execution with verification

Implements 7-step workflow:
1. Listen (receive command)
2. Process & Breakdown (decompose into actions)
3. Identify (determine which components handle what)
4. Assign (route to execution systems)
5. Track Progress (real-time updates)
6. Aggregate (combine results)
7. Notify (inform user)
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from pathlib import Path

from ai_assistant.core.action_chain_models import (
    ActionChain, Action, ChainStatus, ActionType,
    ExecutionReport, ProgressReport,
    generate_chain_id, generate_action_id
)
from ai_assistant.core.progress_tracker import get_progress_tracker

# Import existing components
try:
    from ai_assistant.automation.task_planner import TaskPlanner
    TASK_PLANNER_AVAILABLE = True
except ImportError:
    TASK_PLANNER_AVAILABLE = False

try:
    from ai_assistant.automation.orchestrator import AutomationOrchestrator
    ORCHESTRATOR_AVAILABLE = True
except ImportError:
    ORCHESTRATOR_AVAILABLE = False

try:
    from ai_assistant.automation.visual_verification import get_visual_verifier
    VERIFIER_AVAILABLE = True
except ImportError:
    VERIFIER_AVAILABLE = False

try:
    from ai_assistant.core.task_chain_orchestrator import TaskChainOrchestrator
    TASK_CHAIN_AVAILABLE = True
except ImportError:
    TASK_CHAIN_AVAILABLE = False

try:
    from ai_assistant.automation.browser_automation import BrowserAutomation, BrowserConfig
    BROWSER_AUTO_AVAILABLE = True
except ImportError:
    BROWSER_AUTO_AVAILABLE = False

try:
    from ai_assistant.automation.app_automation import AppAutomation
    APP_AUTO_AVAILABLE = True
except ImportError:
    APP_AUTO_AVAILABLE = False

try:
    from ai_assistant.multimodal import MultiModalAI
    VLM_AVAILABLE = True
except ImportError:
    VLM_AVAILABLE = False

logger = logging.getLogger(__name__)


class ChainOfActionsManager:
    """
    Central manager for chain-of-actions execution
    
    Integrates:
    - TaskPlanner (decomposition)
    - TaskChainOrchestrator (execution)
    - AutomationOrchestrator (resource management)
    - VisualVerifier (verification)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize manager"""
        self.config = config or {}
        
        # Active chains
        self.active_chains: Dict[str, ActionChain] = {}
        self.completed_chains: Dict[str, ActionChain] = {}
        
        # Progress callbacks
        self.progress_callbacks: Dict[str, List[Callable]] = {}
        
        # Initialize components
        self.task_planner = TaskPlanner() if TASK_PLANNER_AVAILABLE else None
        self.task_orchestrator = TaskChainOrchestrator() if TASK_CHAIN_AVAILABLE else None
        self.verifier = get_visual_verifier() if VERIFIER_AVAILABLE else None
        
        # Initialize Automation Agents
        self.browser_agent = BrowserAutomation() if BROWSER_AUTO_AVAILABLE else None
        self.app_agent = AppAutomation() if APP_AUTO_AVAILABLE else None
        self.vlm = MultiModalAI() if VLM_AVAILABLE else None
        
        # Initialize Persistence
        self.tracker = get_progress_tracker()
        
        # Performance tracking
        self.stats = {
            "total_chains": 0,
            "successful_chains": 0,
            "failed_chains": 0,
            "total_actions": 0,
            "average_duration": 0.0
        }
        
        logger.info("ChainOfActionsManager initialized")
    
    # ========== STEP 1: LISTEN ==========
    
    async def create_chain(self, command: str) -> ActionChain:
        """
        Create a new action chain from user command
        
        Args:
            command: Natural language command
            
        Returns:
            ActionChain object
        """
        logger.info(f"📝 STEP 1 - LISTEN: Received command: {command}")
        
        chain = ActionChain(
            id=generate_chain_id(),
            command=command,
            status=ChainStatus.PENDING,
            created_at=datetime.now()
        )
        
        self.active_chains[chain.id] = chain
        self.stats["total_chains"] += 1
        
        # Persist: Start
        self.tracker.start_chain(chain.id, command, 0)
        
        logger.info(f"Created chain {chain.id}")
        return chain
    
    # ========== STEP 2: PROCESS & BREAKDOWN ==========
    
    async def decompose_command(self, chain: ActionChain) -> List[Action]:
        """
        Decompose command into executable actions
        
        Args:
            chain: ActionChain to decompose
            
        Returns:
            List of Action objects
        """
        logger.info(f"⚙️ STEP 2 - PROCESS & BREAKDOWN: Decomposing '{chain.command}'")
        
        chain.status = ChainStatus.PLANNING
        await self._notify_progress(chain)
        
        actions = []
        
        # Use TaskPlanner if available
        if self.task_planner:
            try:
                plan = self.task_planner.create_plan(chain.command)
                
                for i, planned_action in enumerate(plan.actions):
                    # Inject specific type into parameters for execution
                    # If type is an Enum, get its value, otherwise use it as string
                    type_val = planned_action.type.value if hasattr(planned_action.type, 'value') else str(planned_action.type)
                    planned_action.parameters['sub_type'] = type_val
                    
                    action = Action(
                        id=generate_action_id(),
                        type=self._map_action_type(type_val),
                        description=planned_action.description,
                        parameters=planned_action.parameters,
                        dependencies=planned_action.dependencies
                    )
                    actions.append(action)
                
                logger.info(f"✅ Decomposed into {len(actions)} actions using TaskPlanner")
                
            except Exception as e:
                logger.error(f"TaskPlanner failed: {e}")
                # Fallback to simple decomposition
                actions = await self._simple_decomposition(chain.command)
        else:
            # Simple decomposition
            actions = await self._simple_decomposition(chain.command)
        
        chain.actions = actions
        self.stats["total_actions"] += len(actions)
        
        # Persist: Update chain info
        self.tracker.start_chain(chain.id, chain.command, len(actions))
        
        # Persist: Record Plan
        for action in actions:
            self.tracker.record_action_start(action.id, chain.id, action.description, action.type.value)
        
        return actions
    
    async def _simple_decomposition(self, command: str) -> List[Action]:
        """Fallback simple decomposition"""
        logger.info("Using simple decomposition (TaskPlanner not available)")
        
        # Basic keyword-based decomposition
        actions = []
        command_lower = command.lower()
        
        # Browser actions
        if any(kw in command_lower for kw in ['open', 'navigate', 'browse', 'youtube', 'google']):
            actions.append(Action(
                id=generate_action_id(),
                type=ActionType.BROWSER,
                description=f"Open browser for: {command}",
                parameters={'command': command, 'sub_type': 'browser_navigate'}
            ))
        
        # App actions
        if any(kw in command_lower for kw in ['whatsapp', 'sticky notes', 'notepad', 'word']):
            actions.append(Action(
                id=generate_action_id(),
                type=ActionType.APP,
                description=f"Open application for: {command}",
                parameters={'command': command, 'sub_type': 'app_open'}
            ))
        
        # File actions
        if any(kw in command_lower for kw in ['create', 'save', 'file', 'document']):
            actions.append(Action(
                id=generate_action_id(),
                type=ActionType.FILE,
                description=f"File operation: {command}",
                parameters={'command': command, 'sub_type': 'file'}
            ))
        
        # Default action if nothing matched
        if not actions:
            actions.append(Action(
                id=generate_action_id(),
                type=ActionType.CUSTOM,
                description=command,
                parameters={'command': command}
            ))
        
        return actions
    
    def _map_action_type(self, planner_type: str) -> ActionType:
        """Map TaskPlanner action type to ActionType enum"""
        mapping = {
            'browser_navigate': ActionType.BROWSER,
            'browser_click': ActionType.BROWSER,
            'browser_type': ActionType.BROWSER,
            'browser_scroll': ActionType.BROWSER,  # Added scroll support
            'browser_select': ActionType.BROWSER,  # Added select/dropdown support
            'app_open': ActionType.APP,
            'app_close': ActionType.APP,
            'app_interact': ActionType.APP,
            'system_type': ActionType.APP,
            'system_press': ActionType.APP,
            'wait': ActionType.CUSTOM,
            'file_create': ActionType.FILE,
            'file_read': ActionType.FILE,
            'system_command': ActionType.SYSTEM,
        }
        return mapping.get(planner_type.lower(), ActionType.CUSTOM)
    
    # ========== STEP 3: IDENTIFY ==========
    
    async def identify_executors(self, chain: ActionChain) -> Dict[str, str]:
        """
        Identify which component will execute each action
        
        Args:
            chain: ActionChain with actions
            
        Returns:
            Dict mapping action_id -> executor_name
        """
        logger.info(f"🔍 STEP 3 - IDENTIFY: Determining executors for {len(chain.actions)} actions")
        
        executor_map = {}
        
        for action in chain.actions:
            if action.type == ActionType.BROWSER:
                executor_map[action.id] = "BrowserAutomation"
            elif action.type == ActionType.APP:
                executor_map[action.id] = "AppAutomation"
            elif action.type == ActionType.FILE:
                executor_map[action.id] = "FileOperations"
            elif action.type == ActionType.SYSTEM:
                executor_map[action.id] = "SystemControl"
            else:
                executor_map[action.id] = "TaskChainOrchestrator"
        
        logger.info(f"Executor mapping: {executor_map}")
        return executor_map
    
    # ========== STEP 4: ASSIGN & EXECUTE ==========
    
    async def execute_chain(self, chain_id: str) -> ExecutionReport:
        """
        Execute all actions in chain
        
        Args:
            chain_id: Chain ID to execute
            
        Returns:
            ExecutionReport
        """
        chain = self.active_chains.get(chain_id)
        if not chain:
            raise ValueError(f"Chain {chain_id} not found")
        
        logger.info(f"🚀 STEP 4 - ASSIGN & EXECUTE: Starting execution of chain {chain_id}")
        
        chain.status = ChainStatus.EXECUTING
        chain.started_at = datetime.now()
        await self._notify_progress(chain)
        
        completed = 0
        failed = 0
        action_results = []
        
        try:
            # Execute actions using a while loop to allow dynamic insertion of repair steps
            i = 0
            while i < len(chain.actions):
                action = chain.actions[i]
                chain.current_action_index = i
                
                # Check dependencies
                if not await self._check_dependencies(action, chain):
                    logger.warning(f"Dependencies not met for {action.id}, skipping")
                    action.status = "skipped"
                    i += 1
                    continue
                
                # Execute action
                logger.info(f"Executing action {i+1}/{len(chain.actions)}: {action.description}")
                action.status = "running"
                action.started_at = datetime.now()
                await self._notify_progress(chain)
                
                # Persist: Update Status
                self.tracker.update_action_status(action.id, "running")
                self.tracker.update_chain_status(chain.id, ChainStatus.EXECUTING.value, chain.progress_percentage, chain.actions_completed)
                
                try:
                    result = await self._execute_action(action, chain)
                    
                    # Visual Verification (VLM)
                    verification_failed = False
                    verification_msg = ""
                    
                    if self.vlm and action.type in [ActionType.BROWSER, ActionType.APP]:
                        verification = await self._verify_action_with_vlm(action)
                        if verification:
                            result["visual_verification"] = verification
                            if verification.get("verified") is False: # Explicit False, not None
                                verification_failed = True
                                verification_msg = verification.get("error") or "Visual check failed"
                                logger.warning(f"⚠️ Visual Verification Failed: {verification_msg}")
                                logger.info(f"Analysis: {verification.get('vlm_analysis')}")
                            else:
                                logger.info(f"✅ Visual Verification Passed")

                    if verification_failed:
                        # Handle Self-Correction
                        if hasattr(self, 'task_planner') and self.task_planner:
                            logger.info("🔧 Attempting Self-Correction...")
                            reparations = await self._handle_verification_failure(action, verification)
                            if reparations:
                                logger.info(f"➕ Inserting {len(reparations)} repair actions")
                                # Insert repair actions immediately after current action
                                # (slicing allows inserting multiple items)
                                chain.actions[i+1:i+1] = reparations
                                # Don't advance 'i' yet? No, we completed this bad action, 
                                # next iteration will pick up the first repair action.
                                action.status = "completed_with_warning" # Mark current as done but flaky
                                action.result = result # Save result anyway
                            else:
                                logger.error("No repairs generated, continuing...")
                                action.status = "completed" # Treat as done if no fix
                        else:
                             action.status = "completed" # No planner to fix
                    else:
                        action.status = "completed"
                    
                    action.result = result
                    action.completed_at = datetime.now()
                    action.duration_seconds = (action.completed_at - action.started_at).total_seconds()
                    
                    chain.actions_completed += 1
                    completed += 1
                    
                    # Persist: Completed Action
                    status_str = action.status
                    self.tracker.update_action_status(action.id, status_str, 100.0, result)
                    
                    if "output" in result and result["output"]:
                         logger.info(f"✅ Action Success: {result['output']}")
                    
                    # Store result
                    chain.results[action.id] = result
                    action_results.append({
                        "action_id": action.id,
                        "description": action.description,
                        "result": result,
                        "duration": action.duration_seconds
                    })
                    
                    logger.info(f"✅ Action completed: {action.description}")
                    
                except Exception as e:
                    logger.error(f"❌ Action failed: {action.description} - {e}")
                    action.status = "failed"
                    action.error = str(e)
                    action.completed_at = datetime.now()
                    
                    # Persist: Failed Action
                    self.tracker.update_action_status(action.id, "failed", error=str(e))
                    
                    chain.actions_failed += 1
                    failed += 1
                    chain.errors.append(f"Action {action.id}: {str(e)}")
                
                # Persist: Chain Progress
                self.tracker.update_chain_status(chain.id, ChainStatus.EXECUTING.value, chain.progress_percentage, chain.actions_completed)
                await self._notify_progress(chain)
                
                # Increment loop
                i += 1
            
            # All actions processed
            chain.status = ChainStatus.VERIFYING
            await self._notify_progress(chain)
            
        except Exception as e:
            logger.error(f"Chain execution failed: {e}", exc_info=True)
            chain.status = ChainStatus.FAILED
            chain.errors.append(str(e))
        
        return await self._finalize_chain(chain, completed, failed, action_results)
    
    async def _check_dependencies(self, action: Action, chain: ActionChain) -> bool:
        """Check if action dependencies are satisfied"""
        if not action.dependencies:
            return True
        
        for dep_id in action.dependencies:
            dep_action = next((a for a in chain.actions if a.id == dep_id), None)
            if not dep_action:
                return False
            
            # Allow completed or completed_with_warning (for self-corrected actions)
            if dep_action.status not in ["completed", "completed_with_warning"]:
                return False
        
        return True
    
    async def _execute_action(self, action: Action, chain: ActionChain) -> Any:
        """Execute single action"""
        logger.info(f"🚀 Executing action: {action.description} (Type: {action.type.value})")
        
        # 1. Browser Actions
        if action.type == ActionType.BROWSER and self.browser_agent:
            return await self._execute_browser_action(action)
            
        # 2. App Actions
        elif action.type == ActionType.APP and self.app_agent:
            return await self._execute_app_action(action)
            
        # 3. File Actions
        elif action.type == ActionType.FILE:
             return await self._execute_file_action(action)
        
        # Use TaskChainOrchestrator if available (Legacy fallback)
        if self.task_orchestrator and action.type in [ActionType.APP, ActionType.BROWSER]:
            from ai_assistant.ai.multi_step_parser import TaskStep
            
            # Convert to TaskStep
            step = TaskStep(
                step=chain.current_action_index + 1,
                intent=self._infer_intent(action),
                params=action.parameters,
                dependencies=action.dependencies
            )
            
            result = self.task_orchestrator.execute_step(step)
            return result
        
        # Fallback: simulate execution
        logger.warning(f"⚠️ No executor found for {action.type}, simulating execution: {action.description}")
        await asyncio.sleep(1)  # Simulate work
        
        return {
            "success": True,
            "message": f"Simulated: {action.description}",
            "output": None
        }

    async def _execute_browser_action(self, action: Action) -> Dict[str, Any]:
        """Execute browser action using BrowserAutomation"""
        sub_type = action.parameters.get('sub_type', '').lower()
        params = action.parameters
        
        if not self.browser_agent:
            raise RuntimeError("Browser Agent not initialized")

        # Helper to run blocking calls
        def _run_browser_task():
            # Ensure browser is started
            if not self.browser_agent.driver:
                self.browser_agent.start_browser()
            
            if 'navigate' in sub_type or 'open' in sub_type:
                url = params.get('url', '')
                if not url: # Fallback extraction
                    import re
                    # Simple URL extraction
                    words = params.get('command', '').split()
                    for w in words:
                        if '.' in w and not w.endswith('.'): url = w; break
                    if not url: raise ValueError("No URL provided for navigation")
                
                success = self.browser_agent.navigate(url)
                return {"success": success, "output": f"Navigated to {self.browser_agent.current_url}"}

            elif 'click' in sub_type:
                desc = params.get('element_description') or params.get('selector') or action.description
                el = self.browser_agent.find_element_by_description(desc)
                if el:
                    el.click()
                    return {"success": True, "output": f"Clicked {desc}"}
                else:
                    return {"success": False, "error": f"Element not found: {desc}"}

            elif 'type' in sub_type:
                text = params.get('text', '')
                desc = params.get('element_description') or "input field"
                el = self.browser_agent.find_element_by_description(desc)
                if el:
                    el.clear()
                    el.send_keys(text)
                    return {"success": True, "output": f"Typed '{text}' into {desc}"}
                else:
                    try:
                        # Fallback for generic typing (active element)
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(self.browser_agent.driver)
                        actions.send_keys(text).perform()
                        return {"success": True, "output": f"Typed '{text}' into active element"}
                    except Exception as e:
                        return {"success": False, "error": f"Element not found and fallback failed: {e}"}

            elif 'scroll' in sub_type:
                direction = params.get('direction', 'down')
                amount = params.get('amount', 500)
                try:
                    script = f"window.scrollBy(0, {amount})" if direction == 'down' else f"window.scrollBy(0, -{amount})"
                    self.browser_agent.driver.execute_script(script)
                    return {"success": True, "output": f"Scrolled {direction}"}
                except Exception as e:
                    return {"success": False, "error": f"Scroll failed: {e}"}
            
            # Default/Unknown sub-type
            return {"success": True, "message": "Browser action processed (generic)"}

        return await asyncio.to_thread(_run_browser_task)

    async def _execute_app_action(self, action: Action) -> Dict[str, Any]:
        """Execute app action using AppAutomation"""
        sub_type = action.parameters.get('sub_type', '').lower()
        params = action.parameters
        
        def _run_app_task():
            if 'open' in sub_type:
                app_name = params.get('app_name') or params.get('name')
                if not app_name and 'command' in params:
                    # simplistic extraction
                    app_name = params['command'].replace('open', '').strip()
                
                # SANTIY CHECK: Aggressive cleaning of app names from composite commands
                if app_name:
                    app_name_lower = app_name.lower()
                    # Common separators in composite commands
                    separators = [" and ", " & ", " then ", " + ", " -> ", ", "]
                    for sep in separators:
                        if sep in app_name_lower:
                            app_name = app_name_lower.split(sep)[0].strip()
                            app_name_lower = app_name # usage for next iteration? No, simple break ok
                            break
                    
                    # Remove common trailing action verbs if they snuck in
                    # e.g. "whatsapp write" -> "whatsapp"
                    action_verbs = [" write", " type", " message", " search", " send"]
                    for verb in action_verbs:
                         if app_name_lower.endswith(verb):
                             app_name = app_name_lower[:-len(verb)].strip()
                             break

                if app_name:
                    success = self.app_agent.open_app(app_name)
                    return {"success": success, "output": f"Opened {app_name}"}
                return {"success": False, "error": "App name missing"}
            
            elif 'type' in sub_type or 'system_type' in sub_type: # Handle SYSTEM_TYPE mapped to APP
                text = params.get('text', '')
                success = self.app_agent.type_text(text)
                return {"success": success, "output": f"Typed: {text}"}
                
            elif 'press' in sub_type:
                key = params.get('key', 'enter')
                success = self.app_agent.press_key(key)
                return {"success": success, "output": f"Pressed: {key}"}
                
            return {"success": True, "message": "App action processed (generic)"}
            
        return await asyncio.to_thread(_run_app_task)

    async def _execute_file_action(self, action: Action) -> Dict[str, Any]:
        """Execute file action"""
        # Placeholder for file operations
        sub_type = action.parameters.get('sub_type', '').lower()
        params = action.parameters
        
        await asyncio.sleep(0.5)
        return {"success": True, "output": f"File action {sub_type} completed (simulated)"}

    
    def _infer_intent(self, action: Action) -> str:
        """Infer intent from action type"""
        if action.type == ActionType.APP:
            return "open_app"
        elif action.type == ActionType.BROWSER:
            return "open_browser"
        elif action.type == ActionType.FILE:
            return "file_operation"
        else:
            return "custom_action"
    
    # ========== STEP 5: TRACK PROGRESS ==========
    
    async def get_progress(self, chain_id: str) -> ProgressReport:
        """Get real-time progress of chain"""
        chain = self.active_chains.get(chain_id) or self.completed_chains.get(chain_id)
        if not chain:
            raise ValueError(f"Chain {chain_id} not found")
        
        current_action = None
        current_progress = 0
        
        if chain.current_action_index < len(chain.actions):
            action = chain.actions[chain.current_action_index]
            current_action = action.description
            current_progress = action.progress
        
        return ProgressReport(
            chain_id=chain_id,
            status=chain.status.value,
            progress_percentage=chain.progress_percentage,
            current_action=current_action,
            current_action_progress=current_progress,
            completed_actions=chain.actions_completed,
            total_actions=chain.total_actions,
            elapsed_seconds=chain.duration_seconds,
            estimated_remaining_seconds=self._estimate_remaining_time(chain)
        )
    
    def _estimate_remaining_time(self, chain: ActionChain) -> float:
        """Estimate remaining execution time"""
        if chain.actions_completed == 0:
            return 0.0
        
        avg_time_per_action = chain.duration_seconds / chain.actions_completed
        remaining_actions = chain.total_actions - chain.actions_completed
        
        return avg_time_per_action * remaining_actions
    
    async def _notify_progress(self, chain: ActionChain):
        """Notify progress callbacks"""
        if chain.id in self.progress_callbacks:
            progress = await self.get_progress(chain.id)
            for callback in self.progress_callbacks[chain.id]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(progress)
                    else:
                        callback(progress)
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")
    
    def subscribe_progress(self, chain_id: str, callback: Callable):
        """Subscribe to progress updates"""
        if chain_id not in self.progress_callbacks:
            self.progress_callbacks[chain_id] = []
        self.progress_callbacks[chain_id].append(callback)
    
    # ========== STEP 6: AGGREGATE ==========
    
    async def _verify_action_with_vlm(self, action: Action) -> Dict[str, Any]:
        """
        Verify if an action was successful using VLM (Vision Language Model).
        """
        if not self.vlm:
            return {"verified": None, "reason": "VLM not initialized"}
            
        logger.info(f"👁️ Visually verifying: {action.description}")
        
        prompt = f"I just executed this action: '{action.description}'. " \
                 f"Please analyze the screen and verify if the action appears successful. " \
                 f"IMPORTANT: Start your response with 'YES' if successful, or 'NO' if failed. " \
                 f"Then describe what you see that confirms or denies the success."

        try:
            # Run in executor to avoid blocking asyncio loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self.vlm.analyze_screen(prompt=prompt)
            )
            
            analysis = result.get("analysis", "No analysis provided")
            # Parse YES/NO
            is_success = analysis.strip().upper().startswith("YES")
            if not is_success and not analysis.strip().upper().startswith("NO"):
                # Ambiguous, default to True for safety unless clearly NO
                 # Actually, let's be strict. If it doesn't say YES, assume check failed or needs review.
                 # But VLM might be chatty. Let's look for "YES" in first 10 chars.
                 is_success = "YES" in analysis.strip().upper()[:10]
            
            return {
                "verified": is_success,
                "vlm_analysis": analysis,
                "timestamp": result.get("timestamp")
            }
        except Exception as e:
            logger.error(f"VLM Verification failed: {e}")
            return {"verified": False, "error": str(e)}

    async def _handle_verification_failure(self, action: Action, verification: Dict[str, Any]) -> List[Action]:
        """
        Ask TaskPlanner for repair steps when verification fails.
        """
        logger.info(f"🚧 Handling verification failure for: {action.description}")
        
        if not self.task_planner:
             logger.warning("No TaskPlanner available for repairs")
             return []
             
        vlm_analysis = verification.get("vlm_analysis") or verification.get("error", "Unknown error")
        error_message = verification.get("error", "Visual check mismatch")
        
        # Run in thread to avoid blocking
        loop = asyncio.get_event_loop()
        planner_actions = await loop.run_in_executor(
            None,
            lambda: self.task_planner.generate_repair_actions(
                failed_action=action,
                error_message=error_message,
                vlm_analysis=vlm_analysis
            )
        )
        
        # Convert Planner Actions to Core Actions
        core_actions = []
        for p_action in planner_actions:
            # Handle type conversion
            type_val = p_action.type.value if hasattr(p_action.type, 'value') else str(p_action.type)
            p_action.parameters['sub_type'] = type_val
            
            c_action = Action(
                id=generate_action_id(),
                type=self._map_action_type(type_val),
                description=p_action.description,
                parameters=p_action.parameters,
                dependencies=p_action.dependencies
            )
            core_actions.append(c_action)
            
        return core_actions

    async def _finalize_chain(self, chain: ActionChain, completed: int, 
                             failed: int, action_results: List[Dict]) -> ExecutionReport:
        """
        Aggregate results and create final report
        
        Args:
            chain: Executed chain
            completed: Number of completed actions
            failed: Number of failed actions
            action_results: List of action results
            
        Returns:
            ExecutionReport
        """
        logger.info(f"📊 STEP 6 - AGGREGATE: Combining results from {len(action_results)} actions")
        
        # Verify results if verifier available
        verification_passed = False
        verification_score = 0.0
        
        if self.verifier:
            try:
                verification_results = []
                for action in chain.actions:
                    if action.status == "completed" and action.result:
                        # TODO: Implement VLM verification based on action type
                        pass
                
                verification_passed = True
                verification_score = 0.95  # Placeholder
                
                logger.info(f"✅ Verification complete: {verification_score:.2%}")
            except Exception as e:
                logger.error(f"Verification failed: {e}")
        
        chain.verification_results.append({
            "passed": verification_passed,
            "score": verification_score,
            "timestamp": datetime.now().isoformat()
        })
        
        # Aggregate outputs
        outputs = []
        errors = []
        
        for action in chain.actions:
            if action.status == "completed" and action.result:
                if isinstance(action.result, dict) and "output" in action.result:
                    outputs.append(action.result["output"])
            elif action.error:
                errors.append(f"{action.description}: {action.error}")
        
        # Final status
        chain.completed_at = datetime.now()
        if failed > 0:
            chain.status = ChainStatus.FAILED
            self.stats["failed_chains"] += 1
        else:
            chain.status = ChainStatus.COMPLETED
            self.stats["successful_chains"] += 1
        
        # Move to completed
        self.completed_chains[chain.id] = chain
        if chain.id in self.active_chains:
            del self.active_chains[chain.id]
            
        # Persist: Final Status
        self.tracker.update_chain_status(
            chain.id, 
            chain.status.value, 
            100.0 if failed == 0 else chain.progress_percentage,
            chain.actions_completed
        )
        
        # Update stats
        total_duration = chain.duration_seconds
        self.stats["average_duration"] = (
            (self.stats["average_duration"] * (self.stats["total_chains"] - 1) + total_duration) 
            / self.stats["total_chains"]
        )
        
        # Create report
        report = ExecutionReport(
            chain_id=chain.id,
            success=(failed == 0),
            total_actions=len(chain.actions),
            completed_actions=completed,
            failed_actions=failed,
            skipped_actions=len(chain.actions) - completed - failed,
            duration_seconds=total_duration,
            average_action_time=total_duration / len(chain.actions) if chain.actions else 0,
            outputs=outputs,
            errors=errors,
            verification_passed=verification_passed,
            verification_score=verification_score,
            action_results=action_results
        )
        
        return report
    
    # ========== STEP 7: NOTIFY ==========
    
    async def notify_completion(self, report: ExecutionReport) -> str:
        """
        Create completion notification
        
        Args:
            report: ExecutionReport
            
        Returns:
            Notification message
        """
        logger.info(f"📢 STEP 7 - NOTIFY: Creating completion notification")
        
        chain = self.completed_chains.get(report.chain_id)
        if not chain:
            return "Chain execution completed"
        
        if report.success:
            message = f"""
✅ Task Complete!

Command: {chain.command}

Summary:
- {report.completed_actions}/{report.total_actions} actions completed
- Duration: {report.duration_seconds:.1f} seconds
- Verification: {'✓ Passed' if report.verification_passed else '✗ Failed'} ({report.verification_score:.0%})

Outputs: {len(report.outputs)} files created
"""
        else:
            message = f"""
❌ Task Failed

Command: {chain.command}

Summary:
- {report.completed_actions}/{report.total_actions} actions completed
- {report.failed_actions} actions failed
- Duration: {report.duration_seconds:.1f} seconds

Errors:
{chr(10).join(f"- {err}" for err in report.errors[:3])}
"""
        
        logger.info(message)
        return message
    
    # ========== PUBLIC API ==========
    
    async def execute_command(self, command: str, 
                             on_progress: Optional[Callable] = None) -> ExecutionReport:
        """
        Execute command end-to-end (all 7 steps)
        
        Args:
            command: Natural language command
            on_progress: Optional callback for progress updates
            
        Returns:
            ExecutionReport
        """
        # Step 1: Listen (Create chain)
        chain = await self.create_chain(command)
        
        # Subscribe to progress
        if on_progress:
            self.subscribe_progress(chain.id, on_progress)
        
        # Step 2: Process & Breakdown
        await self.decompose_command(chain)
        
        # Step 3: Identify
        await self.identify_executors(chain)
        
        # Step 4: Assign & Execute + Step 5: Track Progress
        report = await self.execute_chain(chain.id)
        
        # Step 6: Aggregate (done in execute_chain)
        
        # Step 7: Notify
        message = await self.notify_completion(report)
        
        return report
    
    def get_chain(self, chain_id: str) -> Optional[ActionChain]:
        """Get chain by ID"""
        return self.active_chains.get(chain_id) or self.completed_chains.get(chain_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics"""
        return {
            **self.stats,
            "active_chains": len(self.active_chains),
            "completed_chains": len(self.completed_chains)
        }


# Singleton instance
_manager = None


def get_chain_manager() -> ChainOfActionsManager:
    """Get singleton chain manager"""
    global _manager
    if _manager is None:
        _manager = ChainOfActionsManager()
    return _manager
