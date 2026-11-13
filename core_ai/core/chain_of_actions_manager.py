"""
Chain of Actions Manager
Central async orchestrator for multi-step DAG & multi-agent action execution with persistence.

Implements 7-step workflow:
1. Listen (receive command, create canonical ActionChain)
2. Process & Breakdown (YAML templates / MultiStepCommandParser / TaskPlanner)
3. Identify (determine local IntentExecutor / Automation / Specialized Agent)
4. Assign & Execute (DAG waves, parallel asyncio.gather, {prev.output} passing, pause/resume/cancel)
5. Track Progress (real-time ProgressTracker SQLite + global & per-chain subscribers)
6. Aggregate (combine results, preserve cancelled/failed/completed states)
7. Notify (emit structured completion / event payloads)
"""

import asyncio
import concurrent.futures
import copy
import logging
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from ai_assistant.core.action_chain_models import (
    Action,
    ActionChain,
    ActionType,
    ChainStatus,
    ExecutionReport,
    ProgressReport,
    _normalize_status_value,
    generate_action_id,
    generate_chain_id,
)
from ai_assistant.core.progress_tracker import get_progress_tracker

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
    from ai_assistant.core.task_chain_orchestrator import get_orchestrator
    TASK_CHAIN_AVAILABLE = True
except ImportError:
    TASK_CHAIN_AVAILABLE = False

try:
    from ai_assistant.automation.browser_automation import BrowserAutomation
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
    Central manager for chain-of-actions execution integrating local automation,
    DAG parallel waves, variable passing, persistent tracking, and the 14 specialized agents.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize manager"""
        self.config = config or {}
        self._lock = threading.RLock()

        # Active & completed chains
        self.active_chains: Dict[str, ActionChain] = {}
        self.completed_chains: Dict[str, ActionChain] = {}

        # Progress callbacks (per-chain AND global)
        self.progress_callbacks: Dict[str, List[Callable]] = {}
        self.global_progress_callbacks: List[Callable] = []

        # Core components (use shared orchestrator singleton!)
        self.task_planner = TaskPlanner() if TASK_PLANNER_AVAILABLE else None
        self.task_orchestrator = get_orchestrator() if TASK_CHAIN_AVAILABLE else None
        self.verifier = get_visual_verifier() if VERIFIER_AVAILABLE else None

        # Automation agents
        self.browser_agent = BrowserAutomation() if BROWSER_AUTO_AVAILABLE else None
        self.app_agent = AppAutomation() if APP_AUTO_AVAILABLE else None
        self._intent_executor = None
        self._agent_coordinator = None

        self.vlm = None
        if VLM_AVAILABLE:
            try:
                self.vlm = MultiModalAI()
            except Exception as e:
                logger.warning(f"Could not initialize MultiModalAI: {e}")

        # Persistence
        self.tracker = get_progress_tracker()

        # Per-chain cancellation & pause events
        self._cancel_events: Dict[str, threading.Event] = {}
        self._pause_events: Dict[str, threading.Event] = {}

        # Performance stats
        self.stats = {
            "total_chains": 0,
            "successful_chains": 0,
            "failed_chains": 0,
            "total_actions": 0,
            "average_duration": 0.0,
        }

        logger.info("ChainOfActionsManager initialized")

    def _get_intent_executor(self):
        if self._intent_executor is None:
            from ai_assistant.core.intent_executor import get_intent_executor
            self._intent_executor = get_intent_executor()
        return self._intent_executor

    def get_agent_coordinator(self):
        """Lazy-load MultiAgentCoordinator with registered agent definitions."""
        if self._agent_coordinator is not None:
            return self._agent_coordinator
        try:
            import ai_assistant.core.multi_agent_coordinator as mac_mod
            getter = getattr(mac_mod, "get_multi_agent_coordinator", None)
            if callable(getter):
                self._agent_coordinator = getter()
                return self._agent_coordinator

            from ai_assistant.agents.registry import AgentRegistry
            from ai_assistant.agents.loader import AgentLoader
            registry = AgentRegistry()
            AgentLoader.register_agent_definitions(registry)
            self._agent_coordinator = mac_mod.MultiAgentCoordinator(registry)
            return self._agent_coordinator
        except Exception as exc:
            logger.warning(f"MultiAgentCoordinator unavailable in ChainOfActionsManager: {exc}")
            return None

    # ========== STEP 1: LISTEN ==========

    async def create_chain(
        self,
        command: str,
        chain_id: Optional[str] = None,
        source: str = "chat",
        app_context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        auto_decompose: bool = True,
    ) -> ActionChain:
        """Create a new ActionChain from user command using canonical chain_<uuid12> IDs."""
        logger.info(f"📝 STEP 1 - LISTEN: Received command: {command}")

        cid = chain_id or generate_chain_id()
        chain = ActionChain(
            id=cid,
            command=command,
            status=ChainStatus.PENDING,
            created_at=datetime.now(),
            source=source,
            app_context=app_context,
            metadata=dict(metadata or {}),
        )

        with self._lock:
            self.active_chains[chain.id] = chain
            self._cancel_events.setdefault(chain.id, threading.Event())
            self._pause_events.setdefault(chain.id, threading.Event())
            self.stats["total_chains"] += 1

        self.tracker.start_chain(
            chain.id,
            command,
            0,
            source=source,
            app_context=app_context,
            status=ChainStatus.PENDING.value,
            metadata=chain.metadata,
        )
        await self._notify_progress(chain, event_type="chain.started", message=f"Chain created for: {command}")

        if auto_decompose:
            await self.decompose_command(chain)
            chain.status = ChainStatus.PENDING

        logger.info(f"Created chain {chain.id}")
        return chain

    # ========== STEP 2: PROCESS & BREAKDOWN ==========

    async def decompose_command(self, chain: ActionChain) -> List[Action]:
        """Decompose command into executable Action DAG nodes with remapped dependencies."""
        logger.info(f"⚙️ STEP 2 - PROCESS & BREAKDOWN: Decomposing '{chain.command}'")

        chain.status = ChainStatus.PLANNING
        await self._notify_progress(chain, event_type="chain_progress", message="Planning actions...")

        actions: List[Action] = []

        # 0. Check Workflow Templates first
        template_actions = self._check_workflow_templates(chain.command)
        if template_actions:
            actions = template_actions
            logger.info(f"✅ Decomposed into {len(actions)} actions using Workflow Template")

        # 1. Deterministic MultiStepCommandParser + IntentRouter (handles mixed delimiters,
        # Hindi/Hinglish, quotes, parallel groups, fallbacks, and all 14 specialized agents)
        if not actions:
            parser_actions, has_confident_intent = self._parser_decomposition(chain.command)
            if has_confident_intent and parser_actions:
                actions = parser_actions
                logger.info(f"✅ Decomposed into {len(actions)} actions using MultiStepCommandParser")

        # 2. TaskPlanner fallback for unstructured high-level requests
        if not actions and self.task_planner:
            try:
                plan = self.task_planner.create_plan(chain.command)
                chain.requires_confirmation = getattr(plan, "requires_confirmation", False)
                chain.safety_level = getattr(plan, "safety_level", "safe")

                planned_list = list(getattr(plan, "actions", None) or [])
                if planned_list:
                    id_map: Dict[str, str] = {}
                    raw_pairs: List[Tuple[Any, Action]] = []
                    for idx, planned_action in enumerate(planned_list, start=1):
                        type_val = (
                            planned_action.type.value
                            if hasattr(planned_action.type, "value")
                            else str(planned_action.type)
                        )
                        params = dict(getattr(planned_action, "parameters", None) or {})
                        params["sub_type"] = type_val
                        new_id = generate_action_id()
                        old_id = getattr(planned_action, "id", None) or f"action_{idx}"
                        id_map[str(old_id)] = new_id
                        id_map[str(idx)] = new_id

                        act = Action(
                            id=new_id,
                            step=idx,
                            intent=str(params.get("intent") or type_val),
                            type=self._map_action_type(type_val),
                            description=planned_action.description,
                            parameters=params,
                            dependencies=[],
                            output_key=f"step_{idx}",
                        )
                        raw_pairs.append((planned_action, act))

                    for planned_action, act in raw_pairs:
                        orig_deps = list(getattr(planned_action, "dependencies", None) or [])
                        act.dependencies = [id_map.get(str(d), str(d)) for d in orig_deps if d is not None]
                        actions.append(act)

                    logger.info(f"✅ Decomposed into {len(actions)} actions using TaskPlanner")
            except Exception as e:
                logger.warning(f"TaskPlanner failed, falling back: {e}")

        # 3. Final fallback (parser even if unknown -> MultiAgentCoordinator, else simple decomposition)
        if not actions:
            parser_actions, _ = self._parser_decomposition(chain.command)
            if parser_actions:
                actions = parser_actions
            else:
                actions = await self._simple_decomposition(chain.command)

        chain.actions = actions
        chain.requires_confirmation = chain.requires_confirmation or any(a.requires_confirmation for a in actions)
        with self._lock:
            self.stats["total_actions"] += len(actions)

        # Persist chain plan safely with status="pending" (never prematurely "running")
        self.tracker.start_chain(
            chain.id,
            chain.command,
            len(actions),
            source=chain.source,
            app_context=chain.app_context,
            status=ChainStatus.PLANNING.value,
            steps=[a.to_dict() for a in actions],
            metadata=chain.metadata,
        )
        for idx, action in enumerate(actions, start=1):
            action.step = action.step or idx
            self.tracker.record_action_planned(
                action.id,
                chain.id,
                action.description,
                action.type.value,
                step_index=action.step,
                intent=action.intent,
                agent_id=action.agent_id,
                dependencies=action.dependencies,
                output_key=action.output_key,
            )

        await self._notify_progress(
            chain,
            event_type="chain.planned",
            message=f"Planned {len(actions)} action(s)",
            include_actions=True,
        )
        return actions

    def _parser_decomposition(self, command: str) -> Tuple[List[Action], bool]:
        """Decompose command via MultiStepCommandParser into canonical Action DAG nodes."""
        try:
            from ai_assistant.ai.multi_step_parser import MultiStepCommandParser
            parser = MultiStepCommandParser()
            steps = parser.parse_command(command)
            if not steps:
                return [], False

            step_to_action_id: Dict[int, str] = {}
            actions: List[Action] = []
            confident = any(s.intent not in ("unknown", "conversational", "info_query") for s in steps)

            for s in steps:
                aid = generate_action_id()
                step_to_action_id[s.step] = aid

            for s in steps:
                act_type = self._map_intent_to_action_type(s.intent, s.execution_target)
                mapped_deps = [step_to_action_id[d] for d in (s.dependencies or []) if d in step_to_action_id]
                params = dict(s.params or {})
                params.setdefault("intent", s.intent)
                if s.execution_target == "agent" or s.intent == "unknown":
                    params.setdefault("execution_target", "agent")
                    params.setdefault("description", s.description or s.original_text)
                if s.agent_id:
                    params.setdefault("agent_id", s.agent_id)
                if s.capability:
                    params.setdefault("capability", s.capability)

                actions.append(
                    Action(
                        id=step_to_action_id[s.step],
                        step=s.step,
                        intent=s.intent if s.intent != "unknown" else "agent_task",
                        type=act_type,
                        description=s.description or s.original_text or s.intent,
                        parameters=params,
                        dependencies=mapped_deps,
                        agent_id=s.agent_id,
                        capability=s.capability,
                        parallel_group=s.parallel_group,
                        requires_confirmation=bool(s.requires_confirmation),
                        output_key=s.output_key or f"step_{s.step}",
                        condition=s.condition,
                        on_failure=s.on_failure or "abort",
                        fallback_action_id=(
                            step_to_action_id.get(s.fallback_step)
                            if getattr(s, "fallback_step", None)
                            else None
                        ),
                    )
                )

            return actions, confident
        except Exception as exc:
            logger.debug(f"Parser decomposition fallback error: {exc}")
            return [], False

    def _map_intent_to_action_type(self, intent: str, execution_target: str = "local") -> ActionType:
        if intent == "wait":
            return ActionType.WAIT
        if intent in ("agent_research", "agent_deep_research"):
            return ActionType.RESEARCH
        if intent in ("agent_communication", "send_message"):
            return ActionType.COMMUNICATION
        if intent in ("agent_database",):
            return ActionType.DATABASE
        if intent in ("agent_web", "youtube_search", "youtube_history", "search_web"):
            return ActionType.BROWSER
        if intent in ("find_file", "open_folder", "move_file", "send_file", "create_folder", "create_document", "agent_file"):
            return ActionType.FILE
        if intent in ("play_media", "play_video", "skip_time", "download_media", "agent_audio", "agent_video"):
            return ActionType.MEDIA
        if intent in ("open_app", "close_app", "type_text"):
            return ActionType.APP
        if intent in (
            "set_brightness", "brightness_control", "dark_mode_toggle", "wifi_toggle", "toggle_wifi",
            "bluetooth_toggle", "volume_control", "battery_status", "list_running_apps",
            "check_taskbar", "open_settings", "system_control", "analyze_screen",
        ):
            return ActionType.SYSTEM
        if execution_target == "agent" or intent.startswith("agent_"):
            return ActionType.AGENT
        return ActionType.CUSTOM

    def _check_workflow_templates(self, command: str) -> Optional[List[Action]]:
        """Check if command matches a YAML workflow template using relative templates path."""
        try:
            import yaml
        except ImportError:
            return None

        templates_dir = Path(__file__).resolve().parents[1] / "workflow" / "templates"
        if not templates_dir.is_dir():
            return None

        cmd_lower = command.lower()
        for file in templates_dir.glob("*.yaml"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    template = yaml.safe_load(f) or {}
                triggers = template.get("triggers", []) or []
                if any(str(t).lower() in cmd_lower for t in triggers):
                    logger.info(f"Matched workflow template: {template.get('name')}")
                    actions: List[Action] = []
                    prev_id: Optional[str] = None
                    for idx, step in enumerate(template.get("steps", []) or [], start=1):
                        action_type_str = str(step.get("action") or "SYSTEM")
                        raw_params = dict(step.get("parameters") or step.get("params") or {})
                        raw_params.setdefault("sub_type", action_type_str)
                        aid = generate_action_id()
                        deps = list(step.get("dependencies") or ([prev_id] if prev_id else []))
                        actions.append(
                            Action(
                                id=aid,
                                step=idx,
                                intent=str(step.get("intent") or action_type_str.lower()),
                                type=self._map_action_type(action_type_str),
                                description=str(step.get("description") or f"Template step: {action_type_str}"),
                                parameters=raw_params,
                                dependencies=deps,
                                agent_id=step.get("agent_id"),
                                capability=step.get("capability"),
                                output_key=step.get("output_key") or f"step_{idx}",
                            )
                        )
                        prev_id = aid
                    return actions or None
            except Exception as e:
                logger.error(f"Failed to parse template {file}: {e}")

        return None

    async def _simple_decomposition(self, command: str) -> List[Action]:
        """Fallback decomposition when parser & planner return no steps."""
        logger.info("Using simple decomposition fallback")
        return [
            Action(
                id=generate_action_id(),
                step=1,
                intent="agent_task",
                type=ActionType.AGENT,
                description=command,
                parameters={"command": command, "description": command, "execution_target": "agent"},
                output_key="step_1",
            )
        ]

    def _map_action_type(self, planner_type: str) -> ActionType:
        """Map TaskPlanner or template action type string to ActionType enum."""
        mapping = {
            "browser_navigate": ActionType.BROWSER,
            "browser_click": ActionType.BROWSER,
            "browser_type": ActionType.BROWSER,
            "browser_scroll": ActionType.BROWSER,
            "browser_select": ActionType.BROWSER,
            "app_open": ActionType.APP,
            "app_close": ActionType.APP,
            "app_interact": ActionType.APP,
            "system_type": ActionType.APP,
            "system_press": ActionType.APP,
            "wait": ActionType.WAIT,
            "file_create": ActionType.FILE,
            "file_read": ActionType.FILE,
            "system_command": ActionType.SYSTEM,
            "system": ActionType.SYSTEM,
            "agent": ActionType.AGENT,
            "research": ActionType.RESEARCH,
            "communication": ActionType.COMMUNICATION,
            "media": ActionType.MEDIA,
            "database": ActionType.DATABASE,
            "api": ActionType.API,
        }
        return mapping.get(str(planner_type).lower().strip(), ActionType.CUSTOM)

    # ========== STEP 3: IDENTIFY ==========

    async def identify_executors(self, chain: ActionChain) -> Dict[str, str]:
        """Identify which execution engine/agent will run each action."""
        logger.info(f"🔍 STEP 3 - IDENTIFY: Determining executors for {len(chain.actions)} actions")

        executor_map: Dict[str, str] = {}
        for action in chain.actions:
            if action.agent_id or action.type in (ActionType.AGENT, ActionType.RESEARCH, ActionType.DATABASE):
                executor_map[action.id] = f"MultiAgent:{action.agent_id or 'auto'}"
            elif action.intent and action.intent in self._get_intent_executor().supported_intents:
                executor_map[action.id] = f"IntentExecutor:{action.intent}"
            elif action.type == ActionType.BROWSER:
                executor_map[action.id] = "BrowserAutomation"
            elif action.type == ActionType.APP:
                executor_map[action.id] = "AppAutomation"
            elif action.type == ActionType.FILE:
                executor_map[action.id] = "FileOperations"
            elif action.type == ActionType.WAIT:
                executor_map[action.id] = "TimerWait"
            elif action.type == ActionType.SYSTEM:
                executor_map[action.id] = "SystemControl"
            else:
                executor_map[action.id] = "MultiAgentCoordinator"

        logger.info(f"Executor mapping: {executor_map}")
        return executor_map

    # ========== RUNTIME CHAIN CONTROL (PAUSE / RESUME / CANCEL) ==========

    def cancel_chain(self, chain_id: str, reason: str = "Cancelled by user") -> bool:
        """Cancel an active chain cleanly and persist cancelled status."""
        with self._lock:
            chain = self.active_chains.get(chain_id)
            if not chain:
                return False
            chain.status = ChainStatus.CANCELLED
            if reason:
                chain.errors.append(reason)
            ev = self._cancel_events.setdefault(chain_id, threading.Event())
            ev.set()
            pause_ev = self._pause_events.get(chain_id)
            if pause_ev:
                pause_ev.clear()

        for act in chain.actions:
            if act.status in ("pending", "running"):
                act.status = "cancelled"
                self.tracker.update_action_status(act.id, "cancelled", error=reason)

        self.tracker.update_chain_status(
            chain.id,
            ChainStatus.CANCELLED.value,
            chain.progress_percentage,
            chain.actions_completed,
            failed_actions=chain.actions_failed,
        )
        return True

    def pause_chain(self, chain_id: str) -> bool:
        """Pause an active chain cleanly."""
        with self._lock:
            chain = self.active_chains.get(chain_id)
            if not chain or _normalize_status_value(chain.status) in (
                ChainStatus.CANCELLED.value,
                ChainStatus.COMPLETED.value,
                ChainStatus.FAILED.value,
            ):
                return False
            chain.status = ChainStatus.PAUSED
            self._pause_events.setdefault(chain_id, threading.Event()).set()

        self.tracker.update_chain_status(
            chain.id,
            ChainStatus.PAUSED.value,
            chain.progress_percentage,
            chain.actions_completed,
            failed_actions=chain.actions_failed,
        )
        return True

    def resume_chain(self, chain_id: str, user_input: Any = None, action: str = "proceed") -> bool:
        """Resume a paused or waiting_confirmation chain (or cancel if action=='cancel')."""
        if str(action).lower() == "cancel":
            return self.cancel_chain(chain_id, reason="Cancelled at confirmation/resume")

        with self._lock:
            chain = self.active_chains.get(chain_id)
            if not chain:
                return False
            if user_input is not None:
                chain.context_vars["user_input"] = user_input
            if chain.status in (ChainStatus.PAUSED, ChainStatus.WAITING_CONFIRMATION):
                chain.status = ChainStatus.EXECUTING
            pause_ev = self._pause_events.get(chain_id)
            if pause_ev:
                pause_ev.clear()

        self.tracker.update_chain_status(
            chain.id,
            ChainStatus.EXECUTING.value,
            chain.progress_percentage,
            chain.actions_completed,
            failed_actions=chain.actions_failed,
        )
        return True

    # ========== VARIABLE RESOLUTION ==========

    def _record_context_output(self, chain: ActionChain, action: Action, result: Dict[str, Any]):
        """Record outputs for {prev.output}, {prev.path}, {step_N.output}, and {output_key}."""
        out_val = (
            result.get("output")
            or result.get("result")
            or result.get("output_path")
            or result.get("message")
            or ""
        )
        path_val = result.get("output_path") or (
            result.get("result") if isinstance(result.get("result"), str) and ("\\" in result["result"] or "/" in result["result"]) else ""
        )
        entry = {
            "output": out_val,
            "result": result.get("result") if result.get("result") is not None else out_val,
            "path": path_val,
            "output_path": result.get("output_path") or path_val,
            "text": str(out_val),
        }
        with self._lock:
            chain.context_vars["prev"] = entry
            if action.step:
                chain.context_vars[f"step_{action.step}"] = entry
                chain.context_vars[f"step{action.step}"] = entry
                chain.context_vars[str(action.step)] = entry
            if action.output_key:
                chain.context_vars[action.output_key] = entry
            chain.context_vars[action.id] = entry
            if path_val:
                chain.context_vars["found_file_path"] = path_val
                chain.context_vars["last_file"] = path_val
            if out_val:
                chain.final_output = out_val

    def _resolve_action_placeholders(self, obj: Any, chain: ActionChain) -> Any:
        if isinstance(obj, str):
            def _repl(match: re.Match) -> str:
                expr = match.group(1).strip()
                with self._lock:
                    if "." in expr:
                        root, attr = expr.split(".", 1)
                        if root == "context":
                            val = chain.context_vars.get(attr)
                            return str(val) if val is not None else match.group(0)
                        bucket = chain.context_vars.get(root)
                        if isinstance(bucket, dict) and attr in bucket:
                            return str(bucket[attr])
                    elif expr in chain.context_vars:
                        val = chain.context_vars[expr]
                        return str(val.get("output", "") if isinstance(val, dict) else val)
                return match.group(0)

            return re.sub(r'\{([A-Za-z0-9_.\-]+)\}', _repl, obj)
        if isinstance(obj, dict):
            return {k: self._resolve_action_placeholders(v, chain) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._resolve_action_placeholders(v, chain) for v in obj]
        return obj

    def _is_chain_cancelled(self, chain: ActionChain) -> bool:
        status_str = _normalize_status_value(chain.status)
        if status_str == ChainStatus.CANCELLED.value:
            chain.status = ChainStatus.CANCELLED
            return True
        ev = self._cancel_events.get(chain.id)
        if ev and ev.is_set():
            chain.status = ChainStatus.CANCELLED
            return True
        if self.task_orchestrator and self.task_orchestrator.is_stopped():
            chain.status = ChainStatus.CANCELLED
            return True
        return False

    def _is_chain_paused(self, chain: ActionChain) -> bool:
        status_str = _normalize_status_value(chain.status)
        pause_ev = self._pause_events.get(chain.id)
        return status_str == ChainStatus.PAUSED.value or bool(pause_ev and pause_ev.is_set())

    # ========== STEP 4: ASSIGN & EXECUTE ==========

    async def execute_chain(self, chain_id: str) -> ExecutionReport:
        """Execute all actions in a chain (DAG waves, parallel steps, pause/resume/cancel)."""
        chain = self.active_chains.get(chain_id)
        if not chain:
            raise ValueError(f"Chain {chain_id} not found")

        logger.info(f"🚀 STEP 4 - ASSIGN & EXECUTE: Starting execution of chain {chain_id}")

        # Confirmation pause gate if unsafe/destructive command flagged
        if getattr(chain, "requires_confirmation", False):
            logger.warning(f"⚠️ Chain {chain_id} requires user confirmation.")
            chain.status = ChainStatus.WAITING_CONFIRMATION
            self.tracker.update_chain_status(chain.id, chain.status.value, chain.progress_percentage, chain.actions_completed)
            await self._notify_progress(chain, event_type="chain_progress", message="Waiting for user confirmation")

            while _normalize_status_value(chain.status) in (
                ChainStatus.PAUSED.value,
                ChainStatus.WAITING_CONFIRMATION.value,
            ):
                if self._is_chain_cancelled(chain):
                    break
                await asyncio.sleep(0.2)

            if self._is_chain_cancelled(chain):
                logger.warning(f"🛑 Chain {chain_id} was cancelled during confirmation.")
                return await self._finalize_chain(chain, 0, 0, [])

        if self._is_chain_cancelled(chain):
            return await self._finalize_chain(chain, 0, 0, [])

        chain.status = ChainStatus.EXECUTING
        chain.started_at = chain.started_at or datetime.now()
        self.tracker.update_chain_status(chain.id, ChainStatus.EXECUTING.value, chain.progress_percentage, chain.actions_completed)
        await self._notify_progress(chain, event_type="chain.started", message=f"Executing {len(chain.actions)} step(s)")

        completed = 0
        failed = 0
        action_results: List[Dict[str, Any]] = []

        try:
            while True:
                # 1. Cancellation check
                if self._is_chain_cancelled(chain):
                    logger.warning(f"🛑 Chain {chain.id} CANCELLED mid-execution. Aborting.")
                    break

                # 2. Pause wait loop (never exits into VERIFYING while paused!)
                if self._is_chain_paused(chain):
                    chain.status = ChainStatus.PAUSED
                    self.tracker.update_chain_status(chain.id, ChainStatus.PAUSED.value, chain.progress_percentage, chain.actions_completed)
                    await self._notify_progress(chain, event_type="chain.paused", message="Execution paused")
                    while self._is_chain_paused(chain) and not self._is_chain_cancelled(chain):
                        await asyncio.sleep(0.1)
                    if self._is_chain_cancelled(chain):
                        break
                    chain.status = ChainStatus.EXECUTING
                    self.tracker.update_chain_status(chain.id, ChainStatus.EXECUTING.value, chain.progress_percentage, chain.actions_completed)
                    await self._notify_progress(chain, event_type="chain.resumed", message="Execution resumed")

                pending_actions = [a for a in chain.actions if a.status == "pending"]
                if not pending_actions:
                    break

                # 3. Skip permanently blocked actions whose non-fallback deps failed/skipped
                progressed = False
                for act in list(pending_actions):
                    state_check = self._dependency_state(act, chain)
                    if state_check == "blocked_failed":
                        act.status = "skipped"
                        act.error = "Upstream dependency failed"
                        self.tracker.update_action_status(act.id, "skipped", error=act.error)
                        progressed = True
                    elif state_check == "skip_fallback":
                        act.status = "skipped"
                        act.result = {"success": True, "skipped": True, "message": "Primary step succeeded"}
                        self.tracker.update_action_status(act.id, "skipped", 100.0, act.result)
                        progressed = True
                if progressed:
                    pending_actions = [a for a in chain.actions if a.status == "pending"]
                    if not pending_actions:
                        break

                # 4. Collect ready actions for current DAG wave
                ready_actions = [a for a in pending_actions if self._dependency_state(a, chain) == "ready"]
                if not ready_actions:
                    # Fallback safeguard if graph has dangling dep IDs
                    ready_actions = [pending_actions[0]]

                # Update current_action_index for progress reporting
                try:
                    chain.current_action_index = chain.actions.index(ready_actions[0])
                except ValueError:
                    pass

                # Run ready wave (parallel via asyncio.gather when >1 action ready)
                async def _run_one(act: Action) -> Tuple[Action, bool, Dict[str, Any], Optional[str]]:
                    act.parameters = self._resolve_action_placeholders(copy.deepcopy(act.parameters or {}), chain)
                    act.status = "running"
                    act.progress = 10
                    act.started_at = datetime.now()
                    if act.agent_id:
                        chain.current_agent = act.agent_id
                    self.tracker.record_action_start(
                        act.id,
                        chain.id,
                        act.description,
                        act.type.value,
                        step_index=act.step,
                        intent=act.intent,
                        agent_id=act.agent_id,
                        status="running",
                    )
                    await self._notify_progress(
                        chain,
                        event_type="chain.step_started",
                        step_id=act.id,
                        current_action=act.description,
                        current_agent=act.agent_id,
                    )

                    try:
                        res = await self._execute_action(act, chain)
                        if isinstance(res, dict) and res.get("success") is False:
                            err_msg = str(res.get("error") or res.get("message") or "Action returned failure")
                            raise RuntimeError(err_msg)

                        # Optional VLM check for UI-heavy actions when Gemini is enabled
                        verification_failed = False
                        verification = None
                        if self.vlm and act.type in (ActionType.BROWSER, ActionType.APP):
                            try:
                                from ai_assistant.core.intent_executor import _is_gemini_active_and_configured
                                if _is_gemini_active_and_configured():
                                    verification = await self._verify_action_with_vlm(act)
                                    if verification and verification.get("verified") is False:
                                        verification_failed = True
                            except Exception:
                                pass

                        if verification_failed and verification:
                            res["visual_verification"] = verification
                            if self.task_planner:
                                repairs = await self._handle_verification_failure(act, verification)
                                if repairs:
                                    idx = chain.actions.index(act)
                                    chain.actions[idx + 1 : idx + 1] = repairs
                                    act.status = "completed_with_warning"
                                else:
                                    act.status = "completed_with_warning"
                            else:
                                act.status = "completed_with_warning"
                        else:
                            act.status = "completed"

                        act.progress = 100
                        act.result = res
                        act.completed_at = datetime.now()
                        act.duration_seconds = (act.completed_at - act.started_at).total_seconds()
                        if isinstance(res, dict) and res.get("agent_id") and not act.agent_id:
                            act.agent_id = res["agent_id"]

                        self.tracker.update_action_status(
                            act.id,
                            act.status,
                            100.0,
                            res,
                            agent_id=act.agent_id,
                            duration_seconds=act.duration_seconds,
                        )
                        return act, True, res, None

                    except Exception as exc:
                        act.status = "failed"
                        act.error = str(exc)
                        act.completed_at = datetime.now()
                        act.duration_seconds = (act.completed_at - act.started_at).total_seconds() if act.started_at else 0.0
                        self.tracker.update_action_status(
                            act.id,
                            "failed",
                            error=str(exc),
                            duration_seconds=act.duration_seconds,
                        )
                        return act, False, {"success": False, "error": str(exc)}, str(exc)

                if len(ready_actions) == 1:
                    outcomes = [await _run_one(ready_actions[0])]
                else:
                    outcomes = list(await asyncio.gather(*[_run_one(a) for a in ready_actions]))

                abort_chain = False
                for act, ok, res, err in outcomes:
                    if ok:
                        with self._lock:
                            chain.actions_completed += 1
                            completed += 1
                            chain.results[act.id] = res
                            self._record_context_output(chain, act, res if isinstance(res, dict) else {"result": res})
                            action_results.append({
                                "action_id": act.id,
                                "step": act.step,
                                "intent": act.intent,
                                "agent_id": act.agent_id,
                                "description": act.description,
                                "result": res,
                                "duration": act.duration_seconds,
                            })
                        await self._notify_progress(
                            chain,
                            event_type="chain.step_completed",
                            step_id=act.id,
                            current_action=act.description,
                            current_agent=act.agent_id,
                        )
                    else:
                        with self._lock:
                            chain.actions_failed += 1
                            failed += 1
                            chain.errors.append(f"Action {act.id}: {err}")
                        await self._notify_progress(
                            chain,
                            event_type="chain.step_failed",
                            step_id=act.id,
                            current_action=act.description,
                            current_agent=act.agent_id,
                            error=err,
                        )
                        if act.on_failure == "abort":
                            abort_chain = True

                self.tracker.update_chain_status(
                    chain.id,
                    ChainStatus.EXECUTING.value,
                    chain.progress_percentage,
                    chain.actions_completed,
                    failed_actions=chain.actions_failed,
                )

                if abort_chain:
                    break

            if not self._is_chain_cancelled(chain) and failed == 0:
                chain.status = ChainStatus.VERIFYING
                await self._notify_progress(chain, event_type="chain_progress", message="Verifying results...")

        except Exception as e:
            logger.error(f"Chain execution failed: {e}", exc_info=True)
            if not self._is_chain_cancelled(chain):
                chain.status = ChainStatus.FAILED
                chain.errors.append(str(e))

        return await self._finalize_chain(chain, completed, failed, action_results)

    def _dependency_state(self, action: Action, chain: ActionChain) -> str:
        """
        Inspect dependency states for DAG scheduling:
        - 'ready': dependencies satisfied (or failed when condition == 'on_failure')
        - 'waiting': at least one dependency still pending/running
        - 'skip_fallback': condition == 'on_failure' and primary dependency succeeded
        - 'blocked_failed': required upstream dependency failed/skipped/cancelled
        """
        if not action.dependencies:
            return "ready"

        dep_actions = []
        for dep_id in action.dependencies:
            dep_act = next((a for a in chain.actions if a.id == dep_id), None)
            if dep_act is None:
                continue
            dep_actions.append(dep_act)

        if not dep_actions:
            return "ready"

        if any(a.status in ("pending", "running") for a in dep_actions):
            return "waiting"

        if action.condition == "on_failure":
            if any(a.status == "failed" for a in dep_actions):
                return "ready"
            return "skip_fallback"

        if all(a.status in ("completed", "completed_with_warning") for a in dep_actions):
            return "ready"

        return "blocked_failed"

    async def _check_dependencies(self, action: Action, chain: ActionChain) -> bool:
        """Backward-compatible dependency readiness check."""
        return self._dependency_state(action, chain) == "ready"

    async def _execute_action(self, action: Action, chain: ActionChain) -> Any:
        """Execute a single Action cleanly across MultiAgentCoordinator, IntentExecutor, or automation engines."""
        logger.info(f"🚀 Executing action: {action.description} (Type: {action.type.value}, Intent: {action.intent})")

        params = dict(action.parameters or {})
        params.setdefault("chain_id", chain.id)

        # 1. Explicit Wait Action
        if action.type == ActionType.WAIT or action.intent == "wait":
            secs = max(0.0, min(60.0, float(params.get("seconds", 1.0))))
            await asyncio.sleep(secs)
            msg = f"Waited {secs:.2f}s" if secs % 1 else f"Waited {int(secs)}s"
            return {"success": True, "intent": "wait", "output": msg, "result": msg}

        # 2. Specialized Multi-Agent Execution
        if (
            action.type in (ActionType.AGENT, ActionType.RESEARCH, ActionType.DATABASE)
            or action.agent_id
            or (action.intent and action.intent.startswith("agent_"))
            or params.get("execution_target") == "agent"
        ):
            return await self._execute_agent_action(action, chain, params)

        # 3. Real IntentExecutor dispatch for all local intents & create_document/file ops
        executor = self._get_intent_executor()
        if action.intent and action.intent in executor.supported_intents:
            ctx_proxy = self.task_orchestrator.context_manager if self.task_orchestrator else None
            return await asyncio.to_thread(executor.execute, action.intent, params, ctx_proxy)

        # 4. BrowserAutomation / AppAutomation / FileOperations explicit planner sub_types
        sub_type = str(params.get("sub_type") or "").lower()
        if action.type == ActionType.BROWSER and self.browser_agent and sub_type.startswith("browser_"):
            return await self._execute_browser_action(action)
        if action.type == ActionType.APP and self.app_agent and sub_type.startswith(("app_", "system_type", "system_press")):
            return await self._execute_app_action(action)
        if action.type == ActionType.FILE:
            return await self._execute_file_action(action, chain)

        # 5. Final intelligent delegation to MultiAgentCoordinator instead of sleeping/simulating
        return await self._execute_agent_action(action, chain, params)

    async def _execute_agent_action(
        self,
        action: Action,
        chain: ActionChain,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute an action directly via async MultiAgentCoordinator."""
        coord = self.get_agent_coordinator()
        if coord is None:
            raise RuntimeError("MultiAgentCoordinator is unavailable")

        preferred_agent_id = action.agent_id or params.get("agent_id")
        capability = action.capability or params.get("capability")
        description = (
            params.get("description")
            or params.get("topic")
            or params.get("task")
            or params.get("prompt")
            or params.get("query")
            or action.description
        )
        chain_ctx = {**chain.context_vars, "command": chain.command, "chain_id": chain.id}

        if hasattr(coord, "execute_step"):
            task_result = await coord.execute_step(
                description=str(description),
                params=params,
                preferred_agent_id=preferred_agent_id,
                capability=capability,
                chain_context=chain_ctx,
                chain_id=chain.id,
            )
        else:
            from ai_assistant.agents.models import Task
            task = Task(
                description=str(description),
                params=dict(params),
                target_agent_id=preferred_agent_id,
                required_capabilities=[capability] if capability else [],
                context=chain_ctx,
                chain_id=chain.id,
            )
            if preferred_agent_id and hasattr(coord, "execute_agent"):
                task_result = await coord.execute_agent(preferred_agent_id, task)
            elif preferred_agent_id and getattr(coord, "registry", None):
                agent = coord.registry.get_agent(preferred_agent_id)
                if agent is not None:
                    task_result = await agent.execute(task)
                else:
                    task_result = await coord.execute_task(task)
            else:
                task_result = await coord.execute_task(task)

        ok = bool(getattr(task_result, "success", False))
        data = dict(getattr(task_result, "data", None) or {})
        out_path = getattr(task_result, "output_path", None) or data.get("output_path")
        output_val = (
            data.get("output")
            or data.get("summary")
            or data.get("text")
            or data.get("message")
            or out_path
            or (data if data else action.description)
        )
        used_agent = getattr(task_result, "agent_id", None) or preferred_agent_id
        if used_agent:
            action.agent_id = used_agent

        res = {
            "success": ok,
            "intent": action.intent or "agent_task",
            "agent_id": used_agent,
            "result": output_val,
            "output": output_val,
            "output_path": out_path,
            "data": data,
        }
        if getattr(task_result, "error", None):
            res["error"] = task_result.error
        return res

    async def _execute_browser_action(self, action: Action) -> Dict[str, Any]:
        """Execute browser action using BrowserAutomation."""
        sub_type = action.parameters.get("sub_type", "").lower()
        params = action.parameters

        if not self.browser_agent:
            raise RuntimeError("Browser Agent not initialized")

        def _run_browser_task():
            if not self.browser_agent.driver:
                self.browser_agent.start_browser()

            if "navigate" in sub_type or "open" in sub_type:
                url = params.get("url", "")
                if not url:
                    for w in params.get("command", "").split():
                        if "." in w and not w.endswith("."):
                            url = w
                            break
                    if not url:
                        raise ValueError("No URL provided for navigation")
                success = self.browser_agent.navigate(url)
                return {"success": success, "output": f"Navigated to {self.browser_agent.current_url}"}

            elif "click" in sub_type:
                desc = params.get("element_description") or params.get("selector") or action.description
                el = self.browser_agent.find_element_by_description(desc)
                if el:
                    el.click()
                    return {"success": True, "output": f"Clicked {desc}"}
                return {"success": False, "error": f"Element not found: {desc}"}

            elif "type" in sub_type:
                text = params.get("text", "")
                desc = params.get("element_description") or "input field"
                el = self.browser_agent.find_element_by_description(desc)
                if el:
                    el.clear()
                    el.send_keys(text)
                    return {"success": True, "output": f"Typed '{text}' into {desc}"}
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.browser_agent.driver)
                actions.send_keys(text).perform()
                return {"success": True, "output": f"Typed '{text}' into active element"}

            elif "scroll" in sub_type:
                direction = params.get("direction", "down")
                amount = params.get("amount", 500)
                script = f"window.scrollBy(0, {amount})" if direction == "down" else f"window.scrollBy(0, -{amount})"
                self.browser_agent.driver.execute_script(script)
                return {"success": True, "output": f"Scrolled {direction}"}

            return {"success": True, "message": "Browser action processed"}

        return await asyncio.to_thread(_run_browser_task)

    async def _execute_app_action(self, action: Action) -> Dict[str, Any]:
        """Execute app action using AppAutomation."""
        sub_type = action.parameters.get("sub_type", "").lower()
        params = action.parameters

        def _run_app_task():
            if "open" in sub_type:
                app_name = params.get("app_name") or params.get("name") or params.get("target")
                if not app_name and "command" in params:
                    app_name = params["command"].replace("open", "").strip()
                if app_name:
                    success = self.app_agent.open_app(app_name)
                    return {"success": success, "output": f"Opened {app_name}"}
                return {"success": False, "error": "App name missing"}
            elif "type" in sub_type or "system_type" in sub_type:
                text = params.get("text", "")
                success = self.app_agent.type_text(text)
                return {"success": success, "output": f"Typed: {text}"}
            elif "press" in sub_type:
                key = params.get("key", "enter")
                success = self.app_agent.press_key(key)
                return {"success": success, "output": f"Pressed: {key}"}
            return {"success": True, "message": "App action processed"}

        return await asyncio.to_thread(_run_app_task)

    async def _execute_file_action(self, action: Action, chain: Optional[ActionChain] = None) -> Dict[str, Any]:
        """Execute real file action via IntentExecutor or FileManagerAgent."""
        executor = self._get_intent_executor()
        params = dict(action.parameters or {})
        sub_type = str(params.get("sub_type") or action.intent or "").lower()

        if action.intent in executor.supported_intents:
            ctx_proxy = self.task_orchestrator.context_manager if self.task_orchestrator else None
            return await asyncio.to_thread(executor.execute, action.intent, params, ctx_proxy)

        if "create" in sub_type or "doc" in sub_type:
            return await asyncio.to_thread(executor.execute, "create_document", params, None)

        return await self._execute_agent_action(
            action,
            chain or ActionChain(id="temp", command=action.description),
            {**params, "agent_id": action.agent_id or "file-001"},
        )

    def _infer_intent(self, action: Action) -> str:
        """Infer intent from action type."""
        if action.intent:
            return action.intent
        if action.type == ActionType.APP:
            return "open_app"
        elif action.type == ActionType.BROWSER:
            return "search_web"
        elif action.type == ActionType.FILE:
            return "create_document"
        else:
            return "agent_task"

    # ========== STEP 5: TRACK PROGRESS ==========

    async def get_progress(
        self,
        chain_id: str,
        event_type: str = "chain_progress",
        step_id: Optional[str] = None,
        current_action: Optional[str] = None,
        current_agent: Optional[str] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
        include_actions: bool = False,
    ) -> ProgressReport:
        """Get real-time progress report for chain."""
        chain = self.active_chains.get(chain_id) or self.completed_chains.get(chain_id)
        if not chain:
            raise ValueError(f"Chain {chain_id} not found")

        cur_action_desc = current_action
        cur_progress = 0
        cur_agent = current_agent or chain.current_agent

        if chain.actions and 0 <= chain.current_action_index < len(chain.actions):
            action = chain.actions[chain.current_action_index]
            cur_action_desc = cur_action_desc or action.description
            cur_progress = action.progress
            cur_agent = cur_agent or action.agent_id

        return ProgressReport(
            chain_id=chain_id,
            status=_normalize_status_value(chain.status),
            progress_percentage=chain.progress_percentage,
            current_action=cur_action_desc,
            current_action_progress=cur_progress,
            completed_actions=chain.actions_completed,
            total_actions=chain.total_actions,
            elapsed_seconds=chain.duration_seconds,
            estimated_remaining_seconds=self._estimate_remaining_time(chain),
            current_agent=cur_agent,
            event_type=event_type,
            step_id=step_id,
            message=message,
            error=error,
            actions=[a.to_dict() for a in chain.actions] if include_actions else None,
        )

    def _estimate_remaining_time(self, chain: ActionChain) -> float:
        if chain.actions_completed == 0:
            return 0.0
        avg_time_per_action = chain.duration_seconds / max(1, chain.actions_completed)
        remaining_actions = max(0, chain.total_actions - chain.actions_completed)
        return avg_time_per_action * remaining_actions

    async def _notify_progress(
        self,
        chain: ActionChain,
        event_type: str = "chain_progress",
        step_id: Optional[str] = None,
        current_action: Optional[str] = None,
        current_agent: Optional[str] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
        include_actions: bool = False,
    ):
        """Notify both per-chain and global progress subscribers."""
        with self._lock:
            per_chain = list(self.progress_callbacks.get(chain.id, []))
            global_cbs = list(self.global_progress_callbacks)

        if not per_chain and not global_cbs:
            return

        try:
            progress = await self.get_progress(
                chain.id,
                event_type=event_type,
                step_id=step_id,
                current_action=current_action,
                current_agent=current_agent,
                message=message,
                error=error,
                include_actions=include_actions,
            )
        except Exception:
            return

        for callback in per_chain + global_cbs:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(progress)
                else:
                    callback(progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    def subscribe_progress(self, chain_id_or_callback: Any, callback: Optional[Callable] = None):
        """
        Subscribe to progress updates.
        Supports both:
        - subscribe_progress(chain_id, callback)
        - subscribe_progress(global_callback)
        """
        with self._lock:
            if callback is None and callable(chain_id_or_callback):
                if chain_id_or_callback not in self.global_progress_callbacks:
                    self.global_progress_callbacks.append(chain_id_or_callback)
                return

            chain_id = str(chain_id_or_callback)
            if callback is not None:
                if chain_id not in self.progress_callbacks:
                    self.progress_callbacks[chain_id] = []
                if callback not in self.progress_callbacks[chain_id]:
                    self.progress_callbacks[chain_id].append(callback)

    def subscribe_global_progress(self, callback: Callable):
        """Register a global listener invoked for all chain lifecycle & step events."""
        with self._lock:
            if callback not in self.global_progress_callbacks:
                self.global_progress_callbacks.append(callback)

    # ========== STEP 6: AGGREGATE ==========

    async def _verify_action_with_vlm(self, action: Action) -> Dict[str, Any]:
        """Verify if an action succeeded using VLM."""
        if not self.vlm:
            return {"verified": None, "reason": "VLM not initialized"}

        logger.info(f"👁️ Visually verifying: {action.description}")
        prompt = (
            f"I just executed this action: '{action.description}'. "
            "Please analyze the screen and verify if the action appears successful. "
            "Start with 'YES' if successful or 'NO' if failed."
        )
        try:
            analysis_res = await asyncio.to_thread(lambda: self.vlm.analyze_screen(prompt=prompt))
            analysis = analysis_res.get("analysis", "No analysis provided")
            head = analysis.strip().upper()[:10]
            is_success = head.startswith("YES") or ("YES" in head and not head.startswith("NO"))
            return {
                "verified": is_success,
                "vlm_analysis": analysis,
                "timestamp": analysis_res.get("timestamp"),
            }
        except Exception as e:
            logger.error(f"VLM Verification failed: {e}")
            return {"verified": None, "error": str(e)}

    async def _handle_verification_failure(self, action: Action, verification: Dict[str, Any]) -> List[Action]:
        """Ask TaskPlanner for repair steps when verification fails."""
        if not self.task_planner:
            return []
        vlm_analysis = verification.get("vlm_analysis") or verification.get("error", "Unknown error")
        error_message = verification.get("error", "Visual check mismatch")
        try:
            planner_actions = await asyncio.to_thread(
                lambda: self.task_planner.generate_repair_actions(
                    failed_action=action,
                    error_message=error_message,
                    vlm_analysis=vlm_analysis,
                )
            )
            core_actions = []
            for p_action in planner_actions or []:
                type_val = p_action.type.value if hasattr(p_action.type, "value") else str(p_action.type)
                p_action.parameters["sub_type"] = type_val
                core_actions.append(
                    Action(
                        id=generate_action_id(),
                        type=self._map_action_type(type_val),
                        description=p_action.description,
                        parameters=p_action.parameters,
                        dependencies=[],
                    )
                )
            return core_actions
        except Exception:
            return []

    async def _finalize_chain(
        self,
        chain: ActionChain,
        completed: int,
        failed: int,
        action_results: List[Dict],
    ) -> ExecutionReport:
        """Aggregate results, preserve terminal CANCELLED state, persist final report, and emit event."""
        logger.info(f"📊 STEP 6 - AGGREGATE: Finalizing chain {chain.id} ({len(action_results)} actions)")

        was_cancelled = self._is_chain_cancelled(chain) or (
            _normalize_status_value(chain.status) == ChainStatus.CANCELLED.value
        )

        # Mark untouched pending actions cancelled if aborted/cancelled
        if was_cancelled:
            for a in chain.actions:
                if a.status in ("pending", "running"):
                    a.status = "cancelled"
                    self.tracker.update_action_status(a.id, "cancelled", error="Chain cancelled")

        # Verification summary
        verification_passed = (not was_cancelled) and (failed == 0)
        verification_score = 1.0 if verification_passed and chain.actions else (
            max(0.0, completed / max(1, len(chain.actions)))
        )

        chain.verification_results.append({
            "passed": verification_passed,
            "score": round(verification_score, 3),
            "timestamp": datetime.now().isoformat(),
        })

        outputs: List[Any] = []
        errors: List[str] = list(chain.errors)
        for action in chain.actions:
            if action.status in ("completed", "completed_with_warning") and action.result is not None:
                if isinstance(action.result, dict):
                    out_val = action.result.get("output") or action.result.get("result") or action.result.get("output_path")
                    if out_val is not None:
                        outputs.append(out_val)
                else:
                    outputs.append(action.result)
            elif action.error and f"{action.description}: {action.error}" not in errors:
                errors.append(f"{action.description}: {action.error}")

        chain.completed_at = datetime.now()
        if chain.final_output is None and outputs:
            chain.final_output = outputs[-1]

        if was_cancelled:
            chain.status = ChainStatus.CANCELLED
            event_type = "chain.cancelled"
            msg = "Chain cancelled by user"
        elif failed > 0:
            chain.status = ChainStatus.FAILED
            event_type = "chain.failed"
            msg = errors[0] if errors else f"{failed} action(s) failed"
            with self._lock:
                self.stats["failed_chains"] += 1
        else:
            chain.status = ChainStatus.COMPLETED
            event_type = "chain.completed"
            msg = f"Completed {completed}/{len(chain.actions)} actions"
            with self._lock:
                self.stats["successful_chains"] += 1

        with self._lock:
            self.completed_chains[chain.id] = chain
            self.active_chains.pop(chain.id, None)
            total_duration = chain.duration_seconds
            n = max(1, self.stats["total_chains"])
            self.stats["average_duration"] = (
                (self.stats["average_duration"] * (n - 1) + total_duration) / n
            )

        self.tracker.save_chain_result(
            chain.id,
            chain.status.value,
            chain.results,
            error="; ".join(errors[:5]) if errors else None,
            final_output=chain.final_output,
            completed_actions=chain.actions_completed,
            failed_actions=chain.actions_failed,
            steps=[a.to_dict() for a in chain.actions],
        )

        await self._notify_progress(
            chain,
            event_type=event_type,
            message=msg,
            error="; ".join(errors[:3]) if errors and not verification_passed else None,
            include_actions=True,
        )

        skipped = max(0, len(chain.actions) - completed - failed)
        return ExecutionReport(
            chain_id=chain.id,
            success=(chain.status == ChainStatus.COMPLETED),
            total_actions=len(chain.actions),
            completed_actions=completed,
            failed_actions=failed,
            skipped_actions=skipped,
            duration_seconds=total_duration,
            average_action_time=total_duration / len(chain.actions) if chain.actions else 0.0,
            outputs=outputs,
            errors=errors,
            verification_passed=verification_passed,
            verification_score=verification_score,
            action_results=action_results,
            status=chain.status,
            message=msg,
            final_output=chain.final_output,
        )

    # ========== STEP 7: NOTIFY ==========

    async def notify_completion(self, report: ExecutionReport) -> str:
        """Create completion notification summary."""
        logger.info("📢 STEP 7 - NOTIFY: Creating completion notification")
        chain = self.completed_chains.get(report.chain_id) or self.active_chains.get(report.chain_id)
        if not chain:
            return report.message or "Chain execution finished"

        if report.status == ChainStatus.CANCELLED:
            return f"🛑 Task Cancelled: {chain.command} ({report.completed_actions}/{report.total_actions} actions ran)"
        if report.success:
            return (
                f"✅ Task Complete: {chain.command} — "
                f"{report.completed_actions}/{report.total_actions} actions in {report.duration_seconds:.1f}s"
            )
        err_preview = "; ".join(report.errors[:2]) if report.errors else report.message
        return f"❌ Task Failed: {chain.command} — {err_preview}"

    # ========== PUBLIC API ==========

    async def execute_command(
        self,
        command: str,
        on_progress: Optional[Callable] = None,
        chain_id: Optional[str] = None,
        source: str = "chat",
    ) -> ExecutionReport:
        """Execute command end-to-end (all 7 steps)."""
        chain = await self.create_chain(command, chain_id=chain_id, source=source, auto_decompose=False)
        if on_progress:
            self.subscribe_progress(chain.id, on_progress)

        await self.decompose_command(chain)
        await self.identify_executors(chain)
        report = await self.execute_chain(chain.id)
        await self.notify_completion(report)
        return report

    def get_chain(self, chain_id: str) -> Optional[ActionChain]:
        """Get chain by ID from active or completed cache."""
        with self._lock:
            return self.active_chains.get(chain_id) or self.completed_chains.get(chain_id)

    def list_chains(self, limit: int = 20) -> List[Dict[str, Any]]:
        """List active, completed, and persisted chains."""
        with self._lock:
            in_mem = {
                cid: c.to_dict()
                for cid, c in list(self.active_chains.items()) + list(self.completed_chains.items())
            }
        persisted = self.tracker.get_recent_chains(limit=limit)
        for p in persisted:
            cid = p.get("chain_id") or p.get("id")
            if cid and cid not in in_mem:
                in_mem[cid] = p
        items = list(in_mem.values())
        items.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
        return items[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        with self._lock:
            return {
                **self.stats,
                "active_chains": len(self.active_chains),
                "completed_chains": len(self.completed_chains),
            }


# Singleton instance
_manager = None
_manager_lock = threading.Lock()


def get_chain_manager() -> ChainOfActionsManager:
    """Get singleton chain manager."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = ChainOfActionsManager()
    return _manager
