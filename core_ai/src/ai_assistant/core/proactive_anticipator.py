import threading
import time
import logging
from datetime import datetime
from ai_assistant.ai.usage_pattern_analyzer import UsagePatternAnalyzer
from ai_assistant.core.context_optimizer import ContextOptimizer

logger = logging.getLogger(__name__)

class ProactiveAnticipator:
    def __init__(self, chat_interface=None):
        self.analyzer = UsagePatternAnalyzer()
        self.context_opt = ContextOptimizer()
        self.chat_interface = chat_interface
        self.running = False
        self.thread = None
        self.last_check_hour = -1
        
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
        
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._schedule_loop, daemon=True)
            self.thread.start()
            logger.info("Proactive Anticipator started.")
            
    def stop(self):
        self.running = False
        
    def _schedule_loop(self):
        # Initial wait to let system settle
        time.sleep(10)
        
        while self.running:
            try:
                now = datetime.now()
                # Check once per hour
                if now.hour != self.last_check_hour:
                    self.last_check_hour = now.hour
                    self._check_for_proactive_actions(now)
            except Exception as e:
                logger.error(f"Error in proactive anticipator: {e}")
            
            # Sleep for 5 minutes before checking again
            time.sleep(300)
            
    def _check_for_proactive_actions(self, now: datetime):
        # Fetch usage pattern summary
        summary = self.analyzer.get_pattern_summary()
        peak_activity = summary.get('peak_activity', 'unknown')
        top_apps = summary.get('top_apps', [])
        frequent_topics = summary.get('frequent_topics', [])
        
        current_hour = now.hour
        context = self.context_opt.get_time_context()
        proactive_msg = None
        
        # 1. Commitment Checks
        if self.commitment_tracker:
            overdue = self.commitment_tracker.get_overdue()
            if overdue:
                proactive_msg = f"Reminder: You have {len(overdue)} overdue commitments, including '{overdue[0].action}'. Shall we tackle them now?"
                
        # 2. Project Checks
        if not proactive_msg and self.project_manager:
            active_projects = self.project_manager.get_all_projects("active")
            if active_projects and current_hour == 10:
                proactive_msg = f"Your project '{active_projects[0].name}' is currently active. Want to make some progress on it today?"

        # 3. Emotion / Pattern Checks
        if not proactive_msg:
            if self.conversational_ai and hasattr(self.conversational_ai, 'get_mood_trend'):
                trend = self.conversational_ai.get_mood_trend(days=1)
                if trend and "stressed" in trend.lower():
                    proactive_msg = "You've seemed a bit stressed lately. Would you like me to block out some quiet time on your calendar?"
                    
        # 4. Routine Checks
        if not proactive_msg:
            if peak_activity != 'unknown' and str(current_hour) in peak_activity:
                proactive_msg = f"Sir, we are entering your peak activity period. Should I prepare your usual workflow? {', '.join(top_apps[:2])} perhaps?"
            elif current_hour == 8 and context == "work":
                proactive_msg = "Good morning! I've pre-fetched your daily briefing. Would you like a summary of today's schedule?"
            elif current_hour >= 23 and context == "night":
                proactive_msg = "It's getting quite late. Based on your energy curve, I recommend wrapping up your current task soon."
            
        if proactive_msg and self.chat_interface:
            # We inject the proactive message into the chat as an assistant message
            self.chat_interface.add_message("assistant", proactive_msg)
            
            try:
                from ai_assistant.backend.routes.common import get_socketio
                socketio = get_socketio()
                if socketio:
                    socketio.emit('chat_response', {'data': proactive_msg})
            except ImportError:
                pass
