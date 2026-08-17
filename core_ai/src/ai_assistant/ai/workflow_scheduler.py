"""
Workflow Scheduler with Reinforcement Learning
Learns optimal timing and ordering of automated tasks

Features:
- Task dependency modeling
- RL-based scheduling optimization
- Resource-aware scheduling
- Adaptive learning from outcomes
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
from collections import defaultdict, deque
import random

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class WorkflowScheduler:
    """
    RL-powered workflow scheduler
    """
    
    def __init__(self, db_path: str = "data/workflow_scheduler.db",
                 learning_rate: float = 0.1,
                 discount_factor: float = 0.9):
        self.db_path = db_path
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Q-learning table: state-action values
        self.q_table = defaultdict(lambda: defaultdict(float))
        
        # Task registry
        self.tasks = {}
        self.task_dependencies = defaultdict(set)
        
        self._init_database()
        self._load_tasks()
        self._load_q_values()
    
    def _init_database(self):
        """Initialize database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,
                    estimated_duration INTEGER NOT NULL,
                    resource_requirements TEXT,
                    dependencies TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    schedule_id TEXT NOT NULL,
                    task_sequence TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    total_duration INTEGER,
                    success_rate REAL,
                    reward REAL,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    scheduled_time TEXT NOT NULL,
                    actual_start TEXT,
                    actual_end TEXT,
                    duration INTEGER,
                    success INTEGER NOT NULL,
                    error_message TEXT,
                    resource_usage TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS q_values (
                    state TEXT NOT NULL,
                    action TEXT NOT NULL,
                    q_value REAL NOT NULL,
                    visit_count INTEGER DEFAULT 1,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (state, action)
                )
            """)
    
    def _load_tasks(self):
        """Load registered tasks"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT task_id, name, category, priority, estimated_duration,
                       resource_requirements, dependencies
                FROM tasks
            """)
            
            for row in cursor.fetchall():
                task_id, name, cat, priority, duration, resources_json, deps_json = row
                
                self.tasks[task_id] = {
                    'name': name,
                    'category': cat,
                    'priority': priority,
                    'estimated_duration': duration,
                    'resources': json.loads(resources_json) if resources_json else {}
                }
                
                if deps_json:
                    self.task_dependencies[task_id] = set(json.loads(deps_json))
    
    def _load_q_values(self):
        """Load Q-learning values"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT state, action, q_value
                FROM q_values
            """)
            
            for row in cursor.fetchall():
                state, action, q_value = row
                self.q_table[state][action] = q_value
    
    def register_task(self, task_id: str, name: str, category: str,
                     estimated_duration: int, priority: int = 5,
                     resource_requirements: Optional[Dict] = None,
                     dependencies: Optional[List[str]] = None):
        """Register a new task"""
        self.tasks[task_id] = {
            'name': name,
            'category': category,
            'priority': priority,
            'estimated_duration': estimated_duration,
            'resources': resource_requirements or {}
        }
        
        if dependencies:
            self.task_dependencies[task_id] = set(dependencies)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tasks
                (task_id, name, category, priority, estimated_duration,
                 resource_requirements, dependencies, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task_id, name, category, priority, estimated_duration,
                json.dumps(resource_requirements or {}),
                json.dumps(dependencies or []),
                datetime.now().isoformat()
            ))
    
    def get_state(self, pending_tasks: Set[str], 
                  current_time: datetime,
                  resources_available: Dict) -> str:
        """
        Get current state representation for RL
        State = (pending_tasks, time_of_day, resources)
        """
        # Simplify state space
        hour = current_time.hour
        time_category = 'morning' if 6 <= hour < 12 else 'afternoon' if 12 <= hour < 18 else 'evening'
        
        # Categorize pending tasks
        categories = set()
        for task_id in pending_tasks:
            if task_id in self.tasks:
                categories.add(self.tasks[task_id]['category'])
        
        # Resource availability
        cpu_available = resources_available.get('cpu', 1.0) > 0.5
        memory_available = resources_available.get('memory', 1.0) > 0.5
        
        state = f"{time_category}_{','.join(sorted(categories))}_{int(cpu_available)}_{int(memory_available)}"
        
        return state
    
    def get_valid_actions(self, pending_tasks: Set[str], 
                         completed_tasks: Set[str]) -> List[str]:
        """Get tasks that can be scheduled (dependencies met)"""
        valid = []
        
        for task_id in pending_tasks:
            # Check if dependencies are satisfied
            deps = self.task_dependencies.get(task_id, set())
            
            if deps.issubset(completed_tasks):
                valid.append(task_id)
        
        return valid
    
    def select_action(self, state: str, valid_actions: List[str],
                     epsilon: float = 0.1) -> str:
        """
        Select action using epsilon-greedy policy
        
        Args:
            state: Current state
            valid_actions: List of valid task IDs
            epsilon: Exploration rate
        """
        if not valid_actions:
            return None
        
        # Exploration
        if random.random() < epsilon:
            return random.choice(valid_actions)
        
        # Exploitation: select best Q-value
        q_values = {action: self.q_table[state][action] for action in valid_actions}
        
        if not q_values or all(v == 0 for v in q_values.values()):
            # No learned values, use priority
            return max(valid_actions, key=lambda a: self.tasks.get(a, {}).get('priority', 0))
        
        return max(q_values.items(), key=lambda x: x[1])[0]
    
    def update_q_value(self, state: str, action: str, reward: float,
                      next_state: str, next_valid_actions: List[str]):
        """Update Q-value using Q-learning"""
        # Q(s,a) = Q(s,a) + α[r + γ max Q(s',a') - Q(s,a)]
        
        current_q = self.q_table[state][action]
        
        # Find max Q-value for next state
        if next_valid_actions:
            max_next_q = max(self.q_table[next_state][a] for a in next_valid_actions)
        else:
            max_next_q = 0
        
        # Update rule
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        self.q_table[state][action] = new_q
        
        # Save to database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO q_values
                (state, action, q_value, last_updated)
                VALUES (?, ?, ?, ?)
            """, (state, action, new_q, datetime.now().isoformat()))
    
    def schedule_workflow(self, task_ids: List[str],
                         resources: Optional[Dict] = None,
                         epsilon: float = 0.1) -> List[Dict]:
        """
        Generate optimal schedule using RL
        
        Returns:
            List of scheduled tasks with timing
        """
        if resources is None:
            resources = {'cpu': 1.0, 'memory': 1.0}
        
        pending = set(task_ids)
        completed = set()
        schedule = []
        
        current_time = datetime.now()
        
        while pending:
            # Get state
            state = self.get_state(pending, current_time, resources)
            
            # Get valid actions
            valid_actions = self.get_valid_actions(pending, completed)
            
            if not valid_actions:
                # Deadlock or circular dependency
                break
            
            # Select action
            task_id = self.select_action(state, valid_actions, epsilon)
            
            if task_id is None:
                break
            
            # Schedule task
            task_info = self.tasks.get(task_id, {})
            duration = task_info.get('estimated_duration', 60)
            
            schedule.append({
                'task_id': task_id,
                'name': task_info.get('name', task_id),
                'scheduled_time': current_time.isoformat(),
                'estimated_duration': duration,
                'priority': task_info.get('priority', 5)
            })
            
            # Update state
            pending.remove(task_id)
            completed.add(task_id)
            current_time += timedelta(seconds=duration)
            
            # Simulate resource consumption
            task_resources = task_info.get('resources', {})
            for resource, amount in task_resources.items():
                if resource in resources:
                    resources[resource] = max(0, resources[resource] - amount)
        
        # Save schedule
        self._save_schedule(schedule)
        
        return schedule
    
    def _save_schedule(self, schedule: List[Dict]):
        """Save generated schedule"""
        schedule_id = f"schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO schedules
                (schedule_id, task_sequence, start_time, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                schedule_id,
                json.dumps([t['task_id'] for t in schedule]),
                schedule[0]['scheduled_time'] if schedule else datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
    
    def record_execution(self, task_id: str, scheduled_time: str,
                        actual_duration: int, success: bool,
                        error_message: Optional[str] = None):
        """Record task execution outcome"""
        reward = 10.0 if success else -5.0
        
        # Adjust reward based on duration accuracy
        task_info = self.tasks.get(task_id, {})
        estimated = task_info.get('estimated_duration', actual_duration)
        
        accuracy = 1 - abs(actual_duration - estimated) / max(estimated, 1)
        reward *= accuracy
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO task_executions
                (task_id, scheduled_time, duration, success, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                scheduled_time,
                actual_duration,
                1 if success else 0,
                error_message,
                datetime.now().isoformat()
            ))
        
        return reward
    
    def get_stats(self) -> Dict:
        """Get scheduler statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_tasks,
                    (SELECT COUNT(*) FROM schedules) as total_schedules,
                    (SELECT COUNT(*) FROM task_executions WHERE success=1) as successful,
                    (SELECT COUNT(*) FROM task_executions WHERE success=0) as failed
                FROM tasks
            """)
            
            row = cursor.fetchone()
            if row:
                total_tasks, schedules, successful, failed = row
                return {
                    'total_tasks': total_tasks or 0,
                    'total_schedules': schedules or 0,
                    'successful_executions': successful or 0,
                    'failed_executions': failed or 0,
                    'success_rate': successful / (successful + failed) if (successful + failed) > 0 else 0,
                    'learned_states': len(self.q_table)
                }
        
        return {}


def example_usage():
    """Demonstrate workflow scheduler"""
    scheduler = WorkflowScheduler()
    
    print("Workflow Scheduler Demo\n" + "="*50)
    
    # Register tasks
    print("\n1. Registering tasks...")
    
    scheduler.register_task('backup', 'Database Backup', 'maintenance',
                           estimated_duration=300, priority=8)
    
    scheduler.register_task('report', 'Generate Report', 'reporting',
                           estimated_duration=120, priority=6,
                           dependencies=['backup'])
    
    scheduler.register_task('notify', 'Send Notifications', 'communication',
                           estimated_duration=30, priority=7,
                           dependencies=['report'])
    
    scheduler.register_task('cleanup', 'Cleanup Logs', 'maintenance',
                           estimated_duration=60, priority=4)
    
    print(f"  Registered {len(scheduler.tasks)} tasks")
    
    # Generate schedule
    print("\n2. Generating optimal schedule...")
    
    schedule = scheduler.schedule_workflow(
        ['backup', 'report', 'notify', 'cleanup'],
        resources={'cpu': 1.0, 'memory': 1.0}
    )
    
    print(f"  Generated schedule with {len(schedule)} tasks:")
    for i, task in enumerate(schedule, 1):
        print(f"    {i}. {task['name']} @ {task['scheduled_time'][:19]} ({task['estimated_duration']}s)")
    
    # Simulate executions
    print("\n3. Simulating task executions...")
    for task in schedule[:2]:
        success = random.random() > 0.2  # 80% success rate
        duration = task['estimated_duration'] + random.randint(-10, 30)
        
        reward = scheduler.record_execution(
            task['task_id'],
            task['scheduled_time'],
            duration,
            success
        )
        
        status = "✓" if success else "✗"
        print(f"  {status} {task['name']}: {duration}s (reward: {reward:.1f})")
    
    # Stats
    stats = scheduler.get_stats()
    print(f"\n4. Statistics:")
    print(f"  Total tasks: {stats['total_tasks']}")
    print(f"  Schedules generated: {stats['total_schedules']}")
    print(f"  Success rate: {stats['success_rate']:.1%}")
    print(f"  Learned states: {stats['learned_states']}")


if __name__ == "__main__":
    example_usage()
