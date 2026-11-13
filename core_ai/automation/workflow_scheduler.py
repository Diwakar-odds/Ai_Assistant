"""
Workflow Scheduler Module
Handles time-based and event-driven trigger dispatching for workflows.
Extracted from automation_engine.py.
"""

import time
import threading
import logging
from typing import Dict, Any, Callable, Optional

logger = logging.getLogger(__name__)

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False


class WorkflowScheduler:
    """Manages scheduled background workflow execution."""
    
    def __init__(self, execution_callback: Optional[Callable[[str], Any]] = None):
        self.execution_callback = execution_callback
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self.scheduled_jobs: Dict[str, Any] = {}

    def start(self):
        """Start the background scheduler thread."""
        if not SCHEDULE_AVAILABLE:
            logger.warning("Schedule library not installed, background scheduling disabled.")
            return
            
        if not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info("✅ Workflow scheduler started")

    def stop(self):
        """Stop the background scheduler."""
        self.running = False

    def schedule_workflow(self, workflow_id: str, cron_or_interval: str):
        """Schedule a workflow for periodic execution."""
        if not SCHEDULE_AVAILABLE:
            return
        try:
            # Simple interval parsing e.g. "every 1 hour", "every 30 minutes"
            if "minute" in cron_or_interval:
                mins = int(cron_or_interval.split()[1]) if len(cron_or_interval.split()) > 1 and cron_or_interval.split()[1].isdigit() else 10
                job = schedule.every(mins).minutes.do(self._trigger_workflow, workflow_id)
                self.scheduled_jobs[workflow_id] = job
            elif "hour" in cron_or_interval:
                hours = int(cron_or_interval.split()[1]) if len(cron_or_interval.split()) > 1 and cron_or_interval.split()[1].isdigit() else 1
                job = schedule.every(hours).hours.do(self._trigger_workflow, workflow_id)
                self.scheduled_jobs[workflow_id] = job
            else:
                job = schedule.every().day.at("09:00").do(self._trigger_workflow, workflow_id)
                self.scheduled_jobs[workflow_id] = job
        except Exception as e:
            logger.error(f"Failed to schedule workflow {workflow_id}: {e}")

    def _trigger_workflow(self, workflow_id: str):
        if self.execution_callback:
            try:
                self.execution_callback(workflow_id)
            except Exception as e:
                logger.error(f"Error executing scheduled workflow {workflow_id}: {e}")

    def _run_loop(self):
        while self.running:
            try:
                if SCHEDULE_AVAILABLE:
                    schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.debug(f"Scheduler loop error: {e}")
                time.sleep(5)
