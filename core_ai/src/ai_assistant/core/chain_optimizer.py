import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict
import time

logger = logging.getLogger(__name__)

class ChainOptimizer:
    """
    AI Learning & Optimization System for Chain of Actions.
    Analyzes execution history to find patterns, optimize plans, and predict success rates.
    """

    def __init__(self):
        self.execution_history: List[Dict[str, Any]] = []
        self.pattern_database: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"successes": 0, "failures": 0, "avg_time": 0.0})
        self.shortcuts: Dict[str, List[Dict[str, Any]]] = {}

    def add_execution_record(self, chain_id: str, plan: List[Dict[str, Any]], result: Dict[str, Any], execution_time: float):
        """Record an execution into history for pattern recognition"""
        record = {
            "chain_id": chain_id,
            "plan": plan,
            "success": result.get("success", False),
            "execution_time": execution_time,
            "timestamp": time.time()
        }
        self.execution_history.append(record)
        self._update_patterns(record)

    def _update_patterns(self, record: Dict[str, Any]):
        """Pattern recognition from execution history"""
        # Simplify the plan to a sequence of action types to find patterns
        plan_signature = "->".join([step.get("type", "unknown") for step in record["plan"]])
        
        stats = self.pattern_database[plan_signature]
        if record["success"]:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
            
        total_runs = stats["successes"] + stats["failures"]
        stats["avg_time"] = ((stats["avg_time"] * (total_runs - 1)) + record["execution_time"]) / total_runs
        
        # Check if we should suggest a shortcut (e.g., highly successful sequences)
        if stats["successes"] > 5 and stats["successes"] / total_runs > 0.9:
            self._generate_shortcut(plan_signature, record["plan"])

    def _generate_shortcut(self, signature: str, plan: List[Dict[str, Any]]):
        """Shortcut suggestion system"""
        if signature not in self.shortcuts:
            logger.info(f"Generated new shortcut for highly successful pattern: {signature}")
            self.shortcuts[signature] = plan

    def optimize_plan(self, current_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Automatic plan optimization based on success rates"""
        signature = "->".join([step.get("type", "unknown") for step in current_plan])
        
        # If we have a verified shortcut for this exact plan signature, we might apply optimizations
        # E.g., combining redundant steps
        optimized_plan = list(current_plan)  # Copy
        
        if signature in self.shortcuts:
            logger.info(f"Applying optimizations using known shortcut for {signature}")
            # Placeholder for actual graph-based plan compression
            # Example: If navigation -> click -> type can be replaced by direct JS injection
            pass
            
        return optimized_plan

    def predict_success_rate(self, plan: List[Dict[str, Any]]) -> float:
        """Success rate prediction for a given plan based on historical data"""
        signature = "->".join([step.get("type", "unknown") for step in plan])
        
        if signature in self.pattern_database:
            stats = self.pattern_database[signature]
            total = stats["successes"] + stats["failures"]
            if total > 0:
                return stats["successes"] / total
                
        # Base success rate if unknown
        return 0.75
