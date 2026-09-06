# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Pulsar AI Assistant - JARVIS-Style Startup Sequence
Provides system diagnostics, contextual briefing, and personalized greetings
"""

import os
import sys
from datetime import datetime
from pathlib import Path
import json

# System monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Import automation tools for app discovery
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from automation_tools_new import (
        get_system_status, get_network_info, 
        discover_applications, get_app_usage_stats
    )
    AUTOMATION_AVAILABLE = True
except ImportError:
    AUTOMATION_AVAILABLE = False


class StartupSequence:
    """Manages JARVIS-style startup sequence and system diagnostics"""
    
    def __init__(self):
        self.startup_time = datetime.now()
        
    def get_time_based_greeting(self):
        """Generate time-aware greeting like JARVIS"""
        current_hour = datetime.now().hour
        
        if 5 <= current_hour < 12:
            greeting = "Good morning"
        elif 12 <= current_hour < 17:
            greeting = "Good afternoon"
        elif 17 <= current_hour < 22:
            greeting = "Good evening"
        else:
            greeting = "Good night"
        
        return greeting
    
    def get_system_diagnostics(self):
        """
        Perform comprehensive system diagnostics
        Returns status of all major subsystems
        """
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "operational",
            "systems": []
        }
        
        # 1. AI Core Status
        ai_status = self._check_ai_core()
        diagnostics["systems"].append(ai_status)
        
        # 2. Voice System Status
        voice_status = self._check_voice_system()
        diagnostics["systems"].append(voice_status)
        
        # 3. Automation System Status
        automation_status = self._check_automation_system()
        diagnostics["systems"].append(automation_status)
        
        # 4. Learning System Status
        learning_status = self._check_learning_system()
        diagnostics["systems"].append(learning_status)
        
        # 5. Network Status
        network_status = self._check_network_status()
        diagnostics["systems"].append(network_status)
        
        # 6. Storage Status
        storage_status = self._check_storage_status()
        diagnostics["systems"].append(storage_status)
        
        # Determine overall status
        statuses = [s["status"] for s in diagnostics["systems"]]
        if "error" in statuses:
            diagnostics["overall_status"] = "degraded"
        elif "warning" in statuses:
            diagnostics["overall_status"] = "partial"
        else:
            diagnostics["overall_status"] = "operational"
        
        return diagnostics
    
    def _check_ai_core(self):
        """Check AI core services (Gemini, OpenAI)"""
        status = {
            "name": "AI Core",
            "icon": " ",
            "status": "operational",
            "message": "Gemini 2.0 Pro ready",
            "details": {}
        }
        
        # Check for API keys
        gemini_key = os.getenv("GEMINI_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if gemini_key:
            status["details"]["gemini"] = "configured"
        else:
            status["status"] = "warning"
            status["message"] = "Gemini API key not configured"
        
        if openai_key:
            status["details"]["openai"] = "configured"
        
        return status
    
    def _check_voice_system(self):
        """Check voice recognition and TTS systems"""
        status = {
            "name": "Voice System",
            "icon": "Ž¤",
            "status": "operational",
            "message": "Voice recognition ready",
            "details": {}
        }
        
        # Check if voice modules are available
        try:
            import speech_recognition
            status["details"]["recognition"] = "available"
        except ImportError:
            status["status"] = "warning"
            status["message"] = "Voice recognition unavailable"
        
        try:
            import kittentts
            status["details"]["tts"] = "available (kittentts)"
        except ImportError:
            if status["status"] != "warning":
                status["status"] = "partial"
        
        return status
    
    def _check_automation_system(self):
        """Check automation and app control systems"""
        status = {
            "name": "Automation",
            "icon": "š",
            "status": "operational",
            "message": "Automation tools active",
            "details": {}
        }
        
        if AUTOMATION_AVAILABLE:
            try:
                # Try to discover apps
                apps = discover_applications()
                status["details"]["apps_discovered"] = len(apps) if apps else 0
                status["message"] = f"{len(apps) if apps else 0} applications available"
            except Exception as e:
                status["status"] = "warning"
                status["message"] = "Automation partially available"
        else:
            status["status"] = "error"
            status["message"] = "Automation unavailable"
        
        return status
    
    def _check_learning_system(self):
        """Check AI learning and memory systems"""
        status = {
            "name": "Learning System",
            "icon": "š",
            "status": "operational",
            "message": "Learning systems active",
            "details": {}
        }
        
        # Check for learning databases
        db_files = [
            "enhanced_learning.db",
            "data/core/conversation_ai.db",
            "data/core/language_data.db"
        ]
        
        active_dbs = 0
        for db_file in db_files:
            if Path(db_file).exists():
                active_dbs += 1
        
        status["details"]["active_databases"] = active_dbs
        
        if active_dbs == 0:
            status["status"] = "warning"
            status["message"] = "Learning databases not initialized"
        else:
            status["message"] = f"{active_dbs} learning databases active"
        
        return status
    
    def _check_network_status(self):
        """Check network connectivity"""
        status = {
            "name": "Network",
            "icon": "Œ",
            "status": "operational",
            "message": "Connected",
            "details": {}
        }
        
        if PSUTIL_AVAILABLE:
            try:
                net_io = psutil.net_io_counters()
                status["details"]["bytes_sent"] = net_io.bytes_sent
                status["details"]["bytes_recv"] = net_io.bytes_recv
                
                # Check if there's any network activity
                if net_io.bytes_sent == 0 and net_io.bytes_recv == 0:
                    status["status"] = "warning"
                    status["message"] = "No network activity detected"
            except Exception:
                status["status"] = "warning"
                status["message"] = "Network status unknown"
        else:
            status["status"] = "partial"
            status["message"] = "Network monitoring unavailable"
        
        return status
    
    def _check_storage_status(self):
        """Check disk storage status"""
        status = {
            "name": "Storage",
            "icon": "¾",
            "status": "operational",
            "message": "Storage healthy",
            "details": {}
        }
        
        if PSUTIL_AVAILABLE:
            try:
                disk = psutil.disk_usage('C:\\' if os.name == 'nt' else '/')
                percent_used = disk.percent
                
                status["details"]["percent_used"] = percent_used
                status["details"]["free_gb"] = round(disk.free / (1024**3), 2)
                
                if percent_used > 90:
                    status["status"] = "warning"
                    status["message"] = f"Low storage: {100 - percent_used:.1f}% free"
                elif percent_used > 95:
                    status["status"] = "error"
                    status["message"] = "Critical: Storage almost full"
                else:
                    status["message"] = f"{100 - percent_used:.1f}% free"
            except Exception:
                status["status"] = "warning"
                status["message"] = "Storage status unknown"
        else:
            status["status"] = "partial"
            status["message"] = "Storage monitoring unavailable"
        
        return status
    
    def get_contextual_briefing(self):
        """
        Generate contextual briefing based on time, calendar, tasks, etc.
        Now enhanced with InsightsEngine for real data.
        """
        briefing = {
            "timestamp": datetime.now().isoformat(),
            "items": []
        }
        
        # Current time and date
        now = datetime.now()
        briefing["items"].append({
            "type": "time",
            "icon": "•",
            "message": now.strftime("%A, %B %d, %Y | %I:%M %p")
        })
        
        try:
            # Get insights from engine
            from insights_engine import get_insights_engine
            insights = get_insights_engine().get_daily_briefing()
            
            # 1. Weather
            weather = insights.get('weather', {})
            if weather:
                temp = weather.get('temperature', 'N/A')
                desc = weather.get('condition', 'Unknown')
                loc = weather.get('location', '')
                briefing["items"].append({
                    "type": "weather",
                    "icon": "Œ¤",
                    "message": f"{temp}, {desc} in {loc}"
                })
            
            # 2. Calendar / Events
            events = insights.get('calendar', [])
            if events:
                next_event = events[0]
                event_time = datetime.fromisoformat(next_event['start']).strftime("%I:%M %p")
                briefing["items"].append({
                    "type": "calendar",
                    "icon": "…",
                    "message": f"Next: {next_event['title']} at {event_time}"
                })
            else:
                briefing["items"].append({
                    "type": "calendar",
                    "icon": "…",
                    "message": "No upcoming events scheduled"
                })
                
            # 3. Focus / Tasks
            tasks = insights.get('tasks', [])
            pending_high_priority = len([t for t in tasks if t.get('priority') == 'high'])
            
            briefing["items"].append({
                "type": "tasks",
                "icon": "…",
                "message": f"{len(tasks)} pending tasks ({pending_high_priority} high priority)"
            })

            # Add raw data for frontend to use if needed
            briefing["raw_insights"] = insights
            
        except Exception as e:
            logger.error(f"Error getting insights: {e}")
            # Fallback to simple uptime
            if PSUTIL_AVAILABLE:
                try:
                    boot_time = datetime.fromtimestamp(psutil.boot_time())
                    uptime = now - boot_time
                    hours = int(uptime.total_seconds() // 3600)
                    briefing["items"].append({
                        "type": "uptime",
                        "icon": "±",
                        "message": f"System uptime: {hours} hours"
                    })
                except Exception:
                    pass
        
        return briefing
    
    def get_startup_sequence_data(self):
        """
        Get complete startup sequence data
        This is the main method called by the API endpoint
        """
        greeting = self.get_time_based_greeting()
        diagnostics = self.get_system_diagnostics()
        briefing = self.get_contextual_briefing()
        
        return {
            "greeting": greeting,
            "timestamp": datetime.now().isoformat(),
            "diagnostics": diagnostics,
            "briefing": briefing,
            "status": diagnostics["overall_status"]
        }


# Singleton instance
_startup_sequence = None

def get_startup_sequence():
    """Get or create startup sequence instance"""
    global _startup_sequence
    if _startup_sequence is None:
        _startup_sequence = StartupSequence()
    return _startup_sequence

