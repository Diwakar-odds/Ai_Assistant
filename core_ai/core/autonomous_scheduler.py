import logging
import time
from typing import Callable, Any, Dict, Optional
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
except ImportError:
    BackgroundScheduler = None
    CronTrigger = None

logger = logging.getLogger(__name__)

class AutonomousScheduler:
    """
    A lightweight wrapper around APScheduler for background autonomous tasks.
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler() if BackgroundScheduler else None
        self.jobs: Dict[str, Any] = {}
        
    def start(self):
        if self.scheduler and not self.scheduler.running:
            self.scheduler.start()
            logger.info("AutonomousScheduler started.")
            
    def stop(self):
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("AutonomousScheduler stopped.")
            
    def add_cron_job(self, job_id: str, func: Callable, cron_expr: str, **kwargs):
        """Add a job using a cron expression (e.g. '0 * * * *')"""
        if not self.scheduler:
            logger.warning("APScheduler not available, cannot add job.")
            return False
            
        try:
            # Simple parser for 5-part cron: min hour day month day_of_week
            parts = cron_expr.split()
            if len(parts) == 5:
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4]
                )
                job = self.scheduler.add_job(func, trigger, id=job_id, replace_existing=True, kwargs=kwargs)
                self.jobs[job_id] = job
                return True
        except Exception as e:
            logger.error(f"Failed to add cron job {job_id}: {e}")
        return False
        
    def add_interval_job(self, job_id: str, func: Callable, seconds: int, **kwargs):
        if not self.scheduler:
            return False
        try:
            job = self.scheduler.add_job(func, 'interval', seconds=seconds, id=job_id, replace_existing=True, kwargs=kwargs)
            self.jobs[job_id] = job
            return True
        except Exception as e:
            logger.error(f"Failed to add interval job {job_id}: {e}")
        return False
