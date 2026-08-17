"""
Workflow Runner Module
Handles execution of workflow tasks, DAG dependency resolution, retries, and errors.
Extracted from automation_engine.py.
"""

import time
import uuid
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ai_assistant.automation.automation_models import (
    Workflow, WorkflowTask, WorkflowResult, WorkflowStatus, TaskType
)

logger = logging.getLogger(__name__)


class WorkflowRunner:
    """Executes workflows and manages task lifecycles."""
    
    def __init__(self, action_registry: Optional[Dict[str, Any]] = None):
        self.action_registry = action_registry or {}
        
    def register_action(self, name: str, handler: Any):
        """Register a handler function for an action name."""
        self.action_registry[name] = handler

    def execute_workflow(self, workflow: Workflow) -> WorkflowResult:
        """Synchronously execute all enabled tasks in a workflow respecting dependencies."""
        execution_id = str(uuid.uuid4())
        start_time_iso = datetime.now().isoformat()
        start_time_ts = time.time()
        
        task_results: Dict[str, Any] = {}
        workflow.status = WorkflowStatus.RUNNING
        
        try:
            # Simple topological / sequential execution
            completed_task_ids = set()
            
            for task in workflow.tasks:
                if not task.enabled:
                    continue
                    
                # Check dependencies
                unmet = [dep for dep in task.dependencies if dep not in completed_task_ids]
                if unmet:
                    logger.warning(f"Task {task.id} skipped due to unmet dependencies: {unmet}")
                    task_results[task.id] = {"status": "skipped", "reason": f"unmet dependencies: {unmet}"}
                    continue
                    
                # Execute task with retries
                success = False
                output = None
                err = None
                
                for attempt in range(task.max_retries + 1):
                    try:
                        output = self._execute_task(task, task_results)
                        success = True
                        break
                    except Exception as e:
                        err = str(e)
                        logger.warning(f"Task {task.name} attempt {attempt+1} failed: {e}")
                        time.sleep(0.5)
                        
                if success:
                    completed_task_ids.add(task.id)
                    task_results[task.id] = {"status": "completed", "output": output}
                else:
                    task_results[task.id] = {"status": "failed", "error": err}
                    workflow.status = WorkflowStatus.FAILED
                    break
                    
            if workflow.status != WorkflowStatus.FAILED:
                workflow.status = WorkflowStatus.COMPLETED
                
            end_time_ts = time.time()
            return WorkflowResult(
                workflow_id=workflow.id,
                execution_id=execution_id,
                status=workflow.status,
                start_time=start_time_iso,
                end_time=datetime.now().isoformat(),
                duration_seconds=round(end_time_ts - start_time_ts, 2),
                task_results=task_results,
                output_data={"last_task_output": task_results.get(list(task_results.keys())[-1]) if task_results else None}
            )
            
        except Exception as e:
            logger.error(f"Workflow execution fatal error: {e}")
            return WorkflowResult(
                workflow_id=workflow.id,
                execution_id=execution_id,
                status=WorkflowStatus.FAILED,
                start_time=start_time_iso,
                end_time=datetime.now().isoformat(),
                duration_seconds=round(time.time() - start_time_ts, 2),
                task_results=task_results,
                error_message=str(e)
            )

    def _execute_task(self, task: WorkflowTask, context: Dict[str, Any]) -> Any:
        """Execute a single task."""
        if task.type == TaskType.DELAY:
            duration = task.parameters.get("duration", 1)
            time.sleep(float(duration))
            return f"Waited {duration}s"
            
        if task.function in self.action_registry:
            fn = self.action_registry[task.function]
            return fn(**task.parameters)
            
        # Fallback dynamic execution
        return f"Simulated execution of task {task.name} ({task.function})"
