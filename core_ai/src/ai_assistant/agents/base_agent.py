from abc import ABC, abstractmethod
import asyncio
import logging
import os
from pathlib import Path
import re
import threading
from typing import Any, Dict, List, Optional

from .models import AgentStatus, ProofreadResult, Task, TaskResult, VerificationResult

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all AI agents."""

    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None):
        self.agent_id = agent_id
        self.name = ""
        self.description = ""
        self.category = ""
        self.capabilities: List[str] = []
        self.status = AgentStatus.IDLE
        self.config: Dict[str, Any] = config or {}

        # Tracking & metrics
        self.current_task: Optional[Task] = None
        self.task_history: List[Task] = []
        self.active_tasks: int = 0
        self.completed_tasks: int = 0
        self.failed_tasks: int = 0
        self.performance_metrics: Dict[str, Any] = {
            "total_execution_time": 0.0,
            "last_error": None,
        }

        # Thread-safe state lock and per-event-loop async execution locks
        self._state_lock = threading.RLock()
        self._loop_locks: Dict[int, asyncio.Lock] = {}

        # VLM and LLM (lazily initialized unless injected in config)
        self.vlm = self.config.get("vlm")
        self.llm = self.config.get("llm")

    def get_async_lock(self) -> asyncio.Lock:
        """Return an asyncio.Lock bound to the currently running event loop."""
        loop = asyncio.get_running_loop()
        loop_id = id(loop)
        with self._state_lock:
            lock = self._loop_locks.get(loop_id)
            if lock is None:
                lock = asyncio.Lock()
                self._loop_locks[loop_id] = lock
            return lock

    def get_status_str(self) -> str:
        """Map internal AgentStatus enum to canonical API status string."""
        if self.status in (AgentStatus.WORKING, AgentStatus.BUSY):
            return "busy"
        if self.status in (AgentStatus.ERROR, AgentStatus.FAILED):
            return "error"
        if self.status == AgentStatus.OFFLINE:
            return "offline"
        return "idle"

    def get_metadata(self) -> Dict[str, Any]:
        """Return standardized metadata dictionary for this agent."""
        return {
            "id": self.agent_id,
            "agent_id": self.agent_id,
            "name": self.name or self.agent_id,
            "category": self.category or "general",
            "description": self.description or "",
            "capabilities": list(self.capabilities),
            "status": self.get_status_str(),
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
        }

    def to_dto(self) -> Dict[str, Any]:
        """Return canonical REST/WebSocket agent DTO."""
        return {
            "id": self.agent_id,
            "name": self.name or self.agent_id,
            "category": self.category or "general",
            "description": self.description or "",
            "capabilities": list(self.capabilities),
            "status": self.get_status_str(),
            "active_tasks": self.active_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
        }

    def get_llm(self, use_fallback: bool = True) -> Any:
        """Lazily obtain a configured UnifiedChatInterface (provider-agnostic)."""
        if self.llm is not None:
            return self.llm
        try:
            from ai_assistant.ai.llm_provider import UnifiedChatInterface
        except ImportError:
            try:
                from ..ai.llm_provider import UnifiedChatInterface  # type: ignore
            except ImportError:
                return None

        try:
            self.llm = UnifiedChatInterface(
                provider=self.config.get("provider"),
                model=self.config.get("model"),
                use_fallback=use_fallback,
            )
            return self.llm
        except Exception as exc:
            logger.warning("[%s] UnifiedChatInterface unavailable: %s", self.agent_id, exc)
            return None

    async def chat_llm(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        **kwargs: Any,
    ) -> Optional[str]:
        """Non-blocking LLM call returning None when unavailable or errored."""
        llm = self.get_llm()
        if llm is None:
            return None

        # Support async generate() mocks/providers
        generate_fn = getattr(llm, "generate", None)
        if callable(generate_fn):
            try:
                if asyncio.iscoroutinefunction(generate_fn):
                    res = await generate_fn(prompt, **kwargs)
                else:
                    res = await asyncio.to_thread(generate_fn, prompt, **kwargs)
                text = str(res or "").strip()
                if text and not text.startswith("Error:"):
                    return text
            except Exception as exc:
                logger.warning("[%s] llm.generate failed: %s", self.agent_id, exc)
                return None

        # Standard UnifiedChatInterface.chat()
        chat_fn = getattr(llm, "chat", None)
        if callable(chat_fn):
            def _run_chat() -> str:
                if system_message and hasattr(llm, "set_system_message"):
                    llm.set_system_message(system_message)
                return str(chat_fn(prompt, **kwargs) or "")

            try:
                text = (await asyncio.to_thread(_run_chat)).strip()
                if text and not text.startswith("Error:"):
                    return text
            except Exception as exc:
                logger.warning("[%s] llm.chat failed: %s", self.agent_id, exc)
        return None

    def get_vlm(self) -> Any:
        """Lazily obtain MultiModalAI VLM helper if available."""
        if self.vlm is not None:
            return self.vlm
        try:
            from ai_assistant.multimodal import MultiModalAI
            self.vlm = MultiModalAI()
            return self.vlm
        except Exception as exc:
            logger.debug("[%s] VLM unavailable: %s", self.agent_id, exc)
            return None

    def get_output_dir(self, task: Optional[Task] = None, subdir: str = "outputs") -> Path:
        """Resolve and create a clean output directory without polluting arbitrary dirs."""
        custom = None
        if task and isinstance(task.params, dict):
            custom = task.params.get("output_dir")
        if not custom:
            custom = self.config.get("output_dir")
        if custom:
            out_dir = Path(custom)
        else:
            out_dir = Path(os.getcwd()) / subdir
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir.resolve()

    def _resolve_output_path(
        self,
        task: Task,
        default_filename: str,
        subdir: str = "outputs",
    ) -> str:
        """Resolve an explicit output_path/filename param into an absolute path."""
        explicit_path = task.params.get("output_path")
        if explicit_path:
            p = Path(str(explicit_path))
            if not p.is_absolute():
                p = Path(os.getcwd()) / p
            p.parent.mkdir(parents=True, exist_ok=True)
            return str(p.resolve())

        filename = task.params.get("filename") or task.params.get("output_filename") or default_filename
        out_dir = self.get_output_dir(task, subdir=subdir)
        target = out_dir / Path(str(filename)).name
        target.parent.mkdir(parents=True, exist_ok=True)
        return str(target.resolve())

    def _extract_upstream_text(self, task: Task) -> str:
        """Extract textual content from upstream dependency outputs in task.context."""
        ctx = task.context or {}
        parts: List[str] = []

        for key in ("previous_output", "upstream_text", "context_text", "summary", "text", "content", "synthesis", "output"):
            val = ctx.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val.strip())

        upstream = ctx.get("upstream_results")
        if isinstance(upstream, dict):
            for step_key, res in upstream.items():
                if isinstance(res, dict):
                    data = res.get("data") if isinstance(res.get("data"), dict) else res
                    for field in ("synthesis", "summary", "content", "text", "output", "answer", "message"):
                        val = data.get(field)
                        if isinstance(val, str) and val.strip():
                            parts.append(f"[{step_key}] {val.strip()}")
                            break
                    if isinstance(data.get("results"), list) and data["results"]:
                        snippets = []
                        for item in data["results"][:5]:
                            if isinstance(item, dict):
                                title = item.get("title", "")
                                desc = item.get("description") or item.get("snippet") or item.get("url", "")
                                snippets.append(f"- {title}: {desc}".strip())
                        if snippets:
                            parts.append(f"[{step_key} sources]\n" + "\n".join(snippets))

        if not parts and isinstance(task.params.get("context"), str):
            parts.append(task.params["context"].strip())

        return "\n\n".join(dict.fromkeys(parts))

    @abstractmethod
    async def can_handle(self, task: Task) -> bool:
        """Check if agent can handle this task."""
        pass

    async def can_handle_score(self, task: Task) -> float:
        """Return relevance score in [0.0, 1.0] for routing."""
        if task.target_agent_id and task.target_agent_id == self.agent_id:
            return 1.0

        score = 0.0
        req_caps = set(c.lower() for c in (task.required_capabilities or []))
        own_caps = set(c.lower() for c in self.capabilities)
        if req_caps and (req_caps & own_caps):
            score = max(score, 0.95)

        desc_lower = (task.description or "").lower()
        tokens = set(re.findall(r"[a-z0-9_]+", desc_lower))
        for cap in own_caps:
            cap_words = [w for w in cap.split("_") if len(w) > 2]
            if cap in desc_lower:
                score = max(score, 0.9)
            elif cap_words and all(w in tokens for w in cap_words):
                score = max(score, 0.85)

        try:
            if await self.can_handle(task):
                score = max(score, 0.7)
        except Exception as exc:
            logger.debug("[%s] can_handle raised: %s", self.agent_id, exc)

        return min(1.0, score)

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """Execute the assigned task."""
        pass

    async def verify(self, result: TaskResult) -> VerificationResult:
        """Verify task completion (file existence/non-emptiness + optional VLM)."""
        if not result.success:
            return VerificationResult(
                is_valid=False,
                score=0.0,
                issues=[result.error or "Task failed"],
            )

        issues: List[str] = []
        suggestions: List[str] = []
        score = 1.0

        if result.output_path:
            if not os.path.exists(result.output_path):
                issues.append(f"Expected output file missing: {result.output_path}")
                score = 0.2
            elif os.path.getsize(result.output_path) == 0:
                issues.append(f"Output file is empty: {result.output_path}")
                score = 0.3

        return VerificationResult(
            is_valid=len(issues) == 0,
            score=score,
            issues=issues,
            suggestions=suggestions,
        )

    async def proofread(self, output_path: str) -> ProofreadResult:
        """Basic proofreading check (delegates to VLM/LLM when available)."""
        if not output_path or not os.path.exists(output_path):
            return ProofreadResult(
                errors=[f"Output file not found: {output_path}"],
                suggestions=[],
                quality_score=0.0,
            )

        ext = Path(output_path).suffix.lower()
        if ext in (".txt", ".md", ".csv", ".json"):
            try:
                content = Path(output_path).read_text(encoding="utf-8", errors="ignore")
                if not content.strip():
                    return ProofreadResult(
                        errors=["Document content is empty"],
                        suggestions=["Add content to the output document."],
                        quality_score=0.2,
                    )
                return ProofreadResult(errors=[], suggestions=[], quality_score=0.95)
            except Exception as exc:
                return ProofreadResult(errors=[str(exc)], suggestions=[], quality_score=0.0)

        return ProofreadResult(errors=[], suggestions=[], quality_score=1.0)
