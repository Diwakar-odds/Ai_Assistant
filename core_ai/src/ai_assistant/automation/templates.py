"""
Automation Templates System

This module provides pre-built templates for common automation workflows,
customizable patterns, and workflow libraries to accelerate automation development.

Features:
- Pre-built automation templates
- Template customization and parameterization
- Workflow pattern library
- Template inheritance and composition
- Dynamic template generation
- Template marketplace and sharing
- Validation and testing framework
"""

import json
import yaml
import re
import os
import uuid
import logging
import sqlite3
import threading
from typing import Dict, List, Optional, Any, Callable, Type, Union, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import inspect
import importlib
import copy

# Template validation
try:
    import cerberus
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False

# Template rendering
try:
    import jinja2
    TEMPLATE_RENDERING_AVAILABLE = True
except ImportError:
    TEMPLATE_RENDERING_AVAILABLE = False

class TemplateCategory(Enum):
    """Template categories"""
    FILE_OPERATIONS = "file_operations"
    DATA_PROCESSING = "data_processing"
    SYSTEM_MONITORING = "system_monitoring"
    NETWORK_AUTOMATION = "network_automation"
    DATABASE_OPERATIONS = "database_operations"
    API_INTEGRATION = "api_integration"
    WORKFLOW_ORCHESTRATION = "workflow_orchestration"
    NOTIFICATION_ALERTS = "notification_alerts"
    BACKUP_RECOVERY = "backup_recovery"
    SECURITY_COMPLIANCE = "security_compliance"
    CUSTOM = "custom"

class TemplateType(Enum):
    """Template types"""
    TASK_TEMPLATE = "task"          # Single task template
    WORKFLOW_TEMPLATE = "workflow"   # Multi-step workflow
    RULE_TEMPLATE = "rule"          # Rule-based automation
    SCHEDULE_TEMPLATE = "schedule"   # Scheduled automation
    EVENT_TEMPLATE = "event"        # Event-driven automation
    COMPOSITE_TEMPLATE = "composite" # Combination of templates

class ParameterType(Enum):
    """Parameter types for templates"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    FILE_PATH = "file_path"
    DIRECTORY_PATH = "directory_path"
    EMAIL = "email"
    URL = "url"
    REGEX = "regex"
    CRON_EXPRESSION = "cron_expression"
    JSON = "json"
    YAML = "yaml"

@dataclass
class TemplateParameter:
    """Template parameter definition"""
    name: str
    param_type: ParameterType
    description: str = ""
    default_value: Any = None
    required: bool = True
    validation_rules: Dict[str, Any] = field(default_factory=dict)
    choices: List[Any] = field(default_factory=list)
    sensitive: bool = False  # For passwords, API keys, etc.
    
    def validate(self, value: Any) -> Tuple[bool, str]:
        """Validate parameter value"""
        try:
            # Type validation
            if not self._validate_type(value):
                return False, f"Invalid type for parameter '{self.name}'"
            
            # Required validation
            if self.required and value is None:
                return False, f"Parameter '{self.name}' is required"
            
            # Choices validation
            if self.choices and value not in self.choices:
                return False, f"Parameter '{self.name}' must be one of {self.choices}"
            
            # Custom validation rules
            if self.validation_rules:
                if not self._validate_rules(value):
                    return False, f"Parameter '{self.name}' failed validation rules"
            
            return True, ""
            
        except Exception as e:
            return False, str(e)
    
    def _validate_type(self, value: Any) -> bool:
        """Validate parameter type"""
        if value is None and not self.required:
            return True
        
        if self.param_type == ParameterType.STRING:
            return isinstance(value, str)
        elif self.param_type == ParameterType.INTEGER:
            return isinstance(value, int)
        elif self.param_type == ParameterType.FLOAT:
            return isinstance(value, (int, float))
        elif self.param_type == ParameterType.BOOLEAN:
            return isinstance(value, bool)
        elif self.param_type == ParameterType.LIST:
            return isinstance(value, list)
        elif self.param_type == ParameterType.DICT:
            return isinstance(value, dict)
        elif self.param_type == ParameterType.FILE_PATH:
            return isinstance(value, str) and (Path(value).is_file() or not Path(value).exists())
        elif self.param_type == ParameterType.DIRECTORY_PATH:
            return isinstance(value, str) and (Path(value).is_dir() or not Path(value).exists())
        elif self.param_type == ParameterType.EMAIL:
            return isinstance(value, str) and "@" in value  # Simplified validation
        elif self.param_type == ParameterType.URL:
            return isinstance(value, str) and (value.startswith("http://") or value.startswith("https://"))
        elif self.param_type == ParameterType.REGEX:
            try:
                re.compile(value)
                return True
            except:
                return False
        elif self.param_type == ParameterType.JSON:
            try:
                json.loads(value) if isinstance(value, str) else json.dumps(value)
                return True
            except:
                return False
        
        return True
    
    def _validate_rules(self, value: Any) -> bool:
        """Validate custom rules"""
        try:
            # Length validation
            if 'min_length' in self.validation_rules:
                if len(str(value)) < self.validation_rules['min_length']:
                    return False
            
            if 'max_length' in self.validation_rules:
                if len(str(value)) > self.validation_rules['max_length']:
                    return False
            
            # Range validation
            if 'min_value' in self.validation_rules and isinstance(value, (int, float)):
                if value < self.validation_rules['min_value']:
                    return False
            
            if 'max_value' in self.validation_rules and isinstance(value, (int, float)):
                if value > self.validation_rules['max_value']:
                    return False
            
            # Pattern validation
            if 'pattern' in self.validation_rules and isinstance(value, str):
                pattern = self.validation_rules['pattern']
                if not re.match(pattern, value):
                    return False
            
            return True
            
        except Exception:
            return False

@dataclass
class TemplateStep:
    """Individual step in template workflow"""
    id: str
    name: str
    action_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None
    retry_count: int = 0
    timeout_seconds: float = 300.0
    on_success: Optional[str] = None  # Next step ID on success
    on_failure: Optional[str] = None  # Next step ID on failure
    parallel: bool = False
    description: str = ""

@dataclass
class AutomationTemplate:
    """Automation template definition"""
    id: str
    name: str
    description: str
    category: TemplateCategory
    template_type: TemplateType
    version: str = "1.0.0"
    
    # Template parameters
    parameters: List[TemplateParameter] = field(default_factory=list)
    
    # Template content
    steps: List[TemplateStep] = field(default_factory=list)
    template_data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    author: str = "system"
    created_time: datetime = field(default_factory=datetime.now)
    updated_time: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    
    # Usage statistics
    usage_count: int = 0
    last_used: Optional[datetime] = None
    
    # Dependencies
    required_modules: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    
    # Template inheritance
    parent_template_id: Optional[str] = None
    child_templates: List[str] = field(default_factory=list)
    
    def validate_parameters(self, parameter_values: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate template parameters"""
        errors = []
        
        for param in self.parameters:
            value = parameter_values.get(param.name, param.default_value)
            is_valid, error_msg = param.validate(value)
            
            if not is_valid:
                errors.append(error_msg)
        
        return len(errors) == 0, errors
    
    def render_with_parameters(self, parameter_values: Dict[str, Any]) -> 'RenderedTemplate':
        """Render template with parameter values"""
        # Validate parameters first
        is_valid, errors = self.validate_parameters(parameter_values)
        if not is_valid:
            raise ValueError(f"Parameter validation failed: {errors}")
        
        # Create merged parameters (defaults + provided values)
        merged_params = {}
        for param in self.parameters:
            value = parameter_values.get(param.name, param.default_value)
            merged_params[param.name] = value
        
        # Render template steps
        rendered_steps = []
        for step in self.steps:
            rendered_step = self._render_step(step, merged_params)
            rendered_steps.append(rendered_step)
        
        # Render template data
        rendered_data = self._render_data(self.template_data, merged_params)
        
        return RenderedTemplate(
            template_id=self.id,
            template_name=self.name,
            parameters=merged_params,
            steps=rendered_steps,
            rendered_data=rendered_data,
            render_time=datetime.now()
        )
    
    def _render_step(self, step: TemplateStep, parameters: Dict[str, Any]) -> TemplateStep:
        """Render template step with parameters"""
        rendered_step = copy.deepcopy(step)
        
        # Render step parameters
        rendered_step.parameters = self._render_data(step.parameters, parameters)
        
        # Render condition if present
        if step.condition:
            rendered_step.condition = self._render_string(step.condition, parameters)
        
        return rendered_step
    
    def _render_data(self, data: Any, parameters: Dict[str, Any]) -> Any:
        """Render data structure with parameters"""
        if isinstance(data, str):
            return self._render_string(data, parameters)
        elif isinstance(data, dict):
            return {key: self._render_data(value, parameters) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._render_data(item, parameters) for item in data]
        else:
            return data
    
    def _render_string(self, template_string: str, parameters: Dict[str, Any]) -> str:
        """Render string template with parameters"""
        try:
            if TEMPLATE_RENDERING_AVAILABLE:
                # Use Jinja2 for advanced templating
                template = jinja2.Template(template_string)
                return template.render(**parameters)
            else:
                # Simple string substitution
                for key, value in parameters.items():
                    template_string = template_string.replace(f"{{{{{key}}}}}", str(value))
                return template_string
                
        except Exception as e:
            logging.warning(f"Template rendering error: {e}")
            return template_string

@dataclass
class RenderedTemplate:
    """Rendered template ready for execution"""
    template_id: str
    template_name: str
    parameters: Dict[str, Any]
    steps: List[TemplateStep]
    rendered_data: Dict[str, Any]
    render_time: datetime
    
    def to_automation_definition(self) -> Dict[str, Any]:
        """Convert to automation system definition"""
        return {
            'id': str(uuid.uuid4()),
            'name': f"{self.template_name} - {self.render_time.strftime('%Y%m%d_%H%M%S')}",
            'template_id': self.template_id,
            'steps': [asdict(step) for step in self.steps],
            'parameters': self.parameters,
            'rendered_data': self.rendered_data,
            'created_from_template': True,
            'creation_time': self.render_time.isoformat()
        }

class TemplateLibrary:
    """
    Library of automation templates
    """
    
    def __init__(self, templates_dir: str = "user_data/automation_templates"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.templates: Dict[str, AutomationTemplate] = {}
        self.categories: Dict[TemplateCategory, List[str]] = defaultdict(list)
        
        # Template discovery
        self._load_builtin_templates()
        self._discover_user_templates()
    
    def add_template(self, template: AutomationTemplate) -> bool:
        """Add template to library"""
        try:
            # Validate template
            if not self._validate_template(template):
                return False
            
            # Store template
            self.templates[template.id] = template
            self.categories[template.category].append(template.id)
            
            # Save to file
            self._save_template_file(template)
            
            self.logger.info(f"Added template: {template.name} (ID: {template.id})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add template {template.name}: {e}")
            return False
    
    def get_template(self, template_id: str) -> Optional[AutomationTemplate]:
        """Get template by ID"""
        return self.templates.get(template_id)
    
    def search_templates(self, query: str = None, category: TemplateCategory = None,
                        tags: List[str] = None) -> List[AutomationTemplate]:
        """Search templates"""
        results = []
        
        for template in self.templates.values():
            # Category filter
            if category and template.category != category:
                continue
            
            # Tags filter
            if tags and not any(tag in template.tags for tag in tags):
                continue
            
            # Text search
            if query:
                search_text = f"{template.name} {template.description} {' '.join(template.tags)}".lower()
                if query.lower() not in search_text:
                    continue
            
            results.append(template)
        
        # Sort by usage count
        return sorted(results, key=lambda t: t.usage_count, reverse=True)
    
    def list_categories(self) -> Dict[str, int]:
        """List template categories with counts"""
        return {category.value: len(template_ids) 
                for category, template_ids in self.categories.items()}
    
    def get_popular_templates(self, limit: int = 10) -> List[AutomationTemplate]:
        """Get most popular templates"""
        all_templates = list(self.templates.values())
        return sorted(all_templates, key=lambda t: t.usage_count, reverse=True)[:limit]
    
    def create_template_from_workflow(self, workflow_definition: Dict[str, Any],
                                    template_info: Dict[str, Any]) -> AutomationTemplate:
        """Create template from existing workflow"""
        # Extract parameters from workflow
        parameters = self._extract_parameters_from_workflow(workflow_definition)
        
        # Convert workflow steps to template steps
        steps = self._convert_workflow_steps(workflow_definition.get('steps', []))
        
        template = AutomationTemplate(
            id=template_info.get('id', str(uuid.uuid4())),
            name=template_info['name'],
            description=template_info['description'],
            category=TemplateCategory(template_info['category']),
            template_type=TemplateType.WORKFLOW_TEMPLATE,
            parameters=parameters,
            steps=steps,
            author=template_info.get('author', 'user'),
            tags=template_info.get('tags', [])
        )
        
        return template
    
    def export_template(self, template_id: str, export_path: str) -> bool:
        """Export template to file"""
        try:
            template = self.get_template(template_id)
            if not template:
                return False
            
            export_data = {
                'template': asdict(template),
                'export_time': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export template {template_id}: {e}")
            return False
    
    def import_template(self, import_path: str) -> Optional[str]:
        """Import template from file"""
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)
            
            template_data = import_data['template']
            
            # Reconstruct template
            template = AutomationTemplate(**template_data)
            
            # Generate new ID if template already exists
            if template.id in self.templates:
                template.id = str(uuid.uuid4())
            
            if self.add_template(template):
                return template.id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to import template from {import_path}: {e}")
            return None
    
    def _validate_template(self, template: AutomationTemplate) -> bool:
        """Validate template structure"""
        try:
            # Basic validation
            if not template.id or not template.name:
                return False
            
            # Parameter validation
            for param in template.parameters:
                if not param.name or not isinstance(param.param_type, ParameterType):
                    return False
            
            # Steps validation
            for step in template.steps:
                if not step.id or not step.name or not step.action_type:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _load_builtin_templates(self):
        """Load built-in automation templates"""
        builtin_templates = [
            self._create_file_copy_template(),
            self._create_backup_template(),
            self._create_log_analysis_template(),
            self._create_api_monitoring_template(),
            self._create_database_backup_template(),
            self._create_email_notification_template(),
            self._create_system_health_check_template(),
            self._create_file_cleanup_template()
        ]
        
        for template in builtin_templates:
            self.templates[template.id] = template
            self.categories[template.category].append(template.id)
    
    def _discover_user_templates(self):
        """Discover user-created templates"""
        try:
            template_files = self.templates_dir.glob("*.json")
            
            for template_file in template_files:
                try:
                    with open(template_file, 'r') as f:
                        template_data = json.load(f)
                    
                    # Convert data back to template object
                    template = AutomationTemplate(**template_data)
                    
                    self.templates[template.id] = template
                    self.categories[template.category].append(template.id)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to load template from {template_file}: {e}")
                    
        except Exception as e:
            self.logger.error(f"Failed to discover user templates: {e}")
    
    def _save_template_file(self, template: AutomationTemplate):
        """Save template to file"""
        try:
            template_file = self.templates_dir / f"{template.id}.json"
            
            with open(template_file, 'w') as f:
                json.dump(asdict(template), f, indent=2, default=str)
                
        except Exception as e:
            self.logger.error(f"Failed to save template file for {template.id}: {e}")
    
    def _extract_parameters_from_workflow(self, workflow: Dict[str, Any]) -> List[TemplateParameter]:
        """Extract parameterizable values from workflow"""
        parameters = []
        
        # This is a simplified implementation
        # In practice, you'd analyze the workflow to find parameterizable values
        
        # Look for common parameterizable fields
        common_params = [
            ("source_path", ParameterType.FILE_PATH, "Source file path"),
            ("destination_path", ParameterType.FILE_PATH, "Destination file path"),
            ("email_address", ParameterType.EMAIL, "Email address for notifications"),
            ("api_url", ParameterType.URL, "API endpoint URL"),
            ("schedule_expression", ParameterType.CRON_EXPRESSION, "Schedule expression"),
            ("timeout_seconds", ParameterType.INTEGER, "Timeout in seconds"),
            ("retry_count", ParameterType.INTEGER, "Number of retries")
        ]
        
        for param_name, param_type, description in common_params:
            parameters.append(TemplateParameter(
                name=param_name,
                param_type=param_type,
                description=description,
                required=False,
                default_value=None
            ))
        
        return parameters
    
    def _convert_workflow_steps(self, workflow_steps: List[Dict[str, Any]]) -> List[TemplateStep]:
        """Convert workflow steps to template steps"""
        template_steps = []
        
        for i, step_data in enumerate(workflow_steps):
            step = TemplateStep(
                id=step_data.get('id', f"step_{i}"),
                name=step_data.get('name', f"Step {i+1}"),
                action_type=step_data.get('action_type', 'custom'),
                parameters=step_data.get('parameters', {}),
                condition=step_data.get('condition'),
                retry_count=step_data.get('retry_count', 0),
                timeout_seconds=step_data.get('timeout_seconds', 300.0),
                description=step_data.get('description', '')
            )
            template_steps.append(step)
        
        return template_steps
    
    # Built-in template creation methods
    def _create_file_copy_template(self) -> AutomationTemplate:
        """Create file copy template"""
        return AutomationTemplate(
            id="builtin_file_copy",
            name="File Copy",
            description="Copy files from source to destination with optional filtering",
            category=TemplateCategory.FILE_OPERATIONS,
            template_type=TemplateType.TASK_TEMPLATE,
            parameters=[
                TemplateParameter("source_path", ParameterType.FILE_PATH, "Source file or directory path", required=True),
                TemplateParameter("destination_path", ParameterType.FILE_PATH, "Destination path", required=True),
                TemplateParameter("file_pattern", ParameterType.STRING, "File pattern to match (e.g., *.txt)", default_value="*"),
                TemplateParameter("overwrite", ParameterType.BOOLEAN, "Overwrite existing files", default_value=False),
                TemplateParameter("preserve_structure", ParameterType.BOOLEAN, "Preserve directory structure", default_value=True)
            ],
            steps=[
                TemplateStep(
                    id="copy_files",
                    name="Copy Files",
                    action_type="file_copy",
                    parameters={
                        "source": "{{source_path}}",
                        "destination": "{{destination_path}}",
                        "pattern": "{{file_pattern}}",
                        "overwrite": "{{overwrite}}",
                        "preserve_structure": "{{preserve_structure}}"
                    }
                )
            ],
            tags=["file", "copy", "backup"]
        )
    
    def _create_backup_template(self) -> AutomationTemplate:
        """Create backup template"""
        return AutomationTemplate(
            id="builtin_backup",
            name="Directory Backup",
            description="Create compressed backup of directory with timestamp",
            category=TemplateCategory.BACKUP_RECOVERY,
            template_type=TemplateType.WORKFLOW_TEMPLATE,
            parameters=[
                TemplateParameter("source_directory", ParameterType.DIRECTORY_PATH, "Directory to backup", required=True),
                TemplateParameter("backup_location", ParameterType.DIRECTORY_PATH, "Backup destination directory", required=True),
                TemplateParameter("compression", ParameterType.STRING, "Compression format", default_value="zip", choices=["zip", "tar", "tar.gz"]),
                TemplateParameter("include_timestamp", ParameterType.BOOLEAN, "Include timestamp in backup name", default_value=True),
                TemplateParameter("max_backups", ParameterType.INTEGER, "Maximum number of backups to keep", default_value=10)
            ],
            steps=[
                TemplateStep(
                    id="create_backup",
                    name="Create Backup Archive",
                    action_type="create_archive",
                    parameters={
                        "source": "{{source_directory}}",
                        "destination": "{{backup_location}}",
                        "format": "{{compression}}",
                        "include_timestamp": "{{include_timestamp}}"
                    }
                ),
                TemplateStep(
                    id="cleanup_old",
                    name="Clean Up Old Backups",
                    action_type="cleanup_files",
                    parameters={
                        "directory": "{{backup_location}}",
                        "max_files": "{{max_backups}}",
                        "sort_by": "creation_time"
                    }
                )
            ],
            tags=["backup", "archive", "cleanup"]
        )
    
    def _create_log_analysis_template(self) -> AutomationTemplate:
        """Create log analysis template"""
        return AutomationTemplate(
            id="builtin_log_analysis",
            name="Log File Analysis",
            description="Analyze log files for errors and generate reports",
            category=TemplateCategory.SYSTEM_MONITORING,
            template_type=TemplateType.WORKFLOW_TEMPLATE,
            parameters=[
                TemplateParameter("log_file_path", ParameterType.FILE_PATH, "Path to log file", required=True),
                TemplateParameter("error_patterns", ParameterType.LIST, "Error patterns to search for", default_value=["ERROR", "FATAL", "EXCEPTION"]),
                TemplateParameter("time_window_hours", ParameterType.INTEGER, "Time window for analysis (hours)", default_value=24),
                TemplateParameter("report_path", ParameterType.FILE_PATH, "Path for analysis report", required=True),
                TemplateParameter("email_alerts", ParameterType.BOOLEAN, "Send email alerts for critical errors", default_value=False),
                TemplateParameter("alert_email", ParameterType.EMAIL, "Email address for alerts", required=False)
            ],
            steps=[
                TemplateStep(
                    id="parse_logs",
                    name="Parse Log File",
                    action_type="parse_log_file",
                    parameters={
                        "file_path": "{{log_file_path}}",
                        "time_window_hours": "{{time_window_hours}}"
                    }
                ),
                TemplateStep(
                    id="search_errors",
                    name="Search for Errors",
                    action_type="search_patterns",
                    parameters={
                        "patterns": "{{error_patterns}}"
                    }
                ),
                TemplateStep(
                    id="generate_report",
                    name="Generate Analysis Report",
                    action_type="generate_report",
                    parameters={
                        "output_path": "{{report_path}}"
                    }
                ),
                TemplateStep(
                    id="send_alerts",
                    name="Send Email Alerts",
                    action_type="send_email",
                    condition="{{email_alerts}} and error_count > 0",
                    parameters={
                        "to": "{{alert_email}}",
                        "subject": "Log Analysis Alert",
                        "body": "Critical errors detected in log analysis"
                    }
                )
            ],
            tags=["logs", "analysis", "monitoring", "alerts"]
        )
    
    def _create_api_monitoring_template(self) -> AutomationTemplate:
        """Create API monitoring template"""
        return AutomationTemplate(
            id="builtin_api_monitoring",
            name="API Health Monitoring",
            description="Monitor API endpoints for availability and performance",
            category=TemplateCategory.NETWORK_AUTOMATION,
            template_type=TemplateType.SCHEDULE_TEMPLATE,
            parameters=[
                TemplateParameter("api_endpoints", ParameterType.LIST, "List of API endpoints to monitor", required=True),
                TemplateParameter("check_interval_minutes", ParameterType.INTEGER, "Check interval in minutes", default_value=5),
                TemplateParameter("timeout_seconds", ParameterType.INTEGER, "Request timeout in seconds", default_value=30),
                TemplateParameter("expected_status_codes", ParameterType.LIST, "Expected HTTP status codes", default_value=[200]),
                TemplateParameter("alert_threshold", ParameterType.INTEGER, "Alert after N consecutive failures", default_value=3),
                TemplateParameter("notification_webhook", ParameterType.URL, "Webhook URL for notifications", required=False)
            ],
            steps=[
                TemplateStep(
                    id="check_endpoints",
                    name="Check API Endpoints",
                    action_type="http_health_check",
                    parameters={
                        "endpoints": "{{api_endpoints}}",
                        "timeout": "{{timeout_seconds}}",
                        "expected_codes": "{{expected_status_codes}}"
                    }
                ),
                TemplateStep(
                    id="evaluate_health",
                    name="Evaluate Health Status",
                    action_type="evaluate_health",
                    parameters={
                        "alert_threshold": "{{alert_threshold}}"
                    }
                ),
                TemplateStep(
                    id="send_notifications",
                    name="Send Notifications",
                    action_type="send_webhook",
                    condition="health_status == 'critical'",
                    parameters={
                        "webhook_url": "{{notification_webhook}}",
                        "payload": {
                            "alert_type": "api_health",
                            "message": "API health check failed"
                        }
                    }
                )
            ],
            tags=["api", "monitoring", "health", "alerts"]
        )
    
    def _create_database_backup_template(self) -> AutomationTemplate:
        """Create database backup template"""
        return AutomationTemplate(
            id="builtin_database_backup",
            name="Database Backup",
            description="Create database backups with compression and cleanup",
            category=TemplateCategory.DATABASE_OPERATIONS,
            template_type=TemplateType.WORKFLOW_TEMPLATE,
            parameters=[
                TemplateParameter("db_type", ParameterType.STRING, "Database type", choices=["mysql", "postgresql", "sqlite"], required=True),
                TemplateParameter("db_host", ParameterType.STRING, "Database host", default_value="localhost"),
                TemplateParameter("db_port", ParameterType.INTEGER, "Database port", default_value=3306),
                TemplateParameter("db_name", ParameterType.STRING, "Database name", required=True),
                TemplateParameter("db_user", ParameterType.STRING, "Database user", required=True),
                TemplateParameter("db_password", ParameterType.STRING, "Database password", required=True, sensitive=True),
                TemplateParameter("backup_path", ParameterType.DIRECTORY_PATH, "Backup directory", required=True),
                TemplateParameter("compress_backup", ParameterType.BOOLEAN, "Compress backup file", default_value=True),
                TemplateParameter("retention_days", ParameterType.INTEGER, "Backup retention in days", default_value=30)
            ],
            steps=[
                TemplateStep(
                    id="create_dump",
                    name="Create Database Dump",
                    action_type="database_dump",
                    parameters={
                        "db_type": "{{db_type}}",
                        "host": "{{db_host}}",
                        "port": "{{db_port}}",
                        "database": "{{db_name}}",
                        "username": "{{db_user}}",
                        "password": "{{db_password}}",
                        "output_path": "{{backup_path}}"
                    }
                ),
                TemplateStep(
                    id="compress_dump",
                    name="Compress Backup",
                    action_type="compress_file",
                    condition="{{compress_backup}}",
                    parameters={
                        "file_path": "{{backup_path}}/{{db_name}}.sql",
                        "compression": "gzip"
                    }
                ),
                TemplateStep(
                    id="cleanup_old_backups",
                    name="Clean Up Old Backups",
                    action_type="cleanup_old_files",
                    parameters={
                        "directory": "{{backup_path}}",
                        "retention_days": "{{retention_days}}",
                        "pattern": "{{db_name}}_*"
                    }
                )
            ],
            tags=["database", "backup", "mysql", "postgresql", "sqlite"]
        )
    
    def _create_email_notification_template(self) -> AutomationTemplate:
        """Create email notification template"""
        return AutomationTemplate(
            id="builtin_email_notification",
            name="Email Notification",
            description="Send formatted email notifications",
            category=TemplateCategory.NOTIFICATION_ALERTS,
            template_type=TemplateType.TASK_TEMPLATE,
            parameters=[
                TemplateParameter("smtp_server", ParameterType.STRING, "SMTP server hostname", required=True),
                TemplateParameter("smtp_port", ParameterType.INTEGER, "SMTP server port", default_value=587),
                TemplateParameter("smtp_username", ParameterType.STRING, "SMTP username", required=True),
                TemplateParameter("smtp_password", ParameterType.STRING, "SMTP password", required=True, sensitive=True),
                TemplateParameter("from_email", ParameterType.EMAIL, "From email address", required=True),
                TemplateParameter("to_emails", ParameterType.LIST, "List of recipient email addresses", required=True),
                TemplateParameter("subject", ParameterType.STRING, "Email subject", required=True),
                TemplateParameter("message_body", ParameterType.STRING, "Email message body", required=True),
                TemplateParameter("use_html", ParameterType.BOOLEAN, "Send as HTML email", default_value=False),
                TemplateParameter("attachments", ParameterType.LIST, "List of file paths to attach", default_value=[])
            ],
            steps=[
                TemplateStep(
                    id="send_email",
                    name="Send Email Notification",
                    action_type="send_email",
                    parameters={
                        "smtp_server": "{{smtp_server}}",
                        "smtp_port": "{{smtp_port}}",
                        "username": "{{smtp_username}}",
                        "password": "{{smtp_password}}",
                        "from_address": "{{from_email}}",
                        "to_addresses": "{{to_emails}}",
                        "subject": "{{subject}}",
                        "body": "{{message_body}}",
                        "html": "{{use_html}}",
                        "attachments": "{{attachments}}"
                    }
                )
            ],
            tags=["email", "notification", "alerts", "smtp"]
        )
    
    def _create_system_health_check_template(self) -> AutomationTemplate:
        """Create system health check template"""
        return AutomationTemplate(
            id="builtin_system_health",
            name="System Health Check",
            description="Comprehensive system health monitoring",
            category=TemplateCategory.SYSTEM_MONITORING,
            template_type=TemplateType.WORKFLOW_TEMPLATE,
            parameters=[
                TemplateParameter("cpu_threshold", ParameterType.FLOAT, "CPU usage threshold (%)", default_value=80.0),
                TemplateParameter("memory_threshold", ParameterType.FLOAT, "Memory usage threshold (%)", default_value=85.0),
                TemplateParameter("disk_threshold", ParameterType.FLOAT, "Disk usage threshold (%)", default_value=90.0),
                TemplateParameter("check_services", ParameterType.LIST, "List of services to check", default_value=[]),
                TemplateParameter("report_path", ParameterType.FILE_PATH, "Health report output path", required=True),
                TemplateParameter("alert_on_issues", ParameterType.BOOLEAN, "Send alerts for issues", default_value=True),
                TemplateParameter("alert_webhook", ParameterType.URL, "Webhook URL for alerts", required=False)
            ],
            steps=[
                TemplateStep(
                    id="check_cpu",
                    name="Check CPU Usage",
                    action_type="check_cpu_usage",
                    parameters={
                        "threshold": "{{cpu_threshold}}"
                    }
                ),
                TemplateStep(
                    id="check_memory",
                    name="Check Memory Usage",
                    action_type="check_memory_usage",
                    parameters={
                        "threshold": "{{memory_threshold}}"
                    }
                ),
                TemplateStep(
                    id="check_disk",
                    name="Check Disk Usage",
                    action_type="check_disk_usage",
                    parameters={
                        "threshold": "{{disk_threshold}}"
                    }
                ),
                TemplateStep(
                    id="check_services",
                    name="Check Services",
                    action_type="check_services",
                    condition="len({{check_services}}) > 0",
                    parameters={
                        "services": "{{check_services}}"
                    }
                ),
                TemplateStep(
                    id="generate_report",
                    name="Generate Health Report",
                    action_type="generate_health_report",
                    parameters={
                        "output_path": "{{report_path}}"
                    }
                ),
                TemplateStep(
                    id="send_alerts",
                    name="Send Health Alerts",
                    action_type="send_webhook",
                    condition="{{alert_on_issues}} and health_issues_found",
                    parameters={
                        "webhook_url": "{{alert_webhook}}",
                        "payload": {
                            "alert_type": "system_health",
                            "issues": "health_issues"
                        }
                    }
                )
            ],
            tags=["system", "health", "monitoring", "cpu", "memory", "disk"]
        )
    
    def _create_file_cleanup_template(self) -> AutomationTemplate:
        """Create file cleanup template"""
        return AutomationTemplate(
            id="builtin_file_cleanup",
            name="File Cleanup",
            description="Clean up old files and directories based on age and patterns",
            category=TemplateCategory.FILE_OPERATIONS,
            template_type=TemplateType.TASK_TEMPLATE,
            parameters=[
                TemplateParameter("target_directory", ParameterType.DIRECTORY_PATH, "Directory to clean up", required=True),
                TemplateParameter("file_patterns", ParameterType.LIST, "File patterns to match", default_value=["*.tmp", "*.log", "*.bak"]),
                TemplateParameter("max_age_days", ParameterType.INTEGER, "Maximum file age in days", default_value=30),
                TemplateParameter("dry_run", ParameterType.BOOLEAN, "Perform dry run (don't delete files)", default_value=True),
                TemplateParameter("recursive", ParameterType.BOOLEAN, "Search subdirectories recursively", default_value=True),
                TemplateParameter("min_size_mb", ParameterType.FLOAT, "Minimum file size in MB (0 for any size)", default_value=0.0),
                TemplateParameter("exclude_patterns", ParameterType.LIST, "Patterns to exclude from cleanup", default_value=[])
            ],
            steps=[
                TemplateStep(
                    id="scan_files",
                    name="Scan Files for Cleanup",
                    action_type="scan_cleanup_files",
                    parameters={
                        "directory": "{{target_directory}}",
                        "patterns": "{{file_patterns}}",
                        "max_age_days": "{{max_age_days}}",
                        "recursive": "{{recursive}}",
                        "min_size_mb": "{{min_size_mb}}",
                        "exclude_patterns": "{{exclude_patterns}}"
                    }
                ),
                TemplateStep(
                    id="cleanup_files",
                    name="Clean Up Files",
                    action_type="cleanup_files",
                    parameters={
                        "dry_run": "{{dry_run}}"
                    }
                )
            ],
            tags=["cleanup", "files", "maintenance", "storage"]
        )

class TemplateManager:
    """
    Main template management system
    """
    
    def __init__(self, library: TemplateLibrary = None):
        self.library = library or TemplateLibrary()
        self.logger = logging.getLogger(__name__)
        
        # Template usage tracking
        self.usage_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Template validation
        self.validators = {}
        self._setup_validators()
    
    def create_automation_from_template(self, template_id: str, 
                                      parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create automation instance from template"""
        try:
            template = self.library.get_template(template_id)
            if not template:
                self.logger.error(f"Template not found: {template_id}")
                return None
            
            # Render template with parameters
            rendered_template = template.render_with_parameters(parameters)
            
            # Update usage statistics
            template.usage_count += 1
            template.last_used = datetime.now()
            self._update_usage_stats(template_id)
            
            # Convert to automation definition
            automation_def = rendered_template.to_automation_definition()
            
            self.logger.info(f"Created automation from template {template.name}")
            return automation_def
            
        except Exception as e:
            self.logger.error(f"Failed to create automation from template {template_id}: {e}")
            return None
    
    def validate_template_parameters(self, template_id: str, 
                                   parameters: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate template parameters"""
        template = self.library.get_template(template_id)
        if not template:
            return False, [f"Template not found: {template_id}"]
        
        return template.validate_parameters(parameters)
    
    def get_template_info(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template information"""
        template = self.library.get_template(template_id)
        if not template:
            return None
        
        return {
            'id': template.id,
            'name': template.name,
            'description': template.description,
            'category': template.category.value,
            'type': template.template_type.value,
            'version': template.version,
            'author': template.author,
            'created_time': template.created_time.isoformat(),
            'updated_time': template.updated_time.isoformat(),
            'usage_count': template.usage_count,
            'last_used': template.last_used.isoformat() if template.last_used else None,
            'tags': template.tags,
            'parameters': [
                {
                    'name': param.name,
                    'type': param.param_type.value,
                    'description': param.description,
                    'required': param.required,
                    'default_value': param.default_value,
                    'choices': param.choices,
                    'sensitive': param.sensitive
                }
                for param in template.parameters
            ],
            'steps': len(template.steps),
            'required_modules': template.required_modules,
            'required_permissions': template.required_permissions
        }
    
    def search_templates(self, query: str = None, category: str = None, 
                        tags: List[str] = None) -> List[Dict[str, Any]]:
        """Search templates with enhanced filtering"""
        category_enum = TemplateCategory(category) if category else None
        templates = self.library.search_templates(query, category_enum, tags)
        
        return [self.get_template_info(template.id) for template in templates]
    
    def get_template_categories(self) -> List[Dict[str, Any]]:
        """Get template categories with metadata"""
        categories = []
        
        for category in TemplateCategory:
            template_count = len(self.library.categories[category])
            
            categories.append({
                'name': category.value,
                'display_name': category.value.replace('_', ' ').title(),
                'template_count': template_count,
                'description': self._get_category_description(category)
            })
        
        return sorted(categories, key=lambda x: x['template_count'], reverse=True)
    
    def get_popular_templates(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get popular templates"""
        popular = self.library.get_popular_templates(limit)
        return [self.get_template_info(template.id) for template in popular]
    
    def create_custom_template(self, template_data: Dict[str, Any]) -> Optional[str]:
        """Create custom template"""
        try:
            # Validate required fields
            required_fields = ['name', 'description', 'category', 'template_type']
            for field in required_fields:
                if field not in template_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create template
            template = AutomationTemplate(
                id=template_data.get('id', str(uuid.uuid4())),
                name=template_data['name'],
                description=template_data['description'],
                category=TemplateCategory(template_data['category']),
                template_type=TemplateType(template_data['template_type']),
                version=template_data.get('version', '1.0.0'),
                parameters=[
                    TemplateParameter(**param_data) 
                    for param_data in template_data.get('parameters', [])
                ],
                steps=[
                    TemplateStep(**step_data)
                    for step_data in template_data.get('steps', [])
                ],
                author=template_data.get('author', 'user'),
                tags=template_data.get('tags', []),
                required_modules=template_data.get('required_modules', []),
                required_permissions=template_data.get('required_permissions', [])
            )
            
            if self.library.add_template(template):
                return template.id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to create custom template: {e}")
            return None
    
    def clone_template(self, template_id: str, new_name: str) -> Optional[str]:
        """Clone existing template"""
        try:
            original = self.library.get_template(template_id)
            if not original:
                return None
            
            # Create cloned template
            cloned = copy.deepcopy(original)
            cloned.id = str(uuid.uuid4())
            cloned.name = new_name
            cloned.version = "1.0.0"
            cloned.created_time = datetime.now()
            cloned.updated_time = datetime.now()
            cloned.usage_count = 0
            cloned.last_used = None
            cloned.author = "user"
            
            if self.library.add_template(cloned):
                return cloned.id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to clone template {template_id}: {e}")
            return None
    
    def _update_usage_stats(self, template_id: str):
        """Update template usage statistics"""
        current_time = datetime.now()
        
        if template_id not in self.usage_stats:
            self.usage_stats[template_id] = {
                'first_used': current_time,
                'last_used': current_time,
                'usage_count': 1,
                'usage_history': []
            }
        else:
            stats = self.usage_stats[template_id]
            stats['last_used'] = current_time
            stats['usage_count'] += 1
            stats['usage_history'].append(current_time)
            
            # Keep only last 100 usage records
            if len(stats['usage_history']) > 100:
                stats['usage_history'] = stats['usage_history'][-100:]
    
    def _setup_validators(self):
        """Setup template validators"""
        if not VALIDATION_AVAILABLE:
            return
        
        # Parameter validation schemas
        self.validators['parameter'] = cerberus.Validator({
            'name': {'type': 'string', 'required': True},
            'param_type': {'type': 'string', 'required': True},
            'description': {'type': 'string'},
            'default_value': {},
            'required': {'type': 'boolean'},
            'validation_rules': {'type': 'dict'},
            'choices': {'type': 'list'},
            'sensitive': {'type': 'boolean'}
        })
        
        # Template step validation schema
        self.validators['step'] = cerberus.Validator({
            'id': {'type': 'string', 'required': True},
            'name': {'type': 'string', 'required': True},
            'action_type': {'type': 'string', 'required': True},
            'parameters': {'type': 'dict'},
            'condition': {'type': 'string'},
            'retry_count': {'type': 'integer'},
            'timeout_seconds': {'type': 'number'},
            'on_success': {'type': 'string'},
            'on_failure': {'type': 'string'},
            'parallel': {'type': 'boolean'},
            'description': {'type': 'string'}
        })
    
    def _get_category_description(self, category: TemplateCategory) -> str:
        """Get description for template category"""
        descriptions = {
            TemplateCategory.FILE_OPERATIONS: "Templates for file and directory operations",
            TemplateCategory.DATA_PROCESSING: "Templates for data transformation and processing",
            TemplateCategory.SYSTEM_MONITORING: "Templates for system monitoring and health checks",
            TemplateCategory.NETWORK_AUTOMATION: "Templates for network operations and monitoring",
            TemplateCategory.DATABASE_OPERATIONS: "Templates for database management and operations",
            TemplateCategory.API_INTEGRATION: "Templates for API interactions and integrations",
            TemplateCategory.WORKFLOW_ORCHESTRATION: "Templates for complex workflow coordination",
            TemplateCategory.NOTIFICATION_ALERTS: "Templates for notifications and alerting",
            TemplateCategory.BACKUP_RECOVERY: "Templates for backup and recovery operations",
            TemplateCategory.SECURITY_COMPLIANCE: "Templates for security and compliance checks",
            TemplateCategory.CUSTOM: "Custom user-created templates"
        }
        
        return descriptions.get(category, "Automation templates")


# Utility functions for template creation
def create_simple_task_template(name: str, description: str, category: TemplateCategory,
                               action_type: str, parameters: Dict[str, Any]) -> AutomationTemplate:
    """Create simple single-task template"""
    template_params = []
    
    # Extract parameterizable values
    for key, value in parameters.items():
        if isinstance(value, str) and "{{" in value:
            param_name = value.replace("{{", "").replace("}}", "")
            template_params.append(TemplateParameter(
                name=param_name,
                param_type=ParameterType.STRING,
                description=f"Parameter for {key}",
                required=True
            ))
    
    step = TemplateStep(
        id="main_task",
        name=name,
        action_type=action_type,
        parameters=parameters
    )
    
    return AutomationTemplate(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        category=category,
        template_type=TemplateType.TASK_TEMPLATE,
        parameters=template_params,
        steps=[step]
    )

def create_workflow_template(name: str, description: str, category: TemplateCategory,
                           workflow_steps: List[Dict[str, Any]]) -> AutomationTemplate:
    """Create workflow template from step definitions"""
    template_params = []
    template_steps = []
    
    # Process steps
    for i, step_def in enumerate(workflow_steps):
        step = TemplateStep(
            id=step_def.get('id', f"step_{i}"),
            name=step_def['name'],
            action_type=step_def['action_type'],
            parameters=step_def.get('parameters', {}),
            condition=step_def.get('condition'),
            description=step_def.get('description', '')
        )
        template_steps.append(step)
        
        # Extract parameters from step
        for key, value in step.parameters.items():
            if isinstance(value, str) and "{{" in value:
                param_name = value.replace("{{", "").replace("}}", "")
                
                # Check if parameter already exists
                if not any(p.name == param_name for p in template_params):
                    template_params.append(TemplateParameter(
                        name=param_name,
                        param_type=ParameterType.STRING,
                        description=f"Parameter for {param_name}",
                        required=True
                    ))
    
    return AutomationTemplate(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        category=category,
        template_type=TemplateType.WORKFLOW_TEMPLATE,
        parameters=template_params,
        steps=template_steps
    )