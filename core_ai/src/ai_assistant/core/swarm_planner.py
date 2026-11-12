"""
Swarm Planner — Dynamic Meta-Planner & Workflow Synthesizer
Transforms novel, unlisted, and complex multi-domain user goals into validated,
parallelized Execution DAGs using the 14 specialized Pulsar agents.

Key Features:
1. Dynamic Agent Capability Manifest with strict Input/Output contracts
2. Typed DAG Models (WorkflowStep, WorkflowWave, WorkflowPlan)
3. Topological Cycle Detection & Dependency Verification (Kahn's Algorithm)
4. Runtime Self-Healing Re-Planner (re-routes on agent failures)
5. Deterministic Offline Fallback Planner
"""

import json
import logging
import re
import uuid
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CONTRACTS & DAG MODELS
# =============================================================================

@dataclass
class WorkflowStep:
    """A single atomic step executed by a specialized agent."""
    step_id: str
    agent_id: str
    capability: str
    task: str
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    output_key: str = ""
    requires_confirmation: bool = False
    fallback_agent_id: Optional[str] = None

    def __post_init__(self):
        if not self.output_key:
            self.output_key = self.step_id
        if self.depends_on is None:
            self.depends_on = []
        if self.params is None:
            self.params = {}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowWave:
    """A collection of independent steps that can be safely executed in parallel."""
    wave_number: int
    steps: List[WorkflowStep] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wave_number": self.wave_number,
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass
class WorkflowPlan:
    """Full execution blueprint for an unlisted or novel multi-agent goal."""
    workflow_id: str
    workflow_name: str
    user_goal: str
    reasoning: str
    waves: List[WorkflowWave] = field(default_factory=list)
    all_steps: List[WorkflowStep] = field(default_factory=list)
    estimated_duration_sec: float = 30.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "user_goal": self.user_goal,
            "reasoning": self.reasoning,
            "waves": [w.to_dict() for w in self.waves],
            "all_steps": [s.to_dict() for s in self.all_steps],
            "estimated_duration_sec": self.estimated_duration_sec,
            "created_at": self.created_at,
        }


# =============================================================================
# AGENT CAPABILITY MANIFEST (14 Specialized Agents)
# =============================================================================

AGENT_CAPABILITY_CONTRACTS: Dict[str, Dict[str, Any]] = {
    "productivity-001": {
        "name": "Productivity Agent",
        "description": "Word, Excel, PowerPoint, PDF generation, document editing, and format conversion",
        "capabilities": [
            "create_word_document", "create_excel_spreadsheet",
            "create_powerpoint", "create_pdf", "edit_document", "convert_formats"
        ],
        "inputs": ["title", "topic", "content", "tables", "images", "output_path"],
        "outputs": ["docx_path", "pptx_path", "xlsx_path", "pdf_path", "file_path"],
        "sensitive": False,
    },
    "research-001": {
        "name": "Research Agent",
        "description": "Fast web searches, Wikipedia lookups, web scraping, and factual queries",
        "capabilities": [
            "web_search", "wikipedia_summary", "scrape_url", "research_topic"
        ],
        "inputs": ["query", "url", "keywords", "topic"],
        "outputs": ["summary", "content", "sources", "results"],
        "sensitive": False,
    },
    "deep-research-001": {
        "name": "Deep Research Agent",
        "description": "Comprehensive multi-query deep research, market analysis, and exhaustive synthesis",
        "capabilities": [
            "deep_research", "social_synthesis", "multi_source_scrape"
        ],
        "inputs": ["topic", "research_depth", "sources_limit"],
        "outputs": ["synthesis", "report", "cited_sources"],
        "sensitive": False,
    },
    "writer-001": {
        "name": "Writer Agent",
        "description": "Professional articles, blog posts, email drafts, executive summaries, and proofreading",
        "capabilities": [
            "write_article", "summarize_text", "draft_email", "proofread", "creative_writing"
        ],
        "inputs": ["topic", "context", "tone", "raw_notes", "format"],
        "outputs": ["article_text", "email_subject", "email_body", "summary", "text"],
        "sensitive": False,
    },
    "creative-001": {
        "name": "Creative Agent",
        "description": "AI image generation, graphic design, banners, thumbnails, and voiceover audio",
        "capabilities": [
            "generate_image", "create_art", "design_layout", "image_editing", "generate_voiceover"
        ],
        "inputs": ["prompt", "style", "dimensions", "aspect_ratio", "text"],
        "outputs": ["image_path", "artwork_url", "voiceover_path"],
        "sensitive": False,
    },
    "video-001": {
        "name": "Video Agent",
        "description": "Video editing, transcription, audio extraction, thumbnail creation, GUI app automation",
        "capabilities": [
            "create_video", "edit_video", "transcribe_video", "extract_audio",
            "create_thumbnail", "add_subtitles", "control_external_app"
        ],
        "inputs": ["video_path", "timestamps", "audio_path", "script"],
        "outputs": ["output_video_path", "transcript", "thumbnail_path"],
        "sensitive": False,
    },
    "audio-001": {
        "name": "Audio Agent",
        "description": "Whisper speech-to-text, KittenTTS/EdgeTTS voice synthesis, audio cleaning and music",
        "capabilities": [
            "transcribe_audio", "synthesize_speech", "text_to_speech", "edit_audio",
            "audio_processing", "generate_music", "generate_sfx", "clean_audio"
        ],
        "inputs": ["audio_path", "text", "voice", "clean_noise"],
        "outputs": ["transcript", "audio_path", "cleaned_audio_path"],
        "sensitive": False,
    },
    "data-001": {
        "name": "Data Analyst Agent",
        "description": "CSV/JSON tabular analysis, statistical modeling, and Matplotlib chart generation",
        "capabilities": [
            "analyze_data", "visualize_data", "create_chart", "statistical_analysis"
        ],
        "inputs": ["data", "csv_path", "chart_type", "title", "columns", "x_axis", "y_axis"],
        "outputs": ["summary_stats", "chart_image_path", "insights"],
        "sensitive": False,
    },
    "database-001": {
        "name": "Database Agent",
        "description": "SQLite/SQL query execution, schema inspection, joins, and table migrations",
        "capabilities": [
            "query_database", "manage_schema", "optimize_query", "db_migration", "sql_analysis"
        ],
        "inputs": ["query", "table_name", "db_path", "params"],
        "outputs": ["query_results", "row_count", "schema"],
        "sensitive": True,
    },
    "comm-001": {
        "name": "Communication Agent",
        "description": "Email sending, messaging (WhatsApp/Slack), and calendar schedule management",
        "capabilities": [
            "send_email", "send_message", "schedule_meeting", "manage_calendar", "post_social"
        ],
        "inputs": ["recipient", "subject", "body", "attachments", "date", "time"],
        "outputs": ["status", "sent_at", "event_id"],
        "sensitive": True,  # Critical action gate
    },
    "web-001": {
        "name": "Web Agent",
        "description": "Interactive browser automation, form filling, web portal monitoring, dynamic scraping",
        "capabilities": [
            "browse_web", "interact_page", "fill_form", "monitor_site", "scrape_dynamic"
        ],
        "inputs": ["url", "actions", "form_fields", "target_selector"],
        "outputs": ["page_content", "screenshot_path", "status"],
        "sensitive": False,
    },
    "student-001": {
        "name": "Student Agent",
        "description": "Math problem solving, study notes, interactive flashcards, local RAG question answering",
        "capabilities": [
            "learn_topic", "take_notes", "summarize_learning", "create_flashcards",
            "study_folder", "answer_exam_questions", "solve_math"
        ],
        "inputs": ["topic", "question", "notes", "folder_path", "equations"],
        "outputs": ["notes", "flashcards", "solution", "explanation"],
        "sensitive": False,
    },
    "file-001": {
        "name": "File Manager Agent",
        "description": "Local file search, folder organization, moving, renaming, disk cleanup, and backups",
        "capabilities": [
            "organize_files", "search_files", "move_files", "backup_files", "rename_files", "list_files"
        ],
        "inputs": ["source", "destination", "pattern", "directory", "files"],
        "outputs": ["found_files", "destination_path", "backup_archive"],
        "sensitive": True,
    },
    "autonomous-001": {
        "name": "Autonomous Learning Agent",
        "description": "Long-term preference memory, user habit observation, macro recipe persistence, reflection",
        "capabilities": [
            "memory_persistence", "behavior_learning", "skill_generation", "reflection"
        ],
        "inputs": ["memory_key", "value", "workflow_recipe", "feedback"],
        "outputs": ["saved_status", "learned_skill_id"],
        "sensitive": False,
    },
}


# =============================================================================
# SWARM PLANNER CLASS
# =============================================================================

class SwarmPlanner:
    """
    Intelligent Meta-Planner that synthesizes multi-agent DAGs for novel goals.
    
    Guarantees:
    - Zero LLM tokens for simple commands (checked upstream by IntentRouter)
    - Pydantic/Typed DAG wave structure
    - Kahn's algorithm cycle prevention
    - Dynamic reflection re-planning on runtime step failure
    - Fallback deterministic planning when offline
    """

    def __init__(self, registry=None, llm_provider=None):
        self.registry = registry
        self.llm_provider = llm_provider

    def _get_registry(self):
        if self.registry is None:
            from ai_assistant.agents.loader import get_global_registry
            self.registry = get_global_registry()
        return self.registry

    def _get_llm(self):
        if self.llm_provider is not None:
            return self.llm_provider
        try:
            from ai_assistant.ai.llm_provider import UnifiedChatInterface
            self.llm_provider = UnifiedChatInterface(use_fallback=True)
            return self.llm_provider
        except Exception as exc:
            logger.debug(f"SwarmPlanner LLM provider load failed: {exc}")
            return None

    def build_agent_manifest_text(self) -> str:
        """Serialize the 14 agents into a high-density LLM capability summary."""
        lines = []
        for aid, data in AGENT_CAPABILITY_CONTRACTS.items():
            lines.append(
                f"- Agent ID: `{aid}` | Name: {data['name']}\n"
                f"  Capabilities: {', '.join(data['capabilities'])}\n"
                f"  Accepted Inputs: {', '.join(data['inputs'])}\n"
                f"  Produced Outputs: {', '.join(data['outputs'])}\n"
                f"  Critical/Confirmation Needed: {data['sensitive']}"
            )
        return "\n".join(lines)

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        llm = self._get_llm()
        if llm is None:
            return None

        generate_fn = getattr(llm, "generate", None)
        if callable(generate_fn):
            try:
                import asyncio
                prompt = f"{system_prompt}\n\nTask:\n{user_prompt}"
                if asyncio.iscoroutinefunction(generate_fn):
                    res = await generate_fn(prompt)
                else:
                    res = await asyncio.to_thread(generate_fn, prompt)
                txt = str(res or "").strip()
                if txt and not txt.startswith("Error:"):
                    return txt
            except Exception as e:
                logger.debug(f"SwarmPlanner llm.generate failed: {e}")

        chat_fn = getattr(llm, "chat", None)
        if callable(chat_fn):
            try:
                import asyncio
                def _run():
                    if hasattr(llm, "set_system_message"):
                        llm.set_system_message(system_prompt)
                    return str(chat_fn(user_prompt) or "")
                res = (await asyncio.to_thread(_run)).strip()
                if res and not res.startswith("Error:"):
                    return res
            except Exception as e:
                logger.debug(f"SwarmPlanner llm.chat failed: {e}")

        return None

    @staticmethod
    def _clean_json_output(raw: str) -> Optional[Dict[str, Any]]:
        txt = raw.strip()
        if "```json" in txt:
            txt = txt.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in txt:
            txt = txt.split("```", 1)[1].split("```", 1)[0].strip()

        try:
            parsed = json.loads(txt)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        match = re.search(r"\{.*\}", txt, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        return None

    # =========================================================================
    # CORE PLANNING METHOD
    # =========================================================================

    async def plan_workflow(self, user_goal: str) -> WorkflowPlan:
        """
        Synthesize a structured WorkflowPlan DAG for the given novel user goal.
        """
        manifest_text = self.build_agent_manifest_text()
        system_prompt = (
            "You are the Master Swarm Architect for Pulsar AI Assistant.\n"
            "Your objective is to decompose an unlisted or novel complex user request into a strictly ordered DAG of agent actions.\n\n"
            "AVAILABLE SPECIALIZED AGENTS:\n"
            f"{manifest_text}\n\n"
            "RULES:\n"
            "1. Parallel Execution: Independent steps MUST have depends_on: [] so they execute simultaneously in Wave 1.\n"
            "2. Dependent Execution: If Step B requires data from Step A, set depends_on: [\"step_a_id\"] and reference output placeholders like `{step_a_id.output}` or `{step_a_id.output_path}`.\n"
            "3. High Precision: Pick the exact canonical agent_id and matching capability.\n"
            "4. Confirmation Gates: If an action sends real emails or modifies/deletes files, set requires_confirmation: true.\n"
            "5. Output Format: Reply ONLY with valid JSON matching this schema:\n"
            "{\n"
            '  "workflow_name": "Concise_Name",\n'
            '  "reasoning": "Why this multi-agent breakdown was chosen",\n'
            '  "estimated_duration_sec": 25.0,\n'
            '  "steps": [\n'
            '    {\n'
            '      "step_id": "step_1",\n'
            '      "agent_id": "research-001",\n'
            '      "capability": "research_topic",\n'
            '      "task": "Specific instructions for agent",\n'
            '      "params": {"topic": "AI trends 2024"},\n'
            '      "depends_on": [],\n'
            '      "output_key": "step_1_summary",\n'
            '      "requires_confirmation": false,\n'
            '      "fallback_agent_id": "deep-research-001"\n'
            '    }\n'
            "  ]\n"
            "}\n"
        )

        llm_raw = await self._call_llm(system_prompt, user_goal)
        if llm_raw:
            data = self._clean_json_output(llm_raw)
            if data and data.get("steps"):
                plan = self._construct_plan_from_data(data, user_goal)
                if plan and plan.all_steps:
                    return plan

        # Fallback to deterministic decomposition
        logger.info(f"SwarmPlanner falling back to deterministic planning for: '{user_goal}'")
        return await self._fallback_plan(user_goal)

    def _construct_plan_from_data(self, data: Dict[str, Any], user_goal: str) -> Optional[WorkflowPlan]:
        raw_steps = data.get("steps") or []
        if not isinstance(raw_steps, list) or not raw_steps:
            return None

        workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        workflow_name = str(data.get("workflow_name") or "Dynamic_Multi_Agent_Workflow")
        reasoning = str(data.get("reasoning") or "Decomposed by Swarm Planner")
        est_duration = float(data.get("estimated_duration_sec") or 30.0)

        steps: List[WorkflowStep] = []
        for idx, s in enumerate(raw_steps):
            if not isinstance(s, dict):
                continue
            step_id = str(s.get("step_id") or f"step_{idx + 1}")
            raw_aid = str(s.get("agent_id") or "").strip()
            
            # Resolve canonical agent ID
            aid = raw_aid
            reg = self._get_registry()
            if reg:
                resolved = reg.resolve_agent_id(raw_aid)
                if resolved:
                    aid = resolved
            # If aid is in AGENT_CAPABILITY_CONTRACTS, great!
            # If not in AGENT_CAPABILITY_CONTRACTS, but exists in reg (e.g. custom/dynamic agent), keep aid!
            # Only if it's completely unresolvable, fallback to research-001
            if aid not in AGENT_CAPABILITY_CONTRACTS:
                if reg and (reg.get_agent(aid) is not None or reg.get_agent_dto(aid) is not None):
                    pass  # Valid dynamically registered agent in registry!
                else:
                    aid = "research-001"  # Default safe agent

            cap_choices = AGENT_CAPABILITY_CONTRACTS.get(aid, {}).get("capabilities", [])
            cap = str(s.get("capability") or (cap_choices[0] if cap_choices else "execute"))
            task = str(s.get("task") or user_goal)
            params = dict(s.get("params") or {})
            deps = [str(d) for d in (s.get("depends_on") or [])]
            out_key = str(s.get("output_key") or step_id)
            is_sensitive = AGENT_CAPABILITY_CONTRACTS.get(aid, {}).get("sensitive", False)
            req_confirm = bool(s.get("requires_confirmation", is_sensitive))
            fallback = s.get("fallback_agent_id")

            step = WorkflowStep(
                step_id=step_id,
                agent_id=aid,
                capability=cap,
                task=task,
                params=params,
                depends_on=deps,
                output_key=out_key,
                requires_confirmation=req_confirm,
                fallback_agent_id=fallback,
            )
            steps.append(step)

        if not steps:
            return None

        # Topological sorting & cycle prevention
        waves = self._build_waves_from_steps(steps)
        if waves is None:
            logger.error("Cyclic dependency detected in LLM plan. Falling back.")
            return None

        return WorkflowPlan(
            workflow_id=workflow_id,
            workflow_name=workflow_name,
            user_goal=user_goal,
            reasoning=reasoning,
            waves=waves,
            all_steps=steps,
            estimated_duration_sec=est_duration,
        )

    # =========================================================================
    # TOPOLOGICAL SORTING & WAVE BUILDER (KAHN'S ALGORITHM)
    # =========================================================================

    @staticmethod
    def _build_waves_from_steps(steps: List[WorkflowStep]) -> Optional[List[WorkflowWave]]:
        """
        Build parallel execution waves using Kahn's topological sort.
        Returns None if a cycle is detected.
        """
        step_map = {s.step_id: s for s in steps}
        indegree = {s.step_id: 0 for s in steps}
        graph: Dict[str, List[str]] = {s.step_id: [] for s in steps}

        for s in steps:
            valid_deps = [d for d in s.depends_on if d in step_map]
            s.depends_on = valid_deps
            indegree[s.step_id] = len(valid_deps)
            for d in valid_deps:
                graph[d].append(s.step_id)

        waves: List[WorkflowWave] = []
        pending = dict(indegree)
        wave_num = 1

        while pending:
            # Nodes with in-degree 0 are ready to execute in parallel
            ready_step_ids = [sid for sid, deg in pending.items() if deg == 0]
            if not ready_step_ids:
                # Cycle detected!
                return None

            wave_steps = [step_map[sid] for sid in ready_step_ids]
            waves.append(WorkflowWave(wave_number=wave_num, steps=wave_steps))
            wave_num += 1

            for sid in ready_step_ids:
                del pending[sid]
                for neighbor in graph[sid]:
                    if neighbor in pending:
                        pending[neighbor] -= 1

        return waves

    # =========================================================================
    # DETERMINISTIC OFFLINE FALLBACK PLANNER
    # =========================================================================

    async def _fallback_plan(self, user_goal: str) -> WorkflowPlan:
        """
        Fallback parser that segments user_goal using multi-step connectors
        and assigns the best agent for each segment.
        """
        clauses = [
            c.strip()
            for c in re.split(r"\s*(?:;|->|\band then\b|\bthen\b|\baur phir\b|\buske baad\b)\s*", user_goal, flags=re.IGNORECASE)
            if c.strip()
        ]
        if not clauses:
            clauses = [user_goal.strip()]

        reg = self._get_registry()
        steps: List[WorkflowStep] = []
        prev_id: Optional[str] = None

        for idx, clause in enumerate(clauses):
            step_id = f"step_{idx + 1}"
            clause_lower = clause.lower()
            aid = "research-001"
            cap = "research_topic"

            # 1. Check if registry has custom matching agents for this clause
            if reg:
                try:
                    from ai_assistant.agents.models import Task
                    matched = await reg.find_best_agent(Task(description=clause))
                    if matched and (matched.agent_id.lower() in clause_lower or matched.name.lower() in clause_lower):
                        aid = matched.agent_id
                        matched_caps = getattr(matched, "capabilities", [])
                        cap = matched_caps[0] if matched_caps else "execute"
                except Exception:
                    pass

            # 2. Check keyword heuristics if still default
            if aid == "research-001":
                if any(w in clause_lower for w in ["chart", "plot", "graph", "analyze data", "statistics", "csv"]):
                    aid = "data-001"
                    cap = "analyze_data"
                elif any(w in clause_lower for w in ["ppt", "presentation", "powerpoint", "word", "docx", "pdf", "sheet", "excel"]):
                    aid = "productivity-001"
                    cap = "create_powerpoint" if "ppt" in clause_lower or "presentation" in clause_lower else "create_word_document"
                elif any(w in clause_lower for w in ["email", "draft email", "mail", "whatsapp", "message"]):
                    aid = "comm-001"
                    cap = "send_email" if "send" in clause_lower else "draft_email"
                elif any(w in clause_lower for w in ["search", "google", "find on web", "wikipedia"]):
                    aid = "research-001"
                    cap = "web_search"
                elif any(w in clause_lower for w in ["in-depth", "deep research", "comprehensive"]):
                    aid = "deep-research-001"
                    cap = "deep_research"
                elif any(w in clause_lower for w in ["write", "article", "blog", "summary", "summarize"]):
                    aid = "writer-001"
                    cap = "write_article"
                elif any(w in clause_lower for w in ["file", "folder", "directory", "backup", "organize"]):
                    aid = "file-001"
                    cap = "organize_files"

            deps = [prev_id] if prev_id else []
            is_sensitive = AGENT_CAPABILITY_CONTRACTS.get(aid, {}).get("sensitive", False)
            step = WorkflowStep(
                step_id=step_id,
                agent_id=aid,
                capability=cap,
                task=clause,
                params={"query": clause, "topic": clause},
                depends_on=deps,
                output_key=step_id,
                requires_confirmation=is_sensitive,
            )
            steps.append(step)
            prev_id = step_id

        waves = self._build_waves_from_steps(steps) or [WorkflowWave(wave_number=1, steps=steps)]
        return WorkflowPlan(
            workflow_id=f"wf-fallback-{uuid.uuid4().hex[:6]}",
            workflow_name="Deterministic_Fallback_Workflow",
            user_goal=user_goal,
            reasoning="Constructed using keyword heuristics and sequential connectors",
            waves=waves,
            all_steps=steps,
            estimated_duration_sec=float(len(steps) * 8),
        )

    # =========================================================================
    # RUNTIME SELF-HEALING & RE-PLANNING
    # =========================================================================

    async def replan_failed_step(
        self,
        failed_step: WorkflowStep,
        error_message: str,
        user_goal: str,
        completed_results: Dict[str, Any],
        remaining_steps: List[WorkflowStep],
    ) -> Optional[WorkflowStep]:
        """
        Dynamically synthesize an alternative step when a step fails at runtime.
        Returns a replacement WorkflowStep or None if unrecoverable.
        """
        logger.warning(
            f"🩹 [SELF-HEALING] Re-planning failed step '{failed_step.step_id}' "
            f"({failed_step.agent_id}): {error_message}"
        )

        # 1. Immediate Fallback if explicit fallback_agent_id was designated
        if failed_step.fallback_agent_id and failed_step.fallback_agent_id in AGENT_CAPABILITY_CONTRACTS:
            fallback_aid = failed_step.fallback_agent_id
            logger.info(f"🩹 [SELF-HEALING] Using designated fallback agent: '{fallback_aid}'")
            return WorkflowStep(
                step_id=failed_step.step_id,
                agent_id=fallback_aid,
                capability=AGENT_CAPABILITY_CONTRACTS[fallback_aid]["capabilities"][0],
                task=failed_step.task,
                params=dict(failed_step.params),
                depends_on=list(failed_step.depends_on),
                output_key=failed_step.output_key,
                requires_confirmation=AGENT_CAPABILITY_CONTRACTS[fallback_aid]["sensitive"],
                fallback_agent_id=None,
            )

        # 2. Ask LLM for dynamic re-route
        manifest_text = self.build_agent_manifest_text()
        system_prompt = (
            "You are the Pulsar Self-Healing Recovery Engine.\n"
            "An agent step in an active swarm execution failed. You must provide a single replacement step using an alternate agent or modified parameters.\n\n"
            f"AVAILABLE AGENTS:\n{manifest_text}\n\n"
            "FAILED STEP DETAILS:\n"
            f"- Step ID: {failed_step.step_id}\n"
            f"- Failed Agent ID: {failed_step.agent_id}\n"
            f"- Capability: {failed_step.capability}\n"
            f"- Task: {failed_step.task}\n"
            f"- Error Message: {error_message}\n\n"
            "Reply ONLY with JSON for the replacement step:\n"
            "{\n"
            '  "replacement_step": {\n'
            f'    "step_id": "{failed_step.step_id}",\n'
            '    "agent_id": "alternate-agent-id",\n'
            '    "capability": "alternate_capability",\n'
            '    "task": "Revised instructions avoiding the error",\n'
            '    "params": {}\n'
            '  }\n'
            "}\n"
        )

        user_prompt = f"Goal: {user_goal}\nError: {error_message}"
        llm_raw = await self._call_llm(system_prompt, user_prompt)
        if llm_raw:
            data = self._clean_json_output(llm_raw)
            if data and data.get("replacement_step"):
                rs = data["replacement_step"]
                aid = str(rs.get("agent_id") or "")
                if aid in AGENT_CAPABILITY_CONTRACTS and aid != failed_step.agent_id:
                    cap = str(rs.get("capability") or AGENT_CAPABILITY_CONTRACTS[aid]["capabilities"][0])
                    logger.info(f"🩹 [SELF-HEALING] LLM provided replacement agent: '{aid}'")
                    return WorkflowStep(
                        step_id=failed_step.step_id,
                        agent_id=aid,
                        capability=cap,
                        task=str(rs.get("task") or failed_step.task),
                        params=dict(rs.get("params") or failed_step.params),
                        depends_on=list(failed_step.depends_on),
                        output_key=failed_step.output_key,
                        requires_confirmation=AGENT_CAPABILITY_CONTRACTS[aid]["sensitive"],
                        fallback_agent_id=None,
                    )

        # 3. Deterministic Alternative Agent Mapping
        default_alternatives = {
            "web-001": ("research-001", "research_topic"),
            "research-001": ("deep-research-001", "deep_research"),
            "deep-research-001": ("research-001", "web_search"),
            "writer-001": ("student-001", "summarize_learning"),
            "data-001": ("database-001", "sql_analysis"),
            "audio-001": ("video-001", "extract_audio"),
        }
        if failed_step.agent_id in default_alternatives:
            alt_aid, alt_cap = default_alternatives[failed_step.agent_id]
            logger.info(f"🩹 [SELF-HEALING] Deterministic fallback to '{alt_aid}' ({alt_cap})")
            return WorkflowStep(
                step_id=failed_step.step_id,
                agent_id=alt_aid,
                capability=alt_cap,
                task=failed_step.task,
                params=dict(failed_step.params),
                depends_on=list(failed_step.depends_on),
                output_key=failed_step.output_key,
                requires_confirmation=AGENT_CAPABILITY_CONTRACTS[alt_aid]["sensitive"],
                fallback_agent_id=None,
            )

        return None
