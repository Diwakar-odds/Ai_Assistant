"""
Automation Rule Engine

This module provides a sophisticated rule engine for automation with condition evaluation,
event-driven triggers, complex workflow management, and intelligent decision making.

Features:
- Complex rule definition with multiple conditions
- Event-driven automation triggers
- Rule chaining and workflow orchestration  
- Dynamic rule evaluation with context awareness
- Rule priority and conflict resolution
- Fact-based inference engine
- Rule template system
- Performance optimized rule execution
"""

import re
import ast
import time
import threading
import logging
import sqlite3
import json
import operator
import importlib
from typing import Dict, List, Optional, Callable, Any, Tuple, Set, Union, Type
from dataclasses import dataclass, field, asdict
from enum import Enum, IntEnum
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import weakref
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
import inspect

# Expression evaluation
try:
    import simpleeval
    SAFE_EVAL_AVAILABLE = True
except ImportError:
    SAFE_EVAL_AVAILABLE = False

class RuleType(Enum):
    """Types of automation rules"""
    CONDITION = "condition"      # If-then rules
    EVENT = "event"             # Event-triggered rules
    SCHEDULE = "schedule"       # Time-based rules
    WORKFLOW = "workflow"       # Multi-step workflows
    INFERENCE = "inference"     # Fact-based inference rules
    REACTIVE = "reactive"       # Reactive rules based on system state

class ConditionOperator(Enum):
    """Operators for rule conditions"""
    EQ = "eq"           # Equal
    NE = "ne"           # Not equal
    LT = "lt"           # Less than
    LE = "le"           # Less than or equal
    GT = "gt"           # Greater than
    GE = "ge"           # Greater than or equal
    IN = "in"           # In list/collection
    NOT_IN = "not_in"   # Not in list/collection
    CONTAINS = "contains" # String contains
    STARTS_WITH = "starts_with" # String starts with
    ENDS_WITH = "ends_with"     # String ends with
    MATCHES = "matches"         # Regex match
    EXISTS = "exists"           # Property exists
    IS_NULL = "is_null"         # Is null/None
    IS_NOT_NULL = "is_not_null" # Is not null/None

class ActionType(Enum):
    """Types of rule actions"""
    FUNCTION_CALL = "function_call"
    SET_PROPERTY = "set_property"
    SEND_EVENT = "send_event"
    LOG_MESSAGE = "log_message"
    DELAY = "delay"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    STOP_RULE = "stop_rule"
    TRIGGER_RULE = "trigger_rule"
    CUSTOM = "custom"

class RuleStatus(Enum):
    """Rule execution status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISABLED = "disabled"
    FAILED = "failed"
    EXPIRED = "expired"

class EventType(Enum):
    """System event types"""
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    FILE_CREATED = "file_created"
    FILE_MODIFIED = "file_modified"
    FILE_DELETED = "file_deleted"
    PROCESS_STARTED = "process_started"
    PROCESS_STOPPED = "process_stopped"
    NETWORK_CONNECTED = "network_connected"
    NETWORK_DISCONNECTED = "network_disconnected"
    CUSTOM = "custom"

@dataclass
class RuleCondition:
    """Individual rule condition"""
    field: str                           # Field/property to check
    operator: ConditionOperator         # Comparison operator  
    value: Any                          # Expected value
    weight: float = 1.0                 # Weight for weighted evaluations
    description: str = ""               # Human-readable description
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate condition against context"""
        try:
            # Get field value from context
            field_value = self._get_field_value(context, self.field)
            
            # Apply operator
            if self.operator == ConditionOperator.EQ:
                return field_value == self.value
            elif self.operator == ConditionOperator.NE:
                return field_value != self.value
            elif self.operator == ConditionOperator.LT:
                return field_value < self.value
            elif self.operator == ConditionOperator.LE:
                return field_value <= self.value
            elif self.operator == ConditionOperator.GT:
                return field_value > self.value
            elif self.operator == ConditionOperator.GE:
                return field_value >= self.value
            elif self.operator == ConditionOperator.IN:
                return field_value in self.value
            elif self.operator == ConditionOperator.NOT_IN:
                return field_value not in self.value
            elif self.operator == ConditionOperator.CONTAINS:
                return str(self.value) in str(field_value)
            elif self.operator == ConditionOperator.STARTS_WITH:
                return str(field_value).startswith(str(self.value))
            elif self.operator == ConditionOperator.ENDS_WITH:
                return str(field_value).endswith(str(self.value))
            elif self.operator == ConditionOperator.MATCHES:
                return bool(re.search(str(self.value), str(field_value)))
            elif self.operator == ConditionOperator.EXISTS:
                return self.field in context
            elif self.operator == ConditionOperator.IS_NULL:
                return field_value is None
            elif self.operator == ConditionOperator.IS_NOT_NULL:
                return field_value is not None
            
            return False
            
        except Exception:
            return False
    
    def _get_field_value(self, context: Dict[str, Any], field_path: str) -> Any:
        """Get field value from context using dot notation"""
        try:
            value = context
            for part in field_path.split('.'):
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = getattr(value, part, None)
            return value
        except Exception:
            return None

@dataclass 
class RuleAction:
    """Rule action definition"""
    action_type: ActionType
    target: str = ""                    # Target for action (function name, property, etc.)
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None     # Optional condition for action
    delay_seconds: float = 0.0          # Delay before executing action
    retry_count: int = 0                # Number of retries on failure
    description: str = ""               # Human-readable description

@dataclass
class RuleEvent:
    """Rule event definition"""
    event_type: EventType
    event_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "system"
    priority: int = 5

@dataclass
class RuleContext:
    """Context for rule evaluation"""
    facts: Dict[str, Any] = field(default_factory=dict)
    events: List[RuleEvent] = field(default_factory=list)
    system_state: Dict[str, Any] = field(default_factory=dict)
    user_context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class AutomationRule:
    """Complete automation rule definition"""
    id: str
    name: str
    rule_type: RuleType
    
    # Conditions and logic
    conditions: List[RuleCondition] = field(default_factory=list)
    condition_logic: str = "AND"        # AND, OR, or custom expression
    custom_logic: Optional[str] = None  # Custom Python expression
    
    # Actions
    actions: List[RuleAction] = field(default_factory=list)
    
    # Triggers and events
    trigger_events: List[EventType] = field(default_factory=list)
    trigger_expression: Optional[str] = None
    
    # Execution settings
    priority: int = 5                   # 1-10, higher is more important
    max_executions: Optional[int] = None # Maximum number of executions
    cooldown_seconds: float = 0.0       # Minimum time between executions
    timeout_seconds: float = 300.0      # Maximum execution time
    
    # Status and tracking
    status: RuleStatus = RuleStatus.ACTIVE
    execution_count: int = 0
    last_execution: Optional[datetime] = None
    last_result: Optional[Any] = None
    error_count: int = 0
    last_error: Optional[str] = None
    
    # Metadata
    created_time: datetime = field(default_factory=datetime.now)
    updated_time: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    description: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Rule dependencies and relationships
    depends_on: List[str] = field(default_factory=list)  # Rule IDs this depends on
    blocks: List[str] = field(default_factory=list)      # Rules this blocks
    
    # Expiration
    expires_at: Optional[datetime] = None
    
    def evaluate_conditions(self, context: RuleContext) -> Tuple[bool, float]:
        """
        Evaluate rule conditions
        
        Returns:
            (result, confidence_score)
        """
        try:
            if not self.conditions:
                return True, 1.0
            
            # Evaluate each condition
            condition_results = []
            total_weight = 0.0
            
            for condition in self.conditions:
                result = condition.evaluate(context.facts)
                condition_results.append(result)
                total_weight += condition.weight
            
            # Apply condition logic
            if self.condition_logic == "AND":
                final_result = all(condition_results)
                confidence = 1.0 if final_result else 0.0
                
            elif self.condition_logic == "OR":
                final_result = any(condition_results)
                confidence = 1.0 if final_result else 0.0
                
            elif self.condition_logic == "WEIGHTED":
                # Weighted evaluation
                weighted_score = sum(
                    result * condition.weight 
                    for result, condition in zip(condition_results, self.conditions)
                )
                confidence = weighted_score / total_weight if total_weight > 0 else 0.0
                final_result = confidence > 0.5
                
            elif self.custom_logic and SAFE_EVAL_AVAILABLE:
                # Custom logic expression
                evaluator = simpleeval.SimpleEval()
                evaluator.names = {
                    f'c{i}': result 
                    for i, result in enumerate(condition_results)
                }
                final_result = bool(evaluator.eval(self.custom_logic))
                confidence = 1.0 if final_result else 0.0
                
            else:
                final_result = all(condition_results)
                confidence = 1.0 if final_result else 0.0
            
            return final_result, confidence
            
        except Exception as e:
            logging.error(f"Error evaluating conditions for rule {self.name}: {e}")
            return False, 0.0

class EventManager:
    """
    Manages events and event-driven rule triggers
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.event_queue = deque(maxlen=10000)
        self.event_handlers: Dict[EventType, List[Callable]] = defaultdict(list)
        self.event_history = deque(maxlen=1000)
        self._lock = threading.RLock()
        
        # Event processing
        self.processing_active = False
        self.processor_thread = None
    
    def start_processing(self):
        """Start event processing"""
        if self.processing_active:
            return
        
        self.processing_active = True
        self.processor_thread = threading.Thread(target=self._process_events, daemon=True)
        self.processor_thread.start()
        self.logger.info("Event processing started")
    
    def stop_processing(self):
        """Stop event processing"""
        self.processing_active = False
        if self.processor_thread:
            self.processor_thread.join(timeout=5.0)
        self.logger.info("Event processing stopped")
    
    def emit_event(self, event_type: EventType, event_data: Dict[str, Any] = None, 
                  source: str = "system", priority: int = 5):
        """Emit system event"""
        event = RuleEvent(
            event_type=event_type,
            event_data=event_data or {},
            source=source,
            priority=priority
        )
        
        with self._lock:
            self.event_queue.append(event)
            self.event_history.append(event)
        
        self.logger.debug(f"Event emitted: {event_type.value} from {source}")
    
    def register_handler(self, event_type: EventType, handler: Callable):
        """Register event handler"""
        with self._lock:
            self.event_handlers[event_type].append(handler)
    
    def unregister_handler(self, event_type: EventType, handler: Callable):
        """Unregister event handler"""
        with self._lock:
            if handler in self.event_handlers[event_type]:
                self.event_handlers[event_type].remove(handler)
    
    def get_recent_events(self, event_type: EventType = None, 
                         limit: int = 100) -> List[RuleEvent]:
        """Get recent events"""
        with self._lock:
            events = list(self.event_history)
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        return sorted(events, key=lambda x: x.timestamp, reverse=True)[:limit]
    
    def _process_events(self):
        """Process events from queue"""
        while self.processing_active:
            try:
                if self.event_queue:
                    with self._lock:
                        event = self.event_queue.popleft()
                    
                    # Call registered handlers
                    handlers = self.event_handlers.get(event.event_type, [])
                    for handler in handlers:
                        try:
                            handler(event)
                        except Exception as e:
                            self.logger.error(f"Event handler error: {e}")
                else:
                    time.sleep(0.1)
                    
            except Exception as e:
                self.logger.error(f"Event processing error: {e}")
                time.sleep(1.0)

class FactDatabase:
    """
    Database for storing and querying facts
    """
    
    def __init__(self):
        self.facts: Dict[str, Any] = {}
        self.fact_history: Dict[str, List[Tuple[datetime, Any]]] = defaultdict(list)
        self._lock = threading.RLock()
        
    def set_fact(self, key: str, value: Any, timestamp: datetime = None):
        """Set fact value"""
        timestamp = timestamp or datetime.now()
        
        with self._lock:
            old_value = self.facts.get(key)
            self.facts[key] = value
            
            # Store in history
            self.fact_history[key].append((timestamp, value))
            
            # Limit history size
            if len(self.fact_history[key]) > 100:
                self.fact_history[key] = self.fact_history[key][-100:]
    
    def get_fact(self, key: str, default: Any = None) -> Any:
        """Get fact value"""
        with self._lock:
            return self.facts.get(key, default)
    
    def delete_fact(self, key: str) -> bool:
        """Delete fact"""
        with self._lock:
            if key in self.facts:
                del self.facts[key]
                return True
            return False
    
    def get_facts_matching(self, pattern: str) -> Dict[str, Any]:
        """Get facts matching pattern"""
        import fnmatch
        
        with self._lock:
            return {
                k: v for k, v in self.facts.items()
                if fnmatch.fnmatch(k, pattern)
            }
    
    def get_fact_history(self, key: str, limit: int = 50) -> List[Tuple[datetime, Any]]:
        """Get fact history"""
        with self._lock:
            history = self.fact_history.get(key, [])
            return sorted(history, key=lambda x: x[0], reverse=True)[:limit]
    
    def get_all_facts(self) -> Dict[str, Any]:
        """Get all facts"""
        with self._lock:
            return self.facts.copy()

class RuleExecutor:
    """
    Executes rule actions
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.function_registry: Dict[str, Callable] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Register built-in functions
        self._register_builtin_functions()
    
    def register_function(self, name: str, function: Callable):
        """Register function for rule actions"""
        self.function_registry[name] = function
        self.logger.debug(f"Registered function: {name}")
    
    def execute_actions(self, actions: List[RuleAction], context: RuleContext) -> List[Any]:
        """Execute list of rule actions"""
        results = []
        
        for action in actions:
            try:
                # Check action condition
                if action.condition and not self._evaluate_action_condition(action.condition, context):
                    continue
                
                # Apply delay
                if action.delay_seconds > 0:
                    time.sleep(action.delay_seconds)
                
                # Execute action
                result = self._execute_single_action(action, context)
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Action execution failed: {e}")
                results.append(None)
        
        return results
    
    def _execute_single_action(self, action: RuleAction, context: RuleContext) -> Any:
        """Execute single rule action"""
        try:
            if action.action_type == ActionType.FUNCTION_CALL:
                return self._execute_function_call(action, context)
                
            elif action.action_type == ActionType.SET_PROPERTY:
                return self._execute_set_property(action, context)
                
            elif action.action_type == ActionType.SEND_EVENT:
                return self._execute_send_event(action, context)
                
            elif action.action_type == ActionType.LOG_MESSAGE:
                return self._execute_log_message(action, context)
                
            elif action.action_type == ActionType.DELAY:
                time.sleep(action.parameters.get('seconds', 1.0))
                return True
                
            elif action.action_type == ActionType.CONDITIONAL:
                return self._execute_conditional(action, context)
                
            elif action.action_type == ActionType.LOOP:
                return self._execute_loop(action, context)
                
            elif action.action_type == ActionType.CUSTOM:
                return self._execute_custom(action, context)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Action execution error: {e}")
            raise e
    
    def _execute_function_call(self, action: RuleAction, context: RuleContext) -> Any:
        """Execute function call action"""
        function_name = action.target
        
        if function_name not in self.function_registry:
            raise ValueError(f"Function '{function_name}' not registered")
        
        function = self.function_registry[function_name]
        parameters = action.parameters.copy()
        
        # Resolve parameter values from context
        resolved_params = self._resolve_parameters(parameters, context)
        
        return function(**resolved_params)
    
    def _execute_set_property(self, action: RuleAction, context: RuleContext) -> Any:
        """Execute set property action"""
        property_path = action.target
        value = action.parameters.get('value')
        
        # Resolve value from context if needed
        if isinstance(value, str) and value.startswith('$'):
            field_path = value[1:]  # Remove $ prefix
            value = self._get_context_value(context, field_path)
        
        # Set property in context
        self._set_context_value(context, property_path, value)
        return True
    
    def _execute_send_event(self, action: RuleAction, context: RuleContext) -> Any:
        """Execute send event action"""
        # This would integrate with the EventManager
        event_type = EventType(action.parameters.get('event_type', 'custom'))
        event_data = action.parameters.get('data', {})
        
        # Emit event through context (would need EventManager reference)
        self.logger.info(f"Event sent: {event_type.value}")
        return True
    
    def _execute_log_message(self, action: RuleAction, context: RuleContext) -> Any:
        """Execute log message action"""
        message = action.parameters.get('message', '')
        level = action.parameters.get('level', 'INFO')
        
        # Resolve message template
        resolved_message = self._resolve_template(message, context)
        
        getattr(self.logger, level.lower(), self.logger.info)(resolved_message)
        return True
    
    def _execute_conditional(self, action: RuleAction, context: RuleContext) -> Any:
        """Execute conditional action"""
        condition = action.parameters.get('condition')
        then_actions = action.parameters.get('then_actions', [])
        else_actions = action.parameters.get('else_actions', [])
        
        # Evaluate condition
        if self._evaluate_action_condition(condition, context):
            return self.execute_actions(then_actions, context)
        else:
            return self.execute_actions(else_actions, context)
    
    def _execute_loop(self, action: RuleAction, context: RuleContext) -> Any:
        """Execute loop action"""
        loop_actions = action.parameters.get('actions', [])
        iterations = action.parameters.get('iterations', 1)
        condition = action.parameters.get('while_condition')
        
        results = []
        
        if condition:
            # While loop
            while self._evaluate_action_condition(condition, context):
                loop_results = self.execute_actions(loop_actions, context)
                results.extend(loop_results)
        else:
            # For loop
            for _ in range(iterations):
                loop_results = self.execute_actions(loop_actions, context)
                results.extend(loop_results)
        
        return results
    
    def _execute_custom(self, action: RuleAction, context: RuleContext) -> Any:
        """Execute custom action"""
        custom_code = action.parameters.get('code', '')
        
        if SAFE_EVAL_AVAILABLE and custom_code:
            evaluator = simpleeval.SimpleEval()
            evaluator.names = {
                'context': context,
                'facts': context.facts,
                'system_state': context.system_state
            }
            
            return evaluator.eval(custom_code)
        
        return None
    
    def _register_builtin_functions(self):
        """Register built-in functions"""
        self.register_function('log', lambda message, level='INFO': 
                             getattr(self.logger, level.lower())(message))
        
        self.register_function('sleep', lambda seconds: time.sleep(seconds))
        
        self.register_function('now', lambda: datetime.now())
        
        self.register_function('format_string', lambda template, **kwargs: 
                             template.format(**kwargs))
    
    def _resolve_parameters(self, parameters: Dict[str, Any], context: RuleContext) -> Dict[str, Any]:
        """Resolve parameter values from context"""
        resolved = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith('$'):
                # Context reference
                field_path = value[1:]
                resolved[key] = self._get_context_value(context, field_path)
            elif isinstance(value, str) and '{{' in value:
                # Template string
                resolved[key] = self._resolve_template(value, context)
            else:
                resolved[key] = value
        
        return resolved
    
    def _get_context_value(self, context: RuleContext, field_path: str) -> Any:
        """Get value from context using dot notation"""
        try:
            parts = field_path.split('.')
            
            if parts[0] == 'facts':
                value = context.facts
                for part in parts[1:]:
                    value = value.get(part) if isinstance(value, dict) else getattr(value, part, None)
                return value
            elif parts[0] == 'system_state':
                value = context.system_state
                for part in parts[1:]:
                    value = value.get(part) if isinstance(value, dict) else getattr(value, part, None)
                return value
            elif parts[0] == 'user_context':
                value = context.user_context
                for part in parts[1:]:
                    value = value.get(part) if isinstance(value, dict) else getattr(value, part, None)
                return value
            
            return None
            
        except Exception:
            return None
    
    def _set_context_value(self, context: RuleContext, field_path: str, value: Any):
        """Set value in context using dot notation"""
        try:
            parts = field_path.split('.')
            
            if parts[0] == 'facts':
                if len(parts) == 2:
                    context.facts[parts[1]] = value
                else:
                    # Nested setting would require more complex logic
                    pass
                    
        except Exception as e:
            self.logger.error(f"Failed to set context value {field_path}: {e}")
    
    def _resolve_template(self, template: str, context: RuleContext) -> str:
        """Resolve template string with context values"""
        try:
            import string
            
            template_obj = string.Template(template)
            
            # Build substitution dictionary
            substitutions = {}
            substitutions.update(context.facts)
            substitutions.update({f'system_{k}': v for k, v in context.system_state.items()})
            substitutions.update({f'user_{k}': v for k, v in context.user_context.items()})
            
            return template_obj.safe_substitute(substitutions)
            
        except Exception:
            return template
    
    def _evaluate_action_condition(self, condition: str, context: RuleContext) -> bool:
        """Evaluate action condition"""
        try:
            if not condition or not SAFE_EVAL_AVAILABLE:
                return True
            
            evaluator = simpleeval.SimpleEval()
            evaluator.names = {
                'facts': context.facts,
                'system_state': context.system_state,
                'user_context': context.user_context
            }
            
            return bool(evaluator.eval(condition))
            
        except Exception:
            return False

class AutomationRuleEngine:
    """
    Main automation rule engine
    """
    
    def __init__(self, db_path: str = "user_data/automation_rules.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.event_manager = EventManager()
        self.fact_database = FactDatabase()
        self.rule_executor = RuleExecutor()
        
        # Rule storage
        self.rules: Dict[str, AutomationRule] = {}
        self.active_rules: Set[str] = set()
        
        # Execution tracking
        self.execution_history = deque(maxlen=1000)
        self.running = False
        
        # Threading
        self.engine_thread = None
        self._lock = threading.RLock()
        
        # Performance settings
        self.max_concurrent_rules = 10
        self.rule_evaluation_interval = 1.0  # seconds
        
        # Initialize database
        self._init_database()
        self._load_rules()
        
        # Set up event handlers
        self._setup_event_handlers()
    
    def start(self):
        """Start rule engine"""
        if self.running:
            return
        
        self.running = True
        self.event_manager.start_processing()
        
        # Start main engine loop
        self.engine_thread = threading.Thread(target=self._engine_loop, daemon=True)
        self.engine_thread.start()
        
        self.logger.info("Automation rule engine started")
    
    def stop(self):
        """Stop rule engine"""
        if not self.running:
            return
        
        self.running = False
        self.event_manager.stop_processing()
        
        if self.engine_thread:
            self.engine_thread.join(timeout=5.0)
        
        self.logger.info("Automation rule engine stopped")
    
    def add_rule(self, rule: AutomationRule) -> bool:
        """Add automation rule"""
        try:
            with self._lock:
                # Validate rule
                if not self._validate_rule(rule):
                    return False
                
                # Store rule
                self.rules[rule.id] = rule
                
                if rule.status == RuleStatus.ACTIVE:
                    self.active_rules.add(rule.id)
                
                # Save to database
                self._save_rule(rule)
                
                # Set up event triggers
                self._setup_rule_triggers(rule)
                
                self.logger.info(f"Added rule: {rule.name} (ID: {rule.id})")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to add rule {rule.name}: {e}")
            return False
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove automation rule"""
        try:
            with self._lock:
                if rule_id not in self.rules:
                    return False
                
                # Remove from active rules
                self.active_rules.discard(rule_id)
                
                # Remove from storage
                del self.rules[rule_id]
                
                # Remove from database
                self._delete_rule(rule_id)
                
                self.logger.info(f"Removed rule: {rule_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to remove rule {rule_id}: {e}")
            return False
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable rule"""
        if rule_id in self.rules:
            rule = self.rules[rule_id]
            rule.status = RuleStatus.ACTIVE
            rule.updated_time = datetime.now()
            
            with self._lock:
                self.active_rules.add(rule_id)
            
            self._save_rule(rule)
            return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable rule"""
        if rule_id in self.rules:
            rule = self.rules[rule_id]
            rule.status = RuleStatus.DISABLED
            rule.updated_time = datetime.now()
            
            with self._lock:
                self.active_rules.discard(rule_id)
            
            self._save_rule(rule)
            return True
        return False
    
    def trigger_rule(self, rule_id: str, context: RuleContext = None) -> bool:
        """Manually trigger rule execution"""
        if rule_id not in self.rules:
            return False
        
        rule = self.rules[rule_id]
        context = context or self._build_context()
        
        return self._execute_rule(rule, context)
    
    def set_fact(self, key: str, value: Any):
        """Set fact in fact database"""
        self.fact_database.set_fact(key, value)
    
    def get_fact(self, key: str, default: Any = None) -> Any:
        """Get fact from fact database"""
        return self.fact_database.get_fact(key, default)
    
    def emit_event(self, event_type: EventType, event_data: Dict[str, Any] = None):
        """Emit system event"""
        self.event_manager.emit_event(event_type, event_data)
    
    def register_function(self, name: str, function: Callable):
        """Register function for rule actions"""
        self.rule_executor.register_function(name, function)
    
    def get_rule_status(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get rule status and information"""
        if rule_id not in self.rules:
            return None
        
        rule = self.rules[rule_id]
        
        return {
            'id': rule.id,
            'name': rule.name,
            'type': rule.rule_type.value,
            'status': rule.status.value,
            'priority': rule.priority,
            'execution_count': rule.execution_count,
            'error_count': rule.error_count,
            'last_execution': rule.last_execution.isoformat() if rule.last_execution else None,
            'last_error': rule.last_error,
            'description': rule.description,
            'tags': rule.tags
        }
    
    def list_rules(self, status: RuleStatus = None) -> List[Dict[str, Any]]:
        """List all rules"""
        rules = []
        
        for rule in self.rules.values():
            if status is None or rule.status == status:
                rule_info = self.get_rule_status(rule.id)
                if rule_info:
                    rules.append(rule_info)
        
        return sorted(rules, key=lambda x: x['priority'], reverse=True)
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get rule engine statistics"""
        with self._lock:
            total_rules = len(self.rules)
            active_rules = len(self.active_rules)
            
            total_executions = sum(rule.execution_count for rule in self.rules.values())
            total_errors = sum(rule.error_count for rule in self.rules.values())
        
        return {
            'running': self.running,
            'total_rules': total_rules,
            'active_rules': active_rules,
            'disabled_rules': total_rules - active_rules,
            'total_executions': total_executions,
            'total_errors': total_errors,
            'success_rate': (total_executions - total_errors) / total_executions if total_executions > 0 else 0.0,
            'execution_history_size': len(self.execution_history),
            'fact_count': len(self.fact_database.facts)
        }
    
    def _engine_loop(self):
        """Main engine evaluation loop"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Build current context
                context = self._build_context()
                
                # Evaluate condition-based rules
                self._evaluate_condition_rules(context)
                
                # Clean up expired rules
                self._cleanup_expired_rules(current_time)
                
                time.sleep(self.rule_evaluation_interval)
                
            except Exception as e:
                self.logger.error(f"Engine loop error: {e}")
                time.sleep(5.0)
    
    def _build_context(self) -> RuleContext:
        """Build current rule context"""
        # Get system state (simplified)
        try:
            import psutil
            system_state = {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent,
                'process_count': len(psutil.pids())
            }
        except Exception:
            system_state = {}
        
        # Get recent events
        recent_events = self.event_manager.get_recent_events(limit=50)
        
        return RuleContext(
            facts=self.fact_database.get_all_facts(),
            events=recent_events,
            system_state=system_state,
            user_context={},  # Would be populated from user session data
            timestamp=datetime.now()
        )
    
    def _evaluate_condition_rules(self, context: RuleContext):
        """Evaluate condition-based rules"""
        with self._lock:
            active_rule_ids = list(self.active_rules)
        
        for rule_id in active_rule_ids:
            if rule_id in self.rules:
                rule = self.rules[rule_id]
                
                if (rule.rule_type in [RuleType.CONDITION, RuleType.REACTIVE] and
                    self._should_evaluate_rule(rule, context)):
                    
                    self._execute_rule(rule, context)
    
    def _should_evaluate_rule(self, rule: AutomationRule, context: RuleContext) -> bool:
        """Check if rule should be evaluated"""
        current_time = context.timestamp
        
        # Check cooldown
        if (rule.last_execution and rule.cooldown_seconds > 0 and
            (current_time - rule.last_execution).total_seconds() < rule.cooldown_seconds):
            return False
        
        # Check execution limit
        if rule.max_executions and rule.execution_count >= rule.max_executions:
            return False
        
        # Check expiration
        if rule.expires_at and current_time > rule.expires_at:
            rule.status = RuleStatus.EXPIRED
            self.active_rules.discard(rule.id)
            return False
        
        return True
    
    def _execute_rule(self, rule: AutomationRule, context: RuleContext) -> bool:
        """Execute automation rule"""
        try:
            start_time = time.time()
            
            # Evaluate conditions
            conditions_met, confidence = rule.evaluate_conditions(context)
            
            if not conditions_met:
                return False
            
            # Execute actions
            results = self.rule_executor.execute_actions(rule.actions, context)
            
            # Update rule statistics
            rule.execution_count += 1
            rule.last_execution = context.timestamp
            rule.last_result = results
            rule.updated_time = datetime.now()
            
            execution_time = time.time() - start_time
            
            # Log execution
            self.execution_history.append({
                'rule_id': rule.id,
                'rule_name': rule.name,
                'timestamp': context.timestamp,
                'execution_time': execution_time,
                'conditions_confidence': confidence,
                'success': True,
                'results': results
            })
            
            self.logger.info(f"Executed rule '{rule.name}' in {execution_time:.3f}s")
            
            # Save updated rule
            self._save_rule(rule)
            
            return True
            
        except Exception as e:
            # Update error statistics
            rule.error_count += 1
            rule.last_error = str(e)
            rule.updated_time = datetime.now()
            
            # Log error
            self.execution_history.append({
                'rule_id': rule.id,
                'rule_name': rule.name,
                'timestamp': context.timestamp,
                'success': False,
                'error': str(e)
            })
            
            self.logger.error(f"Rule '{rule.name}' execution failed: {e}")
            
            # Save updated rule
            self._save_rule(rule)
            
            return False
    
    def _setup_event_handlers(self):
        """Set up event handlers for rule triggers"""
        def handle_event(event: RuleEvent):
            # Find rules triggered by this event
            triggered_rules = []
            
            with self._lock:
                for rule_id in self.active_rules:
                    rule = self.rules[rule_id]
                    if (rule.rule_type == RuleType.EVENT and
                        event.event_type in rule.trigger_events):
                        triggered_rules.append(rule)
            
            # Execute triggered rules
            context = self._build_context()
            context.events = [event] + context.events[:49]  # Add current event
            
            for rule in triggered_rules:
                if self._should_evaluate_rule(rule, context):
                    self._execute_rule(rule, context)
        
        # Register for all event types
        for event_type in EventType:
            self.event_manager.register_handler(event_type, handle_event)
    
    def _setup_rule_triggers(self, rule: AutomationRule):
        """Set up triggers for rule"""
        # Event triggers are handled by the general event handler
        pass
    
    def _validate_rule(self, rule: AutomationRule) -> bool:
        """Validate rule before adding"""
        if not rule.id or not rule.name:
            return False
        
        if rule.id in self.rules:
            return False
        
        if not rule.actions:
            return False
        
        return True
    
    def _cleanup_expired_rules(self, current_time: datetime):
        """Clean up expired rules"""
        expired_rules = []
        
        with self._lock:
            for rule_id, rule in self.rules.items():
                if rule.expires_at and current_time > rule.expires_at:
                    rule.status = RuleStatus.EXPIRED
                    expired_rules.append(rule_id)
        
        for rule_id in expired_rules:
            self.active_rules.discard(rule_id)
    
    def _init_database(self):
        """Initialize database for rule storage"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS automation_rules (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        rule_type TEXT NOT NULL,
                        conditions TEXT,
                        condition_logic TEXT,
                        actions TEXT,
                        trigger_events TEXT,
                        priority INTEGER,
                        max_executions INTEGER,
                        cooldown_seconds REAL,
                        timeout_seconds REAL,
                        status TEXT,
                        execution_count INTEGER DEFAULT 0,
                        error_count INTEGER DEFAULT 0,
                        last_execution TEXT,
                        last_error TEXT,
                        created_time TEXT,
                        updated_time TEXT,
                        created_by TEXT,
                        description TEXT,
                        tags TEXT,
                        expires_at TEXT
                    )
                ''')
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
    
    def _save_rule(self, rule: AutomationRule):
        """Save rule to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO automation_rules 
                    (id, name, rule_type, conditions, condition_logic, actions, trigger_events,
                     priority, max_executions, cooldown_seconds, timeout_seconds, status,
                     execution_count, error_count, last_execution, last_error, created_time,
                     updated_time, created_by, description, tags, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    rule.id, rule.name, rule.rule_type.value,
                    json.dumps([asdict(c) for c in rule.conditions]),
                    rule.condition_logic,
                    json.dumps([asdict(a) for a in rule.actions]),
                    json.dumps([e.value for e in rule.trigger_events]),
                    rule.priority, rule.max_executions, rule.cooldown_seconds,
                    rule.timeout_seconds, rule.status.value, rule.execution_count,
                    rule.error_count,
                    rule.last_execution.isoformat() if rule.last_execution else None,
                    rule.last_error, rule.created_time.isoformat(),
                    rule.updated_time.isoformat(), rule.created_by,
                    rule.description, json.dumps(rule.tags),
                    rule.expires_at.isoformat() if rule.expires_at else None
                ))
                
        except Exception as e:
            self.logger.error(f"Failed to save rule {rule.id}: {e}")
    
    def _load_rules(self):
        """Load rules from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT * FROM automation_rules')
                
                for row in cursor.fetchall():
                    # This is simplified - would need proper deserialization
                    self.logger.debug(f"Found saved rule: {row[1]}")
                    
        except Exception as e:
            self.logger.error(f"Failed to load rules: {e}")
    
    def _delete_rule(self, rule_id: str):
        """Delete rule from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM automation_rules WHERE id = ?', (rule_id,))
                
        except Exception as e:
            self.logger.error(f"Failed to delete rule {rule_id}: {e}")


# Factory functions and utilities
def create_condition_rule(name: str, conditions: List[RuleCondition], 
                         actions: List[RuleAction], **kwargs) -> AutomationRule:
    """Create condition-based rule"""
    return AutomationRule(
        id=str(uuid.uuid4()),
        name=name,
        rule_type=RuleType.CONDITION,
        conditions=conditions,
        actions=actions,
        **kwargs
    )

def create_event_rule(name: str, trigger_events: List[EventType],
                     actions: List[RuleAction], **kwargs) -> AutomationRule:
    """Create event-triggered rule"""
    return AutomationRule(
        id=str(uuid.uuid4()),
        name=name,
        rule_type=RuleType.EVENT,
        trigger_events=trigger_events,
        actions=actions,
        **kwargs
    )

def create_simple_condition(field: str, operator: str, value: Any) -> RuleCondition:
    """Create simple rule condition"""
    return RuleCondition(
        field=field,
        operator=ConditionOperator(operator),
        value=value
    )

def create_function_action(function_name: str, **parameters) -> RuleAction:
    """Create function call action"""
    return RuleAction(
        action_type=ActionType.FUNCTION_CALL,
        target=function_name,
        parameters=parameters
    )