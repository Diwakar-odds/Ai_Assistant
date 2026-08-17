# Smart Automation & Workflows Module
"""
Advanced automation and workflow management system for YourDaddy Assistant.

Features:
- Workflow creation and execution
- Task chaining and dependencies
- Conditional logic and branching
- Schedule-based automation
- Pattern-based workflow suggestions
- Visual workflow builder
- Error handling and recovery
- Performance monitoring
"""

import json
import time
import threading
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    print("Warning: schedule library not available. Scheduled automation disabled.")
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import sqlite3
import os
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor
import traceback
import uuid

class WorkflowStatus(Enum):
    """Workflow execution status."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(Enum):
    """Types of tasks in workflows."""
    ACTION = "action"          # Execute a function/command
    CONDITION = "condition"    # If/then logic
    DELAY = "delay"           # Wait for specified time
    LOOP = "loop"             # Repeat operations
    PARALLEL = "parallel"     # Execute tasks simultaneously
    SEQUENCE = "sequence"     # Execute tasks in order
    TRIGGER = "trigger"       # Event-based activation
    WEBHOOK = "webhook"       # External API calls
    FILE_OPERATION = "file_op" # File system operations

class TriggerType(Enum):
    """Types of workflow triggers."""
    MANUAL = "manual"         # User initiated
    SCHEDULED = "scheduled"   # Time-based
    EVENT = "event"          # System event
    PATTERN = "pattern"      # Behavioral pattern
    CONDITION = "condition"  # State-based
    WEBHOOK = "webhook"      # External trigger

@dataclass
class WorkflowTask:
    """Individual task within a workflow."""
    id: str
    name: str
    type: TaskType
    function: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    timeout: int = 30
    enabled: bool = True
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        result = asdict(self)
        result['type'] = self.type.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create from dictionary."""
        data['type'] = TaskType(data['type'])
        return cls(**data)

@dataclass
class WorkflowTrigger:
    """Workflow trigger configuration."""
    type: TriggerType
    schedule: Optional[str] = None  # Cron-like schedule
    event_pattern: Optional[str] = None  # Event matching pattern
    condition: Optional[str] = None  # Condition expression
    webhook_url: Optional[str] = None  # Webhook endpoint
    enabled: bool = True
    
    def to_dict(self):
        result = asdict(self)
        result['type'] = self.type.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        data['type'] = TriggerType(data['type'])
        return cls(**data)

@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""
    id: str
    name: str
    description: str
    tasks: List[WorkflowTask]
    triggers: List[WorkflowTrigger]
    created_at: datetime
    updated_at: datetime
    version: int = 1
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self):
        result = asdict(self)
        result['tasks'] = [task.to_dict() for task in self.tasks]
        result['triggers'] = [trigger.to_dict() for trigger in self.triggers]
        result['created_at'] = self.created_at.isoformat()
        result['updated_at'] = self.updated_at.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        data['tasks'] = [WorkflowTask.from_dict(task) for task in data['tasks']]
        data['triggers'] = [WorkflowTrigger.from_dict(trigger) for trigger in data['triggers']]
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)

@dataclass
class WorkflowExecution:
    """Workflow execution instance."""
    id: str
    workflow_id: str
    status: WorkflowStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    current_task: Optional[str] = None
    task_results: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    
    def add_log(self, message: str):
        """Add log entry with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")

class SmartAutomationEngine:
    """Advanced automation and workflow management system."""
    
    def __init__(self, db_path: str = "data/automation/automation_engine.db"):
        """Initialize the automation engine."""
        self.db_path = db_path
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.running_workflows: Dict[str, threading.Thread] = {}
        self.scheduler = schedule
        self.executor = ThreadPoolExecutor(max_workers=5)
        
        # Function registry for workflow tasks
        self.function_registry = {}
        self.pattern_detector = PatternDetector()
        
        # Initialize database and load workflows
        self._init_database()
        self._load_workflows()
        self._register_built_in_functions()
        
        # Start scheduler thread
        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
    def _init_database(self):
        """Initialize SQLite database for workflow storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    definition TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    tags TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_executions (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    result TEXT,
                    error_message TEXT,
                    logs TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS automation_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    pattern_data TEXT NOT NULL,
                    frequency INTEGER DEFAULT 1,
                    last_detected TEXT NOT NULL,
                    suggested_workflow TEXT
                )
            """)
    
    def _register_built_in_functions(self):
        """Register built-in functions for workflows."""
        from automation_tools_new import (
            open_application, close_application, search_google,
            get_weather_info, get_latest_news, organize_files_by_type,
            get_system_status, cleanup_temp_files, speak,
            get_inbox_summary, send_email, create_calendar_event
        )
        
        # Basic functions
        self.register_function("open_app", open_application)
        self.register_function("close_app", close_application)
        self.register_function("search_google", search_google)
        self.register_function("speak", speak)
        
        # Information functions
        self.register_function("get_weather", get_weather_info)
        self.register_function("get_news", get_latest_news)
        self.register_function("system_status", get_system_status)
        
        # File functions
        self.register_function("organize_files", organize_files_by_type)
        self.register_function("cleanup_temp", cleanup_temp_files)
        
        # Communication functions
        self.register_function("check_email", get_inbox_summary)
        self.register_function("send_email", send_email)
        self.register_function("create_event", create_calendar_event)
        
        # Utility functions
        self.register_function("wait", time.sleep)
        self.register_function("log", print)
    
    def register_function(self, name: str, function: Callable):
        """Register a function for use in workflows."""
        self.function_registry[name] = function
    
    def create_workflow(self, name: str, description: str, tasks: List[Dict], triggers: List[Dict] = None) -> str:
        """Create a new workflow."""
        workflow_id = str(uuid.uuid4())
        
        # Convert task dictionaries to WorkflowTask objects
        workflow_tasks = []
        for i, task_data in enumerate(tasks):
            if 'id' not in task_data:
                task_data['id'] = f"task_{i+1}"
            if 'type' not in task_data:
                task_data['type'] = TaskType.ACTION.value
            
            workflow_tasks.append(WorkflowTask.from_dict(task_data))
        
        # Convert trigger dictionaries to WorkflowTrigger objects
        workflow_triggers = []
        if triggers:
            for trigger_data in triggers:
                workflow_triggers.append(WorkflowTrigger.from_dict(trigger_data))
        
        # Create workflow definition
        workflow = WorkflowDefinition(
            id=workflow_id,
            name=name,
            description=description,
            tasks=workflow_tasks,
            triggers=workflow_triggers,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.workflows[workflow_id] = workflow
        self._save_workflow(workflow)
        
        # Schedule triggers
        self._schedule_workflow_triggers(workflow)
        
        return workflow_id
    
    def execute_workflow(self, workflow_id: str, manual_params: Dict[str, Any] = None) -> str:
        """Execute a workflow."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        if not workflow.enabled:
            raise ValueError(f"Workflow {workflow_id} is disabled")
        
        # Create execution instance
        execution_id = str(uuid.uuid4())
        execution = WorkflowExecution(
            id=execution_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.RUNNING,
            started_at=datetime.now()
        )
        
        self.executions[execution_id] = execution
        execution.add_log(f"Starting workflow: {workflow.name}")
        
        # Start execution in separate thread
        thread = threading.Thread(
            target=self._execute_workflow_thread,
            args=(workflow, execution, manual_params or {}),
            daemon=True
        )
        thread.start()
        self.running_workflows[execution_id] = thread
        
        return execution_id
    
    def _execute_workflow_thread(self, workflow: WorkflowDefinition, execution: WorkflowExecution, params: Dict[str, Any]):
        """Execute workflow in separate thread."""
        try:
            # Build execution graph
            task_graph = self._build_task_graph(workflow.tasks)
            
            # Execute tasks according to dependencies
            completed_tasks = set()
            task_results = {}
            
            while len(completed_tasks) < len(workflow.tasks):
                # Find tasks ready to execute
                ready_tasks = [
                    task for task in workflow.tasks
                    if task.id not in completed_tasks and
                    all(dep in completed_tasks for dep in task.dependencies) and
                    task.enabled
                ]
                
                if not ready_tasks:
                    if len(completed_tasks) == len([t for t in workflow.tasks if t.enabled]):
                        break  # All enabled tasks completed
                    else:
                        execution.error_message = "Circular dependency or missing dependencies detected"
                        execution.status = WorkflowStatus.FAILED
                        execution.add_log("ERROR: Circular dependency detected")
                        return
                
                # Execute ready tasks
                for task in ready_tasks:
                    execution.current_task = task.id
                    execution.add_log(f"Executing task: {task.name}")
                    
                    try:
                        result = self._execute_task(task, task_results, params)
                        task_results[task.id] = result
                        completed_tasks.add(task.id)
                        execution.task_results[task.id] = result
                        execution.add_log(f"Task {task.name} completed successfully")
                        
                    except Exception as e:
                        if task.retry_count < task.max_retries:
                            task.retry_count += 1
                            execution.add_log(f"Task {task.name} failed, retrying ({task.retry_count}/{task.max_retries}): {str(e)}")
                            time.sleep(2 ** task.retry_count)  # Exponential backoff
                        else:
                            execution.error_message = f"Task {task.name} failed: {str(e)}"
                            execution.status = WorkflowStatus.FAILED
                            execution.add_log(f"ERROR: Task {task.name} failed permanently: {str(e)}")
                            return
            
            # Workflow completed successfully
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.now()
            execution.add_log("Workflow completed successfully")
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error_message = str(e)
            execution.completed_at = datetime.now()
            execution.add_log(f"ERROR: Workflow failed: {str(e)}")
            
        finally:
            # Save execution results
            self._save_execution(execution)
            if execution.id in self.running_workflows:
                del self.running_workflows[execution.id]
    
    def _execute_task(self, task: WorkflowTask, previous_results: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """Execute a single task."""
        if task.type == TaskType.ACTION:
            return self._execute_action_task(task, previous_results, params)
        elif task.type == TaskType.CONDITION:
            return self._execute_condition_task(task, previous_results, params)
        elif task.type == TaskType.DELAY:
            return self._execute_delay_task(task, previous_results, params)
        elif task.type == TaskType.LOOP:
            return self._execute_loop_task(task, previous_results, params)
        else:
            raise ValueError(f"Unsupported task type: {task.type}")
    
    def _execute_action_task(self, task: WorkflowTask, previous_results: Dict[str, Any], params: Dict[str, Any]) -> Any:
        """Execute an action task."""
        function_name = task.function
        if function_name not in self.function_registry:
            raise ValueError(f"Function {function_name} not registered")
        
        function = self.function_registry[function_name]
        
        # Resolve parameters
        resolved_params = self._resolve_parameters(task.parameters, previous_results, params)
        
        # Execute function
        if resolved_params:
            return function(**resolved_params)
        else:
            return function()
    
    def _execute_condition_task(self, task: WorkflowTask, previous_results: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """Execute a condition task."""
        condition = task.parameters.get('condition', 'True')
        
        # Create context for condition evaluation
        context = {
            'results': previous_results,
            'params': params,
            'datetime': datetime,
            'time': time
        }
        
        try:
            try:
                import simpleeval
                evaluator = simpleeval.SimpleEval()
                evaluator.names = context
                return bool(evaluator.eval(condition))
            except ImportError:
                import ast
                return bool(ast.literal_eval(condition))
        except Exception as e:
            raise ValueError(f"Condition evaluation failed: {str(e)}")
    
    def _execute_delay_task(self, task: WorkflowTask, previous_results: Dict[str, Any], params: Dict[str, Any]) -> None:
        """Execute a delay task."""
        duration = task.parameters.get('duration', 1)
        time.sleep(float(duration))
    
    def _execute_loop_task(self, task: WorkflowTask, previous_results: Dict[str, Any], params: Dict[str, Any]) -> List[Any]:
        """Execute a loop task."""
        iterations = task.parameters.get('iterations', 1)
        subtasks = task.parameters.get('subtasks', [])
        results = []
        
        for i in range(iterations):
            loop_context = {**params, 'loop_index': i}
            for subtask_data in subtasks:
                subtask = WorkflowTask.from_dict(subtask_data)
                result = self._execute_task(subtask, previous_results, loop_context)
                results.append(result)
        
        return results
    
    def _resolve_parameters(self, parameters: Dict[str, Any], previous_results: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve parameter placeholders."""
        resolved = {}
        
        for key, value in parameters.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                # Parameter placeholder
                placeholder = value[2:-1]
                if '.' in placeholder:
                    # Nested access like ${results.task1.data}
                    parts = placeholder.split('.')
                    resolved_value = previous_results if parts[0] == 'results' else params
                    for part in parts[1:]:
                        if isinstance(resolved_value, dict) and part in resolved_value:
                            resolved_value = resolved_value[part]
                        else:
                            resolved_value = None
                            break
                    resolved[key] = resolved_value
                else:
                    # Simple parameter like ${param_name}
                    resolved[key] = params.get(placeholder) or previous_results.get(placeholder)
            else:
                resolved[key] = value
        
        return resolved
    
    def _build_task_graph(self, tasks: List[WorkflowTask]) -> Dict[str, List[str]]:
        """Build task dependency graph."""
        graph = {}
        for task in tasks:
            graph[task.id] = task.dependencies.copy()
        return graph
    
    def suggest_workflow_from_pattern(self, pattern_description: str) -> Dict[str, Any]:
        """Suggest a workflow based on detected patterns."""
        patterns = {
            "daily_email_check": {
                "name": "Daily Email Check",
                "description": "Check emails every morning and provide summary",
                "tasks": [
                    {
                        "name": "Get Email Summary",
                        "type": "action",
                        "function": "check_email"
                    },
                    {
                        "name": "Speak Summary",
                        "type": "action",
                        "function": "speak",
                        "parameters": {"text": "${results.task_1}"}
                    }
                ],
                "triggers": [
                    {
                        "type": "scheduled",
                        "schedule": "0 9 * * MON-FRI"  # 9 AM weekdays
                    }
                ]
            },
            "file_organization": {
                "name": "Weekly File Organization",
                "description": "Organize files by type every Friday",
                "tasks": [
                    {
                        "name": "Organize Downloads",
                        "type": "action",
                        "function": "organize_files",
                        "parameters": {"directory": "Downloads"}
                    },
                    {
                        "name": "Cleanup Temp Files",
                        "type": "action",
                        "function": "cleanup_temp"
                    },
                    {
                        "name": "Notify Completion",
                        "type": "action",
                        "function": "speak",
                        "parameters": {"text": "File organization completed"}
                    }
                ],
                "triggers": [
                    {
                        "type": "scheduled",
                        "schedule": "0 17 * * FRI"  # 5 PM Friday
                    }
                ]
            },
            "morning_briefing": {
                "name": "Morning Briefing",
                "description": "Comprehensive morning update",
                "tasks": [
                    {
                        "name": "Get Weather",
                        "type": "action", 
                        "function": "get_weather"
                    },
                    {
                        "name": "Get News",
                        "type": "action",
                        "function": "get_news"
                    },
                    {
                        "name": "Check System",
                        "type": "action",
                        "function": "system_status"
                    },
                    {
                        "name": "Morning Greeting",
                        "type": "action",
                        "function": "speak",
                        "parameters": {"text": "Good morning! Here's your daily briefing."}
                    }
                ],
                "triggers": [
                    {
                        "type": "scheduled",
                        "schedule": "0 8 * * *"  # 8 AM daily
                    }
                ]
            }
        }
        
        # Find matching pattern
        for pattern_key, pattern_config in patterns.items():
            if pattern_key.replace('_', ' ') in pattern_description.lower():
                return pattern_config
        
        # Generic pattern
        return {
            "name": "Custom Workflow",
            "description": f"Workflow based on: {pattern_description}",
            "tasks": [
                {
                    "name": "Custom Task",
                    "type": "action",
                    "function": "log",
                    "parameters": {"text": "Custom workflow executed"}
                }
            ],
            "triggers": []
        }
    
    def create_workflow_from_pattern(self, pattern_description: str) -> str:
        """Create a workflow from a detected pattern."""
        workflow_config = self.suggest_workflow_from_pattern(pattern_description)
        
        return self.create_workflow(
            name=workflow_config["name"],
            description=workflow_config["description"],
            tasks=workflow_config["tasks"],
            triggers=workflow_config["triggers"]
        )
    
    def pause_workflow(self, execution_id: str) -> bool:
        """Pause a running workflow."""
        if execution_id in self.executions:
            self.executions[execution_id].status = WorkflowStatus.PAUSED
            return True
        return False
    
    def cancel_workflow(self, execution_id: str) -> bool:
        """Cancel a running workflow."""
        if execution_id in self.executions:
            self.executions[execution_id].status = WorkflowStatus.CANCELLED
            self.executions[execution_id].completed_at = datetime.now()
            self.executions[execution_id].add_log("Workflow cancelled by user")
            return True
        return False
    
    def get_workflow_status(self, execution_id: str) -> Dict[str, Any]:
        """Get status of workflow execution."""
        if execution_id not in self.executions:
            return {"error": "Execution not found"}
        
        execution = self.executions[execution_id]
        return {
            "id": execution.id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "started_at": execution.started_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "current_task": execution.current_task,
            "progress": len(execution.task_results),
            "error_message": execution.error_message,
            "logs": execution.logs[-10:]  # Last 10 log entries
        }
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows."""
        workflows = []
        for workflow in self.workflows.values():
            workflows.append({
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description,
                "task_count": len(workflow.tasks),
                "trigger_count": len(workflow.triggers),
                "enabled": workflow.enabled,
                "created_at": workflow.created_at.isoformat(),
                "tags": workflow.tags
            })
        return workflows
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow."""
        if workflow_id not in self.workflows:
            return False
        
        # Remove from memory
        del self.workflows[workflow_id]
        
        # Remove from database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
            conn.execute("DELETE FROM workflow_executions WHERE workflow_id = ?", (workflow_id,))
        
        return True
    
    def _schedule_workflow_triggers(self, workflow: WorkflowDefinition):
        """Schedule workflow triggers."""
        for trigger in workflow.triggers:
            if trigger.type == TriggerType.SCHEDULED and trigger.schedule:
                # Parse cron-like schedule and add to scheduler
                try:
                    self._add_scheduled_workflow(workflow.id, trigger.schedule)
                except Exception as e:
                    print(f"Error scheduling workflow {workflow.name}: {e}")
    
    def _add_scheduled_workflow(self, workflow_id: str, schedule_pattern: str):
        """Add scheduled workflow to scheduler."""
        # Simple schedule parsing (extend for full cron support)
        parts = schedule_pattern.split()
        if len(parts) >= 5:
            minute, hour, day, month, weekday = parts[:5]
            
            if hour != '*' and minute != '*':
                time_str = f"{hour.zfill(2)}:{minute.zfill(2)}"
                
                if weekday == '*':
                    # Daily
                    schedule.every().day.at(time_str).do(self.execute_workflow, workflow_id)
                elif weekday == 'MON-FRI':
                    # Weekdays
                    for day_name in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
                        getattr(schedule.every(), day_name).at(time_str).do(self.execute_workflow, workflow_id)
                elif weekday in ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']:
                    # Specific day
                    day_map = {
                        'MON': 'monday', 'TUE': 'tuesday', 'WED': 'wednesday',
                        'THU': 'thursday', 'FRI': 'friday', 'SAT': 'saturday', 'SUN': 'sunday'
                    }
                    getattr(schedule.every(), day_map[weekday]).at(time_str).do(self.execute_workflow, workflow_id)
    
    def _run_scheduler(self):
        """Run the scheduler in background thread."""
        while self.scheduler_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def _save_workflow(self, workflow: WorkflowDefinition):
        """Save workflow to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO workflows 
                (id, name, description, definition, created_at, updated_at, enabled, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow.id,
                workflow.name,
                workflow.description,
                json.dumps(workflow.to_dict()),
                workflow.created_at.isoformat(),
                workflow.updated_at.isoformat(),
                1 if workflow.enabled else 0,
                json.dumps(workflow.tags)
            ))
    
    def _save_execution(self, execution: WorkflowExecution):
        """Save execution results to database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO workflow_executions
                (id, workflow_id, status, started_at, completed_at, result, error_message, logs)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                execution.id,
                execution.workflow_id,
                execution.status.value,
                execution.started_at.isoformat(),
                execution.completed_at.isoformat() if execution.completed_at else None,
                json.dumps(execution.task_results),
                execution.error_message,
                json.dumps(execution.logs)
            ))
    
    def _load_workflows(self):
        """Load workflows from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT definition FROM workflows WHERE enabled = 1")
                for (definition_json,) in cursor:
                    workflow_data = json.loads(definition_json)
                    workflow = WorkflowDefinition.from_dict(workflow_data)
                    self.workflows[workflow.id] = workflow
                    self._schedule_workflow_triggers(workflow)
        except Exception as e:
            print(f"Error loading workflows: {e}")
    
    def cleanup(self):
        """Cleanup resources."""
        self.scheduler_running = False
        if hasattr(self, 'scheduler_thread'):
            self.scheduler_thread.join(timeout=1)
        self.executor.shutdown(wait=False)

class PatternDetector:
    """Detects automation patterns from user behavior."""
    
    def __init__(self):
        self.action_history = []
        self.pattern_threshold = 3  # Minimum occurrences to suggest automation
    
    def record_action(self, action: str, context: Dict[str, Any] = None):
        """Record user action for pattern detection."""
        self.action_history.append({
            "action": action,
            "timestamp": datetime.now(),
            "context": context or {}
        })
        
        # Keep history manageable
        if len(self.action_history) > 1000:
            self.action_history = self.action_history[-500:]
    
    def detect_patterns(self) -> List[Dict[str, Any]]:
        """Detect automation patterns from action history."""
        patterns = []
        
        # Time-based patterns
        time_patterns = self._detect_time_patterns()
        patterns.extend(time_patterns)
        
        # Sequence patterns
        sequence_patterns = self._detect_sequence_patterns()
        patterns.extend(sequence_patterns)
        
        return patterns
    
    def _detect_time_patterns(self) -> List[Dict[str, Any]]:
        """Detect time-based patterns."""
        patterns = []
        
        # Group actions by hour and day of week
        time_groups = {}
        for action in self.action_history:
            timestamp = action["timestamp"]
            time_key = (timestamp.hour, timestamp.weekday())
            if time_key not in time_groups:
                time_groups[time_key] = []
            time_groups[time_key].append(action)
        
        # Find recurring patterns
        for (hour, weekday), actions in time_groups.items():
            if len(actions) >= self.pattern_threshold:
                action_types = [a["action"] for a in actions]
                most_common = max(set(action_types), key=action_types.count)
                
                if action_types.count(most_common) >= self.pattern_threshold:
                    patterns.append({
                        "type": "time_based",
                        "action": most_common,
                        "hour": hour,
                        "weekday": weekday,
                        "frequency": action_types.count(most_common),
                        "confidence": action_types.count(most_common) / len(actions)
                    })
        
        return patterns
    
    def _detect_sequence_patterns(self) -> List[Dict[str, Any]]:
        """Detect action sequence patterns."""
        patterns = []
        
        # Look for sequences of 2-5 actions
        for seq_length in range(2, 6):
            sequences = {}
            
            for i in range(len(self.action_history) - seq_length + 1):
                sequence = tuple(
                    action["action"] for action in 
                    self.action_history[i:i + seq_length]
                )
                
                if sequence not in sequences:
                    sequences[sequence] = 0
                sequences[sequence] += 1
            
            # Find frequent sequences
            for sequence, count in sequences.items():
                if count >= self.pattern_threshold:
                    patterns.append({
                        "type": "sequence",
                        "actions": list(sequence),
                        "frequency": count,
                        "confidence": count / (len(self.action_history) - seq_length + 1)
                    })
        
        return patterns

# Convenience functions for easy integration
def create_simple_workflow(name: str, actions: List[str], schedule: str = None) -> str:
    """Create a simple workflow from action names."""
    engine = SmartAutomationEngine()
    
    tasks = []
    for i, action in enumerate(actions):
        tasks.append({
            "name": f"Step {i+1}",
            "type": "action",
            "function": action,
            "id": f"task_{i+1}"
        })
    
    triggers = []
    if schedule:
        triggers.append({
            "type": "scheduled",
            "schedule": schedule
        })
    
    return engine.create_workflow(name, f"Simple workflow: {', '.join(actions)}", tasks, triggers)

def execute_workflow_by_name(name: str) -> str:
    """Execute a workflow by name."""
    engine = SmartAutomationEngine()
    
    for workflow in engine.workflows.values():
        if workflow.name.lower() == name.lower():
            return engine.execute_workflow(workflow.id)
    
    raise ValueError(f"Workflow '{name}' not found")

def suggest_automation_from_pattern(pattern_description: str) -> Dict[str, Any]:
    """Get automation suggestions based on pattern description."""
    engine = SmartAutomationEngine()
    return engine.suggest_workflow_from_pattern(pattern_description)

def get_workflow_status_simple(execution_id: str) -> str:
    """Get simple workflow status description."""
    engine = SmartAutomationEngine()
    status = engine.get_workflow_status(execution_id)
    
    if "error" in status:
        return status["error"]
    
    return f"Status: {status['status']}, Progress: {status['progress']} tasks completed"

# Export functions
__all__ = [
    'SmartAutomationEngine',
    'WorkflowDefinition',
    'WorkflowTask', 
    'WorkflowTrigger',
    'WorkflowStatus',
    'TaskType',
    'TriggerType',
    'PatternDetector',
    'create_simple_workflow',
    'execute_workflow_by_name',
    'suggest_automation_from_pattern',
    'get_workflow_status_simple'
]

# =============================================================================
# Section 2: Advanced Integration (from advanced_integration.py)
# =============================================================================
"""
Advanced System Integration for YourDaddy Assistant

This module provides deep system integration capabilities including:
- System-wide hooks and event monitoring
- Advanced OS integration (Windows, macOS, Linux)
- Cross-platform compatibility layer
- Hardware access and control
- System service management
- Performance optimization
- Security and permissions management
"""

import os
import sys
import platform
import subprocess
import threading
import time
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import psutil
if platform.system() == "Windows":
    import winreg
else:
    winreg = None
import signal
import socket
from pathlib import Path

class SystemType(Enum):
    """Supported system types"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"

class HookType(Enum):
    """Types of system hooks"""
    FILE_SYSTEM = "filesystem"
    PROCESS = "process"
    NETWORK = "network"
    USB_DEVICE = "usb_device"
    POWER = "power"
    WINDOW = "window"
    KEYBOARD = "keyboard"
    MOUSE = "mouse"

@dataclass
class SystemEvent:
    """Represents a system event"""
    event_id: str
    hook_type: HookType
    timestamp: datetime
    data: Dict[str, Any]
    source: str
    processed: bool = False

@dataclass
class IntegrationCapability:
    """Represents a system integration capability"""
    name: str
    supported_platforms: List[SystemType]
    requires_admin: bool
    description: str
    implementation: Optional[Callable] = None

class PlatformAdapter:
    """Cross-platform compatibility adapter"""
    
    def __init__(self):
        self.system_type = self._detect_system()
        self.capabilities = self._initialize_capabilities()
    
    def _detect_system(self) -> SystemType:
        """Detect the current operating system"""
        system = platform.system().lower()
        if system == "windows":
            return SystemType.WINDOWS
        elif system == "darwin":
            return SystemType.MACOS
        elif system == "linux":
            return SystemType.LINUX
        else:
            return SystemType.UNKNOWN
    
    def _initialize_capabilities(self) -> Dict[str, IntegrationCapability]:
        """Initialize platform-specific capabilities"""
        capabilities = {}
        
        # File system monitoring
        capabilities["fs_monitor"] = IntegrationCapability(
            name="File System Monitor",
            supported_platforms=[SystemType.WINDOWS, SystemType.MACOS, SystemType.LINUX],
            requires_admin=False,
            description="Monitor file system changes in real-time",
            implementation=self._setup_fs_monitor
        )
        
        # Process monitoring
        capabilities["process_monitor"] = IntegrationCapability(
            name="Process Monitor",
            supported_platforms=[SystemType.WINDOWS, SystemType.MACOS, SystemType.LINUX],
            requires_admin=True,
            description="Monitor process creation and termination",
            implementation=self._setup_process_monitor
        )
        
        # Registry access (Windows only)
        if self.system_type == SystemType.WINDOWS:
            capabilities["registry_access"] = IntegrationCapability(
                name="Registry Access",
                supported_platforms=[SystemType.WINDOWS],
                requires_admin=True,
                description="Read/write Windows registry",
                implementation=self._setup_registry_access
            )
        
        # System services
        capabilities["service_control"] = IntegrationCapability(
            name="Service Control",
            supported_platforms=[SystemType.WINDOWS, SystemType.LINUX],
            requires_admin=True,
            description="Control system services",
            implementation=self._setup_service_control
        )
        
        # Hardware monitoring
        capabilities["hardware_monitor"] = IntegrationCapability(
            name="Hardware Monitor",
            supported_platforms=[SystemType.WINDOWS, SystemType.MACOS, SystemType.LINUX],
            requires_admin=False,
            description="Monitor CPU, memory, disk, network usage",
            implementation=self._setup_hardware_monitor
        )
        
        # Window management
        capabilities["window_manager"] = IntegrationCapability(
            name="Window Manager",
            supported_platforms=[SystemType.WINDOWS, SystemType.LINUX],
            requires_admin=False,
            description="Advanced window control and monitoring",
            implementation=self._setup_window_manager
        )
        
        return capabilities
    
    def is_capability_supported(self, capability_name: str) -> bool:
        """Check if a capability is supported on current platform"""
        if capability_name not in self.capabilities:
            return False
        
        capability = self.capabilities[capability_name]
        return self.system_type in capability.supported_platforms
    
    def requires_admin(self, capability_name: str) -> bool:
        """Check if a capability requires admin privileges"""
        if capability_name not in self.capabilities:
            return False
        
        return self.capabilities[capability_name].requires_admin
    
    def get_supported_capabilities(self) -> List[str]:
        """Get list of supported capabilities for current platform"""
        supported = []
        for name, capability in self.capabilities.items():
            if self.system_type in capability.supported_platforms:
                supported.append(name)
        return supported
    
    def _setup_fs_monitor(self):
        """Setup file system monitoring"""
        try:
            if self.system_type == SystemType.WINDOWS:
                import win32file
                import win32con
                return self._windows_fs_monitor
            elif self.system_type == SystemType.LINUX:
                import inotify
                return self._linux_fs_monitor
            elif self.system_type == SystemType.MACOS:
                return self._macos_fs_monitor
        except ImportError:
            return None
    
    def _setup_process_monitor(self):
        """Setup process monitoring"""
        if self.system_type == SystemType.WINDOWS:
            return self._windows_process_monitor
        elif self.system_type in [SystemType.LINUX, SystemType.MACOS]:
            return self._unix_process_monitor
    
    def _setup_registry_access(self):
        """Setup Windows registry access"""
        if self.system_type == SystemType.WINDOWS:
            return WindowsRegistryManager()
        return None
    
    def _setup_service_control(self):
        """Setup system service control"""
        if self.system_type == SystemType.WINDOWS:
            return WindowsServiceManager()
        elif self.system_type == SystemType.LINUX:
            return LinuxServiceManager()
        return None
    
    def _setup_hardware_monitor(self):
        """Setup hardware monitoring"""
        return HardwareMonitor()
    
    def _setup_window_manager(self):
        """Setup window management"""
        if self.system_type == SystemType.WINDOWS:
            return WindowsWindowManager()
        elif self.system_type == SystemType.LINUX:
            return LinuxWindowManager()
        return None

class SystemHookManager:
    """Manages system-wide hooks and events"""
    
    def __init__(self, db_path: str = "system_hooks.db"):
        self.db_path = db_path
        self.adapter = PlatformAdapter()
        self.hooks = {}
        self.event_handlers = {}
        self.monitoring_threads = {}
        self.is_monitoring = False
        
        self.init_database()
    
    def init_database(self):
        """Initialize hooks database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_events (
                event_id TEXT PRIMARY KEY,
                hook_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                source TEXT NOT NULL,
                processed INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS hook_configs (
                hook_name TEXT PRIMARY KEY,
                hook_type TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                config TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def register_hook(self, hook_name: str, hook_type: HookType, config: Dict[str, Any] = None):
        """Register a new system hook"""
        if not self.adapter.is_capability_supported(hook_type.value):
            raise ValueError(f"Hook type {hook_type.value} not supported on {self.adapter.system_type.value}")
        
        self.hooks[hook_name] = {
            "type": hook_type,
            "config": config or {},
            "active": False
        }
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO hook_configs (hook_name, hook_type, config)
            VALUES (?, ?, ?)
        ''', (hook_name, hook_type.value, json.dumps(config or {})))
        conn.commit()
        conn.close()
    
    def start_hook(self, hook_name: str):
        """Start monitoring for a specific hook"""
        if hook_name not in self.hooks:
            raise ValueError(f"Hook {hook_name} not registered")
        
        hook = self.hooks[hook_name]
        hook_type = hook["type"]
        
        if hook_type == HookType.FILE_SYSTEM:
            self._start_filesystem_hook(hook_name, hook["config"])
        elif hook_type == HookType.PROCESS:
            self._start_process_hook(hook_name, hook["config"])
        elif hook_type == HookType.NETWORK:
            self._start_network_hook(hook_name, hook["config"])
        elif hook_type == HookType.POWER:
            self._start_power_hook(hook_name, hook["config"])
        
        hook["active"] = True
    
    def stop_hook(self, hook_name: str):
        """Stop monitoring for a specific hook"""
        if hook_name in self.monitoring_threads:
            # Signal thread to stop
            self.monitoring_threads[hook_name]["stop"] = True
            self.hooks[hook_name]["active"] = False
    
    def register_event_handler(self, hook_type: HookType, handler: Callable[[SystemEvent], None]):
        """Register an event handler for a hook type"""
        if hook_type not in self.event_handlers:
            self.event_handlers[hook_type] = []
        self.event_handlers[hook_type].append(handler)
    
    def _emit_event(self, hook_type: HookType, data: Dict[str, Any], source: str):
        """Emit a system event"""
        event = SystemEvent(
            event_id=f"{hook_type.value}_{int(time.time() * 1000)}",
            hook_type=hook_type,
            timestamp=datetime.now(),
            data=data,
            source=source
        )
        
        # Store in database
        self._store_event(event)
        
        # Call registered handlers
        if hook_type in self.event_handlers:
            for handler in self.event_handlers[hook_type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error in event handler: {e}")
    
    def _store_event(self, event: SystemEvent):
        """Store event in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_events (event_id, hook_type, data, source)
            VALUES (?, ?, ?, ?)
        ''', (event.event_id, event.hook_type.value, json.dumps(event.data), event.source))
        conn.commit()
        conn.close()
    
    def _start_filesystem_hook(self, hook_name: str, config: Dict[str, Any]):
        """Start filesystem monitoring hook"""
        watch_paths = config.get("paths", [os.getcwd()])
        
        def monitor_filesystem():
            thread_data = {"stop": False}
            self.monitoring_threads[hook_name] = thread_data
            
            # Simple polling-based implementation for cross-platform compatibility
            last_check = {}
            
            while not thread_data["stop"]:
                for path in watch_paths:
                    try:
                        for root, dirs, files in os.walk(path):
                            for file in files:
                                filepath = os.path.join(root, file)
                                try:
                                    stat = os.stat(filepath)
                                    mtime = stat.st_mtime
                                    
                                    if filepath not in last_check or last_check[filepath] != mtime:
                                        if filepath in last_check:
                                            # File was modified
                                            self._emit_event(HookType.FILE_SYSTEM, {
                                                "action": "modified",
                                                "path": filepath,
                                                "size": stat.st_size,
                                                "mtime": mtime
                                            }, hook_name)
                                        last_check[filepath] = mtime
                                except (OSError, IOError):
                                    continue
                    except (OSError, IOError):
                        continue
                
                time.sleep(config.get("interval", 1))
        
        thread = threading.Thread(target=monitor_filesystem, daemon=True)
        thread.start()
    
    def _start_process_hook(self, hook_name: str, config: Dict[str, Any]):
        """Start process monitoring hook"""
        def monitor_processes():
            thread_data = {"stop": False}
            self.monitoring_threads[hook_name] = thread_data
            
            last_processes = set(p.pid for p in psutil.process_iter())
            
            while not thread_data["stop"]:
                try:
                    current_processes = set(p.pid for p in psutil.process_iter())
                    
                    # New processes
                    new_processes = current_processes - last_processes
                    for pid in new_processes:
                        try:
                            process = psutil.Process(pid)
                            self._emit_event(HookType.PROCESS, {
                                "action": "created",
                                "pid": pid,
                                "name": process.name(),
                                "cmdline": process.cmdline(),
                                "username": process.username()
                            }, hook_name)
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    
                    # Terminated processes
                    terminated_processes = last_processes - current_processes
                    for pid in terminated_processes:
                        self._emit_event(HookType.PROCESS, {
                            "action": "terminated",
                            "pid": pid
                        }, hook_name)
                    
                    last_processes = current_processes
                    
                except Exception as e:
                    print(f"Process monitoring error: {e}")
                
                time.sleep(config.get("interval", 2))
        
        thread = threading.Thread(target=monitor_processes, daemon=True)
        thread.start()
    
    def _start_network_hook(self, hook_name: str, config: Dict[str, Any]):
        """Start network monitoring hook"""
        def monitor_network():
            thread_data = {"stop": False}
            self.monitoring_threads[hook_name] = thread_data
            
            last_connections = set()
            
            while not thread_data["stop"]:
                try:
                    current_connections = set()
                    for conn in psutil.net_connections():
                        if conn.status == psutil.CONN_ESTABLISHED:
                            current_connections.add((conn.laddr, conn.raddr, conn.pid))
                    
                    # New connections
                    new_connections = current_connections - last_connections
                    for laddr, raddr, pid in new_connections:
                        try:
                            process_name = psutil.Process(pid).name() if pid else "unknown"
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            process_name = "unknown"
                        
                        self._emit_event(HookType.NETWORK, {
                            "action": "connection_established",
                            "local_addr": laddr,
                            "remote_addr": raddr,
                            "pid": pid,
                            "process": process_name
                        }, hook_name)
                    
                    last_connections = current_connections
                    
                except Exception as e:
                    print(f"Network monitoring error: {e}")
                
                time.sleep(config.get("interval", 5))
        
        thread = threading.Thread(target=monitor_network, daemon=True)
        thread.start()
    
    def _start_power_hook(self, hook_name: str, config: Dict[str, Any]):
        """Start power monitoring hook"""
        def monitor_power():
            thread_data = {"stop": False}
            self.monitoring_threads[hook_name] = thread_data
            
            last_battery = None
            last_power_plugged = None
            
            while not thread_data["stop"]:
                try:
                    battery = psutil.sensors_battery()
                    if battery:
                        current_battery = battery.percent
                        current_power_plugged = battery.power_plugged
                        
                        if last_battery is not None:
                            if abs(current_battery - last_battery) > 5:  # 5% change
                                self._emit_event(HookType.POWER, {
                                    "action": "battery_change",
                                    "percent": current_battery,
                                    "power_plugged": current_power_plugged,
                                    "time_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
                                }, hook_name)
                        
                        if last_power_plugged is not None and current_power_plugged != last_power_plugged:
                            self._emit_event(HookType.POWER, {
                                "action": "power_status_change",
                                "power_plugged": current_power_plugged,
                                "percent": current_battery
                            }, hook_name)
                        
                        last_battery = current_battery
                        last_power_plugged = current_power_plugged
                
                except Exception as e:
                    print(f"Power monitoring error: {e}")
                
                time.sleep(config.get("interval", 10))
        
        thread = threading.Thread(target=monitor_power, daemon=True)
        thread.start()
    
    def get_recent_events(self, hook_type: HookType = None, limit: int = 100) -> List[SystemEvent]:
        """Get recent system events"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if hook_type:
            cursor.execute('''
                SELECT event_id, hook_type, timestamp, data, source, processed
                FROM system_events
                WHERE hook_type = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (hook_type.value, limit))
        else:
            cursor.execute('''
                SELECT event_id, hook_type, timestamp, data, source, processed
                FROM system_events
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
        
        events = []
        for row in cursor.fetchall():
            events.append(SystemEvent(
                event_id=row[0],
                hook_type=HookType(row[1]),
                timestamp=datetime.fromisoformat(row[2]),
                data=json.loads(row[3]),
                source=row[4],
                processed=bool(row[5])
            ))
        
        conn.close()
        return events

class HardwareMonitor:
    """Advanced hardware monitoring and control"""
    
    def __init__(self):
        self.monitoring = False
        self.callbacks = {}
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        info = {
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor()
            },
            "cpu": {
                "physical_cores": psutil.cpu_count(logical=False),
                "logical_cores": psutil.cpu_count(logical=True),
                "usage_percent": psutil.cpu_percent(interval=1),
                "frequency": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            },
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "used": psutil.virtual_memory().used,
                "percentage": psutil.virtual_memory().percent
            },
            "disk": [],
            "network": {
                "interfaces": {},
                "stats": psutil.net_io_counters()._asdict()
            }
        }
        
        # Disk information
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                info["disk"].append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percentage": (usage.used / usage.total) * 100
                })
            except PermissionError:
                continue
        
        # Network interfaces
        for interface, addrs in psutil.net_if_addrs().items():
            info["network"]["interfaces"][interface] = [addr._asdict() for addr in addrs]
        
        return info
    
    def get_running_processes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get information about running processes"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        return processes[:limit]
    
    def monitor_performance(self, callback: Callable[[Dict[str, Any]], None], interval: int = 5):
        """Start performance monitoring"""
        def monitor():
            while self.monitoring:
                stats = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory": psutil.virtual_memory()._asdict(),
                    "disk_io": psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else None,
                    "network_io": psutil.net_io_counters()._asdict()
                }
                
                callback(stats)
                time.sleep(interval)
        
        self.monitoring = True
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.monitoring = False

class WindowsRegistryManager:
    """Windows Registry management"""
    
    def __init__(self):
        if platform.system() != "Windows":
            raise RuntimeError("Registry manager only available on Windows")
    
    def read_value(self, hkey: str, subkey: str, value_name: str):
        """Read a value from Windows registry"""
        try:
            hkey_map = {
                "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
                "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
                "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
                "HKEY_USERS": winreg.HKEY_USERS,
                "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG
            }
            
            with winreg.OpenKey(hkey_map[hkey], subkey) as key:
                value, regtype = winreg.QueryValueEx(key, value_name)
                return value
        except Exception as e:
            raise ValueError(f"Failed to read registry value: {e}")
    
    def write_value(self, hkey: str, subkey: str, value_name: str, value: Any, value_type: str = "REG_SZ"):
        """Write a value to Windows registry"""
        try:
            hkey_map = {
                "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
                "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
                "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
                "HKEY_USERS": winreg.HKEY_USERS,
                "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG
            }
            
            type_map = {
                "REG_SZ": winreg.REG_SZ,
                "REG_DWORD": winreg.REG_DWORD,
                "REG_BINARY": winreg.REG_BINARY,
                "REG_MULTI_SZ": winreg.REG_MULTI_SZ
            }
            
            with winreg.OpenKey(hkey_map[hkey], subkey, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, value_name, 0, type_map[value_type], value)
        except Exception as e:
            raise ValueError(f"Failed to write registry value: {e}")

class AdvancedIntegrationManager:
    """Main manager for advanced system integration"""
    
    def __init__(self, db_path: str = "advanced_integration.db"):
        self.db_path = db_path
        self.platform_adapter = PlatformAdapter()
        self.hook_manager = SystemHookManager(f"{db_path}_hooks.db")
        self.hardware_monitor = HardwareMonitor()
        self.capabilities = {}
        
        self.init_database()
        self.initialize_capabilities()
    
    def init_database(self):
        """Initialize integration database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS integration_status (
                capability TEXT PRIMARY KEY,
                enabled INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                config TEXT,
                error_count INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cpu_percent REAL,
                memory_percent REAL,
                disk_usage TEXT,
                network_stats TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def initialize_capabilities(self):
        """Initialize available system integration capabilities"""
        supported = self.platform_adapter.get_supported_capabilities()
        
        for capability in supported:
            self.capabilities[capability] = {
                "enabled": False,
                "instance": None,
                "last_error": None
            }
    
    def enable_capability(self, capability_name: str, config: Dict[str, Any] = None) -> bool:
        """Enable a system integration capability"""
        if capability_name not in self.capabilities:
            return False
        
        if not self.platform_adapter.is_capability_supported(capability_name):
            return False
        
        try:
            # Check admin requirements
            if self.platform_adapter.requires_admin(capability_name) and not self._is_admin():
                raise PermissionError(f"Administrator privileges required for {capability_name}")
            
            # Initialize capability
            capability_def = self.platform_adapter.capabilities[capability_name]
            if capability_def.implementation:
                instance = capability_def.implementation()
                self.capabilities[capability_name]["instance"] = instance
                self.capabilities[capability_name]["enabled"] = True
                
                # Update database
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO integration_status 
                    (capability, enabled, last_used, config)
                    VALUES (?, 1, CURRENT_TIMESTAMP, ?)
                ''', (capability_name, json.dumps(config or {})))
                conn.commit()
                conn.close()
                
                return True
            
        except Exception as e:
            self.capabilities[capability_name]["last_error"] = str(e)
            return False
        
        return False
    
    def disable_capability(self, capability_name: str):
        """Disable a system integration capability"""
        if capability_name in self.capabilities:
            self.capabilities[capability_name]["enabled"] = False
            self.capabilities[capability_name]["instance"] = None
            
            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE integration_status SET enabled = 0 WHERE capability = ?
            ''', (capability_name,))
            conn.commit()
            conn.close()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "platform": self.platform_adapter.system_type.value,
            "capabilities": {},
            "hardware": self.hardware_monitor.get_system_info(),
            "processes": self.hardware_monitor.get_running_processes(20),
            "hooks": {
                "active": len([h for h in self.hook_manager.hooks.values() if h["active"]]),
                "total": len(self.hook_manager.hooks)
            },
            "recent_events": len(self.hook_manager.get_recent_events(limit=10))
        }
        
        for name, capability in self.capabilities.items():
            status["capabilities"][name] = {
                "enabled": capability["enabled"],
                "supported": self.platform_adapter.is_capability_supported(name),
                "requires_admin": self.platform_adapter.requires_admin(name),
                "last_error": capability["last_error"]
            }
        
        return status
    
    def setup_system_hooks(self):
        """Setup basic system monitoring hooks"""
        # File system monitoring
        self.hook_manager.register_hook("fs_monitor", HookType.FILE_SYSTEM, {
            "paths": [os.path.expanduser("~"), "C:\\Windows\\System32" if platform.system() == "Windows" else "/var/log"],
            "interval": 2
        })
        
        # Process monitoring
        self.hook_manager.register_hook("process_monitor", HookType.PROCESS, {
            "interval": 3
        })
        
        # Network monitoring
        self.hook_manager.register_hook("network_monitor", HookType.NETWORK, {
            "interval": 5
        })
        
        # Power monitoring (if battery present)
        if psutil.sensors_battery():
            self.hook_manager.register_hook("power_monitor", HookType.POWER, {
                "interval": 30
            })
    
    def start_monitoring(self):
        """Start system monitoring"""
        for hook_name in self.hook_manager.hooks:
            try:
                self.hook_manager.start_hook(hook_name)
            except Exception as e:
                print(f"Failed to start hook {hook_name}: {e}")
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        for hook_name in self.hook_manager.hooks:
            self.hook_manager.stop_hook(hook_name)
        
        self.hardware_monitor.stop_monitoring()
    
    def _is_admin(self) -> bool:
        """Check if running with administrator privileges"""
        try:
            if platform.system() == "Windows":
                import ctypes
                return ctypes.windll.shell32.IsUserAnAdmin()
            else:
                return os.geteuid() == 0
        except Exception:
            return False
    
    def get_integration_insights(self) -> Dict[str, Any]:
        """Generate insights from system integration"""
        insights = {
            "system_health": "good",
            "performance_trends": {},
            "security_recommendations": [],
            "optimization_suggestions": []
        }
        
        # Analyze recent events
        recent_events = self.hook_manager.get_recent_events(limit=100)
        
        # Count event types
        event_counts = {}
        for event in recent_events:
            event_type = event.hook_type.value
            if event_type not in event_counts:
                event_counts[event_type] = 0
            event_counts[event_type] += 1
        
        insights["event_summary"] = event_counts
        
        # System performance analysis
        hardware_info = self.hardware_monitor.get_system_info()
        cpu_usage = hardware_info["cpu"]["usage_percent"]
        memory_usage = hardware_info["memory"]["percentage"]
        
        if cpu_usage > 80:
            insights["optimization_suggestions"].append("High CPU usage detected - consider closing unnecessary applications")
        
        if memory_usage > 85:
            insights["optimization_suggestions"].append("High memory usage detected - system may benefit from additional RAM")
        
        # Security recommendations
        if len([p for p in self.hardware_monitor.get_running_processes() if "unknown" in p.get("username", "")]) > 5:
            insights["security_recommendations"].append("Multiple processes running with unknown users - review system security")
        
        return insights

def main():
    """Example usage of Advanced System Integration"""
    integration_manager = AdvancedIntegrationManager()
    
    # Get system status
    status = integration_manager.get_system_status()
    print("System Status:", json.dumps(status, indent=2))
    
    # Setup and start monitoring
    integration_manager.setup_system_hooks()
    integration_manager.start_monitoring()
    
    print("System integration started. Monitoring system events...")
    
    # Monitor for a short time
    time.sleep(10)
    
    # Get insights
    insights = integration_manager.get_integration_insights()
    print("Integration Insights:", json.dumps(insights, indent=2))
    
    # Stop monitoring
    integration_manager.stop_monitoring()

if __name__ == "__main__":
    main()
