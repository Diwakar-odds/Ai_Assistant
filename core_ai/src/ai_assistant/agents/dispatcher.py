"""
Dispatcher for natural language intents to workflow execution.
Extracts intent and entities from user input, maps to workflow templates,
and launches the workflow via the launcher agent.
"""

from typing import Dict, Any, Optional
from src.ai_assistant.nlp.intent_extractor import IntentResult
from src.ai_assistant.nlp.unified_intent_classifier import UnifiedIntentClassifier
from src.ai_assistant.workflow.intent_registry import intent_registry
from src.ai_assistant.agents.launcher import LauncherAgent
from src.ai_assistant.automation.task_scheduler import TaskScheduler, ScheduleType
import logging

logger = logging.getLogger(__name__)

class Dispatcher:
    """
    Dispatches natural language commands to appropriate workflows.
    """

    def __init__(self):
        self.intent_extractor = UnifiedIntentClassifier()
        self.launcher = LauncherAgent()
        self.scheduler = TaskScheduler()
        logger.info("Dispatcher initialized")

    def handle(self, user_input: str) -> Dict[str, Any]:
        """
        Process a natural language user input and dispatch to appropriate workflow.
        
        Args:
            user_input: The user's natural language command
            
        Returns:
            A dictionary with the result of the dispatch operation.
        """
        logger.info(f"Processing user input: {user_input}")
        
        # Extract intent and entities
        extraction_result = self.intent_extractor.classify(user_input)
        intent = extraction_result.intent
        entities = extraction_result.entities
        confidence = extraction_result.confidence

        logger.info(f"Extracted intent: {intent}, entities: {entities}, confidence: {confidence}")

        # If confidence is too low, treat as unknown
        if confidence < 0.3:
            return {
                "success": False,
                "message": f"I'm not sure I understand. Could you rephrase? (Intent: {intent}, confidence: {confidence:.2f})",
                "intent": intent,
                "entities": entities
            }

        # Look up the intent in the registry
        mapping = intent_registry.get_intent_mapping(intent)
        if not mapping:
            return {
                "success": False,
                "message": f"I don't know how to handle the intent '{intent}'.",
                "intent": intent,
                "entities": entities
            }

        # Check if the workflow requires scheduling (e.g., based on entities like time)
        # For now, we assume that if there's a 'time' entity, we schedule it.
        # Otherwise, we run it immediately.
        schedule_type = None
        schedule_time = None
        if 'time' in entities and entities['time']:
            # For simplicity, we assume the time entity['time'] is a string that can be parsed by the scheduler.
            # In a real implementation, we would parse the time string into a datetime.
            schedule_type = ScheduleType.ONCE
            schedule_time = entities['time']
            # Remove time from entities for the workflow parameters
            workflow_entities = {k: v for k, v in entities.items() if k != 'time'}
        else:
            workflow_entities = entities

        # Launch the workflow
        try:
            if schedule_type:
                # Schedule the workflow for later
                task_id = self.scheduler.schedule_workflow(
                    workflow_path=mapping.workflow_path,
                    parameters=workflow_entities,
                    schedule_type=schedule_type,
                    schedule_time=schedule_time
                )
                return {
                    "success": True,
                    "message": f"Workflow '{mapping.intent}' scheduled for {schedule_time} with ID {task_id}",
                    "task_id": task_id,
                    "intent": intent,
                    "entities": workflow_entities
                }
            else:
                # Run the workflow immediately
                result = self.launcher.launch_from_nlu(
                    intent_name=mapping.intent,
                    workflow_path=mapping.workflow_path,
                    params=workflow_entities
                )
                return {
                    "success": True,
                    "message": f"Workflow '{mapping.intent}' executed successfully.",
                    "result": result,
                    "intent": intent,
                    "entities": workflow_entities
                }
        except Exception as e:
            logger.error(f"Error launching workflow: {e}")
            return {
                "success": False,
                "message": f"Failed to execute workflow: {str(e)}",
                "intent": intent,
                "entities": workflow_entities
            }

# Global dispatcher instance
dispatcher = Dispatcher()