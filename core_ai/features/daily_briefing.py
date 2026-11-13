import logging
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DailyBriefing:
    """Generates a morning summary including weather, schedule, news, projects, and commitments."""
    
    def __init__(self):
        try:
            from ai_assistant.core.real_time_api_manager import RealTimeAPIManager
            self.api_manager = RealTimeAPIManager()
        except ImportError:
            self.api_manager = None
            
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
            
    def generate_briefing(self, latitude: float = 37.7749, longitude: float = -122.4194) -> str:
        date_str = datetime.now().strftime("%A, %B %d, %Y")
        briefing = [f"Good morning! Here is your daily briefing for {date_str}:\n"]
        
        # Weather
        if self.api_manager:
            weather = self.api_manager.get_weather(latitude, longitude)
            if "temperature" in weather:
                briefing.append(f"🌦️ Weather: {weather['temperature']}C, wind: {weather['windspeed']} km/h.\n")
        
        # Pending Commitments
        if self.commitment_tracker:
            overdue = self.commitment_tracker.get_overdue()
            pending = self.commitment_tracker.get_pending()
            if overdue:
                briefing.append(f"⚠️ You have {len(overdue)} OVERDUE commitments!")
                for c in overdue[:3]:
                    briefing.append(f"  - {c.action} (was due {c.deadline})")
            if pending:
                briefing.append(f"📝 You have {len(pending)} pending commitments.")
            briefing.append("")
                
        # Project Status
        if self.project_manager:
            active_projects = self.project_manager.get_all_projects(status="active")
            if active_projects:
                briefing.append("🚀 Active Projects:")
                for p in active_projects:
                    briefing.append(f"  - {p.name}: {p.progress_pct:.1f}% complete")
            briefing.append("")
        
        # News
        if self.api_manager:
            news = self.api_manager.get_top_news("technology")
            if news:
                briefing.append("📰 Top Tech News:")
                for n in news[:3]:
                    briefing.append(f"  - {n['title']}")
                    
        return "\n".join(briefing)
