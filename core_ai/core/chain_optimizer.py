import logging
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from ai_assistant.core.database_config import get_db_path_str

logger = logging.getLogger(__name__)


class ChainOptimizer:
    """
    AI Learning & Optimization System for Chain of Actions.
    Analyzes execution history, generates multi-plans via lazy LLM deliberation,
    and predicts success rates.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_db_path_str('memory')
        self._llm = None
        self._llm_attempted = False
        self._predictor = None
        self._predictor_attempted = False
        self._setup_db()

    @property
    def llm(self):
        """Lazy-load UnifiedChatInterface only when LLM deliberation is requested."""
        if not self._llm_attempted:
            self._llm_attempted = True
            try:
                from ai_assistant.ai.llm_provider import UnifiedChatInterface
                try:
                    import sys
                    backend_dir = str(Path(__file__).resolve().parents[4] / 'backend')
                    if backend_dir not in sys.path:
                        sys.path.insert(0, backend_dir)
                    from settings_manager import get_provider, get_model
                    _sm_provider, _sm_model = get_provider(), get_model()
                except Exception:
                    _sm_provider, _sm_model = None, None
                self._llm = UnifiedChatInterface(provider=_sm_provider, model=_sm_model, use_fallback=True)
                self._llm.add_system_message(
                    "You are an AI planner optimization engine. "
                    "Given a plan, generate 2 alternative plans that achieve the same goal, "
                    "with different trade-offs (e.g. parallel vs safe sequential). "
                    "Return ONLY valid JSON."
                )
            except Exception as e:
                logger.debug(f"ChainOptimizer LLM unavailable: {e}")
                self._llm = None
        return self._llm

    @llm.setter
    def llm(self, value):
        self._llm = value
        self._llm_attempted = True

    @property
    def predictor(self):
        if not self._predictor_attempted:
            self._predictor_attempted = True
            try:
                from ai_assistant.ai.command_predictor import CommandPredictor
                self._predictor = CommandPredictor()
            except Exception:
                self._predictor = None
        return self._predictor

    @predictor.setter
    def predictor(self, value):
        self._predictor = value
        self._predictor_attempted = True

    def _connect(self) -> sqlite3.Connection:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.db_path, timeout=30.0)

    def _setup_db(self):
        with self._connect() as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS chain_patterns (
                    signature TEXT PRIMARY KEY,
                    successes INTEGER DEFAULT 0,
                    failures INTEGER DEFAULT 0,
                    avg_time REAL DEFAULT 0.0,
                    shortcut_plan TEXT
                )
            ''')
            conn.commit()

    @staticmethod
    def _step_to_dict(step: Any) -> Dict[str, Any]:
        if isinstance(step, dict):
            return step
        if hasattr(step, "to_dict"):
            return step.to_dict()
        return {
            "type": getattr(step, "intent", None) or str(getattr(step, "type", "unknown")),
            "description": getattr(step, "description", "") or getattr(step, "original_text", ""),
        }

    def _plan_signature(self, plan: List[Any]) -> str:
        parts = []
        for s in plan:
            d = self._step_to_dict(s)
            parts.append(str(d.get("intent") or d.get("type") or "unknown"))
        return "->".join(parts)

    def _get_stats(self, signature: str) -> Dict[str, Any]:
        with self._connect() as conn:
            c = conn.cursor()
            c.execute(
                'SELECT successes, failures, avg_time, shortcut_plan FROM chain_patterns WHERE signature = ?',
                (signature,),
            )
            row = c.fetchone()
        if row:
            return {
                "successes": row[0],
                "failures": row[1],
                "avg_time": row[2],
                "shortcut_plan": json.loads(row[3]) if row[3] else None,
            }
        return {"successes": 0, "failures": 0, "avg_time": 0.0, "shortcut_plan": None}

    def _save_stats(self, signature: str, stats: Dict[str, Any]):
        shortcut = json.dumps(stats["shortcut_plan"], default=str) if stats.get("shortcut_plan") else None
        with self._connect() as conn:
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO chain_patterns (signature, successes, failures, avg_time, shortcut_plan)
                VALUES (?, ?, ?, ?, ?)
            ''', (signature, stats["successes"], stats["failures"], stats["avg_time"], shortcut))
            conn.commit()

    def add_execution_record(self, chain_id: str, plan: List[Any], result: Dict[str, Any], execution_time: float):
        """Record an execution into history for pattern recognition"""
        normalized_plan = [self._step_to_dict(s) for s in (plan or [])]
        plan_signature = self._plan_signature(normalized_plan)
        if not plan_signature:
            return
        stats = self._get_stats(plan_signature)

        if result.get("success", False):
            stats["successes"] += 1
        else:
            stats["failures"] += 1

        total_runs = stats["successes"] + stats["failures"]
        stats["avg_time"] = ((stats["avg_time"] * (total_runs - 1)) + float(execution_time or 0.0)) / max(1, total_runs)

        if stats["successes"] > 5 and stats["successes"] / total_runs > 0.9:
            if not stats.get("shortcut_plan"):
                logger.info(f"Generated new shortcut for highly successful pattern: {plan_signature}")
                stats["shortcut_plan"] = normalized_plan

        self._save_stats(plan_signature, stats)

    def optimize_plan(self, current_plan: List[Any]) -> List[Dict[str, Any]]:
        """Automatic plan optimization using historical shortcuts and lazy LLM deliberation."""
        normalized_plan = [self._step_to_dict(s) for s in (current_plan or [])]
        signature = self._plan_signature(normalized_plan)
        if not signature:
            return normalized_plan
        stats = self._get_stats(signature)

        if stats.get("shortcut_plan"):
            logger.info(f"Applying optimizations using known shortcut for {signature}")
            return stats["shortcut_plan"]

        if len(normalized_plan) > 3 and self.llm:
            try:
                prompt = (
                    f"Original Plan:\n{json.dumps(normalized_plan, indent=2, default=str)}\n\n"
                    'Generate optimized alternatives in JSON format: {"alternatives": [[...plan_actions...], [...]]}'
                )
                response = self.llm.chat(prompt, stream=False).strip()
                if response.startswith("```json"):
                    response = response[7:]
                if response.startswith("```"):
                    response = response[3:]
                if response.endswith("```"):
                    response = response[:-3]

                data = json.loads(response.strip())
                alternatives = data.get("alternatives", [])

                if alternatives:
                    best_plan = normalized_plan
                    best_score = self.predict_success_rate(normalized_plan)

                    for alt in alternatives:
                        score = self.predict_success_rate(alt)
                        if score > best_score:
                            best_score = score
                            best_plan = alt

                    if best_plan != normalized_plan:
                        logger.info("Selected optimized alternative plan via LLM deliberation.")
                    return best_plan
            except Exception as e:
                logger.error(f"Deliberation failed: {e}")

        return list(normalized_plan)

    def predict_success_rate(self, plan: List[Any]) -> float:
        """Success rate prediction for a given plan based on historical data"""
        normalized_plan = [self._step_to_dict(s) for s in (plan or [])]
        signature = self._plan_signature(normalized_plan)
        if not signature:
            return 0.75
        stats = self._get_stats(signature)

        total = stats["successes"] + stats["failures"]
        if total > 0:
            return stats["successes"] / total

        if self.predictor:
            try:
                scores = []
                for step in normalized_plan:
                    desc = step.get("description", "")
                    if desc:
                        pred = self.predictor.predict_success(desc)
                        if pred:
                            scores.append(pred.confidence_score)
                if scores:
                    return sum(scores) / len(scores)
            except Exception:
                pass

        return 0.75
