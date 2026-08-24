import threading
import time
import logging

logger = logging.getLogger(__name__)

class HealthMonitor:
    """Daemon that polls system health and feeds data to the SelfHealingEngine."""
    
    def __init__(self, engine):
        self.engine = engine
        self.running = False
        self.thread = None
        self._last_backup = time.time() - (8 * 86400) # Mock: 8 days ago
        from ai_assistant.core.situation_awareness import SituationAwareness
        self.situation_awareness = SituationAwareness()
        
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            logger.info("Health Monitor started.")
            
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
            
    def _monitor_loop(self):
        while self.running:
            try:
                import psutil
                
                # Memory check
                mem = psutil.virtual_memory()
                if mem.percent > 90:
                    logger.warning("High memory usage detected! Triggering self-healing cleanup.")
                    self.engine.report_failure("memory")
                    
                # Disk usage check
                try:
                    disk = psutil.disk_usage('/')
                    if disk.percent > 90:
                        logger.warning("Low disk space! Triggering warning.")
                        # In a real system, emit socket event here
                except Exception:
                    pass
                    
                # API Expiry (Mock)
                api_days_left = 2
                if api_days_left < 3:
                    logger.warning(f"API key expires in {api_days_left} days!")
                    
                # Backup check
                if time.time() - self._last_backup > 7 * 86400:
                    logger.warning("No backup in 7 days!")
                    
                # Context Switch detection
                if hasattr(self, 'situation_awareness'):
                    switched, old_ctx, new_ctx = self.situation_awareness.detect_context_switch()
                    if switched and old_ctx:
                        logger.info(f"Context switched from {old_ctx} to {new_ctx}. Suggesting save.")
                        # Emit a proactive suggestion via assistant if we had a reference
                        
            except Exception as e:
                logger.error(f"HealthMonitor error: {e}")
            
            # Poll every 10 seconds for context switches
            time.sleep(10)
