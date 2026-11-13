"""
Initialization Service

Handles ModernAssistant initialization logic including eager and lazy loading.
Extracted from ModernAssistant for better modularity.
"""

import logging
import threading

logger = logging.getLogger(__name__)

class InitializationService:
    """Manages initialization of assistant services"""
    
    def __init__(self, lazy_init=True):
        """
        Initialize service manager
        
        Args:
            lazy_init: If True, use lazy initialization
        """
        self.lazy_init = lazy_init
        self.background_init_complete = False
        self.init_status = {}
        self._init_lock = threading.Lock()
    
    def initialize_memory(self):
        """Initialize memory system"""
        try:
            from ai_assistant.modules.memory_manager import MemoryManager
            memory = MemoryManager()
            self.init_status['memory'] = 'ready'
            logger.info("Memory uninitialized")
            return memory
        except Exception as e:
            logger.error(f"Memory initialization failed: {e}")
            self.init_status['memory'] = 'failed'
            return None
    
    def background_initialize(self, services):
        """
        Background initialization of services
        
        Args:
            services: Dict of service managers to initialize
        """
        def init():
            logger.info("Background initialization started")
            
            # Initialize AI services in background
            if 'ai_manager' in services:
                try:
                    _ = services['ai_manager'].conversational_ai
                except:
                    pass
            
            # Initialize voice services
            if 'voice_manager' in services:
                try:
                    _ = services['voice_manager'].voice_recognizer
                except:
                    pass
            
            self.background_init_complete = True
            logger.info("Background initialization complete")
        
        thread = threading.Thread(target=init, daemon=True)
        thread.start()
    
    def eager_initialize(self, services):
        """
        Eager initialization - load everything immediately
        
        Args:
            services: Dict of service managers to initialize
        """
        logger.info("Eager initialization started")
        
        # Initialize all services
        if 'ai_manager' in services:
            _ = services['ai_manager'].multimodal_ai
            _ = services['ai_manager'].conversational_ai
            _ = services['ai_manager'].llm_chat
        
        if 'voice_manager' in services:
            _ = services['voice_manager'].voice_recognizer
            _ = services['voice_manager'].tts_engine
        
        logger.info("Eager initialization complete")
    
    def get_status(self):
        """Get initialization status"""
        return self.init_status.copy()
