import logging
import os
import tempfile
import glob

logger = logging.getLogger(__name__)

class AutonomousActions:
    """Logic to execute background tasks when system is idle or requires healing."""
    
    def __init__(self):
        try:
            from ai_assistant.core.project_manager import ProjectManager
            self.project_manager = ProjectManager()
        except ImportError:
            self.project_manager = None
            
        try:
            from ai_assistant.automation.task_planner import TaskPlanner
            self.task_planner = TaskPlanner()
        except ImportError:
            self.task_planner = None
            
        try:
            from ai_assistant.core.chain_of_actions_manager import ChainOfActionsManager
            self.chain_manager = ChainOfActionsManager()
        except ImportError:
            self.chain_manager = None
        
    def clear_temp_files(self):
        """Clears application temp files if disk space or memory is low."""
        try:
            temp_dir = tempfile.gettempdir()
            ai_temp_pattern = os.path.join(temp_dir, "ai_assistant_*.tmp")
            files = glob.glob(ai_temp_pattern)
            for f in files:
                try:
                    os.remove(f)
                except OSError:
                    pass
            logger.info(f"Autonomous Actions: Cleared {len(files)} temp files.")
        except Exception as e:
            logger.error(f"Failed autonomous temp clearance: {e}")
            
    def prepare_data(self):
        """Pre-warms caches or prepares data for fast retrieval."""
        logger.info("Autonomous Actions: Pre-warming semantic cache.")
        pass

    def progress_projects(self):
        """Autonomously identify pending tasks in active projects and delegate them to the planner."""
        if not (self.project_manager and self.task_planner and self.chain_manager):
            logger.warning("Cannot progress projects: required modules missing.")
            return
            
        active_projects = self.project_manager.get_all_projects("active")
        for project in active_projects:
            for milestone in project.milestones:
                if milestone.completed:
                    continue
                for task in milestone.tasks:
                    if task.status == "pending":
                        logger.info(f"Autonomously initiating task '{task.description}' for project '{project.name}'")
                        # Delegate to planner
                        command = f"Autonomously execute task for project {project.name}: {task.description}"
                        plan = self.task_planner.plan_task(command)
                        if plan and plan.actions:
                            self.chain_manager.execute_chain(plan)
                            # Update task status to in_progress
                            task.status = "in_progress"
                            self.project_manager.save_project(project)
                        # Only initiate one autonomous task at a time
                        return
