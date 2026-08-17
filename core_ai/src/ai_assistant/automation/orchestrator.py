"""
Automation Orchestration Layer

This module provides comprehensive automation orchestration with intelligent task coordination,
resource management, and execution prioritization for the AI Assistant.

Features:
- Intelligent task coordination and dependency management
- Dynamic resource allocation and load balancing
- Priority-based execution queuing
- Real-time performance monitoring
- Adaptive scheduling based on system resources
- Cross-module task integration
- Error recovery and retry mechanisms
"""

import asyncio
import threading
import time
import queue
import logging
import json
import sqlite3
import psutil
from typing import Dict, List, Optional, Callable, Any, Tuple, Set, Union
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from datetime import datetime, timedelta
import uuid
import hashlib
import weakref
from pathlib import Path
import concurrent.futures
from collections import defaultdict, deque

# Resource monitoring imports
try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

class TaskPriority(IntEnum):
    """Task execution priority levels"""
    CRITICAL = 0    # Emergency tasks, immediate execution
    HIGH = 1        # Important tasks, high priority
    NORMAL = 2      # Standard tasks
    LOW = 3         # Background tasks
    IDLE = 4        # Execute only when system idle

class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class ResourceType(Enum):
    """System resource types"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    GPU = "gpu"
    FILE_HANDLE = "file_handle"
    DATABASE = "database"

class ExecutionMode(Enum):
    """Task execution modes"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    BATCH = "batch"
    STREAMING = "streaming"

@dataclass
class ResourceRequirements:
    """Resource requirements for task execution"""
    cpu_percent: float = 10.0           # CPU usage percentage
    memory_mb: int = 100                # Memory in MB
    disk_mb: int = 50                   # Disk space in MB
    network_mbps: float = 1.0           # Network bandwidth in Mbps
    gpu_memory_mb: int = 0              # GPU memory in MB
    file_handles: int = 5               # Number of file handles
    database_connections: int = 1        # Database connections
    execution_time_estimate: float = 5.0 # Estimated execution time in seconds

@dataclass
class TaskDependency:
    """Task dependency definition"""
    task_id: str
    dependency_type: str = "completion"  # completion, output, resource
    required_output: Optional[Any] = None
    timeout_seconds: float = 300.0

@dataclass
class TaskMetrics:
    """Task execution metrics"""
    start_time: float = 0.0
    end_time: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_io: float = 0.0
    network_io: float = 0.0
    retry_count: int = 0
    error_count: int = 0

@dataclass
class AutomationTask:
    """Comprehensive automation task definition"""
    id: str
    name: str
    function: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    
    # Resource management
    resource_requirements: ResourceRequirements = field(default_factory=ResourceRequirements)
    exclusive_resources: List[str] = field(default_factory=list)
    
    # Dependencies and ordering
    dependencies: List[TaskDependency] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    
    # Execution configuration
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout_seconds: float = 300.0
    
    # Scheduling
    scheduled_time: Optional[datetime] = None
    deadline: Optional[datetime] = None
    periodic_interval: Optional[timedelta] = None
    
    # Results and metrics
    result: Any = None
    error: Optional[Exception] = None
    metrics: TaskMetrics = field(default_factory=TaskMetrics)
    
    # Metadata
    created_time: datetime = field(default_factory=datetime.now)
    updated_time: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    description: str = ""

@dataclass
class SystemResources:
    """Current system resource state"""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_available_mb: int = 0
    disk_usage_percent: float = 0.0
    disk_free_gb: float = 0.0
    network_sent_mbps: float = 0.0
    network_recv_mbps: float = 0.0
    gpu_usage_percent: float = 0.0
    gpu_memory_percent: float = 0.0
    active_processes: int = 0
    file_handles_used: int = 0
    database_connections: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ExecutionContext:
    """Task execution context"""
    task_id: str
    executor_id: str
    thread_id: int
    start_time: datetime
    allocated_resources: Dict[str, float]
    environment: Dict[str, Any] = field(default_factory=dict)

class ResourceManager:
    """
    Manages system resources and allocation for tasks
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.resource_locks = {
            ResourceType.CPU: threading.Semaphore(100),
            ResourceType.MEMORY: threading.Semaphore(1000),
            ResourceType.DISK: threading.Semaphore(100),
            ResourceType.NETWORK: threading.Semaphore(100),
            ResourceType.FILE_HANDLE: threading.Semaphore(1000),
            ResourceType.DATABASE: threading.Semaphore(10)
        }
        
        if GPU_AVAILABLE:
            self.resource_locks[ResourceType.GPU] = threading.Semaphore(100)
        
        # Resource monitoring
        self.current_resources = SystemResources()
        self.resource_history = deque(maxlen=1000)
        self.monitoring_active = False
        self.monitor_thread = None
        
        # Resource reservations
        self.reserved_resources: Dict[str, Dict[ResourceType, float]] = {}
        
        # Start resource monitoring
        self.start_monitoring()
    
    def start_monitoring(self):
        """Start system resource monitoring"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Resource monitoring started")
    
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        self.logger.info("Resource monitoring stopped")
    
    def _monitor_resources(self):
        """Monitor system resources continuously"""
        while self.monitoring_active:
            try:
                # Get CPU usage
                cpu_percent = psutil.cpu_percent(interval=0.1)
                
                # Get memory info
                memory = psutil.virtual_memory()
                
                # Get disk info
                disk = psutil.disk_usage('/')
                
                # Get network info
                network = psutil.net_io_counters()
                net_sent_mbps = getattr(network, 'bytes_sent', 0) / 1024 / 1024
                net_recv_mbps = getattr(network, 'bytes_recv', 0) / 1024 / 1024
                
                # Get GPU info if available
                gpu_usage = 0.0
                gpu_memory = 0.0
                if GPU_AVAILABLE:
                    try:
                        gpus = GPUtil.getGPUs()
                        if gpus:
                            gpu_usage = gpus[0].load * 100
                            gpu_memory = gpus[0].memoryUtil * 100
                    except Exception:
                        pass
                
                # Update current resources
                self.current_resources = SystemResources(
                    cpu_percent=cpu_percent,
                    memory_percent=memory.percent,
                    memory_available_mb=memory.available // 1024 // 1024,
                    disk_usage_percent=disk.percent,
                    disk_free_gb=disk.free // 1024 // 1024 // 1024,
                    network_sent_mbps=net_sent_mbps,
                    network_recv_mbps=net_recv_mbps,
                    gpu_usage_percent=gpu_usage,
                    gpu_memory_percent=gpu_memory,
                    active_processes=len(psutil.pids()),
                    timestamp=datetime.now()
                )
                
                # Add to history
                self.resource_history.append(self.current_resources)
                
                time.sleep(1.0)  # Update every second
                
            except Exception as e:
                self.logger.error(f"Resource monitoring error: {e}")
                time.sleep(5.0)  # Wait longer on error
    
    def get_current_resources(self) -> SystemResources:
        """Get current system resources"""
        return self.current_resources
    
    def get_resource_history(self, duration_minutes: int = 60) -> List[SystemResources]:
        """Get resource history for specified duration"""
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        return [res for res in self.resource_history if res.timestamp >= cutoff_time]
    
    def can_allocate_resources(self, requirements: ResourceRequirements) -> bool:
        """Check if resources can be allocated for task"""
        try:
            current = self.current_resources
            
            # Check CPU
            if current.cpu_percent + requirements.cpu_percent > 90:
                return False
            
            # Check memory
            if requirements.memory_mb > current.memory_available_mb:
                return False
            
            # Check disk space
            required_gb = requirements.disk_mb / 1024
            if required_gb > current.disk_free_gb:
                return False
            
            # Check GPU if required
            if requirements.gpu_memory_mb > 0 and current.gpu_memory_percent > 80:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Resource allocation check failed: {e}")
            return False
    
    def reserve_resources(self, task_id: str, requirements: ResourceRequirements) -> bool:
        """Reserve resources for task execution"""
        try:
            if not self.can_allocate_resources(requirements):
                return False
            
            # Reserve resources
            reservations = {
                ResourceType.CPU: requirements.cpu_percent,
                ResourceType.MEMORY: requirements.memory_mb,
                ResourceType.DISK: requirements.disk_mb,
                ResourceType.NETWORK: requirements.network_mbps,
                ResourceType.FILE_HANDLE: requirements.file_handles,
                ResourceType.DATABASE: requirements.database_connections
            }
            
            if requirements.gpu_memory_mb > 0:
                reservations[ResourceType.GPU] = requirements.gpu_memory_mb
            
            self.reserved_resources[task_id] = reservations
            return True
            
        except Exception as e:
            self.logger.error(f"Resource reservation failed: {e}")
            return False
    
    def release_resources(self, task_id: str):
        """Release reserved resources"""
        if task_id in self.reserved_resources:
            del self.reserved_resources[task_id]

class TaskQueue:
    """
    Intelligent task queue with priority handling and resource awareness
    """
    
    def __init__(self, resource_manager: ResourceManager):
        self.resource_manager = resource_manager
        self.logger = logging.getLogger(__name__)
        
        # Priority queues for different priority levels
        self.priority_queues = {
            priority: queue.PriorityQueue() for priority in TaskPriority
        }
        
        # Task registry
        self.tasks: Dict[str, AutomationTask] = {}
        self.running_tasks: Dict[str, AutomationTask] = {}
        
        # Task tracking
        self.task_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.task_dependents: Dict[str, Set[str]] = defaultdict(set)
        
        # Queue locks
        self._queue_lock = threading.RLock()
        
    def add_task(self, task: AutomationTask) -> bool:
        """Add task to queue"""
        try:
            with self._queue_lock:
                # Validate task
                if not self._validate_task(task):
                    return False
                
                # Register task
                self.tasks[task.id] = task
                task.status = TaskStatus.QUEUED
                task.updated_time = datetime.now()
                
                # Update dependency tracking
                self._update_dependencies(task)
                
                # Check if task can be queued immediately
                if self._can_queue_task(task):
                    # Calculate priority score
                    priority_score = self._calculate_priority_score(task)
                    
                    # Add to appropriate priority queue
                    self.priority_queues[task.priority].put((priority_score, time.time(), task.id))
                    
                    self.logger.debug(f"Task {task.name} added to queue with priority {task.priority}")
                else:
                    self.logger.debug(f"Task {task.name} waiting for dependencies")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to add task {task.name}: {e}")
            return False
    
    def get_next_task(self) -> Optional[AutomationTask]:
        """Get next task for execution"""
        with self._queue_lock:
            # Check priority queues from highest to lowest priority
            for priority in sorted(TaskPriority, key=lambda x: x.value):
                queue_obj = self.priority_queues[priority]
                
                if not queue_obj.empty():
                    try:
                        _, _, task_id = queue_obj.get_nowait()
                        
                        if task_id in self.tasks:
                            task = self.tasks[task_id]
                            
                            # Check if task is still ready and resources available
                            if (task.status == TaskStatus.QUEUED and 
                                self._can_execute_task(task)):
                                
                                # Move to running tasks
                                self.running_tasks[task_id] = task
                                task.status = TaskStatus.RUNNING
                                task.metrics.start_time = time.time()
                                
                                # Reserve resources
                                self.resource_manager.reserve_resources(task_id, task.resource_requirements)
                                
                                return task
                            
                    except queue.Empty:
                        continue
            
            return None
    
    def complete_task(self, task_id: str, result: Any = None, error: Exception = None):
        """Mark task as completed and update dependents"""
        with self._queue_lock:
            if task_id not in self.running_tasks:
                return
            
            task = self.running_tasks[task_id]
            
            # Update task state
            if error:
                task.status = TaskStatus.FAILED
                task.error = error
                task.metrics.error_count += 1
            else:
                task.status = TaskStatus.COMPLETED
                task.result = result
            
            task.metrics.end_time = time.time()
            task.updated_time = datetime.now()
            
            # Release resources
            self.resource_manager.release_resources(task_id)
            
            # Move from running to completed
            del self.running_tasks[task_id]
            
            # Check dependent tasks
            if task.status == TaskStatus.COMPLETED:
                self._check_dependent_tasks(task_id)
            
            self.logger.debug(f"Task {task.name} completed with status {task.status}")
    
    def _validate_task(self, task: AutomationTask) -> bool:
        """Validate task before adding to queue"""
        if not task.id or not task.name or not task.function:
            return False
        
        if task.id in self.tasks:
            return False  # Duplicate task ID
        
        return True
    
    def _update_dependencies(self, task: AutomationTask):
        """Update task dependency tracking"""
        for dependency in task.dependencies:
            dep_id = dependency.task_id
            self.task_dependencies[task.id].add(dep_id)
            self.task_dependents[dep_id].add(task.id)
    
    def _can_queue_task(self, task: AutomationTask) -> bool:
        """Check if task can be queued (dependencies satisfied)"""
        for dependency in task.dependencies:
            dep_id = dependency.task_id
            
            if dep_id not in self.tasks:
                return False  # Dependency not found
            
            dep_task = self.tasks[dep_id]
            
            if dep_task.status not in [TaskStatus.COMPLETED]:
                return False  # Dependency not completed
        
        return True
    
    def _can_execute_task(self, task: AutomationTask) -> bool:
        """Check if task can be executed (resources available)"""
        # Check scheduled time
        if task.scheduled_time and datetime.now() < task.scheduled_time:
            return False
        
        # Check deadline
        if task.deadline and datetime.now() > task.deadline:
            task.status = TaskStatus.FAILED
            task.error = Exception("Task deadline exceeded")
            return False
        
        # Check resource availability
        if not self.resource_manager.can_allocate_resources(task.resource_requirements):
            return False
        
        return True
    
    def _calculate_priority_score(self, task: AutomationTask) -> float:
        """Calculate dynamic priority score for task"""
        base_score = float(task.priority.value)
        
        # Adjust for deadline urgency
        if task.deadline:
            time_remaining = (task.deadline - datetime.now()).total_seconds()
            if time_remaining < 3600:  # Less than 1 hour
                base_score -= 0.5
        
        # Adjust for waiting time
        wait_time = (datetime.now() - task.created_time).total_seconds()
        age_factor = min(wait_time / 3600, 2.0)  # Up to 2 hours impact
        base_score -= age_factor * 0.1
        
        # Adjust for retry count (failed tasks get lower priority)
        base_score += task.metrics.retry_count * 0.2
        
        return base_score
    
    def _check_dependent_tasks(self, completed_task_id: str):
        """Check and queue dependent tasks that are now ready"""
        dependents = self.task_dependents.get(completed_task_id, set())
        
        for dependent_id in dependents:
            if dependent_id in self.tasks:
                dependent_task = self.tasks[dependent_id]
                
                if (dependent_task.status == TaskStatus.PENDING and 
                    self._can_queue_task(dependent_task)):
                    
                    # Add to queue
                    dependent_task.status = TaskStatus.QUEUED
                    priority_score = self._calculate_priority_score(dependent_task)
                    self.priority_queues[dependent_task.priority].put(
                        (priority_score, time.time(), dependent_id)
                    )
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        with self._queue_lock:
            queue_sizes = {}
            for priority in TaskPriority:
                queue_sizes[priority.name] = self.priority_queues[priority].qsize()
            
            return {
                'queue_sizes': queue_sizes,
                'total_tasks': len(self.tasks),
                'running_tasks': len(self.running_tasks),
                'pending_tasks': len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
                'completed_tasks': len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]),
                'failed_tasks': len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED])
            }

class TaskExecutor:
    """
    Executes automation tasks with intelligent resource management
    """
    
    def __init__(self, task_queue: TaskQueue, max_workers: int = None):
        self.task_queue = task_queue
        self.logger = logging.getLogger(__name__)
        
        # Worker configuration
        self.max_workers = max_workers or min(32, (psutil.cpu_count() or 1) + 4)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Execution tracking
        self.active_executions: Dict[str, ExecutionContext] = {}
        self.execution_futures: Dict[str, concurrent.futures.Future] = {}
        
        # Execution control
        self.running = False
        self.coordinator_thread = None
        
    def start(self):
        """Start task execution"""
        if self.running:
            return
        
        self.running = True
        self.coordinator_thread = threading.Thread(target=self._execution_coordinator, daemon=True)
        self.coordinator_thread.start()
        self.logger.info(f"Task executor started with {self.max_workers} workers")
    
    def stop(self):
        """Stop task execution"""
        self.running = False
        
        if self.coordinator_thread:
            self.coordinator_thread.join(timeout=5.0)
        
        # Cancel pending futures
        for future in self.execution_futures.values():
            future.cancel()
        
        self.executor.shutdown(wait=True)
        self.logger.info("Task executor stopped")
    
    def _execution_coordinator(self):
        """Coordinate task execution"""
        while self.running:
            try:
                # Get next task from queue
                task = self.task_queue.get_next_task()
                
                if task:
                    self._execute_task_async(task)
                else:
                    time.sleep(0.1)  # No tasks available, wait
                
                # Clean up completed executions
                self._cleanup_completed_executions()
                
            except Exception as e:
                self.logger.error(f"Execution coordinator error: {e}")
                time.sleep(1.0)
    
    def _execute_task_async(self, task: AutomationTask):
        """Execute task asynchronously"""
        try:
            # Create execution context
            context = ExecutionContext(
                task_id=task.id,
                executor_id=str(uuid.uuid4()),
                thread_id=threading.get_ident(),
                start_time=datetime.now(),
                allocated_resources={}
            )
            
            self.active_executions[task.id] = context
            
            # Submit task for execution
            future = self.executor.submit(self._execute_task, task, context)
            self.execution_futures[task.id] = future
            
            # Add completion callback
            future.add_done_callback(lambda f: self._task_completion_callback(task.id, f))
            
        except Exception as e:
            self.logger.error(f"Failed to start task execution {task.name}: {e}")
            self.task_queue.complete_task(task.id, error=e)
    
    def _execute_task(self, task: AutomationTask, context: ExecutionContext) -> Any:
        """Execute single task"""
        self.logger.info(f"Executing task: {task.name}")
        
        try:
            # Set up execution environment
            original_cwd = None
            if 'working_directory' in task.parameters:
                import os
                original_cwd = os.getcwd()
                os.chdir(task.parameters['working_directory'])
            
            # Record start metrics
            start_cpu = psutil.cpu_percent()
            start_memory = psutil.virtual_memory().percent
            
            # Execute task function
            if task.execution_mode == ExecutionMode.SEQUENTIAL:
                result = self._execute_sequential(task)
            elif task.execution_mode == ExecutionMode.PARALLEL:
                result = self._execute_parallel(task)
            elif task.execution_mode == ExecutionMode.BATCH:
                result = self._execute_batch(task)
            elif task.execution_mode == ExecutionMode.STREAMING:
                result = self._execute_streaming(task)
            else:
                result = task.function(**task.parameters)
            
            # Record end metrics
            end_cpu = psutil.cpu_percent()
            end_memory = psutil.virtual_memory().percent
            
            task.metrics.cpu_usage = end_cpu - start_cpu
            task.metrics.memory_usage = end_memory - start_memory
            
            # Restore environment
            if original_cwd:
                import os
                os.chdir(original_cwd)
            
            self.logger.info(f"Task {task.name} completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Task {task.name} failed: {e}")
            raise e
    
    def _execute_sequential(self, task: AutomationTask) -> Any:
        """Execute task in sequential mode"""
        return task.function(**task.parameters)
    
    def _execute_parallel(self, task: AutomationTask) -> Any:
        """Execute task in parallel mode"""
        # For parallel execution, task function should handle its own parallelization
        return task.function(**task.parameters)
    
    def _execute_batch(self, task: AutomationTask) -> Any:
        """Execute task in batch mode"""
        # Batch mode processes multiple items
        batch_items = task.parameters.get('batch_items', [])
        batch_function = task.function
        
        results = []
        for item in batch_items:
            if isinstance(item, dict):
                result = batch_function(**item)
            else:
                result = batch_function(item)
            results.append(result)
        
        return results
    
    def _execute_streaming(self, task: AutomationTask) -> Any:
        """Execute task in streaming mode"""
        # Streaming mode processes data as it arrives
        return task.function(**task.parameters)
    
    def _task_completion_callback(self, task_id: str, future: concurrent.futures.Future):
        """Handle task completion"""
        try:
            if future.cancelled():
                self.task_queue.complete_task(task_id, error=Exception("Task cancelled"))
            elif future.exception():
                self.task_queue.complete_task(task_id, error=future.exception())
            else:
                result = future.result()
                self.task_queue.complete_task(task_id, result=result)
                
        except Exception as e:
            self.logger.error(f"Task completion callback error: {e}")
            self.task_queue.complete_task(task_id, error=e)
    
    def _cleanup_completed_executions(self):
        """Clean up completed task executions"""
        completed_tasks = []
        
        for task_id, future in self.execution_futures.items():
            if future.done():
                completed_tasks.append(task_id)
        
        for task_id in completed_tasks:
            if task_id in self.execution_futures:
                del self.execution_futures[task_id]
            
            if task_id in self.active_executions:
                del self.active_executions[task_id]

class AutomationOrchestrator:
    """
    Main automation orchestration layer that coordinates all automation subsystems
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.resource_manager = ResourceManager()
        self.task_queue = TaskQueue(self.resource_manager)
        self.task_executor = TaskExecutor(self.task_queue)
        
        # State management
        self.running = False
        self.statistics = {
            'tasks_created': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'total_execution_time': 0.0,
            'average_execution_time': 0.0
        }
        
        # Database for persistence
        self.db_path = self.config.get('db_path', 'user_data/automation_orchestrator.db')
        self._init_database()
        
        self.logger.info("Automation orchestrator initialized")
    
    def start(self):
        """Start automation orchestration"""
        if self.running:
            return
        
        self.running = True
        self.task_executor.start()
        self.logger.info("Automation orchestrator started")
    
    def stop(self):
        """Stop automation orchestration"""
        if not self.running:
            return
        
        self.running = False
        self.task_executor.stop()
        self.resource_manager.stop_monitoring()
        self.logger.info("Automation orchestrator stopped")
    
    def submit_task(self, 
                   name: str,
                   function: Callable,
                   parameters: Dict[str, Any] = None,
                   priority: TaskPriority = TaskPriority.NORMAL,
                   resource_requirements: ResourceRequirements = None,
                   dependencies: List[str] = None,
                   deadline: datetime = None,
                   tags: List[str] = None) -> str:
        """
        Submit automation task for execution
        
        Args:
            name: Task name
            function: Function to execute
            parameters: Function parameters
            priority: Task priority
            resource_requirements: Resource requirements
            dependencies: List of task IDs this task depends on
            deadline: Task deadline
            tags: Task tags for categorization
            
        Returns:
            Task ID
        """
        try:
            # Generate unique task ID
            task_id = str(uuid.uuid4())
            
            # Create task dependencies
            task_dependencies = []
            if dependencies:
                for dep_id in dependencies:
                    task_dependencies.append(TaskDependency(task_id=dep_id))
            
            # Create automation task
            task = AutomationTask(
                id=task_id,
                name=name,
                function=function,
                parameters=parameters or {},
                priority=priority,
                resource_requirements=resource_requirements or ResourceRequirements(),
                dependencies=task_dependencies,
                deadline=deadline,
                tags=tags or [],
                description=f"Automated task: {name}"
            )
            
            # Add to queue
            if self.task_queue.add_task(task):
                self.statistics['tasks_created'] += 1
                self._save_task(task)
                
                self.logger.info(f"Task '{name}' submitted with ID {task_id}")
                return task_id
            else:
                raise Exception("Failed to add task to queue")
                
        except Exception as e:
            self.logger.error(f"Failed to submit task '{name}': {e}")
            raise e
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status and details"""
        if task_id in self.task_queue.tasks:
            task = self.task_queue.tasks[task_id]
            
            return {
                'id': task.id,
                'name': task.name,
                'status': task.status.value,
                'priority': task.priority.value,
                'created_time': task.created_time.isoformat(),
                'updated_time': task.updated_time.isoformat(),
                'execution_time': task.metrics.end_time - task.metrics.start_time if task.metrics.end_time else None,
                'retry_count': task.metrics.retry_count,
                'error': str(task.error) if task.error else None,
                'result_available': task.result is not None,
                'tags': task.tags
            }
        
        return {'error': 'Task not found'}
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel pending or running task"""
        try:
            if task_id in self.task_queue.tasks:
                task = self.task_queue.tasks[task_id]
                
                if task.status in [TaskStatus.PENDING, TaskStatus.QUEUED]:
                    task.status = TaskStatus.CANCELLED
                    task.updated_time = datetime.now()
                    return True
                elif task.status == TaskStatus.RUNNING:
                    # Try to cancel running task
                    if task_id in self.task_executor.execution_futures:
                        future = self.task_executor.execution_futures[task_id]
                        return future.cancel()
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to cancel task {task_id}: {e}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        resources = self.resource_manager.get_current_resources()
        queue_status = self.task_queue.get_queue_status()
        
        return {
            'orchestrator_running': self.running,
            'system_resources': {
                'cpu_percent': resources.cpu_percent,
                'memory_percent': resources.memory_percent,
                'memory_available_mb': resources.memory_available_mb,
                'disk_usage_percent': resources.disk_usage_percent,
                'disk_free_gb': resources.disk_free_gb,
                'gpu_usage_percent': resources.gpu_usage_percent
            },
            'task_queue': queue_status,
            'statistics': self.statistics,
            'active_workers': len(self.task_executor.active_executions),
            'max_workers': self.task_executor.max_workers
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics and analytics"""
        # Get resource history
        resource_history = self.resource_manager.get_resource_history(60)
        
        if resource_history:
            avg_cpu = sum(r.cpu_percent for r in resource_history) / len(resource_history)
            avg_memory = sum(r.memory_percent for r in resource_history) / len(resource_history)
            max_cpu = max(r.cpu_percent for r in resource_history)
            max_memory = max(r.memory_percent for r in resource_history)
        else:
            avg_cpu = avg_memory = max_cpu = max_memory = 0.0
        
        # Task performance
        completed_tasks = [t for t in self.task_queue.tasks.values() if t.status == TaskStatus.COMPLETED]
        failed_tasks = [t for t in self.task_queue.tasks.values() if t.status == TaskStatus.FAILED]
        
        if completed_tasks:
            avg_execution_time = sum(
                (t.metrics.end_time - t.metrics.start_time) for t in completed_tasks
                if t.metrics.end_time and t.metrics.start_time
            ) / len(completed_tasks)
        else:
            avg_execution_time = 0.0
        
        return {
            'resource_utilization': {
                'average_cpu_percent': avg_cpu,
                'average_memory_percent': avg_memory,
                'peak_cpu_percent': max_cpu,
                'peak_memory_percent': max_memory
            },
            'task_performance': {
                'total_tasks': len(self.task_queue.tasks),
                'completed_tasks': len(completed_tasks),
                'failed_tasks': len(failed_tasks),
                'success_rate': len(completed_tasks) / len(self.task_queue.tasks) if self.task_queue.tasks else 0.0,
                'average_execution_time': avg_execution_time
            },
            'queue_efficiency': {
                'pending_tasks': len([t for t in self.task_queue.tasks.values() if t.status == TaskStatus.PENDING]),
                'running_tasks': len([t for t in self.task_queue.tasks.values() if t.status == TaskStatus.RUNNING]),
                'worker_utilization': len(self.task_executor.active_executions) / self.task_executor.max_workers
            }
        }
    
    def _init_database(self):
        """Initialize SQLite database for persistence"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS automation_tasks (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        priority INTEGER NOT NULL,
                        created_time TEXT NOT NULL,
                        updated_time TEXT NOT NULL,
                        parameters TEXT,
                        result TEXT,
                        error TEXT,
                        metrics TEXT,
                        tags TEXT
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        timestamp TEXT PRIMARY KEY,
                        cpu_percent REAL,
                        memory_percent REAL,
                        disk_percent REAL,
                        gpu_percent REAL,
                        active_tasks INTEGER
                    )
                ''')
                
        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
    
    def _save_task(self, task: AutomationTask):
        """Save task to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO automation_tasks 
                    (id, name, status, priority, created_time, updated_time, parameters, result, error, metrics, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.id,
                    task.name,
                    task.status.value,
                    task.priority.value,
                    task.created_time.isoformat(),
                    task.updated_time.isoformat(),
                    json.dumps(task.parameters),
                    json.dumps(task.result) if task.result else None,
                    str(task.error) if task.error else None,
                    json.dumps(task.metrics.__dict__),
                    json.dumps(task.tags)
                ))
                
        except Exception as e:
            self.logger.error(f"Failed to save task {task.id}: {e}")


# Factory functions for easy instantiation
def create_automation_orchestrator(config: Dict[str, Any] = None) -> AutomationOrchestrator:
    """Create and configure automation orchestrator"""
    return AutomationOrchestrator(config)

def create_automation_task(name: str, function: Callable, **kwargs) -> AutomationTask:
    """Create automation task with default settings"""
    return AutomationTask(
        id=str(uuid.uuid4()),
        name=name,
        function=function,
        **kwargs
    )

# Convenience functions
def quick_submit_task(orchestrator: AutomationOrchestrator, 
                     name: str, 
                     function: Callable, 
                     **kwargs) -> str:
    """Quick task submission"""
    return orchestrator.submit_task(name, function, **kwargs)

def get_orchestrator_status(orchestrator: AutomationOrchestrator) -> Dict[str, Any]:
    """Get orchestrator status summary"""
    return orchestrator.get_system_status()