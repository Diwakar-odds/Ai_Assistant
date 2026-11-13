"""
Workflow Memory & Caching Engine
Implements the 'Never Think Twice' dimension:
Saves successfully executed multi-agent DAG plans as parameterized macro recipes.
When a semantically similar or identical task arrives, retrieves and binds parameters
in ~0ms, avoiding redundant LLM planning calls and minimizing API token expenditure.
"""

import os
import json
import sqlite3
import logging
import threading
import time
import re
from typing import Optional, Dict, Any, List
from pathlib import Path

from ai_assistant.core.swarm_planner import WorkflowPlan, WorkflowStep, WorkflowWave

logger = logging.getLogger(__name__)

_memory_lock = threading.RLock()
_workflow_memory_instance = None


def get_workflow_memory() -> "WorkflowMemory":
    global _workflow_memory_instance
    with _memory_lock:
        if _workflow_memory_instance is None:
            _workflow_memory_instance = WorkflowMemory()
        return _workflow_memory_instance


class WorkflowMemory:
    """
    Persistent store for learned Swarm Workflows.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            try:
                from ai_assistant.core.database_config import DATA_DIR
                db_path = str(DATA_DIR / "core" / "workflow_memory.db")
            except Exception:
                db_path = "data/core/workflow_memory.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_recipes (
                    id TEXT PRIMARY KEY,
                    normalized_pattern TEXT NOT NULL,
                    workflow_name TEXT NOT NULL,
                    plan_json TEXT NOT NULL,
                    tags TEXT,
                    success_count INTEGER DEFAULT 1,
                    last_used REAL,
                    created_at REAL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_workflow_pattern ON workflow_recipes(normalized_pattern)"
            )
            conn.commit()

    @staticmethod
    def normalize_query_to_pattern(query: str) -> str:
        """
        Normalize query into a generic structural pattern by abstracting entity tokens
        (file paths, urls, dates, numbers, quoted strings).
        """
        q = query.strip().lower()

        # Replace URLs FIRST before file paths
        q = re.sub(r'https?://[^\s]+', '<URL>', q)

        # Replace file paths with <FILE_PATH>
        q = re.sub(r'[a-zA-Z]:\\[^\s]+', '<FILE_PATH>', q)
        q = re.sub(r'(?:^|(?<=\s))/(?:[^\s]+)', '<FILE_PATH>', q)
        q = re.sub(r'[\w\-.]+\.(?:csv|xlsx?|docx?|pptx?|pdf|txt|png|jpe?g|mp3|mp4|json|py)\b', '<FILE_PATH>', q)

        # Replace quoted phrases with <TOPIC>
        q = re.sub(r'"[^"]+"', '<TOPIC>', q)
        q = re.sub(r"'[^']+'", '<TOPIC>', q)

        # Replace numbers
        q = re.sub(r'\b\d+\b', '<NUM>', q)

        # Strip extra whitespace and punctuation
        q = re.sub(r'[^\w\s<>]', ' ', q)
        q = re.sub(r'\s+', ' ', q).strip()
        return q

    def record_success(self, query: str, plan: WorkflowPlan):
        """
        Save or increment success count for a validated, successfully executed WorkflowPlan.
        """
        if not plan or not plan.all_steps:
            return

        pattern = self.normalize_query_to_pattern(query)
        plan_dict = plan.to_dict()
        now = time.time()

        with self._lock, self._get_connection() as conn:
            # Check if matching pattern exists
            cursor = conn.execute(
                "SELECT id, success_count FROM workflow_recipes WHERE normalized_pattern = ?",
                (pattern,)
            )
            row = cursor.fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE workflow_recipes 
                    SET success_count = success_count + 1, last_used = ?, plan_json = ?
                    WHERE id = ?
                    """,
                    (now, json.dumps(plan_dict), row["id"])
                )
                logger.info(f"🧠 [WORKFLOW MEMORY] Updated cached recipe for pattern: '{pattern}' (Hits: {row['success_count'] + 1})")
            else:
                recipe_id = plan.workflow_id or f"wf-{int(now)}"
                tags = ",".join(dict.fromkeys(s.agent_id for s in plan.all_steps))
                conn.execute(
                    """
                    INSERT INTO workflow_recipes (id, normalized_pattern, workflow_name, plan_json, tags, success_count, last_used, created_at)
                    VALUES (?, ?, ?, ?, ?, 1, ?, ?)
                    """,
                    (recipe_id, pattern, plan.workflow_name, json.dumps(plan_dict), tags, now, now)
                )
                logger.info(f"🧠 [WORKFLOW MEMORY] Learned new workflow recipe: '{plan.workflow_name}' for pattern: '{pattern}'")
            conn.commit()

    def find_matching_workflow(self, query: str) -> Optional[WorkflowPlan]:
        """
        Check if an incoming query matches an existing learned recipe.
        If matched, instantiates a parameterized copy ready for execution.
        """
        pattern = self.normalize_query_to_pattern(query)

        with self._lock, self._get_connection() as conn:
            # 1. Exact pattern match
            cursor = conn.execute(
                "SELECT plan_json, success_count FROM workflow_recipes WHERE normalized_pattern = ? ORDER BY success_count DESC LIMIT 1",
                (pattern,)
            )
            row = cursor.fetchone()

            # 2. Token overlap similarity fallback if not exact
            if not row:
                query_tokens = set(pattern.split())
                if len(query_tokens) >= 3:
                    cursor = conn.execute("SELECT plan_json, normalized_pattern, success_count FROM workflow_recipes")
                    best_match = None
                    best_jaccard = 0.0

                    for r in cursor.fetchall():
                        pat_tokens = set(r["normalized_pattern"].split())
                        intersection = query_tokens.intersection(pat_tokens)
                        union = query_tokens.union(pat_tokens)
                        if union:
                            jaccard = len(intersection) / len(union)
                            if jaccard > best_jaccard and jaccard >= 0.80:
                                best_jaccard = jaccard
                                best_match = r

                    if best_match:
                        row = best_match
                        logger.info(f"🧠 [WORKFLOW MEMORY] Fuzzy matched recipe (similarity: {best_jaccard:.2f})")

            if row:
                try:
                    plan_dict = json.loads(row["plan_json"])
                    plan = self._reconstitute_plan(plan_dict, query)
                    logger.info(f"⚡ [WORKFLOW CACHE HIT] Reusing cached workflow '{plan.workflow_name}' (0 LLM tokens, ~0ms)")
                    return plan
                except Exception as e:
                    logger.warning(f"Failed to reconstitute cached plan: {e}")

        return None

    @staticmethod
    def _reconstitute_plan(data: Dict[str, Any], query: str) -> WorkflowPlan:
        # Extract dynamic entity substitutions between original_goal and new query
        orig_goal = data.get("user_goal", "")
        orig_urls = re.findall(r'https?://[^\s]+', orig_goal)
        new_urls = re.findall(r'https?://[^\s]+', query)
        orig_paths = re.findall(r'[a-zA-Z]:\\[^\s]+', orig_goal)
        new_paths = re.findall(r'[a-zA-Z]:\\[^\s]+', query)
        orig_files = re.findall(r'[\w\-.]+\.(?:csv|xlsx?|docx?|pptx?|pdf|txt|png|jpe?g|mp3|mp4|json|py)\b', orig_goal)
        new_files = re.findall(r'[\w\-.]+\.(?:csv|xlsx?|docx?|pptx?|pdf|txt|png|jpe?g|mp3|mp4|json|py)\b', query)

        subs: Dict[str, str] = {}
        for ou, nu in zip(orig_urls, new_urls):
            subs[ou] = nu
        for op, np in zip(orig_paths, new_paths):
            subs[op] = np
        for of, nf in zip(orig_files, new_files):
            subs[of] = nf

        steps: List[WorkflowStep] = []
        for s in data.get("all_steps", []):
            task_str = s.get("task") or query
            params_dict = dict(s.get("params") or {})
            for old_val, new_val in subs.items():
                task_str = task_str.replace(old_val, new_val)
                for pk, pv in list(params_dict.items()):
                    if isinstance(pv, str):
                        params_dict[pk] = pv.replace(old_val, new_val)

            step = WorkflowStep(
                step_id=s["step_id"],
                agent_id=s["agent_id"],
                capability=s["capability"],
                task=task_str,
                params=params_dict,
                depends_on=list(s.get("depends_on") or []),
                output_key=s.get("output_key") or s["step_id"],
                requires_confirmation=bool(s.get("requires_confirmation", False)),
                fallback_agent_id=s.get("fallback_agent_id"),
            )
            steps.append(step)

        # Re-build waves
        waves: List[WorkflowWave] = []
        for w in data.get("waves", []):
            wave_steps = [s for s in steps if s.step_id in [st["step_id"] for st in w.get("steps", [])]]
            waves.append(WorkflowWave(wave_number=w.get("wave_number", 1), steps=wave_steps))

        if not waves:
            from ai_assistant.core.swarm_planner import SwarmPlanner
            waves = SwarmPlanner._build_waves_from_steps(steps) or [WorkflowWave(wave_number=1, steps=steps)]

        return WorkflowPlan(
            workflow_id=f"wf-cached-{int(time.time() * 1000)}",
            workflow_name=data.get("workflow_name", "Cached_Workflow"),
            user_goal=query,
            reasoning=f"Reused from learned workflow cache (originally {data.get('workflow_name')})",
            waves=waves,
            all_steps=steps,
            estimated_duration_sec=float(data.get("estimated_duration_sec", 20.0)),
        )

    def list_all_recipes(self) -> List[Dict[str, Any]]:
        """List all saved macro workflow recipes."""
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, normalized_pattern, workflow_name, tags, success_count, last_used FROM workflow_recipes ORDER BY success_count DESC"
            )
            return [dict(r) for r in cursor.fetchall()]

    def clear_memory(self):
        """Clear all cached recipes."""
        with self._lock, self._get_connection() as conn:
            conn.execute("DELETE FROM workflow_recipes")
            conn.commit()
