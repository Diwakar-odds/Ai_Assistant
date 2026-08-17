"""
Advanced Task Scheduler

This module provides sophisticated task scheduling capabilities with cron-like scheduling,
priority management, dynamic resource allocation, and intelligent load balancing.

Features:
- Cron-like scheduling with advanced patterns
- Dynamic priority adjustment based on system load
- Resource-aware scheduling
- Time zone support
- Recurring task management
- Conditional scheduling based on system state
- Holiday and business hour awareness
- Adaptive scheduling based on historical performance
"""

from __future__ import annotations

import time
import threading
import logging
import sqlite3
import json
import re
from typing import Dict, List, Optional, Callable, Any, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid
try:
    import cron_descriptor
except ImportError:
    cron_descriptor = None

try:
    from croniter import croniter
except ImportError:
    croniter = None

try:
    import pytz
except ImportError:
    pytz = None
import calendar
import bisect
from collections import defaultdict, deque

try:
    import holidays
    HOLIDAYS_AVAILABLE = True
except ImportError:
    HOLIDAYS_AVAILABLE = False

class ScheduleType(Enum):
    """Types of schedule patterns"""
    ONCE = "once"           # Execute once at specified time
    CRON = "cron"           # Cron-like pattern
    INTERVAL = "interval"   # Execute every N seconds/minutes/hours
    DAILY = "daily"         # Execute daily at specific time
    WEEKLY = "weekly"       # Execute weekly on specific days
    MONTHLY = "monthly"     # Execute monthly on specific date
    CONDITIONAL = "conditional"  # Execute when conditions are met

class ScheduleStatus(Enum):
    """Schedule status"""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    EXPIRED = "expired"
    COMPLETED = "completed"

class BusinessHours(Enum):
    """Business hour patterns"""
    STANDARD = "09:00-17:00"
    EXTENDED = "08:00-20:00"
    NIGHT_SHIFT = "22:00-06:00"
    WEEKENDS_ONLY = "weekend"
    WEEKDAYS_ONLY = "weekday"

@dataclass
class ScheduleCondition:
    """Condition for conditional scheduling"""
    condition_type: str  # 'system_load', 'user_presence', 'resource_usage', 'custom'
    operator: str        # 'lt', 'gt', 'eq', 'ne', 'in', 'not_in'
    value: Any          # Threshold value or list of values
    tolerance: float = 0.0  # Tolerance for numeric comparisons

@dataclass
class ScheduleConstraint:
    """Constraints for schedule execution"""
    max_concurrent: int = 1         # Maximum concurrent executions
    max_daily_executions: int = 100 # Maximum executions per day
    min_interval_seconds: int = 60   # Minimum interval between executions
    business_hours_only: bool = False # Execute only during business hours
    exclude_holidays: bool = False   # Skip execution on holidays
    allowed_days: Optional[List[int]] = None  # Days of week (0=Monday)
    timezone: str = "UTC"           # Timezone for scheduling

@dataclass
class ScheduledTask:
    """Scheduled task definition"""
    id: str
    name: str
    function: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Schedule configuration
    schedule_type: ScheduleType = ScheduleType.ONCE
    schedule_pattern: str = ""       # Cron pattern, interval, or time
    schedule_timezone: str = "UTC"
    
    # Execution constraints
    constraints: ScheduleConstraint = field(default_factory=ScheduleConstraint)
    conditions: List[ScheduleCondition] = field(default_factory=list)
    
    # Status and tracking
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    next_execution: Optional[datetime] = None
    last_execution: Optional[datetime] = None
    execution_count: int = 0
    failure_count: int = 0
    
    # Metadata
    created_time: datetime = field(default_factory=datetime.now)
    updated_time: datetime = field(default_factory=datetime.now)
    description: str = ""
    tags: List[str] = field(default_factory=list)
    priority: int = 5  # 1-10, higher is more important
    
    # Execution limits
    max_executions: Optional[int] = None
    expires_at: Optional[datetime] = None

@dataclass
class ExecutionRecord:
    """Record of task execution"""
    id: str
    task_id: str
    scheduled_time: datetime
    actual_time: datetime
    duration: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    result: Optional[Any] = None
    system_load: Dict[str, float] = field(default_factory=dict)

class CronParser:
    """
    Advanced cron pattern parser with extended features
    """
    
    # Extended cron patterns
    MACROS = {
        '@yearly': '0 0 1 1 *',
        '@annually': '0 0 1 1 *',
        '@monthly': '0 0 1 * *',
        '@weekly': '0 0 * * 0',
        '@daily': '0 0 * * *',
        '@midnight': '0 0 * * *',
        '@hourly': '0 * * * *',
        '@reboot': 'REBOOT'
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def parse_pattern(self, pattern: str, base_time: datetime = None) -> Optional[croniter]:
        """Parse cron pattern and return croniter object"""
        if croniter is None:
            self.logger.error("croniter is not installed; cron patterns are unavailable")
            return None

        try:
            # Replace macros
            if pattern in self.MACROS:
                pattern = self.MACROS[pattern]
            
            # Handle special cases
            if pattern == 'REBOOT':
                return None  # Handle reboot separately
            
            # Validate pattern
            if not self._validate_pattern(pattern):
                return None
            
            base_time = base_time or datetime.now()
            return croniter(pattern, base_time)
            
        except Exception as e:
            self.logger.error(f"Failed to parse cron pattern '{pattern}': {e}")
            return None
    
    def _validate_pattern(self, pattern: str) -> bool:
        """Validate cron pattern format"""
        try:
            parts = pattern.split()
            if len(parts) != 5:
                return False
            
            # Basic validation for each field
            minute, hour, day, month, weekday = parts
            
            # Minute: 0-59
            if not self._validate_field(minute, 0, 59):
                return False
            
            # Hour: 0-23
            if not self._validate_field(hour, 0, 23):
                return False
            
            # Day: 1-31
            if not self._validate_field(day, 1, 31):
                return False
            
            # Month: 1-12
            if not self._validate_field(month, 1, 12):
                return False
            
            # Weekday: 0-7 (0 and 7 are Sunday)
            if not self._validate_field(weekday, 0, 7):
                return False
            
            return True
            
        except Exception:
            return False
    
    def _validate_field(self, field: str, min_val: int, max_val: int) -> bool:
        """Validate individual cron field"""
        if field == '*':
            return True
        
        # Handle ranges (e.g., 1-5)
        if '-' in field:
            try:
                start, end = field.split('-')
                start, end = int(start), int(end)
                return min_val <= start <= end <= max_val
            except ValueError:
                return False
        
        # Handle lists (e.g., 1,3,5)
        if ',' in field:
            try:
                values = [int(v.strip()) for v in field.split(',')]
                return all(min_val <= v <= max_val for v in values)
            except ValueError:
                return False
        
        # Handle step values (e.g., */5, 0-20/2)
        if '/' in field:
            try:
                base, step = field.split('/')
                step = int(step)
                
                if base == '*':
                    return min_val <= step <= max_val
                elif '-' in base:
                    start, end = base.split('-')
                    start, end = int(start), int(end)
                    return min_val <= start <= end <= max_val and step > 0
                else:
                    value = int(base)
                    return min_val <= value <= max_val and step > 0
            except ValueError:
                return False
        
        # Handle single values
        try:
            value = int(field)
            return min_val <= value <= max_val
        except ValueError:
            return False
    
    def get_next_execution(self, pattern: str, 
                          base_time: datetime = None,
                          timezone_str: str = "UTC") -> Optional[datetime]:
        """Get next execution time for pattern"""
        try:
            cron_iter = self.parse_pattern(pattern, base_time)
            if not cron_iter:
                return None
            
            next_time = cron_iter.get_next(datetime)
            
            # Apply timezone
            if timezone_str != "UTC" and pytz is not None:
                tz = pytz.timezone(timezone_str)
                next_time = tz.localize(next_time) if next_time.tzinfo is None else next_time.astimezone(tz)
            
            return next_time
            
        except Exception as e:
            self.logger.error(f"Failed to get next execution for pattern '{pattern}': {e}")
            return None
    
    def describe_pattern(self, pattern: str) -> str:
        """Get human-readable description of cron pattern"""
        try:
            if pattern in self.MACROS:
                pattern = self.MACROS[pattern]

            if cron_descriptor is None:
                return f"Cron pattern: {pattern}"

            return cron_descriptor.get_description(pattern)
            
        except Exception:
            return f"Custom pattern: {pattern}"

class ScheduleEvaluator:
    """
    Evaluates schedule conditions and constraints
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.holiday_cache = {}  # Cache for holiday lookups
    
    def should_execute(self, task: ScheduledTask, current_time: datetime = None) -> Tuple[bool, str]:
        """
        Determine if task should execute now
        
        Returns:
            (should_execute, reason)
        """
        current_time = current_time or datetime.now()
        
        try:
            # Check if task is active
            if task.status != ScheduleStatus.ACTIVE:
                return False, f"Task status is {task.status.value}"
            
            # Check expiration
            if task.expires_at and current_time > task.expires_at:
                return False, "Task has expired"
            
            # Check execution limits
            if task.max_executions and task.execution_count >= task.max_executions:
                return False, "Maximum executions reached"
            
            # Check business hours constraint
            if task.constraints.business_hours_only:
                if not self._is_business_hours(current_time, task.constraints.timezone):
                    return False, "Outside business hours"
            
            # Check allowed days
            if task.constraints.allowed_days:
                weekday = current_time.weekday()  # 0=Monday
                if weekday not in task.constraints.allowed_days:
                    return False, f"Day {weekday} not in allowed days"
            
            # Check holidays
            if task.constraints.exclude_holidays:
                if self._is_holiday(current_time, task.constraints.timezone):
                    return False, "Holiday exclusion"
            
            # Check minimum interval
            if task.last_execution:
                time_since_last = (current_time - task.last_execution).total_seconds()
                if time_since_last < task.constraints.min_interval_seconds:
                    return False, f"Minimum interval not met ({time_since_last:.1f}s < {task.constraints.min_interval_seconds}s)"
            
            # Check daily execution limit
            if task.constraints.max_daily_executions > 0:
                daily_count = self._get_daily_execution_count(task, current_time)
                if daily_count >= task.constraints.max_daily_executions:
                    return False, f"Daily execution limit reached ({daily_count})"
            
            # Evaluate custom conditions
            for condition in task.conditions:
                if not self._evaluate_condition(condition, current_time):
                    return False, f"Condition not met: {condition.condition_type}"
            
            return True, "All checks passed"
            
        except Exception as e:
            self.logger.error(f"Error evaluating task {task.name}: {e}")
            return False, f"Evaluation error: {e}"
    
    def _is_business_hours(self, current_time: datetime, timezone_str: str) -> bool:
        """Check if current time is within business hours"""
        try:
            # Convert to specified timezone
            if timezone_str != "UTC" and pytz is not None:
                tz = pytz.timezone(timezone_str)
                local_time = current_time.astimezone(tz)
            else:
                local_time = current_time
            
            # Check if weekend
            weekday = local_time.weekday()  # 0=Monday, 6=Sunday
            if weekday >= 5:  # Saturday or Sunday
                return False
            
            # Check time range (9 AM to 5 PM by default)
            hour = local_time.hour
            return 9 <= hour < 17
            
        except Exception:
            return True  # Default to allowing execution
    
    def _is_holiday(self, current_time: datetime, timezone_str: str) -> bool:
        """Check if current date is a holiday"""
        if not HOLIDAYS_AVAILABLE:
            return False
        
        try:
            # Get country from timezone (simplified)
            country = 'US'  # Default to US
            if 'Europe' in timezone_str:
                country = 'UK'
            elif 'Asia' in timezone_str:
                country = 'CN'
            
            # Check cache
            year = current_time.year
            cache_key = f"{country}_{year}"
            
            if cache_key not in self.holiday_cache:
                self.holiday_cache[cache_key] = holidays.CountryHoliday(country, years=year)
            
            holiday_list = self.holiday_cache[cache_key]
            return current_time.date() in holiday_list
            
        except Exception:
            return False
    
    def _get_daily_execution_count(self, task: ScheduledTask, current_time: datetime) -> int:
        """Get number of executions today (simplified - would need execution history)"""
        # This would typically query execution history from database
        # For now, return 0 as placeholder
        return 0
    
    def _evaluate_condition(self, condition: ScheduleCondition, current_time: datetime) -> bool:
        """Evaluate custom condition"""
        try:
            if condition.condition_type == 'system_load':
                import psutil
                cpu_percent = psutil.cpu_percent()
                return self._compare_values(cpu_percent, condition.operator, condition.value, condition.tolerance)
            
            elif condition.condition_type == 'memory_usage':
                import psutil
                memory = psutil.virtual_memory()
                return self._compare_values(memory.percent, condition.operator, condition.value, condition.tolerance)
            
            elif condition.condition_type == 'time_range':
                # condition.value should be like "09:00-17:00"
                if isinstance(condition.value, str) and '-' in condition.value:
                    start_time, end_time = condition.value.split('-')
                    start_hour, start_min = map(int, start_time.split(':'))
                    end_hour, end_min = map(int, end_time.split(':'))
                    
                    current_hour = current_time.hour
                    current_min = current_time.minute
                    
                    start_minutes = start_hour * 60 + start_min
                    end_minutes = end_hour * 60 + end_min
                    current_minutes = current_hour * 60 + current_min
                    
                    return start_minutes <= current_minutes <= end_minutes
            
            elif condition.condition_type == 'user_presence':
                # Simplified user presence check
                return True  # Placeholder
            
            elif condition.condition_type == 'custom':
                # Custom condition evaluation
                if callable(condition.value):
                    return condition.value(current_time)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error evaluating condition {condition.condition_type}: {e}")
            return False
    
    def _compare_values(self, actual: float, operator: str, expected: Any, tolerance: float = 0.0) -> bool:
        """Compare values based on operator"""
        try:
            if operator == 'lt':
                return actual < (expected + tolerance)
            elif operator == 'gt':
                return actual > (expected - tolerance)
            elif operator == 'eq':
                return abs(actual - expected) <= tolerance
            elif operator == 'ne':
                return abs(actual - expected) > tolerance
            elif operator == 'le':
                return actual <= (expected + tolerance)
            elif operator == 'ge':
                return actual >= (expected - tolerance)
            elif operator == 'in':
                return actual in expected
            elif operator == 'not_in':
                return actual not in expected
            
            return False
            
        except Exception:
            return False

class LoadBalancer:
    """
    Intelligent load balancer for scheduled tasks
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.execution_history = deque(maxlen=1000)
        self.current_load = 0.0
        self.load_samples = deque(maxlen=100)
    
    def calculate_optimal_delay(self, task: ScheduledTask, current_load: float) -> float:
        """Calculate optimal delay before execution based on system load"""
        try:
            # Base delay based on priority (higher priority = less delay)
            base_delay = max(0, (10 - task.priority) * 0.1)
            
            # Adjust based on system load
            if current_load > 80:
                load_delay = (current_load - 80) * 0.1  # Up to 2 seconds extra delay
            elif current_load < 20:
                load_delay = -0.5  # Execute sooner on low load
            else:
                load_delay = 0
            
            # Consider historical performance
            historical_delay = self._calculate_historical_delay(task)
            
            total_delay = max(0, base_delay + load_delay + historical_delay)
            
            return total_delay
            
        except Exception as e:
            self.logger.error(f"Error calculating delay for task {task.name}: {e}")
            return 0.0
    
    def _calculate_historical_delay(self, task: ScheduledTask) -> float:
        """Calculate delay based on historical performance"""
        # Simplified - would analyze execution history
        return 0.0
    
    def should_defer_execution(self, task: ScheduledTask, current_load: float) -> bool:
        """Determine if execution should be deferred due to high load"""
        # Defer low-priority tasks during high load
        if task.priority <= 3 and current_load > 85:
            return True
        
        # Defer all non-critical tasks during extreme load
        if task.priority < 9 and current_load > 95:
            return True
        
        return False

class AdvancedTaskScheduler:
    """
    Advanced task scheduler with intelligent scheduling and load management
    """
    
    def __init__(self, db_path: str = "data/automation/task_scheduler.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.cron_parser = CronParser()
        self.evaluator = ScheduleEvaluator()
        self.load_balancer = LoadBalancer()
        
        # Task storage
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.execution_queue: List[Tuple[datetime, str]] = []  # (execution_time, task_id)
        
        # Execution tracking
        self.execution_records: Dict[str, List[ExecutionRecord]] = defaultdict(list)
        self.running = False
        
        # Threading
        self.scheduler_thread = None
        self.executor_thread = None
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        
        # Statistics
        self.stats = {
            'total_scheduled': 0,
            'total_executed': 0,
            'total_failed': 0,
            'average_delay': 0.0
        }
        
        # Initialize database
        self._init_database()
        self._load_tasks()
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            return
        
        self._stop_event.clear()
        self.running = True
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        # Start executor thread
        self.executor_thread = threading.Thread(target=self._executor_loop, daemon=True)
        self.executor_thread.start()
        
        self.logger.info("Advanced task scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            return
        
        self.running = False
        self._stop_event.set()
        
        # Wait for threads to finish
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=10.0)
        
        if self.executor_thread:
            self.executor_thread.join(timeout=10.0)

        self.scheduler_thread = None
        self.executor_thread = None
        
        self.logger.info("Advanced task scheduler stopped")
    
    def schedule_task(self, task: ScheduledTask) -> bool:
        """Schedule a new task"""
        try:
            with self._lock:
                # Validate task
                if not self._validate_task(task):
                    return False
                
                # Calculate next execution time
                next_exec = self._calculate_next_execution(task)
                if next_exec:
                    task.next_execution = next_exec
                
                # Store task
                self.scheduled_tasks[task.id] = task
                
                # Add to execution queue if ready
                if task.next_execution and task.status == ScheduleStatus.ACTIVE:
                    self._add_to_queue(task.next_execution, task.id)
                
                # Save to database
                self._save_task(task)
                
                self.stats['total_scheduled'] += 1
                self.logger.info(f"Scheduled task '{task.name}' (ID: {task.id})")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to schedule task '{task.name}': {e}")
            return False
    
    def unschedule_task(self, task_id: str) -> bool:
        """Remove scheduled task"""
        try:
            with self._lock:
                if task_id not in self.scheduled_tasks:
                    return False
                
                # Remove from queue
                self.execution_queue = [(time, tid) for time, tid in self.execution_queue if tid != task_id]
                
                # Remove from storage
                del self.scheduled_tasks[task_id]
                
                # Remove from database
                self._delete_task(task_id)
                
                self.logger.info(f"Unscheduled task {task_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to unschedule task {task_id}: {e}")
            return False
    
    def pause_task(self, task_id: str) -> bool:
        """Pause scheduled task"""
        if task_id in self.scheduled_tasks:
            task = self.scheduled_tasks[task_id]
            task.status = ScheduleStatus.PAUSED
            task.updated_time = datetime.now()
            self._save_task(task)
            return True
        return False
    
    def resume_task(self, task_id: str) -> bool:
        """Resume paused task"""
        if task_id in self.scheduled_tasks:
            task = self.scheduled_tasks[task_id]
            if task.status == ScheduleStatus.PAUSED:
                task.status = ScheduleStatus.ACTIVE
                task.updated_time = datetime.now()
                
                # Recalculate next execution
                next_exec = self._calculate_next_execution(task)
                if next_exec:
                    task.next_execution = next_exec
                    self._add_to_queue(next_exec, task_id)
                
                self._save_task(task)
                return True
        return False
    
    def get_task_info(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get information about scheduled task"""
        if task_id not in self.scheduled_tasks:
            return None
        
        task = self.scheduled_tasks[task_id]
        
        return {
            'id': task.id,
            'name': task.name,
            'schedule_type': task.schedule_type.value,
            'schedule_pattern': task.schedule_pattern,
            'status': task.status.value,
            'next_execution': task.next_execution.isoformat() if task.next_execution else None,
            'last_execution': task.last_execution.isoformat() if task.last_execution else None,
            'execution_count': task.execution_count,
            'failure_count': task.failure_count,
            'priority': task.priority,
            'description': task.description,
            'tags': task.tags
        }
    
    def list_tasks(self, status: ScheduleStatus = None) -> List[Dict[str, Any]]:
        """List all scheduled tasks"""
        tasks = []
        
        for task in self.scheduled_tasks.values():
            if status is None or task.status == status:
                tasks.append(self.get_task_info(task.id))
        
        return sorted(tasks, key=lambda x: x.get('next_execution', ''))
    
    def get_execution_history(self, task_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get execution history for task"""
        if task_id not in self.execution_records:
            return []
        
        records = self.execution_records[task_id][-limit:]
        
        return [
            {
                'id': record.id,
                'scheduled_time': record.scheduled_time.isoformat(),
                'actual_time': record.actual_time.isoformat(),
                'duration': record.duration,
                'success': record.success,
                'error_message': record.error_message,
                'system_load': record.system_load
            }
            for record in records
        ]
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics"""
        with self._lock:
            active_tasks = len([t for t in self.scheduled_tasks.values() if t.status == ScheduleStatus.ACTIVE])
            paused_tasks = len([t for t in self.scheduled_tasks.values() if t.status == ScheduleStatus.PAUSED])
            
            return {
                'total_tasks': len(self.scheduled_tasks),
                'active_tasks': active_tasks,
                'paused_tasks': paused_tasks,
                'queue_size': len(self.execution_queue),
                'running': self.running,
                'statistics': self.stats.copy()
            }
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running and not self._stop_event.is_set():
            try:
                current_time = datetime.now()
                
                # Reschedule recurring tasks
                self._reschedule_recurring_tasks(current_time)
                
                # Clean up expired tasks
                self._cleanup_expired_tasks(current_time)
                
                self._stop_event.wait(60)  # Check every minute or stop immediately
                
            except Exception as e:
                self.logger.error(f"Scheduler loop error: {e}")
                self._stop_event.wait(10)
    
    def _executor_loop(self):
        """Main executor loop"""
        while self.running and not self._stop_event.is_set():
            try:
                current_time = datetime.now()
                
                # Check for tasks ready to execute
                ready_tasks = []
                
                with self._lock:
                    while (self.execution_queue and 
                           self.execution_queue[0][0] <= current_time):
                        exec_time, task_id = self.execution_queue.pop(0)
                        
                        if task_id in self.scheduled_tasks:
                            task = self.scheduled_tasks[task_id]
                            
                            # Final check if task should execute
                            should_execute, reason = self.evaluator.should_execute(task, current_time)
                            
                            if should_execute:
                                ready_tasks.append((task, exec_time))
                            else:
                                self.logger.debug(f"Skipping task {task.name}: {reason}")
                
                # Execute ready tasks
                for task, scheduled_time in ready_tasks:
                    self._execute_task(task, scheduled_time, current_time)
                
                self._stop_event.wait(1)  # Check every second or stop immediately
                
            except Exception as e:
                self.logger.error(f"Executor loop error: {e}")
                self._stop_event.wait(5)
    
    def _execute_task(self, task: ScheduledTask, scheduled_time: datetime, actual_time: datetime):
        """Execute scheduled task"""
        try:
            # Get current system load
            import psutil
            system_load = {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent
            }
            
            # Check if execution should be deferred
            if self.load_balancer.should_defer_execution(task, system_load['cpu_percent']):
                # Reschedule for later
                delay = self.load_balancer.calculate_optimal_delay(task, system_load['cpu_percent'])
                new_time = actual_time + timedelta(seconds=delay)
                self._add_to_queue(new_time, task.id)
                self.logger.debug(f"Deferred task {task.name} by {delay:.1f}s due to high load")
                return
            
            # Create execution record
            record = ExecutionRecord(
                id=str(uuid.uuid4()),
                task_id=task.id,
                scheduled_time=scheduled_time,
                actual_time=actual_time,
                system_load=system_load
            )
            
            start_time = time.time()
            
            try:
                # Execute task function
                result = task.function(**task.parameters)
                
                # Record successful execution
                record.success = True
                record.result = result
                record.duration = time.time() - start_time
                
                # Update task
                task.execution_count += 1
                task.last_execution = actual_time
                task.updated_time = datetime.now()
                
                self.stats['total_executed'] += 1
                self.logger.info(f"Executed task '{task.name}' successfully in {record.duration:.2f}s")
                
            except Exception as e:
                # Record failed execution
                record.success = False
                record.error_message = str(e)
                record.duration = time.time() - start_time
                
                # Update task
                task.failure_count += 1
                task.last_execution = actual_time
                task.updated_time = datetime.now()
                
                self.stats['total_failed'] += 1
                self.logger.error(f"Task '{task.name}' failed: {e}")
            
            # Store execution record
            self.execution_records[task.id].append(record)
            
            # Schedule next execution for recurring tasks
            if task.schedule_type != ScheduleType.ONCE:
                next_exec = self._calculate_next_execution(task)
                if next_exec:
                    task.next_execution = next_exec
                    self._add_to_queue(next_exec, task.id)
            
            # Save updated task
            self._save_task(task)
            
        except Exception as e:
            self.logger.error(f"Error executing task {task.name}: {e}")
    
    def _calculate_next_execution(self, task: ScheduledTask) -> Optional[datetime]:
        """Calculate next execution time for task"""
        try:
            current_time = datetime.now()
            
            if task.schedule_type == ScheduleType.ONCE:
                # Parse specific date/time
                if task.schedule_pattern:
                    try:
                        return datetime.fromisoformat(task.schedule_pattern)
                    except ValueError:
                        return None
                return None
            
            elif task.schedule_type == ScheduleType.CRON:
                return self.cron_parser.get_next_execution(
                    task.schedule_pattern, current_time, task.schedule_timezone
                )
            
            elif task.schedule_type == ScheduleType.INTERVAL:
                # Parse interval (e.g., "30s", "5m", "1h")
                interval_seconds = self._parse_interval(task.schedule_pattern)
                if interval_seconds and task.last_execution:
                    return task.last_execution + timedelta(seconds=interval_seconds)
                elif interval_seconds:
                    return current_time + timedelta(seconds=interval_seconds)
                return None
            
            elif task.schedule_type == ScheduleType.DAILY:
                # Parse daily time (e.g., "14:30")
                if ':' in task.schedule_pattern:
                    hour, minute = map(int, task.schedule_pattern.split(':'))
                    next_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    if next_time <= current_time:
                        next_time += timedelta(days=1)
                    
                    return next_time
                return None
            
            elif task.schedule_type == ScheduleType.WEEKLY:
                # Parse weekly pattern (e.g., "monday:14:30", "1:09:00" for Tuesday 9 AM)
                if ':' in task.schedule_pattern:
                    parts = task.schedule_pattern.split(':')
                    if len(parts) == 3:
                        weekday, hour, minute = parts
                        if weekday.isdigit():
                            weekday = int(weekday)
                        else:
                            weekday = ['monday', 'tuesday', 'wednesday', 'thursday', 
                                     'friday', 'saturday', 'sunday'].index(weekday.lower())
                        
                        hour, minute = int(hour), int(minute)
                        
                        # Find next occurrence
                        days_ahead = weekday - current_time.weekday()
                        if days_ahead <= 0:  # Target day already happened this week
                            days_ahead += 7
                        
                        next_time = current_time + timedelta(days=days_ahead)
                        next_time = next_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        
                        return next_time
                return None
            
            elif task.schedule_type == ScheduleType.MONTHLY:
                # Parse monthly pattern (e.g., "15:14:30" for 15th day at 14:30)
                if ':' in task.schedule_pattern:
                    parts = task.schedule_pattern.split(':')
                    if len(parts) == 3:
                        day, hour, minute = map(int, parts)
                        
                        # Find next occurrence
                        next_time = current_time.replace(day=day, hour=hour, minute=minute, second=0, microsecond=0)
                        
                        if next_time <= current_time:
                            # Move to next month
                            if current_time.month == 12:
                                next_time = next_time.replace(year=current_time.year + 1, month=1)
                            else:
                                next_time = next_time.replace(month=current_time.month + 1)
                        
                        return next_time
                return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error calculating next execution for task {task.name}: {e}")
            return None
    
    def _parse_interval(self, interval_str: str) -> Optional[int]:
        """Parse interval string to seconds"""
        try:
            if interval_str.endswith('s'):
                return int(interval_str[:-1])
            elif interval_str.endswith('m'):
                return int(interval_str[:-1]) * 60
            elif interval_str.endswith('h'):
                return int(interval_str[:-1]) * 3600
            elif interval_str.endswith('d'):
                return int(interval_str[:-1]) * 86400
            else:
                return int(interval_str)  # Assume seconds
        except ValueError:
            return None
    
    def _validate_task(self, task: ScheduledTask) -> bool:
        """Validate task before scheduling"""
        if not task.id or not task.name or not task.function:
            return False
        
        if task.id in self.scheduled_tasks:
            return False
        
        if not callable(task.function):
            return False
        
        return True
    
    def _add_to_queue(self, execution_time: datetime, task_id: str):
        """Add task to execution queue"""
        with self._lock:
            # Insert in sorted order
            bisect.insort(self.execution_queue, (execution_time, task_id))
    
    def _reschedule_recurring_tasks(self, current_time: datetime):
        """Reschedule recurring tasks that need updating"""
        with self._lock:
            for task in self.scheduled_tasks.values():
                if (task.status == ScheduleStatus.ACTIVE and 
                    task.schedule_type != ScheduleType.ONCE and
                    (not task.next_execution or task.next_execution <= current_time)):
                    
                    next_exec = self._calculate_next_execution(task)
                    if next_exec:
                        task.next_execution = next_exec
                        self._add_to_queue(next_exec, task.id)
    
    def _cleanup_expired_tasks(self, current_time: datetime):
        """Remove expired tasks"""
        with self._lock:
            expired_tasks = []
            
            for task_id, task in self.scheduled_tasks.items():
                if task.expires_at and current_time > task.expires_at:
                    task.status = ScheduleStatus.EXPIRED
                    expired_tasks.append(task_id)
                
                elif (task.max_executions and 
                      task.execution_count >= task.max_executions):
                    task.status = ScheduleStatus.COMPLETED
                    expired_tasks.append(task_id)
            
            for task_id in expired_tasks:
                self._save_task(self.scheduled_tasks[task_id])
    
    def _init_database(self):
        """Initialize database for task storage"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS scheduled_tasks (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        schedule_type TEXT NOT NULL,
                        schedule_pattern TEXT,
                        schedule_timezone TEXT,
                        status TEXT NOT NULL,
                        priority INTEGER,
                        constraints TEXT,
                        conditions TEXT,
                        next_execution TEXT,
                        last_execution TEXT,
                        execution_count INTEGER DEFAULT 0,
                        failure_count INTEGER DEFAULT 0,
                        max_executions INTEGER,
                        expires_at TEXT,
                        created_time TEXT,
                        updated_time TEXT,
                        description TEXT,
                        tags TEXT,
                        function_module TEXT,
                        function_name TEXT,
                        parameters TEXT
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS execution_records (
                        id TEXT PRIMARY KEY,
                        task_id TEXT,
                        scheduled_time TEXT,
                        actual_time TEXT,
                        duration REAL,
                        success BOOLEAN,
                        error_message TEXT,
                        system_load TEXT,
                        FOREIGN KEY (task_id) REFERENCES scheduled_tasks (id)
                    )
                ''')
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
    
    def _save_task(self, task: ScheduledTask):
        """Save task to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO scheduled_tasks 
                    (id, name, schedule_type, schedule_pattern, schedule_timezone, status,
                     priority, constraints, conditions, next_execution, last_execution,
                     execution_count, failure_count, max_executions, expires_at,
                     created_time, updated_time, description, tags, function_module,
                     function_name, parameters)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.id,
                    task.name,
                    task.schedule_type.value,
                    task.schedule_pattern,
                    task.schedule_timezone,
                    task.status.value,
                    task.priority,
                    json.dumps(task.constraints.__dict__),
                    json.dumps([c.__dict__ for c in task.conditions]),
                    task.next_execution.isoformat() if task.next_execution else None,
                    task.last_execution.isoformat() if task.last_execution else None,
                    task.execution_count,
                    task.failure_count,
                    task.max_executions,
                    task.expires_at.isoformat() if task.expires_at else None,
                    task.created_time.isoformat(),
                    task.updated_time.isoformat(),
                    task.description,
                    json.dumps(task.tags),
                    task.function.__module__ if hasattr(task.function, '__module__') else '',
                    task.function.__name__ if hasattr(task.function, '__name__') else '',
                    json.dumps(task.parameters)
                ))
                
        except Exception as e:
            self.logger.error(f"Failed to save task {task.id}: {e}")
    
    def _load_tasks(self):
        """Load tasks from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT * FROM scheduled_tasks')
                
                for row in cursor.fetchall():
                    # This is a simplified load - in practice, you'd need to
                    # restore the function references properly
                    self.logger.debug(f"Found saved task: {row[1]}")
                    
        except Exception as e:
            self.logger.error(f"Failed to load tasks: {e}")
    
    def _delete_task(self, task_id: str):
        """Delete task from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM scheduled_tasks WHERE id = ?', (task_id,))
                conn.execute('DELETE FROM execution_records WHERE task_id = ?', (task_id,))
                
        except Exception as e:
            self.logger.error(f"Failed to delete task {task_id}: {e}")


# Convenience functions
def create_cron_task(name: str, cron_pattern: str, function: Callable, 
                    parameters: Dict[str, Any] = None, **kwargs) -> ScheduledTask:
    """Create a cron-scheduled task"""
    return ScheduledTask(
        id=str(uuid.uuid4()),
        name=name,
        function=function,
        parameters=parameters or {},
        schedule_type=ScheduleType.CRON,
        schedule_pattern=cron_pattern,
        **kwargs
    )

def create_interval_task(name: str, interval: str, function: Callable,
                        parameters: Dict[str, Any] = None, **kwargs) -> ScheduledTask:
    """Create an interval-scheduled task"""
    return ScheduledTask(
        id=str(uuid.uuid4()),
        name=name,
        function=function,
        parameters=parameters or {},
        schedule_type=ScheduleType.INTERVAL,
        schedule_pattern=interval,
        **kwargs
    )

def create_daily_task(name: str, time_str: str, function: Callable,
                     parameters: Dict[str, Any] = None, **kwargs) -> ScheduledTask:
    """Create a daily scheduled task"""
    return ScheduledTask(
        id=str(uuid.uuid4()),
        name=name,
        function=function,
        parameters=parameters or {},
        schedule_type=ScheduleType.DAILY,
        schedule_pattern=time_str,
        **kwargs
    )