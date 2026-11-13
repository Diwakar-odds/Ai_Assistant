import logging
import asyncio
from typing import Dict, Any, List, Optional
import time
import math

logger = logging.getLogger(__name__)

class SelfHealingEngine:
    """
    Self Healing Engine for Chain of Actions.
    Detects failures, learns patterns, and implements recovery plans with exponential backoff.
    """

    def __init__(self):
        self.failure_database: Dict[str, List[Dict[str, Any]]] = {}
        self.base_backoff_seconds = 2
        self.max_retries = 3

    def detect_failure_type(self, error_details: Dict[str, Any]) -> str:
        """Detect the type of failure based on error details"""
        error_msg = str(error_details.get("error", "")).lower()
        if "timeout" in error_msg or "connection" in error_msg:
            return "network_timeout"
        elif "not found" in error_msg or "404" in error_msg:
            return "resource_not_found"
        elif "auth" in error_msg or "401" in error_msg or "403" in error_msg:
            return "authentication_error"
        elif "dom" in error_msg or "element" in error_msg:
            return "ui_element_changed"
        else:
            return "unknown_failure"

    def record_failure(self, action_id: str, step_type: str, error_details: Dict[str, Any]) -> None:
        """Record failure into the pattern learning database"""
        failure_type = self.detect_failure_type(error_details)
        
        if step_type not in self.failure_database:
            self.failure_database[step_type] = []
            
        record = {
            "action_id": action_id,
            "failure_type": failure_type,
            "details": error_details,
            "timestamp": time.time()
        }
        self.failure_database[step_type].append(record)
        logger.info(f"Recorded failure of type '{failure_type}' for step '{step_type}'")

    async def generate_recovery_plan(self, action_id: str, step_type: str, failure_type: str) -> Dict[str, Any]:
        """Automatic recovery plan generation based on failure type"""
        logger.info(f"Generating recovery plan for action {action_id} (Type: {failure_type})")
        
        plan = {
            "action_id": action_id,
            "can_recover": True,
            "strategy": "retry",
            "alternative_steps": []
        }
        
        if failure_type == "network_timeout":
            plan["strategy"] = "exponential_backoff_retry"
        elif failure_type == "ui_element_changed":
            plan["strategy"] = "fallback_selector"
            plan["alternative_steps"] = [{"type": "scan_dom", "objective": "find_alternative_element"}]
        elif failure_type == "authentication_error":
            plan["strategy"] = "re_authenticate"
            plan["alternative_steps"] = [{"type": "auth", "objective": "refresh_token"}]
        else:
            plan["can_recover"] = False
            plan["strategy"] = "manual_intervention"
            
        return plan

    def get_backoff_time(self, retry_count: int) -> float:
        """Exponential backoff strategy"""
        if retry_count < 0:
            return 0
        return self.base_backoff_seconds * math.pow(2, retry_count)

    async def auto_retry(self, action_id: str, execute_func, *args, **kwargs) -> Dict[str, Any]:
        """Execute a function with automatic retry and exponential backoff"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    backoff = self.get_backoff_time(attempt - 1)
                    logger.info(f"Retry attempt {attempt} for action {action_id} in {backoff} seconds...")
                    await asyncio.sleep(backoff)
                
                result = await execute_func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Action {action_id} recovered successfully on attempt {attempt}")
                return {"success": True, "result": result, "attempts": attempt + 1}
                
            except Exception as e:
                last_error = e
                logger.warning(f"Execution failed for action {action_id} on attempt {attempt}: {e}")
                error_details = {"error": str(e), "attempt": attempt}
                self.record_failure(action_id, kwargs.get("step_type", "unknown"), error_details)
                
                # Check if we should abort early
                failure_type = self.detect_failure_type(error_details)
                plan = await self.generate_recovery_plan(action_id, kwargs.get("step_type", "unknown"), failure_type)
                
                if not plan["can_recover"]:
                    logger.error(f"Unrecoverable error for action {action_id}: {failure_type}")
                    break
                    
        return {"success": False, "error": str(last_error), "attempts": self.max_retries + 1}
