"""
Conversation Context Manager
Maintains conversation state across multiple turns and task executions.
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionState(Enum):
    """States of task execution."""
    IDLE = "idle"
    PARSING = "parsing"
    EXECUTING = "executing"
    WAITING_FOR_INPUT = "waiting_for_input"
    WAITING_FOR_APP = "waiting_for_app"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETE = "complete"


@dataclass
class ConversationContext:
    """
    Container for conversation context.
    
    Tracks:
    - Current task chain being executed
    - Current step in the chain
    - Execution state
    - Context variables (current_app, contact, etc.)
    - Command history
    """
    
    # Task execution
    current_task_chain: List[Dict[str, Any]] = None
    current_step: int = 0
    execution_state: str = "idle"
    
    # Context variables
    context_vars: Dict[str, Any] = None
    
    # History
    command_history: List[Dict[str, Any]] = None
    
    # Timestamps
    created_at: float = None
    updated_at: float = None
    
    def __post_init__(self):
        if self.current_task_chain is None:
            self.current_task_chain = []
        if self.context_vars is None:
            self.context_vars = {}
        if self.command_history is None:
            self.command_history = []
        if self.created_at is None:
            self.created_at = time.time()
        if self.updated_at is None:
            self.updated_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """Create from dictionary."""
        return cls(**data)


class ContextManager:
    """
    Manages conversation context with persistence.
    
    Features:
    - Context variable management (current_app, selected_contact, etc.)
    - Command history tracking
    - State persistence to disk
    - Override detection
    - Context-aware intent resolution
    """
    
    def __init__(self, storage_path: str = None):
        """
        Initialize context manager.
        
        Args:
            storage_path: Path to store context data
        """
        if storage_path is None:
            storage_path = "data/conversation_context.json"
        
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Current context
        self.context = ConversationContext()
        
        # Load from disk if exists
        self.load_context()
        
        logger.info(f"Context manager initialized with storage: {self.storage_path}")
    
    # ===== CONTEXT VARIABLE MANAGEMENT =====
    
    def set_var(self, key: str, value: Any):
        """Set a context variable."""
        self.context.context_vars[key] = value
        self.context.updated_at = time.time()
        self.save_context()
        logger.debug(f"Set context var: {key} = {value}")
    
    def get_var(self, key: str, default: Any = None) -> Any:
        """Get a context variable."""
        return self.context.context_vars.get(key, default)
    
    def has_var(self, key: str) -> bool:
        """Check if context variable exists."""
        return key in self.context.context_vars
    
    def delete_var(self, key: str):
        """Delete a context variable."""
        if key in self.context.context_vars:
            del self.context.context_vars[key]
            self.context.updated_at = time.time()
            self.save_context()
    
    def clear_vars(self):
        """Clear all context variables."""
        self.context.context_vars = {}
        self.context.updated_at = time.time()
        self.save_context()
    
    # ===== STATE MANAGEMENT =====
    
    def set_state(self, state: ExecutionState):
        """Set execution state."""
        self.context.execution_state = state.value
        self.context.updated_at = time.time()
        self.save_context()
        logger.info(f"State changed to: {state.value}")
    
    def get_state(self) -> ExecutionState:
        """Get current execution state."""
        try:
            return ExecutionState(self.context.execution_state)
        except ValueError:
            return ExecutionState.IDLE
    
    # ===== TASK CHAIN MANAGEMENT =====
    
    def set_task_chain(self, task_chain: List[Dict[str, Any]]):
        """Set current task chain."""
        self.context.current_task_chain = task_chain
        self.context.current_step = 0
        self.context.updated_at = time.time()
        self.save_context()
        logger.info(f"Task chain set with {len(task_chain)} steps")
    
    def get_task_chain(self) -> List[Dict[str, Any]]:
        """Get current task chain."""
        return self.context.current_task_chain
    
    def advance_step(self):
        """Move to next step in task chain."""
        self.context.current_step += 1
        self.context.updated_at = time.time()
        self.save_context()
    
    def get_current_step(self) -> int:
        """Get current step number."""
        return self.context.current_step
    
    def clear_task_chain(self):
        """Clear task chain."""
        self.context.current_task_chain = []
        self.context.current_step = 0
        self.set_state(ExecutionState.IDLE)
    
    # ===== COMMAND HISTORY =====
    
    def add_command(self, command: str, intent: str = None, completed: bool = False):
        """Add command to history."""
        entry = {
            'timestamp': time.time(),
            'command': command,
            'intent': intent,
            'completed': completed,
            'context_snapshot': dict(self.context.context_vars)
        }
        
        self.context.command_history.append(entry)
        self.context.updated_at = time.time()
        
        # Keep only last 50 commands
        if len(self.context.command_history) > 50:
            self.context.command_history = self.context.command_history[-50:]
        
        self.save_context()
    
    def get_last_command(self) -> Optional[Dict[str, Any]]:
        """Get last command from history."""
        if self.context.command_history:
            return self.context.command_history[-1]
        return None
    
    def get_command_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent command history."""
        return self.context.command_history[-limit:]
    
    # ===== OVERRIDE DETECTION =====
    
    def is_override(self, new_command: str) -> bool:
        """
        Detect if new command is an override of current task.
        
        Override keywords: नहीं, no, wait, stop, cancel, change
        """
        override_keywords = ['नहीं', 'nahi', 'no', 'wait', 'stop', 'cancel', 'change', 'instead']
        
        new_command_lower = new_command.lower()
        for keyword in override_keywords:
            if keyword in new_command_lower:
                return True
        
        # Check if currently executing
        state = self.get_state()
        if state in [ExecutionState.EXECUTING, ExecutionState.WAITING_FOR_INPUT]:
            # New command while executing = potential override
            return True
        
        return False
    
    def handle_override(self, new_command: str):
        """
        Handle command override.
        
        Pauses current execution and prepares for new command.
        """
        logger.warning(f"Override detected: {new_command}")
        
        # Save current state
        self.set_var('paused_task_chain', self.context.current_task_chain)
        self.set_var('paused_step', self.context.current_step)
        
        # Clear current task
        self.clear_task_chain()
        
        # Mark as override
        self.set_var('last_action', 'override')
        self.add_command(new_command, intent='override')
    
    # ===== CONTEXT-AWARE HELPERS =====
    
    def infer_missing_params(self, intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Infer missing parameters from context.
        
        For example:
        - "message करो" → infer app from current_app
        - "send" → infer contact from last used contact
        """
        result = dict(params)
        
        # Infer app for message/type intents
        if intent in ['send_message', 'type_text'] and 'app_name' not in result:
            current_app = self.get_var('current_app')
            if current_app:
                result['app_name'] = current_app
                logger.debug(f"Inferred app_name from context: {current_app}")
        
        # Infer contact for send_message
        if intent == 'send_message' and 'contact' not in result:
            last_contact = self.get_var('selected_contact')
            if last_contact:
                result['contact'] = last_contact
                logger.debug(f"Inferred contact from context: {last_contact}")
        
        return result
    
    # ===== PERSISTENCE =====
    
    def save_context(self):
        """Save context to disk."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.context.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save context: {e}")
    
    def load_context(self):
        """Load context from disk."""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.context = ConversationContext.from_dict(data)
                    logger.info("Context loaded from disk")
        except Exception as e:
            logger.error(f"Failed to load context: {e}")
            self.context = ConversationContext()
    
    def reset(self):
        """Reset context to initial state."""
        self.context = ConversationContext()
        self.save_context()
        logger.info("Context reset")
    
    # ===== UTILITY =====
    
    def get_summary(self) -> Dict[str, Any]:
        """Get context summary."""
        return {
            'state': self.context.execution_state,
            'current_step': f"{self.context.current_step}/{len(self.context.current_task_chain)}",
            'active_vars': len(self.context.context_vars),
            'command_history_count': len(self.context.command_history),
            'key_vars': {
                'current_app': self.get_var('current_app'),
                'selected_contact': self.get_var('selected_contact'),
                'last_action': self.get_var('last_action'),
            }
        }


# Singleton instance
_context_manager = None

def get_context_manager() -> ContextManager:
    """Get singleton context manager."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager
