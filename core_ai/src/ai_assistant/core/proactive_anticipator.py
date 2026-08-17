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
        # Fetch time patterns
        patterns = self.analyzer._analyze_time_patterns(days_back=7)
        if not patterns:
            return
            
        current_hour = now.hour
        # simplified check: if we have significant usage at this hour, maybe generate a greeting/summary
        # Since actual pattern structure is nested, let's just do a basic contextual proactive push
        
        context = self.context_opt.get_time_context()
        proactive_msg = None
        
        if current_hour == 8 and context == "work":
            proactive_msg = "Good morning! It's 8 AM. Would you like your morning briefing and schedule summary?"
        elif current_hour == 18 and context == "home":
            proactive_msg = "Good evening! You've transitioned to home context. Should I play some relaxing music?"
        elif current_hour == 23 and context == "night":
            proactive_msg = "It's getting late. Don't forget to wind down and rest soon."
            
        if proactive_msg and self.chat_interface:
            # We inject the proactive message into the chat as an assistant message
            self.chat_interface.add_message("assistant", proactive_msg)
            # Depending on UI implementation, we might need to push this via socketio
            try:
                from ai_assistant.services.modern_web_backend import socketio
                if socketio:
                    socketio.emit('chat_response', {'data': proactive_msg})
            except ImportError:
                pass
