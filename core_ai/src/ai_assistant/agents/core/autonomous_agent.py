import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..base_agent import BaseAgent
from ..models import Task, TaskResult

logger = logging.getLogger(__name__)


class AutonomousAgent(BaseAgent):
    """
    Autonomous continuous learning & reflection agent:
    1. Observes conversations and user preferences
    2. Routes observations to LearningDataRouter (when available) & local memory store
    3. Reflects on accumulated patterns / knowledge graph
    4. Proposes reusable skills from observed workflows
    """

    def __init__(self, agent_id: str = "autonomous-001", config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_id, config or {})
        self.name = "Autonomous Learning Agent"
        self.category = "core"
        self.description = "Observes interactions, persists memory/preferences, reflects on history, and proposes reusable skills."
        self.capabilities = [
            "memory_persistence",
            "behavior_learning",
            "skill_generation",
            "reflection",
        ]
        self._memories: List[Dict[str, Any]] = []
        self.router = None
        if not self.config.get("disable_router", False):
            try:
                from ...ai.auto_learning_router import LearningDataRouter

                self.router = LearningDataRouter()
            except Exception as exc:
                logger.warning("LearningDataRouter unavailable; running with local memory store: %s", exc)
                self.router = None

    async def can_handle(self, task: Task) -> bool:
        """Check if task involves memory persistence, reflection, preferences, or skill generation."""
        desc = (task.description or "").lower()
        keywords = [
            "remember", "learn", "reflect", "what did i say",
            "my preferences", "save this", "propose skill", "skill", "memorize",
        ]
        return any(kw in desc for kw in keywords)

    async def execute(self, task: Task) -> TaskResult:
        """Execute memory, reflection, or skill-generation task."""
        desc = (task.description or "").lower()
        params = task.params or {}
        req_caps = set(c.lower() for c in (task.required_capabilities or []))

        try:
            if "skill_generation" in req_caps or any(k in desc for k in ("propose skill", "generate skill", "create skill", "learn skill")):
                return await self._generate_skill(task)

            if "reflection" in req_caps or any(k in desc for k in ("reflect", "what did i say", "preferences", "recall", "what do you know")):
                return await self._reflect(task)

            content = str(params.get("content") or params.get("memory") or task.description).strip()
            importance = 5 if ("remember" in desc or "save this" in desc or "memorize" in desc) else int(params.get("importance", 3))
            category = str(params.get("category", "command" if importance >= 5 else "general"))

            entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "speaker": str(params.get("speaker", "user")),
                "content": content,
                "category": category,
                "importance": importance,
            }
            self._memories.append(entry)

            if self.router is not None:
                await asyncio.to_thread(
                    self.router.route_conversation,
                    speaker=entry["speaker"],
                    content=content,
                    category=category,
                    importance=importance,
                    success=True,
                )

            msg = (
                "Memory explicitly saved to Knowledge Graph and memory store."
                if importance >= 5
                else "Observation logged to Autonomous Learning Loop."
            )
            return TaskResult(
                success=True,
                data={
                    "message": msg,
                    "summary": msg,
                    "output": content,
                    "memory_count": len(self._memories),
                },
            )
        except Exception as exc:
            return TaskResult(success=False, error=str(exc))

    async def _reflect(self, task: Task) -> TaskResult:
        """Reflect over saved memories, LearningDataRouter stats, and upstream context."""
        stats: Dict[str, Any] = {}
        history: List[Dict[str, Any]] = list(self._memories)

        if self.router is not None:
            try:
                stats = await asyncio.to_thread(self.router.get_routing_stats)
                router_hist = getattr(self.router, "conversation_history", [])
                if isinstance(router_hist, list):
                    for item in router_hist[-20:]:
                        if item not in history:
                            history.append(item)
            except Exception as exc:
                logger.debug("Router stats unavailable during reflection: %s", exc)

        recent_items = [str(m.get("content", "")) for m in history[-10:] if m.get("content")]
        query = (task.params or {}).get("query") or task.description
        matches = [c for c in recent_items if any(w in c.lower() for w in query.lower().split() if len(w) > 3)]

        reflection = await self.chat_llm(
            f"Reflect on these recorded user memories and answer '{query}'.\nMemories:\n" + "\n".join(f"- {m}" for m in recent_items[-10:]),
            system_message="You summarize learned user preferences and factual memories accurately.",
        )
        if not reflection:
            if matches:
                reflection = "Matching memories found:\n" + "\n".join(f"- {m}" for m in matches[:5])
            elif recent_items:
                reflection = f"Recorded {len(recent_items)} memory item(s). Most recent: {recent_items[-1]}"
            else:
                reflection = "No stored memories recorded yet in this session."

        return TaskResult(
            success=True,
            data={
                "message": "Reflection complete.",
                "summary": reflection[:240],
                "output": reflection,
                "text": reflection,
                "memories": recent_items,
                "learning_stats": stats,
            },
        )

    async def _generate_skill(self, task: Task) -> TaskResult:
        """Propose a structured reusable skill/workflow from observed patterns or description."""
        upstream = self._extract_upstream_text(task)
        recent = [m.get("content", "") for m in self._memories[-5:]]
        prompt = (
            f"Propose a reusable agent skill JSON specification (keys: name, trigger_keywords, steps, required_capabilities) "
            f"for:\n{task.description}\nContext:\n{upstream}\nRecent observations:\n{recent}"
        )
        llm_out = await self.chat_llm(prompt, system_message="You design modular assistant workflow skills.")

        blueprint: Dict[str, Any] = {
            "name": f"skill_{task.task_id[:6]}",
            "description": task.description,
            "steps": ["analyze_input", "execute_action", "verify_output"],
            "observations_used": len(recent),
        }
        if llm_out:
            try:
                raw = llm_out.split("```json", 1)[1].split("```", 1)[0] if "```json" in llm_out else llm_out
                parsed = json.loads(raw.strip())
                if isinstance(parsed, dict):
                    blueprint = parsed
            except Exception:
                blueprint["rationale"] = llm_out

        text_out = json.dumps(blueprint, indent=2)
        return TaskResult(
            success=True,
            data={
                "skill": blueprint,
                "output": text_out,
                "summary": f"Proposed skill '{blueprint.get('name', 'custom_skill')}'",
                "message": "Skill proposal generated",
            },
        )

    def passive_observe(self, speaker: str, content: str, category: str = "general") -> None:
        """Passively record an observation without running an async Task."""
        self._memories.append({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "speaker": speaker,
            "content": content,
            "category": category,
            "importance": 3,
        })
        if self.router is not None:
            try:
                self.router.route_conversation(
                    speaker=speaker,
                    content=content,
                    category=category,
                    importance=3,
                    success=True,
                )
            except Exception as exc:
                logger.debug("Passive router observe failed: %s", exc)
