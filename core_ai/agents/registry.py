from dataclasses import dataclass, field
import logging
import re
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base_agent import BaseAgent
from .models import AgentStatus, Task

logger = logging.getLogger(__name__)

_DEFAULT_ALIASES: Dict[str, str] = {
    "productivity": "productivity-001",
    "research": "research-001",
    "writer": "writer-001",
    "video": "video-001",
    "creative": "creative-001",
    "creative_01": "creative-001",
    "data": "data-001",
    "data_analyst": "data-001",
    "data-analyst": "data-001",
    "database": "database-001",
    "comm": "comm-001",
    "communication": "comm-001",
    "communication_01": "comm-001",
    "web": "web-001",
    "web_01": "web-001",
    "student": "student-001",
    "student_01": "student-001",
    "file": "file-001",
    "file_01": "file-001",
    "file_manager": "file-001",
    "audio": "audio-001",
    "audio_01": "audio-001",
    "deep_research": "deep-research-001",
    "deep-research": "deep-research-001",
    "autonomous": "autonomous-001",
}


@dataclass
class AgentMetadata:
    """Metadata for a registered/lazy-loaded agent."""

    agent_id: str
    name: str
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    status: str = "standby"  # standby, active, error, offline
    category: str = "general"
    keywords: List[str] = field(default_factory=list)
    active_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    last_error: Optional[str] = None


class AgentRegistry:
    """Thread-safe registry for agents and capabilities with lazy loading support."""

    def __init__(self):
        self._lock = threading.RLock()
        self._active_agents: Dict[str, BaseAgent] = {}
        self._definitions: Dict[str, AgentMetadata] = {}
        self._factories: Dict[str, Callable[[], BaseAgent]] = {}
        self._capabilities: Dict[str, List[str]] = {}  # capability -> agent_ids
        self._aliases: Dict[str, str] = dict(_DEFAULT_ALIASES)

    def resolve_agent_id(self, agent_id: str) -> str:
        """Resolve short/legacy aliases to canonical agent_id if known."""
        if not agent_id:
            return agent_id
        with self._lock:
            if agent_id in self._definitions or agent_id in self._active_agents:
                return agent_id
            key = agent_id.strip().lower()
            if key in self._aliases:
                candidate = self._aliases[key]
                if candidate in self._definitions or candidate in self._active_agents:
                    return candidate
            # Partial prefix match fallback (e.g. "creative" -> "creative-001")
            for known_id, meta in self._definitions.items():
                if known_id.lower() == key or meta.name.lower() == key:
                    return known_id
        return agent_id

    def register_alias(self, alias: str, agent_id: str) -> None:
        with self._lock:
            self._aliases[alias.strip().lower()] = agent_id

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an already instantiated agent."""
        with self._lock:
            desc = getattr(agent, "description", "") or ""
            cat = getattr(agent, "category", "") or "general"
            caps = list(getattr(agent, "capabilities", []) or [])
            name = getattr(agent, "name", "") or agent.agent_id
            metadata = AgentMetadata(
                agent_id=agent.agent_id,
                name=name,
                description=desc,
                capabilities=caps,
                status="active",
                category=cat,
                active_tasks=getattr(agent, "active_tasks", 0),
                completed_tasks=getattr(agent, "completed_tasks", 0),
                failed_tasks=getattr(agent, "failed_tasks", 0),
            )
            self._definitions[agent.agent_id] = metadata
            self._active_agents[agent.agent_id] = agent
            self._register_capabilities(agent.agent_id, caps)
            logger.info("Registered active agent: %s (%s)", name, agent.agent_id)

    def register_agent_definition(
        self,
        metadata: AgentMetadata,
        factory: Callable[[], BaseAgent],
    ) -> None:
        """Register an agent definition for lazy loading."""
        with self._lock:
            self._definitions[metadata.agent_id] = metadata
            self._factories[metadata.agent_id] = factory
            self._register_capabilities(metadata.agent_id, metadata.capabilities)
            logger.debug("Registered agent definition: %s (%s)", metadata.name, metadata.agent_id)

    def unregister_agent(self, agent_id: str) -> bool:
        """Remove an agent from active & definition maps."""
        resolved = self.resolve_agent_id(agent_id)
        with self._lock:
            removed = False
            if resolved in self._active_agents:
                del self._active_agents[resolved]
                removed = True
            if resolved in self._definitions:
                del self._definitions[resolved]
                removed = True
            if resolved in self._factories:
                del self._factories[resolved]
                removed = True
            for cap, ids in list(self._capabilities.items()):
                if resolved in ids:
                    ids.remove(resolved)
                if not ids:
                    del self._capabilities[cap]
            return removed

    def _register_capabilities(self, agent_id: str, capabilities: List[str]) -> None:
        for cap in capabilities:
            if cap not in self._capabilities:
                self._capabilities[cap] = []
            if agent_id not in self._capabilities[cap]:
                self._capabilities[cap].append(agent_id)

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID or alias, lazy-instantiating if necessary."""
        resolved = self.resolve_agent_id(agent_id)
        with self._lock:
            if resolved in self._active_agents:
                return self._active_agents[resolved]
            factory = self._factories.get(resolved)
            meta = self._definitions.get(resolved)

        if factory is None:
            return None

        try:
            logger.info("Lazy loading agent: %s...", resolved)
            agent = factory()
            # Ensure canonical agent_id consistency
            if agent.agent_id != resolved:
                agent.agent_id = resolved
            if meta:
                if not getattr(agent, "description", "") and meta.description:
                    agent.description = meta.description
                if not getattr(agent, "category", "") and meta.category:
                    agent.category = meta.category
                if not getattr(agent, "capabilities", None) and meta.capabilities:
                    agent.capabilities = list(meta.capabilities)
                elif getattr(agent, "capabilities", None):
                    merged = list(dict.fromkeys([*meta.capabilities, *agent.capabilities]))
                    meta.capabilities = merged
                    agent.capabilities = merged

            with self._lock:
                self._active_agents[resolved] = agent
                if resolved in self._definitions:
                    self._definitions[resolved].status = "active"
                    self._definitions[resolved].last_error = None
                self._register_capabilities(resolved, list(agent.capabilities))

            logger.info("Agent %s loaded successfully", resolved)
            return agent
        except Exception as exc:
            logger.error("Failed to lazy load agent %s: %s", resolved, exc, exc_info=True)
            with self._lock:
                if resolved in self._definitions:
                    self._definitions[resolved].status = "error"
                    self._definitions[resolved].last_error = str(exc)
            return None

    def get_all_agents(self) -> List[BaseAgent]:
        """Get all currently ACTIVE agent instances."""
        with self._lock:
            return list(self._active_agents.values())

    def get_all_metadata(self) -> List[AgentMetadata]:
        """Get metadata for ALL agents (active and standby)."""
        with self._lock:
            return list(self._definitions.values())

    def find_agents_by_capability(self, capability: str) -> List[str]:
        """Find agent IDs that declare a specific capability."""
        with self._lock:
            if capability in self._capabilities:
                return list(self._capabilities[capability])
            cap_low = capability.lower()
            matched: List[str] = []
            for cap_key, ids in self._capabilities.items():
                if cap_low == cap_key.lower() or cap_low in cap_key.lower():
                    for aid in ids:
                        if aid not in matched:
                            matched.append(aid)
            return matched

    def get_capabilities_map(self) -> Dict[str, List[str]]:
        """Return mapping of capability -> list of agent_ids."""
        with self._lock:
            return {k: list(v) for k, v in self._capabilities.items()}

    def _meta_to_dto(self, meta: AgentMetadata) -> Dict[str, Any]:
        agent = self._active_agents.get(meta.agent_id)
        if agent is not None:
            dto = agent.to_dto()
            if not dto["description"] and meta.description:
                dto["description"] = meta.description
            if dto["category"] == "general" and meta.category:
                dto["category"] = meta.category
            return dto

        status_str = "idle"
        if meta.status == "error":
            status_str = "error"
        elif meta.status == "offline":
            status_str = "offline"

        return {
            "id": meta.agent_id,
            "name": meta.name,
            "category": meta.category or "general",
            "description": meta.description or "",
            "capabilities": list(meta.capabilities),
            "status": status_str,
            "active_tasks": meta.active_tasks,
            "completed_tasks": meta.completed_tasks,
            "failed_tasks": meta.failed_tasks,
        }

    def list_agents_dto(self) -> List[Dict[str, Any]]:
        """Return canonical DTOs for all registered agents."""
        with self._lock:
            return [self._meta_to_dto(meta) for meta in self._definitions.values()]

    def get_agent_dto(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Return canonical DTO for a single agent."""
        resolved = self.resolve_agent_id(agent_id)
        with self._lock:
            meta = self._definitions.get(resolved)
            if meta is None:
                return None
            return self._meta_to_dto(meta)

    def _score_metadata(self, meta: AgentMetadata, task: Task) -> float:
        """Heuristic scoring over metadata capabilities, keywords, and description."""
        desc_lower = (task.description or "").lower()
        tokens = set(re.findall(r"[a-z0-9_]+", desc_lower))
        score = 0.0

        req_caps = set(c.lower() for c in (task.required_capabilities or []))
        own_caps = set(c.lower() for c in meta.capabilities)
        if req_caps and (req_caps & own_caps):
            score = max(score, 0.95)

        for cap in own_caps:
            if cap in desc_lower:
                score = max(score, 0.9)
                continue
            words = [w for w in cap.split("_") if len(w) > 2]
            if words and all(w in tokens for w in words):
                score = max(score, 0.85)
            elif any(w in tokens for w in words):
                score = max(score, 0.45)

        for kw in meta.keywords:
            kw_low = kw.lower()
            if " " in kw_low:
                if kw_low in desc_lower:
                    score = max(score, 0.78)
            elif kw_low in tokens or (len(kw_low) > 4 and kw_low in desc_lower):
                score = max(score, 0.65)

        desc_words = set(re.findall(r"[a-z0-9]{4,}", meta.description.lower()))
        overlap = tokens & desc_words
        if overlap:
            score = max(score, min(0.6, 0.25 + 0.1 * len(overlap)))

        return score

    async def find_ranked_agents(
        self,
        task: Task,
        include_standby: bool = True,
    ) -> List[Tuple[BaseAgent, float]]:
        """Find and rank candidate agents for a task (supports lazy loading)."""
        if task.target_agent_id:
            target = self.get_agent(task.target_agent_id)
            if target is not None:
                return [(target, 1.0)]

        with self._lock:
            metas = list(self._definitions.values())
            active_copy = dict(self._active_agents)

        # Score metadata first to find promising candidates without loading unrelated agents
        meta_scores: List[Tuple[str, float]] = []
        for meta in metas:
            if meta.status == "offline":
                continue
            ms = self._score_metadata(meta, task)
            if ms > 0:
                meta_scores.append((meta.agent_id, ms))

        meta_scores.sort(key=lambda item: item[1], reverse=True)

        candidate_ids: List[str] = [aid for aid, _ in meta_scores]
        if not candidate_ids:
            # Check all currently active agents first
            for aid in active_copy:
                if aid not in candidate_ids:
                    candidate_ids.append(aid)
            # If still empty and standby allowed, inspect all standby definitions
            if not candidate_ids and include_standby:
                candidate_ids = [m.agent_id for m in metas if m.status != "offline"]

        ranked: List[Tuple[BaseAgent, float]] = []
        seen = set()
        meta_score_map = dict(meta_scores)

        for aid in candidate_ids:
            if aid in seen:
                continue
            seen.add(aid)
            if aid not in active_copy and not include_standby:
                continue
            agent = self.get_agent(aid)
            if agent is None:
                continue

            agent_score = await agent.can_handle_score(task)
            meta_score = meta_score_map.get(aid, 0.0)
            if agent_score > 0:
                if meta_score > 0:
                    combined = min(1.0, (agent_score * 0.65) + (meta_score * 0.35))
                else:
                    combined = agent_score
            else:
                combined = 0.0

            if combined > 0:
                # Prefer idle agents over busy ones on near-ties
                if agent.status == AgentStatus.IDLE:
                    combined = min(1.0, combined + 0.03)
                elif agent.status in (AgentStatus.WORKING, AgentStatus.BUSY):
                    combined = max(0.01, combined - 0.05)
                ranked.append((agent, combined))

        # Fallback: if metadata heuristic picked candidates whose can_handle returned 0,
        # scan remaining agents when no valid match was found
        if not ranked and include_standby:
            for meta in metas:
                if meta.agent_id in seen or meta.status == "offline":
                    continue
                agent = self.get_agent(meta.agent_id)
                if agent is None:
                    continue
                score = await agent.can_handle_score(task)
                if score > 0:
                    if agent.status == AgentStatus.IDLE:
                        score = min(1.0, score + 0.03)
                    ranked.append((agent, score))

        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked

    async def find_best_agent(self, task: Task) -> Optional[BaseAgent]:
        """Find the highest-scoring agent for a task (triggers lazy load if needed)."""
        ranked = await self.find_ranked_agents(task, include_standby=True)
        if not ranked:
            return None
        return ranked[0][0]


def get_global_registry(eager: bool = False) -> AgentRegistry:
    """Convenience forwarder for loader.get_global_registry."""
    from .loader import get_global_registry as _get
    return _get(eager=eager)
