from __future__ import annotations

import asyncio
from datetime import datetime
import inspect
import json
import logging
import re
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

from ..agents.base_agent import BaseAgent
from ..agents.loader import get_global_registry
from ..agents.models import AgentStatus, Task, TaskResult
from ..agents.registry import AgentRegistry
from .interaction import InteractionManager
from .memory_manager import MemoryManager

logger = logging.getLogger(__name__)

_coordinator_lock = threading.RLock()
_coordinator_singleton: Optional["MultiAgentCoordinator"] = None


def get_multi_agent_coordinator(
    registry: Optional[AgentRegistry] = None,
) -> "MultiAgentCoordinator":
    """Return the process-wide singleton MultiAgentCoordinator."""
    global _coordinator_singleton
    with _coordinator_lock:
        if _coordinator_singleton is None:
            reg = registry if registry is not None else get_global_registry()
            _coordinator_singleton = MultiAgentCoordinator(reg)
        elif registry is not None and _coordinator_singleton.registry is not registry:
            _coordinator_singleton.registry = registry
        return _coordinator_singleton


def reset_multi_agent_coordinator() -> None:
    """Reset the singleton coordinator (primarily for isolated tests)."""
    global _coordinator_singleton
    with _coordinator_lock:
        _coordinator_singleton = None


class MultiAgentCoordinator:
    """
    Central coordinator for the Multi-Agent System.
    Supports:
    - Provider-agnostic LLM routing & multi-step DAG planning (with deterministic fallback)
    - Parallel wave execution across independent DAG steps with cycle detection
    - Inter-agent data passing ({step.output}, {prev.output}, upstream_results)
    - Per-agent async locking, timeout/retry guards, task lifecycle & cancellation
    - Real-time event subscription for backend WebSocket/API consumers
    - Chain-of-actions step execution contract (`execute_step`)
    """

    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        memory: Optional[MemoryManager] = None,
        interaction: Optional[InteractionManager] = None,
        llm: Optional[Any] = None,
    ):
        self.registry: AgentRegistry = registry if registry is not None else get_global_registry()
        self.memory: MemoryManager = memory if memory is not None else MemoryManager()
        self.interaction: InteractionManager = interaction if interaction is not None else InteractionManager()
        self.llm: Optional[Any] = llm

        self._lock = threading.RLock()
        self.active_tasks: Dict[str, Task] = {}
        self.task_results: Dict[str, TaskResult] = {}
        self._task_records: Dict[str, Dict[str, Any]] = {}
        self._running_handles: Dict[str, asyncio.Task] = {}
        self._cancelled_tasks: set[str] = set()
        self._subscribers: List[Callable[..., Any]] = []

    # ------------------------------------------------------------------
    # Event Bus
    # ------------------------------------------------------------------

    def subscribe_events(self, callback: Callable[..., Any]) -> None:
        """Subscribe a sync or async listener for coordinator/agent lifecycle events."""
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe_events(self, callback: Callable[..., Any]) -> None:
        """Unsubscribe a previously registered event listener."""
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    async def _emit_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        with self._lock:
            listeners = list(self._subscribers)
        if not listeners:
            return

        for cb in listeners:
            try:
                sig = inspect.signature(cb)
                pos_params = [
                    p for p in sig.parameters.values()
                    if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                ]
                has_varargs = any(p.kind == inspect.Parameter.VAR_POSITIONAL for p in sig.parameters.values())
                if len(pos_params) == 1 and not has_varargs:
                    res = cb({"event": event_type, "type": event_type, "data": payload, **payload})
                else:
                    res = cb(event_type, payload)

                if inspect.isawaitable(res):
                    await res
            except Exception as exc:
                logger.warning("Event subscriber error on '%s': %s", event_type, exc)

    def _sync_registry_metrics(self, agent: BaseAgent, status_str: str) -> None:
        """Mirror runtime counters back to AgentRegistry metadata."""
        meta_list = [m for m in self.registry.get_all_metadata() if m.agent_id == agent.agent_id]
        if meta_list:
            meta = meta_list[0]
            meta.active_tasks = agent.active_tasks
            meta.completed_tasks = agent.completed_tasks
            meta.failed_tasks = agent.failed_tasks
            meta.last_error = agent.performance_metrics.get("last_error")
            meta.status = "active" if status_str != "offline" else "offline"

    # ------------------------------------------------------------------
    # Provider-Agnostic LLM Helper
    # ------------------------------------------------------------------

    def _get_llm(self) -> Any:
        if self.llm is not None:
            return self.llm
        try:
            from ai_assistant.ai.llm_provider import UnifiedChatInterface

            self.llm = UnifiedChatInterface(use_fallback=True)
            return self.llm
        except Exception as exc:
            logger.debug("Coordinator UnifiedChatInterface unavailable: %s", exc)
            return None

    async def _call_planner_llm(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        llm = self._get_llm()
        if llm is None:
            return None

        generate_fn = getattr(llm, "generate", None)
        if callable(generate_fn):
            try:
                prompt = f"{system_prompt}\n\nUser request:\n{user_prompt}"
                if asyncio.iscoroutinefunction(generate_fn):
                    res = await generate_fn(prompt)
                else:
                    res = await asyncio.to_thread(generate_fn, prompt)
                txt = str(res or "").strip()
                if txt and not txt.startswith("Error:"):
                    return txt
            except Exception as exc:
                logger.debug("Coordinator llm.generate failed: %s", exc)
                return None

        chat_fn = getattr(llm, "chat", None)
        if callable(chat_fn):
            def _run() -> str:
                if hasattr(llm, "set_system_message"):
                    llm.set_system_message(system_prompt)
                return str(chat_fn(user_prompt) or "")

            try:
                txt = (await asyncio.to_thread(_run)).strip()
                if txt and not txt.startswith("Error:"):
                    return txt
            except Exception as exc:
                logger.debug("Coordinator llm.chat failed: %s", exc)
        return None

    # ------------------------------------------------------------------
    # Single-Agent & Chain Step Execution
    # ------------------------------------------------------------------

    async def execute_agent(self, agent_id: str, task: Task) -> TaskResult:
        """
        Execute a Task on a specific agent (resolved via canonical ID or alias),
        enforcing per-agent locking, timeouts, retries, status metrics, and lifecycle events.
        """
        resolved_id = self.registry.resolve_agent_id(agent_id)
        agent = self.registry.get_agent(resolved_id)
        if not agent:
            return TaskResult(
                success=False,
                agent_id=resolved_id,
                error=f"Agent '{agent_id}' not found or could not be loaded.",
            )

        if not task.task_id:
            task.task_id = str(uuid.uuid4())

        now_iso = datetime.utcnow().isoformat() + "Z"
        with self._lock:
            self.active_tasks[task.task_id] = task
            self._task_records[task.task_id] = {
                "task_id": task.task_id,
                "agent_id": agent.agent_id,
                "agent_name": agent.name or agent.agent_id,
                "description": task.description,
                "status": "running",
                "chain_id": task.chain_id,
                "created_at": now_iso,
                "started_at": now_iso,
                "completed_at": None,
                "error": None,
            }

        async def _run_with_lock() -> TaskResult:
            async with agent.get_async_lock():
                if task.task_id in self._cancelled_tasks:
                    return TaskResult(
                        success=False,
                        agent_id=agent.agent_id,
                        agent_name=agent.name,
                        error="Task cancelled before start",
                    )

                with agent._state_lock:
                    agent.status = AgentStatus.WORKING
                    agent.current_task = task
                    agent.active_tasks += 1
                    agent.task_history.append(task)
                    self._sync_registry_metrics(agent, "busy")

                await self._emit_event(
                    "agent.task_started",
                    {
                        "task_id": task.task_id,
                        "agent_id": agent.agent_id,
                        "agent_name": agent.name or agent.agent_id,
                        "description": task.description,
                        "chain_id": task.chain_id,
                    },
                )
                await self._emit_event(
                    "agent.status_changed",
                    {
                        "agent_id": agent.agent_id,
                        "name": agent.name or agent.agent_id,
                        "status": "busy",
                        "task_id": task.task_id,
                        "active_tasks": agent.active_tasks,
                        "completed_tasks": agent.completed_tasks,
                        "failed_tasks": agent.failed_tasks,
                    },
                )

                t0 = time.monotonic()
                max_attempts = 1 + max(0, int(task.max_retries or 0))
                last_result: Optional[TaskResult] = None

                try:
                    for attempt in range(max_attempts):
                        try:
                            res = await asyncio.wait_for(
                                agent.execute(task),
                                timeout=float(task.timeout or 120.0),
                            )
                            last_result = res
                        except asyncio.TimeoutError:
                            last_result = TaskResult(
                                success=False,
                                error=f"Agent '{agent.agent_id}' timed out after {task.timeout}s",
                            )
                        except asyncio.CancelledError:
                            with self._lock:
                                self._cancelled_tasks.add(task.task_id)
                            raise
                        except Exception as exc:
                            last_result = TaskResult(success=False, error=str(exc))

                        if last_result.success:
                            break
                        if last_result.metadata.get("requires_confirmation"):
                            break
                        if task.task_id in self._cancelled_tasks:
                            break

                    assert last_result is not None
                    elapsed = round(time.monotonic() - t0, 4)
                    last_result.execution_time = elapsed
                    last_result.agent_id = agent.agent_id
                    last_result.agent_name = agent.name or agent.agent_id

                    if last_result.success and (task.params or {}).get("verify"):
                        try:
                            verification = await agent.verify(last_result)
                            last_result.verification = verification
                        except Exception as ver_exc:
                            logger.debug("Verification skipped due to error: %s", ver_exc)

                    with agent._state_lock:
                        if last_result.success:
                            agent.completed_tasks += 1
                            agent.performance_metrics["last_error"] = None
                        else:
                            agent.failed_tasks += 1
                            agent.performance_metrics["last_error"] = last_result.error
                        agent.performance_metrics["total_execution_time"] = (
                            float(agent.performance_metrics.get("total_execution_time", 0.0)) + elapsed
                        )

                    return last_result
                finally:
                    with agent._state_lock:
                        agent.active_tasks = max(0, agent.active_tasks - 1)
                        agent.current_task = None
                        agent.status = AgentStatus.IDLE
                        self._sync_registry_metrics(agent, "idle")

                    await self._emit_event(
                        "agent.status_changed",
                        {
                            "agent_id": agent.agent_id,
                            "name": agent.name or agent.agent_id,
                            "status": "idle",
                            "task_id": None,
                            "active_tasks": agent.active_tasks,
                            "completed_tasks": agent.completed_tasks,
                            "failed_tasks": agent.failed_tasks,
                        },
                    )

        exec_coro = asyncio.create_task(_run_with_lock())
        with self._lock:
            self._running_handles[task.task_id] = exec_coro

        result: Optional[TaskResult] = None
        try:
            result = await exec_coro
        except asyncio.CancelledError:
            with self._lock:
                self._cancelled_tasks.add(task.task_id)
            result = TaskResult(
                success=False,
                agent_id=agent.agent_id,
                agent_name=agent.name,
                error="Task cancelled",
            )
        finally:
            finished_iso = datetime.utcnow().isoformat() + "Z"
            with self._lock:
                self._running_handles.pop(task.task_id, None)
                self.active_tasks.pop(task.task_id, None)
                if result is not None:
                    self.task_results[task.task_id] = result
                rec = self._task_records.get(task.task_id)
                if rec is not None:
                    if task.task_id in self._cancelled_tasks:
                        rec["status"] = "cancelled"
                    elif result and result.success:
                        rec["status"] = "completed"
                    else:
                        rec["status"] = "failed"
                    rec["completed_at"] = finished_iso
                    rec["error"] = None if (result and result.success) else (result.error if result else "Cancelled")
                    rec["execution_time"] = result.execution_time if result else 0.0
                    rec["output_path"] = result.output_path if result else None

        assert result is not None
        if result.success:
            summary_val = (
                result.data.get("summary")
                or result.data.get("message")
                or str(result.data.get("output") or result.data.get("text") or "")[:200]
            )
            await self._emit_event(
                "agent.task_completed",
                {
                    "task_id": task.task_id,
                    "agent_id": agent.agent_id,
                    "agent_name": agent.name or agent.agent_id,
                    "success": True,
                    "execution_time": result.execution_time,
                    "output_path": result.output_path,
                    "summary": summary_val,
                    "chain_id": task.chain_id,
                },
            )
        else:
            await self._emit_event(
                "agent.task_failed",
                {
                    "task_id": task.task_id,
                    "agent_id": agent.agent_id,
                    "agent_name": agent.name or agent.agent_id,
                    "error": result.error or "Unknown error",
                    "execution_time": result.execution_time,
                    "chain_id": task.chain_id,
                },
            )

        return result

    async def assign_task(self, task: Task) -> Optional[str]:
        """Resolve and assign a Task to the best matching agent (legacy helper)."""
        if task.target_agent_id:
            resolved = self.registry.resolve_agent_id(task.target_agent_id)
            agent = self.registry.get_agent(resolved)
        else:
            agent = await self.registry.find_best_agent(task)
        if not agent:
            return None
        with self._lock:
            self.active_tasks[task.task_id] = task
        return agent.agent_id

    async def execute_task(self, task: Task) -> TaskResult:
        """Find the best agent for a Task (respecting target_agent_id / capabilities) and execute it."""
        if task.target_agent_id:
            return await self.execute_agent(task.target_agent_id, task)

        agent = await self.registry.find_best_agent(task)
        if not agent:
            return TaskResult(success=False, error="No suitable agent found for task")
        return await self.execute_agent(agent.agent_id, task)

    async def execute_step(
        self,
        description: str,
        params: Optional[Dict[str, Any]] = None,
        preferred_agent_id: Optional[str] = None,
        capability: Optional[str] = None,
        chain_context: Optional[Dict[str, Any]] = None,
        chain_id: Optional[str] = None,
    ) -> TaskResult:
        """
        Cross-team contract helper for IntentExecutor / ChainOfActionsManager.
        Routes a single chain step to preferred_agent_id, capability match, or best scored agent.
        """
        task = Task(
            task_id=str(uuid.uuid4()),
            description=description,
            params=dict(params or {}),
            target_agent_id=preferred_agent_id,
            required_capabilities=[capability] if capability else [],
            context=dict(chain_context or {}),
            chain_id=chain_id,
        )

        if preferred_agent_id:
            resolved = self.registry.resolve_agent_id(preferred_agent_id)
            if self.registry.get_agent(resolved):
                return await self.execute_agent(resolved, task)

        if capability:
            candidates = self.registry.find_agents_by_capability(capability)
            if candidates:
                return await self.execute_agent(candidates[0], task)

        return await self.execute_task(task)

    # ------------------------------------------------------------------
    # Multi-Step DAG Planning & Execution
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_payload(raw: str) -> Optional[Dict[str, Any]]:
        txt = raw.strip()
        if "```json" in txt:
            txt = txt.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in txt:
            txt = txt.split("```", 1)[1].split("```", 1)[0].strip()
        try:
            data = json.loads(txt)
            return data if isinstance(data, dict) else None
        except Exception:
            match = re.search(r"\{.*\}", txt, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                    return data if isinstance(data, dict) else None
                except Exception:
                    return None
        return None

    async def plan_command(self, command_text: str) -> List[Dict[str, Any]]:
        """
        Produce a validated DAG execution plan:
        [{"step_id", "agent_id", "task", "depends_on", "params", "required_capabilities"}]
        1. Checks WorkflowMemory cache first (0 LLM tokens, ~0ms).
        2. If cache miss, utilizes SwarmPlanner (Pydantic DAG + Kahn's cycle check).
        3. Falls back cleanly to deterministic multi-step decomposition if offline.
        """
        # 1. Fast Cache Check (Never Think Twice)
        try:
            from ai_assistant.core.workflow_memory import get_workflow_memory
            cached_plan = get_workflow_memory().find_matching_workflow(command_text)
            if cached_plan and cached_plan.all_steps:
                logger.info(f"⚡ [WORKFLOW CACHE HIT] Using learned recipe: '{cached_plan.workflow_name}'")
                return [
                    {
                        "step_id": s.step_id,
                        "agent_id": s.agent_id,
                        "task": s.task,
                        "depends_on": s.depends_on,
                        "params": s.params,
                        "required_capabilities": [s.capability] if s.capability else [],
                        "output_key": s.output_key,
                        "requires_confirmation": s.requires_confirmation,
                        "fallback_agent_id": s.fallback_agent_id,
                    }
                    for s in cached_plan.all_steps
                ]
        except Exception as cache_err:
            logger.debug(f"Workflow cache lookup skipped: {cache_err}")

        # 2. Dynamic SwarmPlanner Meta-Planning
        try:
            from ai_assistant.core.swarm_planner import SwarmPlanner
            planner = SwarmPlanner(registry=self.registry, llm_provider=self.llm)
            plan = await planner.plan_workflow(command_text)
            if plan and plan.all_steps:
                return [
                    {
                        "step_id": s.step_id,
                        "agent_id": s.agent_id,
                        "task": s.task,
                        "depends_on": s.depends_on,
                        "params": s.params,
                        "required_capabilities": [s.capability] if s.capability else [],
                        "output_key": s.output_key,
                        "requires_confirmation": s.requires_confirmation,
                        "fallback_agent_id": s.fallback_agent_id,
                    }
                    for s in plan.all_steps
                ]
        except Exception as planner_err:
            logger.debug(f"SwarmPlanner dynamic planning skipped: {planner_err}")

        return await self._fallback_plan_steps(command_text)

    async def _fallback_plan_steps(self, command_text: str) -> List[Dict[str, Any]]:
        """Deterministic multi-step planner when LLM is offline or unavailable."""
        # Split on explicit sequential connectors first
        clauses = [c.strip() for c in re.split(r"\s*(?:;|->|\band then\b|\bthen\b)\s*", command_text, flags=re.IGNORECASE) if c.strip()]

        # If single clause, check "X and Y" where X and Y score highest on distinct agents
        if len(clauses) == 1 and re.search(r"\s+and\s+", command_text, flags=re.IGNORECASE):
            parts = [p.strip() for p in re.split(r"\s+and\s+", command_text, maxsplit=1, flags=re.IGNORECASE) if p.strip()]
            if len(parts) == 2 and min(len(parts[0].split()), len(parts[1].split())) >= 2:
                a1 = await self.registry.find_best_agent(Task(description=parts[0]))
                a2 = await self.registry.find_best_agent(Task(description=parts[1]))
                if a1 and a2 and a1.agent_id != a2.agent_id:
                    clauses = parts

        steps: List[Dict[str, Any]] = []
        prev_step_id: Optional[str] = None
        for idx, clause in enumerate(clauses):
            step_id = f"step_{idx + 1}"
            agent = await self.registry.find_best_agent(Task(description=clause))
            if not agent:
                continue
            deps = [prev_step_id] if prev_step_id is not None else []
            steps.append({
                "step_id": step_id,
                "agent_id": agent.agent_id,
                "task": clause,
                "depends_on": deps,
                "params": {},
                "required_capabilities": [],
            })
            prev_step_id = step_id

        if not steps:
            agent = await self.registry.find_best_agent(Task(description=command_text))
            if agent:
                steps.append({
                    "step_id": "step_1",
                    "agent_id": agent.agent_id,
                    "task": command_text,
                    "depends_on": [],
                    "params": {},
                    "required_capabilities": [],
                })
        return steps

    @staticmethod
    def _extract_result_values(res: TaskResult) -> Dict[str, str]:
        data = res.data or {}
        text = ""
        for key in ("synthesis", "summary", "content", "text", "output", "answer", "message"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                text = val.strip()
                break
        if not text and isinstance(data.get("results"), list):
            text = "\n".join(
                f"- {r.get('title', '')}: {r.get('description') or r.get('snippet') or r.get('url', '')}"
                for r in data["results"][:5]
                if isinstance(r, dict)
            )
        summary = str(data.get("summary") or text[:300])
        path = str(res.output_path or data.get("output_path") or data.get("path") or "")
        return {"output": text, "text": text, "summary": summary, "path": path, "output_path": path}

    @classmethod
    def _interpolate_string(
        cls,
        raw: str,
        dep_results: Dict[str, TaskResult],
        ordered_deps: List[str],
    ) -> str:
        lookup: Dict[str, str] = {}
        for sid, res in dep_results.items():
            vals = cls._extract_result_values(res)
            for k, v in vals.items():
                lookup[f"{sid}.{k}"] = v
        if ordered_deps and ordered_deps[-1] in dep_results:
            prev_vals = cls._extract_result_values(dep_results[ordered_deps[-1]])
            for k, v in prev_vals.items():
                lookup[f"prev.{k}"] = v

        def _repl(match: re.Match) -> str:
            token = match.group(1)
            return lookup.get(token, match.group(0))

        return re.sub(r"\{([A-Za-z0-9_.-]+)\}", _repl, raw)

    @classmethod
    def _interpolate_params(
        cls,
        params: Dict[str, Any],
        dep_results: Dict[str, TaskResult],
        ordered_deps: List[str],
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k, v in params.items():
            if isinstance(v, str):
                out[k] = cls._interpolate_string(v, dep_results, ordered_deps)
            elif isinstance(v, dict):
                out[k] = cls._interpolate_params(v, dep_results, ordered_deps)
            else:
                out[k] = v
        return out

    async def execute_dag(
        self,
        steps: List[Dict[str, Any]],
        base_params: Optional[Dict[str, Any]] = None,
        chain_id: Optional[str] = None,
        command_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a multi-step DAG in topological parallel waves.
        Propagates upstream step outputs into task.context['upstream_results'] and {step.output}/{prev.output}.
        Includes Self-Healing (re-routes on failure) and Workflow Memory caching on success.
        """
        if not steps:
            return {"status": "rejected", "steps": [], "results": {}}

        step_map: Dict[str, Dict[str, Any]] = {str(s["step_id"]): s for s in steps}
        # Validate dependencies & detect cycles before running
        indegree: Dict[str, int] = {}
        children: Dict[str, List[str]] = {sid: [] for sid in step_map}
        for sid, s in step_map.items():
            deps = [str(d) for d in (s.get("depends_on") or []) if str(d) in step_map]
            s["_valid_deps"] = deps
            indegree[sid] = len(deps)
            for d in deps:
                children[d].append(sid)

        # Kahn's topological check
        q = [sid for sid, deg in indegree.items() if deg == 0]
        visited = 0
        temp_indeg = dict(indegree)
        while q:
            cur = q.pop(0)
            visited += 1
            for nxt in children[cur]:
                temp_indeg[nxt] -= 1
                if temp_indeg[nxt] == 0:
                    q.append(nxt)
        if visited != len(step_map):
            return {
                "status": "error",
                "message": "Cyclic dependency detected in workflow plan",
                "steps": [],
                "results": {},
            }

        completed_results: Dict[str, TaskResult] = {}
        step_reports: List[Dict[str, Any]] = []
        pending = set(step_map.keys())
        dag_chain_id = chain_id or f"dag-{uuid.uuid4().hex[:8]}"

        while pending:
            ready = [
                sid for sid in steps_order(steps, pending)
                if all(dep in completed_results for dep in step_map[sid]["_valid_deps"])
            ]
            if not ready:
                break

            async def _run_step(sid: str) -> Tuple[str, TaskResult]:
                spec = step_map[sid]
                deps = spec["_valid_deps"]
                dep_res_map = {d: completed_results[d] for d in deps}

                upstream_payload = {
                    d: {
                        "success": completed_results[d].success,
                        "output_path": completed_results[d].output_path,
                        "data": completed_results[d].data,
                    }
                    for d in deps
                }
                prev_text = ""
                if deps:
                    prev_text = self._extract_result_values(completed_results[deps[-1]])["output"]

                merged_params = dict(base_params or {})
                merged_params.update(spec.get("params") or {})
                merged_params = self._interpolate_params(merged_params, dep_res_map, deps)
                desc = self._interpolate_string(str(spec.get("task", "")), dep_res_map, deps)

                task = Task(
                    task_id=str(uuid.uuid4()),
                    description=desc,
                    params=merged_params,
                    target_agent_id=spec.get("agent_id"),
                    required_capabilities=list(spec.get("required_capabilities") or []),
                    context={
                        "upstream_results": upstream_payload,
                        "previous_output": prev_text,
                    },
                    chain_id=dag_chain_id,
                )
                aid = str(spec.get("agent_id") or "")
                res = await self.execute_agent(aid, task) if aid else await self.execute_task(task)
                return sid, res

            wave_outcomes = await asyncio.gather(*(_run_step(sid) for sid in ready))
            wave_failed = False
            for sid, res in wave_outcomes:
                if not res.success:
                    spec = step_map[sid]
                    healed = False

                    # Self-Healing Layer 1: Check explicit fallback_agent_id
                    fallback_aid = spec.get("fallback_agent_id")
                    if fallback_aid and fallback_aid != spec.get("agent_id"):
                        logger.warning(
                            f"🩹 [SELF-HEALING] Attempting designated fallback agent '{fallback_aid}' for step '{sid}'"
                        )
                        await self._emit_event(
                            "swarm.self_healing",
                            {
                                "step_id": sid,
                                "original_agent": spec.get("agent_id"),
                                "fallback_agent": fallback_aid,
                                "reason": res.error or "Step failed",
                                "status": "recovering",
                            },
                        )
                        fallback_task = Task(
                            task_id=str(uuid.uuid4()),
                            description=str(spec.get("task", "")),
                            params=spec.get("params", {}),
                            target_agent_id=fallback_aid,
                            chain_id=dag_chain_id,
                        )
                        fallback_res = await self.execute_agent(fallback_aid, fallback_task)
                        if fallback_res.success:
                            logger.info(f"✅ [SELF-HEALING SUCCESS] Step '{sid}' recovered via '{fallback_aid}'")
                            res = fallback_res
                            healed = True
                            await self._emit_event(
                                "swarm.self_healing",
                                {
                                    "step_id": sid,
                                    "healed_by": fallback_aid,
                                    "status": "resolved",
                                },
                            )

                    # Self-Healing Layer 2: Dynamic Re-Planning Engine
                    if not healed:
                        try:
                            from ai_assistant.core.swarm_planner import SwarmPlanner, WorkflowStep
                            planner = SwarmPlanner(registry=self.registry, llm_provider=self.llm)
                            curr_step = WorkflowStep(
                                step_id=sid,
                                agent_id=spec.get("agent_id", ""),
                                capability=spec.get("required_capabilities", [""])[0] if spec.get("required_capabilities") else "",
                                task=spec.get("task", ""),
                                params=spec.get("params", {}),
                                depends_on=spec.get("depends_on", []),
                                fallback_agent_id=fallback_aid,
                            )
                            replacement = await planner.replan_failed_step(
                                failed_step=curr_step,
                                error_message=res.error or "Step execution failed",
                                user_goal=command_text or spec.get("task", ""),
                                completed_results={d: completed_results[d].model_dump() for d in completed_results},
                                remaining_steps=[
                                    WorkflowStep(
                                        step_id=p,
                                        agent_id=step_map[p].get("agent_id", ""),
                                        capability="",
                                        task=step_map[p].get("task", ""),
                                    )
                                    for p in pending if p != sid
                                ],
                            )
                            if replacement and replacement.agent_id != spec.get("agent_id"):
                                logger.warning(
                                    f"🩹 [SELF-HEALING] Re-routing step '{sid}' to replacement agent '{replacement.agent_id}'"
                                )
                                await self._emit_event(
                                    "swarm.self_healing",
                                    {
                                        "step_id": sid,
                                        "original_agent": spec.get("agent_id"),
                                        "replacement_agent": replacement.agent_id,
                                        "reason": res.error or "Step failed",
                                        "status": "recovering",
                                    },
                                )
                                repl_task = Task(
                                    task_id=str(uuid.uuid4()),
                                    description=replacement.task,
                                    params=replacement.params,
                                    target_agent_id=replacement.agent_id,
                                    chain_id=dag_chain_id,
                                )
                                repl_res = await self.execute_agent(replacement.agent_id, repl_task)
                                if repl_res.success:
                                    logger.info(f"✅ [SELF-HEALING SUCCESS] Step '{sid}' recovered via '{replacement.agent_id}'")
                                    res = repl_res
                                    healed = True
                                    await self._emit_event(
                                        "swarm.self_healing",
                                        {
                                            "step_id": sid,
                                            "healed_by": replacement.agent_id,
                                            "status": "resolved",
                                        },
                                    )
                        except Exception as replan_e:
                            logger.debug(f"Self-healing dynamic replan error: {replan_e}")

                    if not healed:
                        wave_failed = True

                completed_results[sid] = res
                pending.discard(sid)
                step_reports.append({
                    "step_id": sid,
                    "agent_id": res.agent_id or step_map[sid].get("agent_id"),
                    "agent_name": res.agent_name,
                    "success": res.success,
                    "error": res.error,
                    "output_path": res.output_path,
                    "execution_time": res.execution_time,
                    "data": res.data,
                })

            if wave_failed:
                # Skip downstream steps whose dependencies failed
                break

        overall_ok = bool(step_reports) and all(r["success"] for r in step_reports) and len(step_reports) == len(steps)
        final_step = step_reports[-1] if step_reports else {}

        # Cache successful novel workflows into WorkflowMemory (Never Think Twice)
        if overall_ok and command_text:
            try:
                from ai_assistant.core.workflow_memory import get_workflow_memory
                from ai_assistant.core.swarm_planner import WorkflowPlan, WorkflowStep, WorkflowWave, SwarmPlanner

                wf_steps = [
                    WorkflowStep(
                        step_id=s["step_id"],
                        agent_id=s["agent_id"],
                        capability=s.get("capability") or (s.get("required_capabilities", [""])[0] if s.get("required_capabilities") else "task"),
                        task=s.get("task", ""),
                        params=s.get("params", {}),
                        depends_on=s.get("depends_on", []),
                        output_key=s.get("output_key", s["step_id"]),
                        requires_confirmation=s.get("requires_confirmation", False),
                    )
                    for s in steps
                ]
                waves = SwarmPlanner._build_waves_from_steps(wf_steps) or [WorkflowWave(wave_number=1, steps=wf_steps)]
                wf_plan = WorkflowPlan(
                    workflow_id=dag_chain_id,
                    workflow_name=f"Learned_{dag_chain_id}",
                    user_goal=command_text,
                    reasoning="Successfully executed and remembered for future zero-cost recall",
                    waves=waves,
                    all_steps=wf_steps,
                )
                get_workflow_memory().record_success(command_text, wf_plan)
            except Exception as mem_e:
                logger.debug(f"Workflow memory record skipped: {mem_e}")

        return {
            "status": "completed" if overall_ok else "failed",
            "chain_id": dag_chain_id,
            "agents_used": list(dict.fromkeys(r["agent_name"] or r["agent_id"] for r in step_reports)),
            "agent_used": final_step.get("agent_name") or final_step.get("agent_id"),
            "result": final_step.get("data") if final_step.get("success") else final_step.get("error"),
            "steps": step_reports,
            "results": {sid: res.model_dump() for sid, res in completed_results.items()},
        }

    async def process_command(
        self,
        command_text: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a natural-language user command, build a 1..N step execution DAG
        (via LLM planner with deterministic fallback), and execute it.
        """
        try:
            plan = await self.plan_command(command_text)
            if not plan:
                return {
                    "status": "rejected",
                    "message": "No suitable agent found for this command.",
                }

            outcome = await self.execute_dag(plan, base_params=params, command_text=command_text)
            outcome["plan"] = plan
            return outcome
            if not plan:
                return {
                    "status": "rejected",
                    "message": "No suitable agent found for this command.",
                }

            outcome = await self.execute_dag(plan, base_params=params)
            outcome["plan"] = plan
            return outcome
        except Exception as exc:
            logger.error("Orchestration error: %s", exc, exc_info=True)
            return {"status": "error", "message": f"Orchestration error: {exc}"}

    # ------------------------------------------------------------------
    # Task Query & Cancellation API (Contract with @backend-api)
    # ------------------------------------------------------------------

    def list_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent tracked tasks ordered newest first."""
        with self._lock:
            records = list(self._task_records.values())
        records.reverse()
        return records[: max(1, limit)]

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Return detailed metadata and serialized result for a task_id."""
        with self._lock:
            rec = self._task_records.get(task_id)
            if rec is None:
                return None
            out = dict(rec)
            res = self.task_results.get(task_id)
            if res is not None:
                out["result"] = res.model_dump()
            return out

    def cancel_task(self, task_id: str) -> bool:
        """Request cancellation of a running or queued task."""
        with self._lock:
            self._cancelled_tasks.add(task_id)
            handle = self._running_handles.get(task_id)
            rec = self._task_records.get(task_id)
            if handle is not None and not handle.done():
                handle.cancel()
                if rec is not None:
                    rec["status"] = "cancelled"
                return True
            if rec is not None and rec["status"] == "running":
                rec["status"] = "cancelled"
                return True
            return False


def steps_order(steps: List[Dict[str, Any]], subset: set[str]) -> List[str]:
    return [str(s["step_id"]) for s in steps if str(s["step_id"]) in subset]
