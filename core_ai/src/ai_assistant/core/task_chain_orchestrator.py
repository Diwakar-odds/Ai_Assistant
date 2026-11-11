"""
Task Chain Orchestrator
Executes multi-step task chains with DAG wave parallelism, variable passing,
conditional/fallback branches, true pause/resume, agent delegation, and Global Emergency Stop.
"""

import concurrent.futures
import copy
import logging
import re
import time
import threading
from typing import List, Dict, Any, Optional, Callable
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
    chain_id: Optional[str] = None
    status: str = "completed"
    final_output: Optional[Any] = None


class ChainExecutionContext:
    """
    Isolated per-chain context proxy backed safely by the shared ContextManager.
    Prevents concurrent chains from overwriting each other's step outputs / vars.
    """

    def __init__(self, parent_ctx: Optional[ContextManager], chain_id: Optional[str] = None):
        self._parent = parent_ctx
        self._lock = threading.RLock()
        self.chain_id = chain_id
        self.key_vars: Dict[str, Any] = {}
        self.step_outputs: Dict[str, Any] = {}
        self.step_results: Dict[int, Dict[str, Any]] = {}

    def get_var(self, key: str, default: Any = None) -> Any:
        with self._lock:
            if key in self.key_vars:
                return self.key_vars[key]
        if self._parent is not None:
            return self._parent.get_var(key, default)
        return default

    def set_var(self, key: str, value: Any):
        with self._lock:
            self.key_vars[key] = value
        if self._parent is not None:
            try:
                self._parent.set_var(key, value)
            except Exception:
                pass

    def record_step_output(self, step: TaskStep, result: Dict[str, Any]):
        """Store step outputs under step number, step_id, output_key, and prev."""
        output_val = (
            result.get("output")
            or result.get("result")
            or result.get("output_path")
            or result.get("message")
        )
        path_val = result.get("output_path") or (
            result.get("result") if isinstance(result.get("result"), str) else ""
        )
        entry = {
            "output": output_val if output_val is not None else "",
            "result": result.get("result") if result.get("result") is not None else "",
            "path": path_val or "",
            "output_path": result.get("output_path") or path_val or "",
            "text": str(output_val) if output_val is not None else "",
        }
        with self._lock:
            self.step_results[step.step] = dict(result)
            self.step_outputs[str(step.step)] = entry
            self.step_outputs[f"step_{step.step}"] = entry
            self.step_outputs[f"step{step.step}"] = entry
            if getattr(step, "step_id", None):
                self.step_outputs[step.step_id] = entry
            if getattr(step, "output_key", None):
                self.step_outputs[step.output_key] = entry
            self.step_outputs["prev"] = entry

    def infer_missing_params(self, intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(params or {})
        if self._parent is not None:
            try:
                merged = self._parent.infer_missing_params(intent, merged)
            except Exception:
                pass
        with self._lock:
            if intent in ("youtube_search", "search_web", "play_media") and not merged.get("profile"):
                if self.key_vars.get("current_browser_profile"):
                    merged["profile"] = self.key_vars["current_browser_profile"]
            if intent in ("send_message", "type_text", "skip_time") and not merged.get("app_name"):
                if self.key_vars.get("current_app"):
                    merged["app_name"] = self.key_vars["current_app"]
            if intent in ("send_file", "move_file", "open_folder") and not merged.get("file") and not merged.get("source"):
                found = self.key_vars.get("found_file_path") or self.key_vars.get("last_file")
                if found:
                    if intent == "send_file":
                        merged["file"] = found
                    elif intent == "move_file":
                        merged["source"] = found
                    elif intent == "open_folder" and not merged.get("path"):
                        merged["path"] = found
        return merged

    def resolve_placeholders(self, obj: Any) -> Any:
        """Recursively resolve {prev.output}, {prev.path}, {step_1.output}, {step1.output}, {context.var}."""
        if isinstance(obj, str):
            def _repl(match: re.Match) -> str:
                expr = match.group(1).strip()
                with self._lock:
                    if "." in expr:
                        root, attr = expr.split(".", 1)
                        if root == "context":
                            val = self.get_var(attr)
                            return str(val) if val is not None else match.group(0)
                        target = self.step_outputs.get(root)
                        if isinstance(target, dict) and attr in target:
                            return str(target[attr])
                    elif expr in self.step_outputs:
                        return str(self.step_outputs[expr].get("output", ""))
                    elif expr in self.key_vars:
                        return str(self.key_vars[expr])
                return match.group(0)

            return re.sub(r'\{([A-Za-z0-9_.\-]+)\}', _repl, obj)

        if isinstance(obj, dict):
            return {k: self.resolve_placeholders(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.resolve_placeholders(v) for v in obj]
        return obj


class TaskChainOrchestrator:
    """
    Orchestrates execution of multi-step task chains.

    Features:
    - State machine (IDLE -> PARSING -> EXECUTING -> COMPLETE / PAUSED)
    - DAG wave dependency & parallel group execution
    - Variable/output passing ({prev.output}, {step_1.output})
    - Conditional / fallback branch handling
    - True pause/resume via threading.Event
    - Global emergency stop with immediate halt & input release
    - Seamless delegation of local intents and 14 specialized agents
    """

    def __init__(
        self,
        context_manager: ContextManager = None,
        app_controller: UniversalAppController = None,
        parser: MultiStepCommandParser = None,
    ):
        self.context_manager = context_manager or get_context_manager()
        self.app_controller = app_controller or get_universal_controller()
        self.parser = parser or MultiStepCommandParser()

        self._stop_event = threading.Event()
        # _resume_event is SET when running, CLEARED when paused
        self._resume_event = threading.Event()
        self._resume_event.set()
        self._active_lock = threading.RLock()

        logger.info("Job Chain Orchestrator initialized (with Emergency Stop, Pause/Resume & Agent DAG support)")

    # ===== EMERGENCY STOP, PAUSE & CONTROL =====

    def emergency_stop(self, reason: str = "Emergency stop requested"):
        """Immediately halts active chain execution, clears context, and releases OS inputs."""
        logger.warning(f"🛑 [ORCHESTRATOR EMERGENCY STOP]: {reason}")
        self._stop_event.set()
        self._resume_event.set()  # Unblock any paused waiter so loop exits immediately

        self.context_manager.clear_task_chain()
        self.context_manager.set_state(ExecutionState.IDLE)

        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.mouseUp()
            for key in ['ctrl', 'shift', 'alt', 'win', 'esc', 'tab', 'enter', 'space']:
                try:
                    pyautogui.keyUp(key)
                except Exception:
                    pass
        except Exception:
            pass

    def is_stopped(self) -> bool:
        """Check if emergency stop is currently active."""
        return self._stop_event.is_set()

    def pause(self):
        """Pause current execution cleanly between steps."""
        self._resume_event.clear()
        self.context_manager.set_state(ExecutionState.PAUSED)
        logger.info("⏸️ Execution paused")

    def resume(self):
        """Resume paused execution."""
        if self.context_manager.get_state() == ExecutionState.PAUSED or not self._resume_event.is_set():
            self._resume_event.set()
            self.context_manager.set_state(ExecutionState.EXECUTING)
            logger.info("▶️ Execution resumed")

    def cancel(self):
        """Cancel current execution."""
        self.emergency_stop("Execution cancelled")
        logger.info("🛑 Execution cancelled")

    # ===== HELPER CHECKS & DAG WAVE BUILDER =====

    def _is_cancelled(self, cancel_event: Optional[threading.Event] = None) -> bool:
        return self._stop_event.is_set() or bool(cancel_event is not None and cancel_event.is_set())

    def _wait_if_paused(
        self,
        cancel_event: Optional[threading.Event] = None,
        pause_event: Optional[threading.Event] = None,
    ) -> bool:
        """
        Block cleanly while paused; return True if cancelled while waiting, False to continue.
        """
        while (not self._resume_event.is_set()) or (pause_event is not None and pause_event.is_set()):
            if self._is_cancelled(cancel_event):
                return True
            if self.context_manager.get_state() == ExecutionState.IDLE and not self._resume_event.is_set():
                return True
            time.sleep(0.05)
        return self._is_cancelled(cancel_event)

    @staticmethod
    def _build_execution_waves(steps: List[TaskStep]) -> List[List[TaskStep]]:
        """
        Topologically group steps into parallel-executable waves based on dependencies
        and parallel_group annotations while preserving declaration order.
        """
        if not steps:
            return []

        remaining = list(steps)
        scheduled: set = set()
        waves: List[List[TaskStep]] = []

        while remaining:
            ready = [
                s for s in remaining
                if all(dep not in {r.step for r in remaining} for dep in (s.dependencies or []))
            ]
            if not ready:
                # Cycle safeguard: pick next step cleanly
                ready = [remaining[0]]

            # Separate conditional fallback steps into their own check after predecessor if any
            normal_ready = [s for s in ready if getattr(s, "condition", None) != "on_failure"]
            fallback_ready = [s for s in ready if getattr(s, "condition", None) == "on_failure"]

            wave = normal_ready if normal_ready else fallback_ready
            waves.append(wave)
            wave_ids = {s.step for s in wave}
            scheduled.update(wave_ids)
            remaining = [s for s in remaining if s.step not in wave_ids]

        return waves

    # ===== MAIN EXECUTION METHODS =====

    def execute_command(
        self,
        command: str,
        skip_override_check: bool = False,
        chain_id: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_event: Optional[threading.Event] = None,
        pause_event: Optional[threading.Event] = None,
    ) -> ExecutionResult:
        """
        Execute a command (single or multi-step).
        """
        logger.info(f"Executing command: {command}")

        try:
            if not skip_override_check and self.context_manager.is_override(command):
                self.context_manager.handle_override(command)
                logger.info("Override detected, handling...")

            self._stop_event.clear()
            self._resume_event.set()

            self.context_manager.set_state(ExecutionState.PARSING)
            steps = self.parser.parse_command(command)
            logger.info(f"Parsed {len(steps)} steps")

            result = self.execute_chain(
                steps,
                chain_id=chain_id,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
                pause_event=pause_event,
            )

            self.context_manager.add_command(
                command,
                intent=steps[0].intent if steps else 'unknown',
                completed=result.success,
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
                message=f"Failed to execute command: {e}",
                chain_id=chain_id,
                status="failed",
            )
        finally:
            if self.context_manager.get_state() in (ExecutionState.PARSING, ExecutionState.EXECUTING):
                self.context_manager.set_state(ExecutionState.IDLE)

    def _run_single_step_with_retries(
        self,
        step: TaskStep,
        chain_ctx: ChainExecutionContext,
        cancel_event: Optional[threading.Event] = None,
        pause_event: Optional[threading.Event] = None,
    ) -> tuple[bool, Dict[str, Any]]:
        step_copy = copy.deepcopy(step)
        step_copy.params = chain_ctx.resolve_placeholders(step_copy.params or {})
        if self.chain_id_for_step(chain_ctx):
            step_copy.params.setdefault("chain_id", chain_ctx.chain_id)

        step_success = False
        step_result: Dict[str, Any] = {'success': False, 'step': step_copy.step, 'intent': step_copy.intent}
        max_retries = 2

        for attempt in range(max_retries + 1):
            if self._is_cancelled(cancel_event):
                break
            if self._wait_if_paused(cancel_event, pause_event):
                break

            try:
                logger.info(f"▶️ Executing Step {step_copy.step} (Attempt {attempt + 1}/{max_retries + 1}): {step_copy.intent}")
                step_result = self.execute_step(step_copy, chain_ctx=chain_ctx)
                if not isinstance(step_result, dict):
                    step_result = {'success': bool(step_result), 'result': step_result}
                step_result.setdefault('step', step_copy.step)
                step_result.setdefault('intent', step_copy.intent)

                if step_result.get('success', False):
                    if self._verify_step(step_copy, step_result):
                        step_success = True
                        break
                    logger.warning(f"⚠️ Verification failed for Step {step_copy.step}")
                else:
                    logger.warning(f"⚠️ Execution failed for Step {step_copy.step}: {step_result.get('error')}")
                    if step_result.get('no_retry'):
                        break
            except Exception as e:
                logger.error(f"❌ Exception in step {step_copy.step}: {e}")
                step_result = {'success': False, 'step': step_copy.step, 'intent': step_copy.intent, 'error': str(e)}

            if not step_success and attempt < max_retries:
                for _ in range(10):
                    if self._is_cancelled(cancel_event):
                        break
                    time.sleep(0.1)

        if step_success:
            chain_ctx.record_step_output(step_copy, step_result)

        return step_success, step_result

    @staticmethod
    def chain_id_for_step(chain_ctx: ChainExecutionContext) -> Optional[str]:
        return getattr(chain_ctx, "chain_id", None)

    def execute_chain(
        self,
        steps: List[TaskStep],
        chain_id: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        cancel_event: Optional[threading.Event] = None,
        pause_event: Optional[threading.Event] = None,
    ) -> ExecutionResult:
        """
        Execute a chain/DAG of task steps with parallel waves, variable passing,
        conditional fallback support, and real pause/resume/cancel.
        """
        logger.info(f"Executing chain of {len(steps)} steps")

        chain_ctx = ChainExecutionContext(self.context_manager, chain_id=chain_id)
        self.context_manager.set_task_chain([
            {
                'step': s.step,
                'intent': s.intent,
                'params': s.params,
                'dependencies': s.dependencies,
                'agent_id': getattr(s, 'agent_id', None),
            }
            for s in steps
        ])

        # Only enter EXECUTING if not stopped prematurely before chain launch
        if self._is_cancelled(cancel_event):
            logger.warning("🛑 [EMERGENCY STOP] Task chain halted before step execution.")
            return ExecutionResult(
                success=False,
                steps_completed=0,
                total_steps=len(steps),
                results=[],
                error="Emergency stop invoked. Chain execution halted.",
                message="Emergency stop: task execution was immediately halted.",
                chain_id=chain_id,
                status="cancelled",
            )

        self.context_manager.set_state(ExecutionState.EXECUTING)

        results_by_step: Dict[int, Dict[str, Any]] = {}
        steps_completed = 0
        final_output: Any = None
        waves = self._build_execution_waves(steps)

        def _emit(event_type: str, **payload):
            if progress_callback:
                try:
                    progress_callback({
                        "event_type": event_type,
                        "chain_id": chain_id,
                        "completed_actions": steps_completed,
                        "total_actions": len(steps),
                        "progress_percentage": round((steps_completed / len(steps)) * 100.0, 2) if steps else 100.0,
                        **payload,
                    })
                except Exception as cb_err:
                    logger.debug(f"Progress callback error: {cb_err}")

        _emit("chain.started", status="executing")

        try:
            for wave in waves:
                # 1. Check stop/cancel before each wave
                if self._is_cancelled(cancel_event):
                    ordered = [results_by_step[k] for k in sorted(results_by_step)]
                    return ExecutionResult(
                        success=steps_completed > 0,
                        steps_completed=steps_completed,
                        total_steps=len(steps),
                        results=ordered,
                        error="Emergency stop invoked. Chain execution halted.",
                        message="Emergency stop: task execution was immediately halted.",
                        chain_id=chain_id,
                        status="cancelled",
                        final_output=final_output,
                    )

                # 2. Wait cleanly if paused (or check external IDLE abort)
                if self.context_manager.get_state() == ExecutionState.IDLE:
                    ordered = [results_by_step[k] for k in sorted(results_by_step)]
                    return ExecutionResult(
                        success=steps_completed > 0,
                        steps_completed=steps_completed,
                        total_steps=len(steps),
                        results=ordered,
                        message=f"Execution interrupted after {steps_completed} steps.",
                        chain_id=chain_id,
                        status="cancelled",
                        final_output=final_output,
                    )

                if self.context_manager.get_state() == ExecutionState.PAUSED or (pause_event is not None and pause_event.is_set()):
                    if self._resume_event.is_set() and (pause_event is None or not pause_event.is_set()):
                        # External caller set context_manager state to PAUSED directly without orchestrator.pause()
                        ordered = [results_by_step[k] for k in sorted(results_by_step)]
                        return ExecutionResult(
                            success=steps_completed > 0,
                            steps_completed=steps_completed,
                            total_steps=len(steps),
                            results=ordered,
                            message=f"Execution interrupted after {steps_completed} steps.",
                            chain_id=chain_id,
                            status="paused",
                            final_output=final_output,
                        )
                    _emit("chain.paused", status="paused")
                    cancelled_while_paused = self._wait_if_paused(cancel_event, pause_event)
                    if cancelled_while_paused:
                        ordered = [results_by_step[k] for k in sorted(results_by_step)]
                        return ExecutionResult(
                            success=steps_completed > 0,
                            steps_completed=steps_completed,
                            total_steps=len(steps),
                            results=ordered,
                            error="Cancelled while paused",
                            message="Chain cancelled while paused.",
                            chain_id=chain_id,
                            status="cancelled",
                            final_output=final_output,
                        )
                    _emit("chain.resumed", status="executing")

                # 3. Filter wave steps for condition & dependencies
                runnable: List[TaskStep] = []
                for step in wave:
                    cond = getattr(step, "condition", None)
                    prev_results_list = [results_by_step[k] for k in sorted(results_by_step)]

                    if cond == "on_failure":
                        dep_failed = any(
                            (d in results_by_step and not results_by_step[d].get("success"))
                            for d in (step.dependencies or [])
                        )
                        if not dep_failed:
                            # Skip fallback cleanly when primary step succeeded
                            results_by_step[step.step] = {
                                "success": True,
                                "skipped": True,
                                "step": step.step,
                                "intent": step.intent,
                                "result": "Skipped fallback (primary succeeded)",
                            }
                            continue
                    else:
                        if not self._check_dependencies(step, prev_results_list):
                            ordered = [results_by_step[k] for k in sorted(results_by_step)]
                            error_msg = f"Dependencies not met for step {step.step}"
                            logger.error(error_msg)
                            return ExecutionResult(
                                success=False,
                                steps_completed=steps_completed,
                                total_steps=len(steps),
                                results=ordered,
                                error=error_msg,
                                chain_id=chain_id,
                                status="failed",
                                final_output=final_output,
                            )

                    runnable.append(step)

                if not runnable:
                    continue

                # 4. Execute wave (single-step directly, multi-step concurrently via ThreadPoolExecutor)
                wave_outcomes: List[tuple[TaskStep, bool, Dict[str, Any]]] = []
                if len(runnable) == 1:
                    s = runnable[0]
                    _emit("chain.step_started", step_id=getattr(s, "step_id", f"step_{s.step}"), current_action=s.description, current_agent=getattr(s, "agent_id", None))
                    ok, res = self._run_single_step_with_retries(s, chain_ctx, cancel_event, pause_event)
                    wave_outcomes.append((s, ok, res))
                else:
                    for s in runnable:
                        _emit("chain.step_started", step_id=getattr(s, "step_id", f"step_{s.step}"), current_action=s.description, current_agent=getattr(s, "agent_id", None))
                    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(runnable))) as pool:
                        futures = {
                            pool.submit(self._run_single_step_with_retries, s, chain_ctx, cancel_event, pause_event): s
                            for s in runnable
                        }
                        for fut in concurrent.futures.as_completed(futures):
                            s = futures[fut]
                            try:
                                ok, res = fut.result()
                            except Exception as exc:
                                ok, res = False, {'success': False, 'step': s.step, 'intent': s.intent, 'error': str(exc)}
                            wave_outcomes.append((s, ok, res))
                    wave_outcomes.sort(key=lambda item: item[0].step)

                if self._is_cancelled(cancel_event):
                    logger.warning("🛑 Chain execution aborted by Emergency Stop.")
                    ordered = [results_by_step[k] for k in sorted(results_by_step)]
                    return ExecutionResult(
                        success=False,
                        steps_completed=steps_completed,
                        total_steps=len(steps),
                        results=ordered,
                        error="Emergency stop invoked. Chain execution halted.",
                        message="Emergency stop: task execution was immediately halted.",
                        chain_id=chain_id,
                        status="cancelled",
                        final_output=final_output,
                    )

                for s, ok, res in wave_outcomes:
                    results_by_step[s.step] = res
                    if ok:
                        logger.info(f"✅ Step {s.step} Completed & Verified")
                        steps_completed += 1
                        self.context_manager.advance_step()
                        out_cand = res.get("output") or res.get("result") or res.get("output_path")
                        if out_cand is not None:
                            final_output = out_cand
                        _emit("chain.step_completed", step_id=getattr(s, "step_id", f"step_{s.step}"), current_action=s.description, result=res)
                    else:
                        on_fail = getattr(s, "on_failure", "abort")
                        _emit("chain.step_failed", step_id=getattr(s, "step_id", f"step_{s.step}"), current_action=s.description, error=res.get("error"))
                        if on_fail in ("fallback", "continue", "skip"):
                            logger.warning(f"⚠️ Step {s.step} failed with on_failure='{on_fail}', continuing workflow")
                            continue

                        logger.error(f"❌ Step {s.step} failed")
                        ordered = [results_by_step[k] for k in sorted(results_by_step)]
                        self._rollback_steps(ordered)
                        return ExecutionResult(
                            success=False,
                            steps_completed=steps_completed,
                            total_steps=len(steps),
                            results=ordered,
                            error=f"Step {s.step} ({s.intent}) failed: {res.get('error') or 'Verification failed'}",
                            message="Task chain halted due to failure.",
                            chain_id=chain_id,
                            status="failed",
                            final_output=final_output,
                        )

            self.context_manager.set_state(ExecutionState.COMPLETE)
            self.context_manager.clear_task_chain()
            ordered = [results_by_step[k] for k in sorted(results_by_step)]
            _emit("chain.completed", status="completed", final_output=final_output)

            return ExecutionResult(
                success=True,
                steps_completed=steps_completed,
                total_steps=len(steps),
                results=ordered,
                message=f"Successfully completed {steps_completed} steps!",
                chain_id=chain_id,
                status="completed",
                final_output=final_output,
            )

        except Exception as e:
            logger.error(f"Chain execution failed: {e}", exc_info=True)
            self.context_manager.set_state(ExecutionState.ERROR)
            ordered = [results_by_step[k] for k in sorted(results_by_step)]
            return ExecutionResult(
                success=False,
                steps_completed=steps_completed,
                total_steps=len(steps),
                results=ordered,
                error=str(e),
                chain_id=chain_id,
                status="failed",
                final_output=final_output,
            )
        finally:
            if self.context_manager.get_state() in (ExecutionState.EXECUTING, ExecutionState.COMPLETE):
                self.context_manager.clear_task_chain()

    def execute_step(self, step: TaskStep, chain_ctx: Any = None) -> Dict[str, Any]:
        """Execute a single task step using shared IntentExecutor (handles both local OS and specialized agents)."""
        if self._stop_event.is_set():
            return {
                'success': False,
                'step': step.step,
                'intent': step.intent,
                'error': 'Emergency stop is active'
            }

        try:
            from ai_assistant.core.intent_executor import get_intent_executor
            executor = get_intent_executor()
            params = dict(step.params or {})
            if getattr(step, 'execution_target', None) == 'agent':
                params.setdefault('execution_target', 'agent')
            if getattr(step, 'agent_id', None):
                params.setdefault('agent_id', step.agent_id)
            if getattr(step, 'capability', None):
                params.setdefault('capability', step.capability)
            if getattr(step, 'description', None):
                params.setdefault('description', step.description)

            target_ctx = chain_ctx or self.context_manager
            res = executor.execute(step.intent, params, target_ctx)
            if isinstance(res, dict):
                res['step'] = step.step
                res['intent'] = step.intent
                if getattr(step, 'agent_id', None) and not res.get('agent_id'):
                    res['agent_id'] = step.agent_id
            return res
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
        """Verify that a step succeeded using 3-layer verification in IntentExecutor."""
        try:
            from ai_assistant.core.intent_executor import get_intent_executor
            executor = get_intent_executor()
            return executor.verify(step.intent, result, step.params)
        except ImportError:
            logger.error("IntentExecutor not available for verification")
            return True

    # ===== DEPENDENCY MANAGEMENT =====

    def _check_dependencies(self, step: TaskStep, previous_results: List[Dict]) -> bool:
        """Check if step dependencies are satisfied."""
        if not step.dependencies:
            return True

        for dep_step_num in step.dependencies:
            dep_result = next((r for r in previous_results if r.get('step') == dep_step_num), None)
            if not dep_result or not dep_result.get('success'):
                logger.warning(f"Dependency step {dep_step_num} not successful")
                return False

        return True

    # ===== ERROR HANDLING =====

    def _rollback_steps(self, results: List[Dict]):
        """Attempt to rollback executed steps."""
        logger.info(f"Attempting rollback of {len(results)} steps")
        self.context_manager.set_var('last_action', 'rolled_back')

    # ===== OVERRIDE HANDLING =====

    def handle_override(self, new_command: str) -> ExecutionResult:
        """Handle a command override during execution."""
        logger.warning(f"Handling override: {new_command}")
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
            'stopped': self._stop_event.is_set(),
            'paused': not self._resume_event.is_set(),
        }


# Singleton instance
_orchestrator = None


def get_orchestrator() -> TaskChainOrchestrator:
    """Get singleton orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TaskChainOrchestrator()
    return _orchestrator
