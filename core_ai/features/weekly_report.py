import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class WeeklyReport:
    """Generates a Friday evening summary of productivity and time saved."""
    
    def __init__(self):
        try:
            from ai_assistant.core.project_manager import ProjectManager
            self.project_manager = ProjectManager()
        except ImportError:
            self.project_manager = None
            
        try:
            from ai_assistant.core.commitment_tracker import CommitmentTracker
            self.commitment_tracker = CommitmentTracker()
        except ImportError:
            self.commitment_tracker = None
            
        try:
            from ai_assistant.ai.conversational_ai import get_conversational_ai
            self.conversational_ai = get_conversational_ai()
        except ImportError:
            self.conversational_ai = None
        
    def generate_report(self) -> str:
        report = [
            "📊 Weekly Productivity Report",
            "-------------------------------"
        ]
        
        # Real tasks completed
        if self.project_manager:
            projects = self.project_manager.get_all_projects()
            completed_tasks = 0
            active_projects = 0
            for p in projects:
                if p.status == "active":
                    active_projects += 1
                for m in p.milestones:
                    completed_tasks += sum(1 for t in m.tasks if t.status == "completed")
            report.append(f"✅ Tasks Completed: {completed_tasks}")
            report.append(f"🚀 Active Projects Progressed: {active_projects}")
            
        # Commitments met
        if self.commitment_tracker:
            # We don't have a get_fulfilled method yet, but we could add one.
            # For now, just show pending vs overdue
            overdue = len(self.commitment_tracker.get_overdue())
            pending = len(self.commitment_tracker.get_pending())
            report.append(f"📝 Commitments: {pending} pending, {overdue} overdue")
            
        # Emotion trend
        if self.conversational_ai and hasattr(self.conversational_ai, 'get_mood_trend'):
            try:
                trend = self.conversational_ai.get_mood_trend(days=7)
                if trend:
                    report.append(f"🧠 Mood Trend: {trend}")
            except Exception:
                pass
                
        report.append("-------------------------------")
        report.append("Keep up the great work next week!")
        
        return "\n".join(report)
