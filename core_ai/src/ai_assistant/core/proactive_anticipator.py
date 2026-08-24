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
        # Fetch usage pattern summary
        summary = self.analyzer.get_pattern_summary()
        peak_activity = summary.get('peak_activity', 'unknown')
        top_apps = summary.get('top_apps', [])
        frequent_topics = summary.get('frequent_topics', [])
        
        current_hour = now.hour
        context = self.context_opt.get_time_context()
        proactive_msg = None
        
        # Pattern-driven proactive logic
        if peak_activity != 'unknown' and str(current_hour) in peak_activity:
            proactive_msg = f"Sir, we are entering your peak activity period. Should I prepare your usual workflow? {', '.join(top_apps[:2])} perhaps?"
        elif current_hour == 8 and context == "work":
            proactive_msg = "Good morning! I've pre-fetched your daily briefing. Would you like a summary of today's schedule?"
        elif current_hour == 18 and context == "home":
            proactive_msg = "Good evening! It appears you've transitioned to your home context. Shall I prepare some relaxing music or focus on winding down?"
        elif current_hour >= 23 and context == "night":
            proactive_msg = "It's getting quite late. Based on your energy curve, I recommend wrapping up your current task soon."
        elif len(frequent_topics) > 0 and current_hour == 13: # Lunch break suggestion
            proactive_msg = f"Taking a break? You frequently ask about {frequent_topics[0]}. Would you like me to fetch the latest updates on that?"
            
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
