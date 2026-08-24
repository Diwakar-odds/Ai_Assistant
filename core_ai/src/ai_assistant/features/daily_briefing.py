import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class DailyBriefing:
    """Generates a morning summary including weather, schedule, and news."""
    
    def __init__(self):
        try:
            from ai_assistant.core.real_time_api_manager import RealTimeAPIManager
            self.api_manager = RealTimeAPIManager()
        except ImportError:
            self.api_manager = None
            
    def generate_briefing(self, latitude: float = 37.7749, longitude: float = -122.4194) -> str:
        briefing = ["Good morning! Here is your daily briefing:"]
        
        # Weather
        if self.api_manager:
            weather = self.api_manager.get_weather(latitude, longitude)
            if "temperature" in weather:
                briefing.append(f"🌦️ Weather: It is currently {weather['temperature']}°C with windspeeds of {weather['windspeed']} km/h.")
        
        # News
        if self.api_manager:
            news = self.api_manager.get_top_news("technology")
            if news:
                briefing.append("📰 Top Tech News:")
                for n in news[:3]:
                    briefing.append(f"  - {n['title']}")
                    
        return "\n".join(briefing)
