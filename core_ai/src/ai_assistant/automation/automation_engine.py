"""
Smart Automation & Workflows Engine (Modular Coordinator)

Coordinates workflow models, storage, execution runner, and scheduler.
Decomposed from the monolithic 1,899 lines version into modular subcomponents:
- automation_models: Dataclasses & Enums
- automation_storage: SQLite persistence
- workflow_runner: Task execution and DAG runner
- workflow_scheduler: Schedule and trigger dispatcher
"""

import logging
from typing import Dict, List, Optional, Any

from ai_assistant.automation.automation_models import (
    WorkflowStatus, TaskType, TriggerType,
    WorkflowTask, WorkflowTrigger, WorkflowResult, Workflow
)
from ai_assistant.automation.automation_storage import AutomationStorage
from ai_assistant.automation.workflow_runner import WorkflowRunner
from ai_assistant.automation.workflow_scheduler import WorkflowScheduler

logger = logging.getLogger(__name__)

# Re-export key dataclasses for backwards compatibility
__all__ = [
    'WorkflowStatus', 'TaskType', 'TriggerType',
    'WorkflowTask', 'WorkflowTrigger', 'WorkflowResult', 'Workflow',
    'AutomationStorage', 'WorkflowRunner', 'WorkflowScheduler',
    'SmartAutomationEngine', 'AutomationEngine'
]


class SmartAutomationEngine:
    """Main facade for creating, scheduling, and running workflows."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.storage = AutomationStorage(db_path)
        self.runner = WorkflowRunner()
        self.scheduler = WorkflowScheduler(execution_callback=self.run_workflow_by_id)
        
        # Register standard automation actions
        self._register_default_actions()
        self.scheduler.start()
        logger.info("✅ SmartAutomationEngine initialized (modular engine architecture)")

    def _register_default_actions(self):
        """Register built-in system actions."""
        try:
            from ai_assistant.automation.automation_tools_new import (
                smart_open_application, close_application,
                search_google, search_and_play_spotify,
                set_system_volume, write_a_note
            )
            self.runner.register_action("open_app", smart_open_application)
            self.runner.register_action("close_app", close_application)
            self.runner.register_action("google_search", search_google)
            self.runner.register_action("spotify_play", search_and_play_spotify)
            self.runner.register_action("volume", set_system_volume)
            self.runner.register_action("note", write_a_note)
        except Exception as e:
            logger.debug(f"Action registration note: {e}")

    def create_workflow(self, name: str, description: str = "", tasks: Optional[List[WorkflowTask]] = None) -> Workflow:
        """Create and persist a new workflow."""
        workflow = Workflow(
            name=name,
            description=description,
            tasks=tasks or []
        )
        self.storage.save_workflow(workflow)
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Fetch workflow by ID."""
        return self.storage.get_workflow(workflow_id)

    def list_workflows(self) -> List[Workflow]:
        """List all defined workflows."""
        return self.storage.list_workflows()

    def run_workflow(self, workflow: Workflow) -> WorkflowResult:
        """Execute a workflow and record its result."""
        result = self.runner.execute_workflow(workflow)
        self.storage.record_execution(result)
        self.storage.save_workflow(workflow)
        return result

    def run_workflow_by_id(self, workflow_id: str) -> Optional[WorkflowResult]:
        """Load and run a workflow by ID."""
        wf = self.get_workflow(workflow_id)
        if wf:
            return self.run_workflow(wf)
        logger.error(f"Workflow {workflow_id} not found to run.")
        return None

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete workflow by ID."""
        return self.storage.delete_workflow(workflow_id)


# Alias for backward compatibility
AutomationEngine = SmartAutomationEngine
