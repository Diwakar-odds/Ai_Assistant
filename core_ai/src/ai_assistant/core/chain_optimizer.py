import logging
import sqlite3
import json
import time
from typing import Dict, Any, List, Optional
from collections import defaultdict
from ai_assistant.core.database_config import get_db_path_str

logger = logging.getLogger(__name__)

class ChainOptimizer:
    """
    AI Learning & Optimization System for Chain of Actions.
    Analyzes execution history, generates multi-plans via LLM, and predicts success rates.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_db_path_str('memory')
        self._setup_db()
        
        try:
            from ai_assistant.ai.llm_provider import UnifiedChatInterface
            self.llm = UnifiedChatInterface()
            self.llm.add_system_message("You are an AI planner optimization engine. "
                                        "Given a plan, generate 2 alternative plans that achieve the same goal, "
                                        "but with different trade-offs (e.g. faster but riskier, safer but slower). "
                                        "Return ONLY valid JSON.")
        except ImportError:
            self.llm = None
            
        try:
            from ai_assistant.ai.command_predictor import CommandPredictor
            self.predictor = CommandPredictor()
        except ImportError:
            self.predictor = None

    def _setup_db(self):
        conn = sqlite3.connect(self.db_path)
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
        conn.close()

    def _get_stats(self, signature: str) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT successes, failures, avg_time, shortcut_plan FROM chain_patterns WHERE signature = ?', (signature,))
        row = c.fetchone()
        conn.close()
        if row:
            return {"successes": row[0], "failures": row[1], "avg_time": row[2], "shortcut_plan": json.loads(row[3]) if row[3] else None}
        return {"successes": 0, "failures": 0, "avg_time": 0.0, "shortcut_plan": None}

    def _save_stats(self, signature: str, stats: Dict[str, Any]):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        shortcut = json.dumps(stats["shortcut_plan"]) if stats.get("shortcut_plan") else None
        c.execute('''
            INSERT OR REPLACE INTO chain_patterns (signature, successes, failures, avg_time, shortcut_plan)
            VALUES (?, ?, ?, ?, ?)
        ''', (signature, stats["successes"], stats["failures"], stats["avg_time"], shortcut))
        conn.commit()
        conn.close()

    def add_execution_record(self, chain_id: str, plan: List[Dict[str, Any]], result: Dict[str, Any], execution_time: float):
        """Record an execution into history for pattern recognition"""
        # Simplify the plan to a sequence of action types to find patterns
        plan_signature = "->".join([step.get("type", "unknown") for step in plan])
        stats = self._get_stats(plan_signature)
        
        if result.get("success", False):
            stats["successes"] += 1
        else:
            stats["failures"] += 1
            
        total_runs = stats["successes"] + stats["failures"]
        stats["avg_time"] = ((stats["avg_time"] * (total_runs - 1)) + execution_time) / total_runs
        
        # Check if we should suggest a shortcut (e.g., highly successful sequences)
        if stats["successes"] > 5 and stats["successes"] / total_runs > 0.9:
            if not stats.get("shortcut_plan"):
                logger.info(f"Generated new shortcut for highly successful pattern: {plan_signature}")
                stats["shortcut_plan"] = plan
                
        self._save_stats(plan_signature, stats)

    def optimize_plan(self, current_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Automatic plan optimization using LLM deliberation and historical data."""
        signature = "->".join([step.get("type", "unknown") for step in current_plan])
        stats = self._get_stats(signature)
        
        # If we have a verified shortcut for this exact plan signature, apply it
        if stats.get("shortcut_plan"):
            logger.info(f"Applying optimizations using known shortcut for {signature}")
            return stats["shortcut_plan"]
            
        # If plan is complex (> 3 steps) and LLM is available, deliberate
        if len(current_plan) > 3 and self.llm:
            try:
                prompt = f"Original Plan:\n{json.dumps(current_plan, indent=2)}\n\nGenerate optimized alternatives in JSON format: {{\"alternatives\": [[...plan_actions...], [...]]}}"
                response = self.llm.chat(prompt, stream=False).strip()
                if response.startswith("```json"):
                    response = response[7:]
                if response.startswith("```"):
                    response = response[3:]
                if response.endswith("```"):
                    response = response[:-3]
                
                data = json.loads(response)
                alternatives = data.get("alternatives", [])
                
                if alternatives:
                    best_plan = current_plan
                    best_score = self.predict_success_rate(current_plan)
                    
                    for alt in alternatives:
                        score = self.predict_success_rate(alt)
                        if score > best_score:
                            best_score = score
                            best_plan = alt
                            
                    if best_plan != current_plan:
                        logger.info("Selected optimized alternative plan via LLM deliberation.")
                    return best_plan
            except Exception as e:
                logger.error(f"Deliberation failed: {e}")
                
        return list(current_plan)

    def predict_success_rate(self, plan: List[Dict[str, Any]]) -> float:
        """Success rate prediction for a given plan based on historical data"""
        signature = "->".join([step.get("type", "unknown") for step in plan])
        stats = self._get_stats(signature)
        
        total = stats["successes"] + stats["failures"]
        if total > 0:
            return stats["successes"] / total
            
        # Base success rate if unknown
        if self.predictor:
            # Aggregate per-step confidence
            try:
                scores = []
                for step in plan:
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
