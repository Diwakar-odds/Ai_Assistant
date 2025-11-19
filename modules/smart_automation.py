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
import schedule
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
    
    def __init__(self, db_path: str = "automation_engine.db"):
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
            return bool(eval(condition, {"__builtins__": {}}, context))
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