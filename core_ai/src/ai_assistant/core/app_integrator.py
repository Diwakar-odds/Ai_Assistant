"""
Secure App Integration Manager for AI Assistant

This module provides a secure way to integrate third-party applications
with the AI assistant while protecting sensitive information and credentials.
"""

import os
import json
import logging
import subprocess
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import requests
import threading
from dataclasses import dataclass, asdict

from .app_security import secure_app_manager

@dataclass
class AppIntegration:
    """Represents an app integration configuration."""
    name: str
    display_name: str
    category: str
    integration_type: str  # 'basic', 'api', 'oauth', 'webhook'
    executable_path: Optional[str] = None
    api_endpoint: Optional[str] = None
    permissions: List[str] = None
    startup_delay: int = 0
    auto_start: bool = False
    enabled: bool = True
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []

class SecureAppIntegrator:
    """Manages secure integration with third-party applications."""
    
    def __init__(self, assistant_config=None):
        self.assistant_config = assistant_config or {}
        self.logger = logging.getLogger(__name__)
        self.running_integrations: Dict[str, Any] = {}
        self.integration_lock = threading.Lock()
        
        # Integration categories with default permissions
        self.integration_categories = {
            'productivity': ['file_access', 'clipboard_access'],
            'media': ['audio_control', 'video_control'],
            'development': ['system_access', 'file_access', 'network_access'],
            'communication': ['network_access', 'notification_access'],
            'social': ['network_access', 'notification_access'],
            'utility': ['system_access'],
            'entertainment': ['audio_control', 'video_control'],
            'business': ['file_access', 'network_access']
        }
    
    def register_app(self, app_config: Dict[str, Any]) -> Tuple[bool, str]:
        """Register a new app integration."""
        try:
            # Validate required fields
            required_fields = ['name', 'display_name', 'category', 'integration_type']
            missing_fields = [field for field in required_fields if field not in app_config]
            if missing_fields:
                return False, f"Missing required fields: {missing_fields}"
            
            # Sanitize app name
            app_name = app_config['name'].lower().strip()
            if not app_name.replace('_', '').replace('-', '').isalnum():
                return False, "App name must contain only letters, numbers, hyphens, and underscores"
            
            # Validate integration type
            valid_types = ['basic', 'api', 'oauth', 'webhook']
            if app_config['integration_type'] not in valid_types:
                return False, f"Invalid integration type. Must be one of: {valid_types}"
            
            # Set default permissions based on category
            category = app_config.get('category', 'utility')
            default_permissions = self.integration_categories.get(category, [])
            app_config.setdefault('permissions', default_permissions.copy())
            
            # Add security metadata
            app_config['registered_at'] = datetime.now().isoformat()
            app_config['security_level'] = self._determine_security_level(app_config)
            
            # Register with secure manager
            success = secure_app_manager.register_secure_app(app_config)
            
            if success:
                self.logger.info(f"Successfully registered app: {app_name}")
                return True, f"App '{app_config['display_name']}' registered successfully"
            else:
                return False, "Failed to register app with secure manager"
                
        except Exception as e:
            self.logger.error(f"Error registering app: {e}")
            return False, f"Registration failed: {str(e)}"
    
    def _determine_security_level(self, app_config: Dict[str, Any]) -> str:
        """Determine security level based on permissions and integration type."""
        permissions = app_config.get('permissions', [])
        integration_type = app_config.get('integration_type', 'basic')
        
        high_risk_permissions = ['system_access', 'file_access', 'network_access']
        medium_risk_permissions = ['audio_control', 'clipboard_access', 'notification_access']
        
        if integration_type in ['oauth', 'webhook'] or any(p in high_risk_permissions for p in permissions):
            return 'high'
        elif integration_type == 'api' or any(p in medium_risk_permissions for p in permissions):
            return 'medium'
        else:
            return 'low'
    
    def launch_app(self, app_name: str, args: List[str] = None) -> Tuple[bool, str]:
        """Securely launch an integrated application."""
        try:
            app_name = app_name.lower()
            
            # Check if app is registered
            registered_apps = secure_app_manager.list_registered_apps()
            if app_name not in registered_apps:
                return False, f"App '{app_name}' is not registered"
            
            app_config = registered_apps[app_name]
            
            # Check if app is enabled
            if not app_config.get('enabled', True):
                return False, f"App '{app_name}' is disabled"
            
            # Validate permissions if required
            required_permissions = app_config.get('permissions', [])
            if not secure_app_manager.validate_app_permissions(app_name, required_permissions):
                return False, f"Insufficient permissions for '{app_name}'"
            
            executable_path = app_config.get('executable_path')
            if not executable_path or not Path(executable_path).exists():
                return False, f"Executable not found for '{app_name}'"
            
            # Prepare launch command
            launch_args = [executable_path]
            startup_args = app_config.get('startup_args', [])
            if startup_args:
                launch_args.extend(startup_args)
            if args:
                launch_args.extend(args)
            
            # Apply startup delay if configured
            startup_delay = app_config.get('startup_delay', 0)
            if startup_delay > 0:
                threading.Timer(startup_delay, self._delayed_launch, args=(launch_args, app_name)).start()
                return True, f"'{app_config['display_name']}' will start in {startup_delay} seconds"
            else:
                return self._launch_process(launch_args, app_name, app_config['display_name'])
                
        except Exception as e:
            self.logger.error(f"Error launching app {app_name}: {e}")
            return False, f"Failed to launch app: {str(e)}"
    
    def _delayed_launch(self, launch_args: List[str], app_name: str):
        """Launch app after delay."""
        try:
            registered_apps = secure_app_manager.list_registered_apps()
            app_config = registered_apps.get(app_name, {})
            display_name = app_config.get('display_name', app_name)
            self._launch_process(launch_args, app_name, display_name)
        except Exception as e:
            self.logger.error(f"Error in delayed launch for {app_name}: {e}")
    
    def _launch_process(self, launch_args: List[str], app_name: str, display_name: str) -> Tuple[bool, str]:
        """Actually launch the process."""
        try:
            # Launch the application
            process = subprocess.Popen(
                launch_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            with self.integration_lock:
                self.running_integrations[app_name] = {
                    'process': process,
                    'launched_at': datetime.now(),
                    'display_name': display_name
                }
            
            self.logger.info(f"Successfully launched {display_name} (PID: {process.pid})")
            return True, f"'{display_name}' launched successfully"
            
        except FileNotFoundError:
            return False, f"Executable not found for '{display_name}'"
        except PermissionError:
            return False, f"Permission denied when launching '{display_name}'"
        except Exception as e:
            return False, f"Failed to launch '{display_name}': {str(e)}"
    
    def stop_app(self, app_name: str) -> Tuple[bool, str]:
        """Stop a running integrated application."""
        try:
            app_name = app_name.lower()
            
            with self.integration_lock:
                if app_name not in self.running_integrations:
                    return False, f"App '{app_name}' is not running"
                
                integration_info = self.running_integrations[app_name]
                process = integration_info['process']
                display_name = integration_info['display_name']
                
                # Terminate the process
                process.terminate()
                
                # Wait for termination with timeout
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    process.kill()
                    process.wait()
                
                del self.running_integrations[app_name]
            
            self.logger.info(f"Successfully stopped {display_name}")
            return True, f"'{display_name}' stopped successfully"
            
        except Exception as e:
            self.logger.error(f"Error stopping app {app_name}: {e}")
            return False, f"Failed to stop app: {str(e)}"
    
    def list_running_apps(self) -> Dict[str, Dict[str, Any]]:
        """List currently running integrated applications."""
        with self.integration_lock:
            running_info = {}
            for app_name, integration_info in self.running_integrations.items():
                process = integration_info['process']
                if process.poll() is None:  # Process is still running
                    running_info[app_name] = {
                        'display_name': integration_info['display_name'],
                        'pid': process.pid,
                        'launched_at': integration_info['launched_at'].isoformat(),
                        'status': 'running'
                    }
                else:
                    # Process has terminated
                    running_info[app_name] = {
                        'display_name': integration_info['display_name'],
                        'pid': process.pid,
                        'launched_at': integration_info['launched_at'].isoformat(),
                        'status': 'terminated',
                        'return_code': process.returncode
                    }
            
            return running_info
    
    def cleanup_terminated_processes(self):
        """Clean up terminated processes from running integrations."""
        with self.integration_lock:
            terminated = []
            for app_name, integration_info in self.running_integrations.items():
                if integration_info['process'].poll() is not None:
                    terminated.append(app_name)
            
            for app_name in terminated:
                del self.running_integrations[app_name]
    
    def get_app_status(self, app_name: str) -> Dict[str, Any]:
        """Get detailed status of an integrated application."""
        app_name = app_name.lower()
        
        # Get registration info
        registered_apps = secure_app_manager.list_registered_apps()
        app_config = registered_apps.get(app_name)
        
        if not app_config:
            return {'status': 'not_registered'}
        
        # Get running status
        with self.integration_lock:
            is_running = app_name in self.running_integrations
            
        status_info = {
            'status': 'running' if is_running else 'registered',
            'display_name': app_config.get('display_name'),
            'category': app_config.get('category'),
            'integration_type': app_config.get('integration_type'),
            'security_level': app_config.get('security_level'),
            'enabled': app_config.get('enabled', True),
            'permissions': app_config.get('permissions', [])
        }
        
        if is_running:
            integration_info = self.running_integrations[app_name]
            status_info.update({
                'pid': integration_info['process'].pid,
                'launched_at': integration_info['launched_at'].isoformat()
            })
        
        return status_info
    
    def auto_start_apps(self):
        """Auto-start applications that are configured for auto-start."""
        try:
            registered_apps = secure_app_manager.list_registered_apps()
            
            for app_name, app_config in registered_apps.items():
                if app_config.get('auto_start', False) and app_config.get('enabled', True):
                    success, message = self.launch_app(app_name)
                    if success:
                        self.logger.info(f"Auto-started {app_name}: {message}")
                    else:
                        self.logger.warning(f"Failed to auto-start {app_name}: {message}")
                        
        except Exception as e:
            self.logger.error(f"Error during auto-start: {e}")

# Global instance
secure_app_integrator = SecureAppIntegrator()