"""
Main Automation Interface

This module provides the unified interface for the automation system, including
web dashboard, CLI tools, API endpoints, and comprehensive management capabilities.

Features:
- Unified automation API
- Web-based dashboard
- Command-line interface
- Task management interface
- System configuration
- Monitoring and reporting
- Integration management
- User interface components
"""

import os
import json
import logging
import threading
import time
import asyncio
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import uuid

# Web framework
try:
    from flask import Flask, request, jsonify, render_template, session
    from flask_socketio import SocketIO, emit
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# CLI framework
try:
    import click
    CLICK_AVAILABLE = True
except ImportError:
    CLICK_AVAILABLE = False

# Import our automation components
from .orchestrator import AutomationOrchestrator
from .task_scheduler import AdvancedTaskScheduler
from .rule_engine import AutomationRuleEngine
from .analytics import AutomationAnalytics
from .templates import AutomationTemplates
from .context_aware import ContextAwareAutomation
from .security import AutomationSecurity, ResourceType, PermissionType, SecurityLevel

@dataclass
class AutomationStatus:
    """Overall automation system status"""
    active: bool = False
    total_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    scheduled_tasks: int = 0
    
    # Performance metrics
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    avg_response_time: float = 0.0
    
    # Components status
    orchestrator_active: bool = False
    scheduler_active: bool = False
    rules_active: bool = False
    analytics_active: bool = False
    templates_active: bool = False
    context_aware_active: bool = False
    security_active: bool = False
    
    # Last update time
    last_update: datetime = None

@dataclass
class AutomationConfig:
    """Automation system configuration"""
    # Core settings
    max_concurrent_tasks: int = 10
    task_timeout_seconds: int = 3600
    retry_attempts: int = 3
    
    # Scheduler settings
    scheduler_interval: int = 60
    enable_schedule_optimization: bool = True
    
    # Security settings
    enable_security: bool = True
    session_timeout_hours: int = 8
    max_failed_logins: int = 5
    
    # Analytics settings
    enable_analytics: bool = True
    metrics_retention_days: int = 30
    
    # Context-aware settings
    enable_context_awareness: bool = True
    context_update_interval: int = 300  # 5 minutes
    
    # Web interface settings
    web_host: str = "127.0.0.1"
    web_port: int = 8080
    enable_web_interface: bool = True
    
    # API settings
    enable_api: bool = True
    api_rate_limit: int = 1000  # requests per hour
    
    # File paths
    data_directory: str = "user_data/automation"
    log_directory: str = "logs/automation"
    backup_directory: str = "backups/automation"

class AutomationAPI:
    """
    RESTful API interface for automation system
    """
    
    def __init__(self, automation_manager):
        self.automation_manager = automation_manager
        self.logger = logging.getLogger(__name__)
        
        if FLASK_AVAILABLE:
            self.app = Flask(__name__)
            self.app.secret_key = os.environ.get('AUTOMATION_SECRET_KEY', 'dev-key-change-me')
            self.socketio = SocketIO(self.app, cors_allowed_origins="*")
            self._setup_routes()
        else:
            self.app = None
            self.socketio = None
            self.logger.warning("Flask not available - web API disabled")
    
    def _setup_routes(self):
        """Setup API routes"""
        
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """Get system status"""
            try:
                status = self.automation_manager.get_status()
                return jsonify(asdict(status))
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/tasks', methods=['GET'])
        def list_tasks():
            """List all tasks"""
            try:
                tasks = self.automation_manager.list_tasks()
                return jsonify(tasks)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/tasks', methods=['POST'])
        def create_task():
            """Create new task"""
            try:
                task_data = request.json
                task_id = self.automation_manager.create_task(task_data)
                return jsonify({'task_id': task_id})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/tasks/<task_id>', methods=['GET'])
        def get_task(task_id):
            """Get task details"""
            try:
                task = self.automation_manager.get_task(task_id)
                if task:
                    return jsonify(task)
                else:
                    return jsonify({'error': 'Task not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/tasks/<task_id>/execute', methods=['POST'])
        def execute_task(task_id):
            """Execute task"""
            try:
                result = self.automation_manager.execute_task(task_id)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/tasks/<task_id>', methods=['DELETE'])
        def delete_task(task_id):
            """Delete task"""
            try:
                success = self.automation_manager.delete_task(task_id)
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/schedules', methods=['GET'])
        def list_schedules():
            """List all schedules"""
            try:
                schedules = self.automation_manager.list_schedules()
                return jsonify(schedules)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/schedules', methods=['POST'])
        def create_schedule():
            """Create new schedule"""
            try:
                schedule_data = request.json
                schedule_id = self.automation_manager.create_schedule(schedule_data)
                return jsonify({'schedule_id': schedule_id})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/templates', methods=['GET'])
        def list_templates():
            """List automation templates"""
            try:
                templates = self.automation_manager.list_templates()
                return jsonify(templates)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/templates/<template_id>/instantiate', methods=['POST'])
        def instantiate_template(template_id):
            """Instantiate template"""
            try:
                parameters = request.json
                task_id = self.automation_manager.instantiate_template(template_id, parameters)
                return jsonify({'task_id': task_id})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/analytics/metrics', methods=['GET'])
        def get_metrics():
            """Get analytics metrics"""
            try:
                metrics = self.automation_manager.get_analytics_metrics()
                return jsonify(metrics)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/analytics/reports/<report_type>', methods=['GET'])
        def get_report(report_type):
            """Get analytics report"""
            try:
                report = self.automation_manager.get_report(report_type)
                return jsonify(report)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/context', methods=['GET'])
        def get_context():
            """Get current context information"""
            try:
                context = self.automation_manager.get_context_info()
                return jsonify(context)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/security/dashboard', methods=['GET'])
        def security_dashboard():
            """Get security dashboard"""
            try:
                dashboard = self.automation_manager.get_security_dashboard()
                return jsonify(dashboard)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/auth/login', methods=['POST'])
        def login():
            """User login"""
            try:
                credentials = request.json
                session_id = self.automation_manager.authenticate_user(
                    credentials.get('username'),
                    credentials.get('password'),
                    request.remote_addr,
                    request.headers.get('User-Agent')
                )
                if session_id:
                    return jsonify({'session_id': session_id})
                else:
                    return jsonify({'error': 'Authentication failed'}), 401
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/config', methods=['GET'])
        def get_config():
            """Get system configuration"""
            try:
                config = self.automation_manager.get_config()
                return jsonify(asdict(config))
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/config', methods=['POST'])
        def update_config():
            """Update system configuration"""
            try:
                config_data = request.json
                success = self.automation_manager.update_config(config_data)
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        # WebSocket events
        @self.socketio.on('connect')
        def handle_connect():
            """Handle WebSocket connection"""
            self.logger.info(f"WebSocket client connected: {request.sid}")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle WebSocket disconnection"""
            self.logger.info(f"WebSocket client disconnected: {request.sid}")
        
        @self.socketio.on('subscribe_status')
        def handle_subscribe_status():
            """Subscribe to status updates"""
            self.automation_manager.add_status_subscriber(request.sid)
        
        @self.socketio.on('unsubscribe_status')
        def handle_unsubscribe_status():
            """Unsubscribe from status updates"""
            self.automation_manager.remove_status_subscriber(request.sid)
    
    def run(self, host: str = '127.0.0.1', port: int = 8080, debug: bool = False):
        """Run the web API server"""
        if not self.app:
            self.logger.error("Flask not available - cannot run web API")
            return
        
        self.logger.info(f"Starting automation API server on {host}:{port}")
        self.socketio.run(self.app, host=host, port=port, debug=debug)

class AutomationCLI:
    """
    Command-line interface for automation system
    """
    
    def __init__(self, automation_manager):
        self.automation_manager = automation_manager
        self.logger = logging.getLogger(__name__)
        
        if CLICK_AVAILABLE:
            self._setup_commands()
        else:
            self.logger.warning("Click not available - CLI disabled")
    
    def _setup_commands(self):
        """Setup CLI commands"""
        
        @click.group()
        def automation():
            """Automation System CLI"""
            pass
        
        @automation.command()
        def status():
            """Show system status"""
            try:
                status = self.automation_manager.get_status()
                
                click.echo("=== Automation System Status ===")
                click.echo(f"System Active: {status.active}")
                click.echo(f"Total Tasks: {status.total_tasks}")
                click.echo(f"Running Tasks: {status.running_tasks}")
                click.echo(f"Completed Tasks: {status.completed_tasks}")
                click.echo(f"Failed Tasks: {status.failed_tasks}")
                click.echo(f"Scheduled Tasks: {status.scheduled_tasks}")
                click.echo()
                click.echo("Component Status:")
                click.echo(f"  Orchestrator: {status.orchestrator_active}")
                click.echo(f"  Scheduler: {status.scheduler_active}")
                click.echo(f"  Rules: {status.rules_active}")
                click.echo(f"  Analytics: {status.analytics_active}")
                click.echo(f"  Templates: {status.templates_active}")
                click.echo(f"  Context-Aware: {status.context_aware_active}")
                click.echo(f"  Security: {status.security_active}")
                
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
        
        @automation.command()
        def start():
            """Start automation system"""
            try:
                self.automation_manager.start()
                click.echo("Automation system started successfully")
            except Exception as e:
                click.echo(f"Error starting system: {e}", err=True)
        
        @automation.command()
        def stop():
            """Stop automation system"""
            try:
                self.automation_manager.stop()
                click.echo("Automation system stopped successfully")
            except Exception as e:
                click.echo(f"Error stopping system: {e}", err=True)
        
        @automation.group()
        def task():
            """Task management commands"""
            pass
        
        @task.command()
        def list():
            """List all tasks"""
            try:
                tasks = self.automation_manager.list_tasks()
                
                click.echo("=== Task List ===")
                for task in tasks:
                    status_emoji = {
                        'pending': '⏳',
                        'running': '🔄',
                        'completed': '✅',
                        'failed': '❌'
                    }.get(task.get('status', 'unknown'), '❓')
                    
                    click.echo(f"{status_emoji} {task.get('id', '')} - {task.get('name', 'Unnamed')} ({task.get('status', 'unknown')})")
                    
            except Exception as e:
                click.echo(f"Error listing tasks: {e}", err=True)
        
        @task.command()
        @click.argument('task_id')
        def show(task_id):
            """Show task details"""
            try:
                task = self.automation_manager.get_task(task_id)
                if task:
                    click.echo(f"=== Task Details: {task_id} ===")
                    click.echo(json.dumps(task, indent=2))
                else:
                    click.echo("Task not found", err=True)
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
        
        @task.command()
        @click.argument('task_id')
        def execute(task_id):
            """Execute a task"""
            try:
                result = self.automation_manager.execute_task(task_id)
                click.echo(f"Task execution result: {result}")
            except Exception as e:
                click.echo(f"Error executing task: {e}", err=True)
        
        @automation.group()
        def template():
            """Template management commands"""
            pass
        
        @template.command()
        def list():
            """List available templates"""
            try:
                templates = self.automation_manager.list_templates()
                
                click.echo("=== Available Templates ===")
                for template in templates:
                    click.echo(f"📋 {template.get('id', '')} - {template.get('name', 'Unnamed')}")
                    click.echo(f"   Description: {template.get('description', 'No description')}")
                    click.echo()
                    
            except Exception as e:
                click.echo(f"Error listing templates: {e}", err=True)
        
        @automation.group()
        def analytics():
            """Analytics commands"""
            pass
        
        @analytics.command()
        def metrics():
            """Show system metrics"""
            try:
                metrics = self.automation_manager.get_analytics_metrics()
                
                click.echo("=== System Metrics ===")
                click.echo(json.dumps(metrics, indent=2))
                
            except Exception as e:
                click.echo(f"Error getting metrics: {e}", err=True)
        
        @automation.command()
        @click.option('--host', default='127.0.0.1', help='Host to bind to')
        @click.option('--port', default=8080, help='Port to bind to')
        @click.option('--debug', is_flag=True, help='Enable debug mode')
        def serve(host, port, debug):
            """Start web interface"""
            try:
                self.automation_manager.start_web_interface(host, port, debug)
            except Exception as e:
                click.echo(f"Error starting web interface: {e}", err=True)
        
        self.cli = automation
    
    def run(self, args=None):
        """Run CLI"""
        if not CLICK_AVAILABLE:
            self.logger.error("Click not available - cannot run CLI")
            return
        
        self.cli(args)

class AutomationDashboard:
    """
    Web dashboard for automation system
    """
    
    def __init__(self, automation_manager):
        self.automation_manager = automation_manager
        self.logger = logging.getLogger(__name__)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get dashboard data"""
        try:
            status = self.automation_manager.get_status()
            metrics = self.automation_manager.get_analytics_metrics()
            context = self.automation_manager.get_context_info()
            security = self.automation_manager.get_security_dashboard()
            
            # Recent tasks
            recent_tasks = self.automation_manager.list_tasks(limit=10)
            
            # Upcoming schedules
            upcoming_schedules = self.automation_manager.list_schedules(limit=5, upcoming_only=True)
            
            return {
                'status': asdict(status),
                'metrics': metrics,
                'context': context,
                'security': security,
                'recent_tasks': recent_tasks,
                'upcoming_schedules': upcoming_schedules,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard data: {e}")
            return {'error': str(e)}

class AutomationManager:
    """
    Main automation system manager
    
    This is the central coordination point for all automation components.
    """
    
    def __init__(self, config: AutomationConfig = None):
        self.config = config or AutomationConfig()
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self.orchestrator = None
        self.scheduler = None
        self.rule_engine = None
        self.analytics = None
        self.templates = None
        self.context_aware = None
        self.security = None
        
        # Interface components
        self.api = None
        self.cli = None
        self.dashboard = None
        
        # State management
        self.active = False
        self.status_subscribers = set()
        self._lock = threading.RLock()
        
        # Initialize components
        self._initialize_components()
        
        # Status monitoring
        self._status_thread = None
        self._status_running = False
    
    def _initialize_components(self):
        """Initialize all automation components"""
        try:
            # Create data directories
            Path(self.config.data_directory).mkdir(parents=True, exist_ok=True)
            Path(self.config.log_directory).mkdir(parents=True, exist_ok=True)
            Path(self.config.backup_directory).mkdir(parents=True, exist_ok=True)
            
            # Initialize security first
            if self.config.enable_security:
                self.security = AutomationSecurity(
                    db_path=str(Path(self.config.data_directory) / "security.db")
                )
            
            # Initialize core components
            self.orchestrator = AutomationOrchestrator(
                max_workers=self.config.max_concurrent_tasks,
                db_path=str(Path(self.config.data_directory) / "orchestrator.db")
            )
            
            self.scheduler = AdvancedTaskScheduler(
                db_path=str(Path(self.config.data_directory) / "scheduler.db")
            )
            
            self.rule_engine = AutomationRuleEngine(
                db_path=str(Path(self.config.data_directory) / "rules.db")
            )
            
            if self.config.enable_analytics:
                self.analytics = AutomationAnalytics(
                    db_path=str(Path(self.config.data_directory) / "analytics.db")
                )
            
            self.templates = AutomationTemplates(
                db_path=str(Path(self.config.data_directory) / "templates.db")
            )
            
            if self.config.enable_context_awareness:
                self.context_aware = ContextAwareAutomation(
                    db_path=str(Path(self.config.data_directory) / "context.db")
                )
            
            # Initialize interface components
            self.api = AutomationAPI(self)
            self.cli = AutomationCLI(self)
            self.dashboard = AutomationDashboard(self)
            
            self.logger.info("Automation components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize automation components: {e}")
            raise e
    
    def start(self):
        """Start the automation system"""
        try:
            if self.active:
                self.logger.warning("Automation system is already active")
                return
            
            self.logger.info("Starting automation system...")
            
            # Start security first
            if self.security:
                self.security.start_security()
            
            # Start core components
            self.orchestrator.start()
            self.scheduler.start()
            self.rule_engine.start()
            
            if self.analytics:
                self.analytics.start()
            
            if self.templates:
                self.templates.start()
            
            if self.context_aware:
                self.context_aware.start()
            
            # Start status monitoring
            self._start_status_monitoring()
            
            self.active = True
            self.logger.info("Automation system started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start automation system: {e}")
            self.stop()  # Cleanup on failure
            raise e
    
    def stop(self):
        """Stop the automation system"""
        try:
            if not self.active:
                return
            
            self.logger.info("Stopping automation system...")
            
            # Stop status monitoring
            self._stop_status_monitoring()
            
            # Stop components in reverse order
            if self.context_aware:
                self.context_aware.stop()
            
            if self.templates:
                self.templates.stop()
            
            if self.analytics:
                self.analytics.stop()
            
            if self.rule_engine:
                self.rule_engine.stop()
            
            if self.scheduler:
                self.scheduler.stop()
            
            if self.orchestrator:
                self.orchestrator.stop()
            
            if self.security:
                self.security.stop_security()
            
            self.active = False
            self.logger.info("Automation system stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping automation system: {e}")
    
    def get_status(self) -> AutomationStatus:
        """Get current system status"""
        try:
            # Get basic task counts
            total_tasks = len(self.orchestrator.list_all_tasks()) if self.orchestrator else 0
            running_tasks = len(self.orchestrator.get_running_tasks()) if self.orchestrator else 0
            completed_tasks = len(self.orchestrator.get_completed_tasks()) if self.orchestrator else 0
            failed_tasks = len(self.orchestrator.get_failed_tasks()) if self.orchestrator else 0
            scheduled_tasks = len(self.scheduler.get_scheduled_tasks()) if self.scheduler else 0
            
            # Get performance metrics
            performance_metrics = {}
            if self.analytics:
                performance_metrics = self.analytics.get_current_metrics()
            
            status = AutomationStatus(
                active=self.active,
                total_tasks=total_tasks,
                running_tasks=running_tasks,
                completed_tasks=completed_tasks,
                failed_tasks=failed_tasks,
                scheduled_tasks=scheduled_tasks,
                
                cpu_usage=performance_metrics.get('cpu_usage', 0.0),
                memory_usage=performance_metrics.get('memory_usage', 0.0),
                avg_response_time=performance_metrics.get('avg_response_time', 0.0),
                
                orchestrator_active=self.orchestrator.is_active() if self.orchestrator else False,
                scheduler_active=self.scheduler.is_active() if self.scheduler else False,
                rules_active=self.rule_engine.is_active() if self.rule_engine else False,
                analytics_active=self.analytics.is_active() if self.analytics else False,
                templates_active=True,  # Templates are always active
                context_aware_active=self.context_aware.is_active() if self.context_aware else False,
                security_active=self.security.security_active if self.security else False,
                
                last_update=datetime.now()
            )
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return AutomationStatus(last_update=datetime.now())
    
    def create_task(self, task_data: Dict[str, Any]) -> str:
        """Create a new automation task"""
        if not self.orchestrator:
            raise Exception("Orchestrator not available")
        
        return self.orchestrator.create_task(
            name=task_data.get('name'),
            task_type=task_data.get('type'),
            config=task_data.get('config', {}),
            dependencies=task_data.get('dependencies', []),
            priority=task_data.get('priority', 1)
        )
    
    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a task"""
        if not self.orchestrator:
            raise Exception("Orchestrator not available")
        
        return self.orchestrator.execute_task(task_id)
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details"""
        if not self.orchestrator:
            return None
        
        return self.orchestrator.get_task_details(task_id)
    
    def list_tasks(self, limit: int = None, status_filter: str = None) -> List[Dict[str, Any]]:
        """List tasks with optional filtering"""
        if not self.orchestrator:
            return []
        
        tasks = self.orchestrator.list_all_tasks()
        
        # Apply status filter
        if status_filter:
            tasks = [t for t in tasks if t.get('status') == status_filter]
        
        # Apply limit
        if limit:
            tasks = tasks[:limit]
        
        return tasks
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task"""
        if not self.orchestrator:
            return False
        
        return self.orchestrator.delete_task(task_id)
    
    def create_schedule(self, schedule_data: Dict[str, Any]) -> str:
        """Create a new schedule"""
        if not self.scheduler:
            raise Exception("Scheduler not available")
        
        return self.scheduler.create_schedule(
            task_id=schedule_data.get('task_id'),
            cron_expression=schedule_data.get('cron_expression'),
            name=schedule_data.get('name'),
            description=schedule_data.get('description', ''),
            enabled=schedule_data.get('enabled', True)
        )
    
    def list_schedules(self, limit: int = None, upcoming_only: bool = False) -> List[Dict[str, Any]]:
        """List schedules"""
        if not self.scheduler:
            return []
        
        schedules = self.scheduler.list_schedules()
        
        # Apply filters
        if upcoming_only:
            schedules = [s for s in schedules if s.get('next_run')]
        
        if limit:
            schedules = schedules[:limit]
        
        return schedules
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List available templates"""
        if not self.templates:
            return []
        
        return self.templates.list_templates()
    
    def instantiate_template(self, template_id: str, parameters: Dict[str, Any]) -> str:
        """Instantiate a template"""
        if not self.templates or not self.orchestrator:
            raise Exception("Templates or orchestrator not available")
        
        workflow = self.templates.render_template(template_id, parameters)
        
        # Create tasks from workflow
        task_ids = []
        for step in workflow.get('steps', []):
            task_id = self.orchestrator.create_task(
                name=step.get('name'),
                task_type=step.get('type'),
                config=step.get('config', {}),
                dependencies=step.get('dependencies', [])
            )
            task_ids.append(task_id)
        
        return task_ids[0] if task_ids else None
    
    def get_analytics_metrics(self) -> Dict[str, Any]:
        """Get analytics metrics"""
        if not self.analytics:
            return {}
        
        return self.analytics.get_comprehensive_metrics()
    
    def get_report(self, report_type: str) -> Dict[str, Any]:
        """Generate analytics report"""
        if not self.analytics:
            return {}
        
        return self.analytics.generate_report(report_type)
    
    def get_context_info(self) -> Dict[str, Any]:
        """Get context information"""
        if not self.context_aware:
            return {}
        
        return self.context_aware.get_current_context()
    
    def get_security_dashboard(self) -> Dict[str, Any]:
        """Get security dashboard data"""
        if not self.security:
            return {'security_enabled': False}
        
        return self.security.get_security_dashboard()
    
    def authenticate_user(self, username: str, password: str, 
                         ip_address: str = None, user_agent: str = None) -> Optional[str]:
        """Authenticate user"""
        if not self.security:
            return None
        
        return self.security.authenticate(username, password, ip_address, user_agent)
    
    def get_config(self) -> AutomationConfig:
        """Get system configuration"""
        return self.config
    
    def update_config(self, config_data: Dict[str, Any]) -> bool:
        """Update system configuration"""
        try:
            for key, value in config_data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
            
            self.logger.info("Configuration updated successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update configuration: {e}")
            return False
    
    def start_web_interface(self, host: str = None, port: int = None, debug: bool = False):
        """Start web interface"""
        if not self.api or not self.api.app:
            raise Exception("Web interface not available")
        
        host = host or self.config.web_host
        port = port or self.config.web_port
        
        self.api.run(host, port, debug)
    
    def add_status_subscriber(self, subscriber_id: str):
        """Add status update subscriber"""
        with self._lock:
            self.status_subscribers.add(subscriber_id)
    
    def remove_status_subscriber(self, subscriber_id: str):
        """Remove status update subscriber"""
        with self._lock:
            self.status_subscribers.discard(subscriber_id)
    
    def _start_status_monitoring(self):
        """Start status monitoring thread"""
        self._status_running = True
        self._status_thread = threading.Thread(target=self._status_monitor_loop)
        self._status_thread.daemon = True
        self._status_thread.start()
    
    def _stop_status_monitoring(self):
        """Stop status monitoring thread"""
        self._status_running = False
        if self._status_thread:
            self._status_thread.join(timeout=5)
    
    def _status_monitor_loop(self):
        """Status monitoring loop"""
        while self._status_running:
            try:
                # Broadcast status to subscribers
                if self.status_subscribers and self.api and self.api.socketio:
                    status = self.get_status()
                    self.api.socketio.emit('status_update', asdict(status))
                
                time.sleep(5)  # Update every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Status monitoring error: {e}")
                time.sleep(10)

def create_automation_manager(config_path: str = None) -> AutomationManager:
    """Factory function to create automation manager"""
    
    # Load configuration
    config = AutomationConfig()
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            for key, value in config_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
                    
        except Exception as e:
            logging.getLogger(__name__).warning(f"Failed to load config from {config_path}: {e}")
    
    return AutomationManager(config)

# CLI Entry Point
def main():
    """Main CLI entry point"""
    import sys
    
    try:
        # Create automation manager
        manager = create_automation_manager()
        
        # Run CLI
        cli = AutomationCLI(manager)
        cli.run(sys.argv[1:])
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

if __name__ == "__main__":
    main()