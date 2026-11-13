"""
Dispatcher for natural language intents to workflow or multi-agent execution.
Extracts intent and entities from user input, maps to workflow templates or
delegates cleanly to MultiAgentCoordinator without broken module-import crashes.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class Dispatcher:
    """Dispatches natural language commands to appropriate workflows or agents."""

    def __init__(self):
        self._intent_extractor = None
        self._scheduler = None
        self._intent_registry = None
        logger.debug("Dispatcher created (lazy dependencies)")

    def _get_intent_extractor(self):
        if self._intent_extractor is None:
            from ai_assistant.nlp.unified_intent_classifier import UnifiedIntentClassifier
            self._intent_extractor = UnifiedIntentClassifier()
        return self._intent_extractor

    def _get_intent_registry(self):
        if self._intent_registry is None:
            from ai_assistant.workflow.intent_registry import intent_registry
            self._intent_registry = intent_registry
        return self._intent_registry

    def _get_scheduler(self):
        if self._scheduler is None:
            from ai_assistant.automation.task_scheduler import TaskScheduler
            self._scheduler = TaskScheduler()
        return self._scheduler

    def _run_async(self, coro):
        try:
            asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result(timeout=120)
        except RuntimeError:
            return asyncio.run(coro)

    def handle(self, user_input: str) -> Dict[str, Any]:
        """Process a natural language user input and dispatch to workflow or agent."""
        logger.info("Processing user input: %s", user_input)

        intent = "unknown"
        entities: Dict[str, Any] = {}
        confidence = 0.0

        try:
            extractor = self._get_intent_extractor()
            extraction_result = extractor.classify(user_input)
            intent = getattr(extraction_result, "intent", "unknown")
            entities = dict(getattr(extraction_result, "entities", {}) or {})
            confidence = float(getattr(extraction_result, "confidence", 0.0) or 0.0)
        except Exception as exc:
            logger.warning("Intent classification unavailable, falling back to MultiAgentCoordinator: %s", exc)

        logger.info("Extracted intent: %s, entities: %s, confidence: %.2f", intent, entities, confidence)

        mapping = None
        try:
            mapping = self._get_intent_registry().get_intent_mapping(intent)
        except Exception as exc:
            logger.debug("Intent registry lookup failed: %s", exc)

        # Schedule workflow if time entity + mapping present
        if mapping and entities.get("time"):
            try:
                from ai_assistant.automation.task_scheduler import ScheduleType
                schedule_time = entities["time"]
                workflow_entities = {k: v for k, v in entities.items() if k != "time"}
                task_id = self._get_scheduler().schedule_workflow(
                    workflow_path=mapping.workflow_path,
                    parameters=workflow_entities,
                    schedule_type=ScheduleType.ONCE,
                    schedule_time=schedule_time,
                )
                return {
                    "success": True,
                    "message": f"Workflow '{mapping.intent}' scheduled for {schedule_time} with ID {task_id}",
                    "task_id": task_id,
                    "intent": intent,
                    "entities": workflow_entities,
                }
            except Exception as exc:
                logger.error("Error scheduling workflow: %s", exc)
                return {
                    "success": False,
                    "message": f"Failed to schedule workflow: {exc}",
                    "intent": intent,
                    "entities": entities,
                }

        # Fallback or direct execution through MultiAgentCoordinator
        try:
            from ai_assistant.core.multi_agent_coordinator import get_multi_agent_coordinator
            coordinator = get_multi_agent_coordinator()
            result = self._run_async(coordinator.process_command(user_input))
            ok = result.get("status") in ("completed", "success")
            return {
                "success": ok,
                "message": str(result.get("summary") or result.get("message") or ("Dispatched" if ok else "No suitable handler")),
                "result": result,
                "intent": intent,
                "entities": entities,
            }
        except Exception as exc:
            logger.error("Error dispatching command: %s", exc)
            return {
                "success": False,
                "message": f"Failed to dispatch command: {exc}",
                "intent": intent,
                "entities": entities,
            }


_dispatcher: Optional[Dispatcher] = None


def get_dispatcher() -> Dispatcher:
    """Return lazy singleton Dispatcher instance."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = Dispatcher()
    return _dispatcher


# Backward-compatible attribute without eager heavy construction
dispatcher = Dispatcher()
