"""
Centralized Permission and Authorization System

This module provides a comprehensive permission system for all system-level operations,
including file operations, application execution, system commands, and API calls.

Author: YourDaddy AI Assistant Team
Date: January 9, 2026
"""

import enum
import json
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class PermissionLevel(enum.Enum):
    """Permission levels for operations"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"


class RiskLevel(enum.Enum):
    """Risk levels for operations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class OperationRequest:
    """Represents a request to perform an operation"""
    operation_type: str
    resource: str
    permission_level: PermissionLevel
    risk_level: RiskLevel
    description: str
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class PermissionResult:
    """Result of a permission check"""
    granted: bool
    reason: str
    requires_confirmation: bool = False
    confirmation_message: Optional[str] = None


class PermissionPolicy:
    """Defines permission policies for different operation types"""
    
    def __init__(self):
        self.policies = self._load_default_policies()
    
    def _load_default_policies(self) -> Dict[str, Dict]:
        """Load default permission policies"""
        return {
            # File operations
            "file_read": {
                "permission_level": PermissionLevel.READ,
                "risk_level": RiskLevel.LOW,
                "requires_confirmation": False
            },
            "file_write": {
                "permission_level": PermissionLevel.WRITE,
                "risk_level": RiskLevel.MEDIUM,
                "requires_confirmation": True
            },
            "file_delete": {
                "permission_level": PermissionLevel.DELETE,
                "risk_level": RiskLevel.HIGH,
                "requires_confirmation": True
            },
            
            # Application operations
            "app_launch": {
                "permission_level": PermissionLevel.EXECUTE,
                "risk_level": RiskLevel.MEDIUM,
                "requires_confirmation": True
            },
            "app_close": {
                "permission_level": PermissionLevel.EXECUTE,
                "risk_level": RiskLevel.LOW,
                "requires_confirmation": False
            },
            
            # System operations
            "system_command": {
                "permission_level": PermissionLevel.ADMIN,
                "risk_level": RiskLevel.CRITICAL,
                "requires_confirmation": True
            },
            "system_setting": {
                "permission_level": PermissionLevel.ADMIN,
                "risk_level": RiskLevel.HIGH,
                "requires_confirmation": True
            },
            
            # External API operations
            "external_api_call": {
                "permission_level": PermissionLevel.EXECUTE,
                "risk_level": RiskLevel.MEDIUM,
                "requires_confirmation": False
            },
            "audio_transmission": {
                "permission_level": PermissionLevel.EXECUTE,
                "risk_level": RiskLevel.HIGH,
                "requires_confirmation": True
            },
            "biometric_storage": {
                "permission_level": PermissionLevel.WRITE,
                "risk_level": RiskLevel.CRITICAL,
                "requires_confirmation": True
            },
        }
    
    def get_policy(self, operation_type: str) -> Optional[Dict]:
        """Get policy for an operation type"""
        return self.policies.get(operation_type)


class PermissionSystem:
    """
    Centralized permission and authorization system
    
    This system manages permissions for all sensitive operations including:
    - File system operations (read, write, delete)
    - Application execution
    - System commands
    - External API calls
    - Biometric data storage
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.policy = PermissionPolicy()
        self.user_permissions: Dict[str, List[PermissionLevel]] = {}
        self.operation_whitelist: Dict[str, List[str]] = {}
        self.operation_blacklist: Dict[str, List[str]] = {}
        self.config_path = config_path or Path("user_data/permissions.json")
        self._load_permissions()
        
        logger.info("Permission system initialized")
    
    def _load_permissions(self):
        """Load user permissions from config file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                    self.user_permissions = {
                        k: [PermissionLevel(v) for v in vals]
                        for k, vals in data.get('user_permissions', {}).items()
                    }
                    self.operation_whitelist = data.get('whitelist', {})
                    self.operation_blacklist = data.get('blacklist', {})
                    logger.info("User permissions loaded from config")
        except Exception as e:
            logger.error(f"Error loading permissions: {e}")
    
    def _save_permissions(self):
        """Save user permissions to config file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'user_permissions': {
                    k: [v.value for v in vals]
                    for k, vals in self.user_permissions.items()
                },
                'whitelist': self.operation_whitelist,
                'blacklist': self.operation_blacklist,
                'updated_at': datetime.now().isoformat()
            }
            with open(self.config_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info("User permissions saved to config")
        except Exception as e:
            logger.error(f"Error saving permissions: {e}")
    
    def check_permission(self, request: OperationRequest) -> PermissionResult:
        """
        Check if an operation is permitted
        
        Args:
            request: OperationRequest containing operation details
            
        Returns:
            PermissionResult with grant status and reason
        """
        # Check blacklist first
        if self._is_blacklisted(request.operation_type, request.resource):
            return PermissionResult(
                granted=False,
                reason=f"Operation '{request.operation_type}' on '{request.resource}' is blacklisted",
                requires_confirmation=False
            )
        
        # Get policy for operation type
        policy = self.policy.get_policy(request.operation_type)
        if not policy:
            logger.warning(f"No policy defined for operation: {request.operation_type}")
            # Default to requiring confirmation for unknown operations
            return PermissionResult(
                granted=False,
                reason=f"No policy defined for operation: {request.operation_type}",
                requires_confirmation=True,
                confirmation_message=f"Allow {request.description}?"
            )
        
        # Check user has required permission level
        user_id = request.user_id or "default"
        user_perms = self.user_permissions.get(user_id, [PermissionLevel.READ])
        required_perm = policy['permission_level']
        
        if required_perm not in user_perms and PermissionLevel.ADMIN not in user_perms:
            return PermissionResult(
                granted=False,
                reason=f"User lacks required permission: {required_perm.value}",
                requires_confirmation=False
            )
        
        # Check if whitelisted (auto-approve)
        if self._is_whitelisted(request.operation_type, request.resource):
            return PermissionResult(
                granted=True,
                reason="Operation is whitelisted",
                requires_confirmation=False
            )
        
        # Check if confirmation required
        requires_confirmation = policy.get('requires_confirmation', False)
        
        if requires_confirmation:
            confirmation_msg = self._generate_confirmation_message(request, policy)
            return PermissionResult(
                granted=False,  # Requires user confirmation
                reason="User confirmation required",
                requires_confirmation=True,
                confirmation_message=confirmation_msg
            )
        
        # Grant permission
        return PermissionResult(
            granted=True,
            reason="Permission granted by policy",
            requires_confirmation=False
        )
    
    def _is_blacklisted(self, operation_type: str, resource: str) -> bool:
        """Check if operation/resource is blacklisted"""
        blacklist = self.operation_blacklist.get(operation_type, [])
        return resource in blacklist or "*" in blacklist
    
    def _is_whitelisted(self, operation_type: str, resource: str) -> bool:
        """Check if operation/resource is whitelisted"""
        whitelist = self.operation_whitelist.get(operation_type, [])
        return resource in whitelist
    
    def _generate_confirmation_message(self, request: OperationRequest, policy: Dict) -> str:
        """Generate user-friendly confirmation message"""
        risk_emoji = {
            RiskLevel.LOW: "ℹ️",
            RiskLevel.MEDIUM: "⚠️",
            RiskLevel.HIGH: "🔴",
            RiskLevel.CRITICAL: "🚨"
        }
        
        emoji = risk_emoji.get(request.risk_level, "❓")
        
        message = f"{emoji} {request.description}\n\n"
        message += f"Operation: {request.operation_type}\n"
        message += f"Resource: {request.resource}\n"
        message += f"Risk Level: {request.risk_level.value.upper()}\n\n"
        message += "Do you want to proceed?"
        
        return message
    
    def grant_user_permission(self, user_id: str, permission: PermissionLevel):
        """Grant a permission level to a user"""
        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = []
        
        if permission not in self.user_permissions[user_id]:
            self.user_permissions[user_id].append(permission)
            self._save_permissions()
            logger.info(f"Granted {permission.value} permission to user {user_id}")
    
    def revoke_user_permission(self, user_id: str, permission: PermissionLevel):
        """Revoke a permission level from a user"""
        if user_id in self.user_permissions and permission in self.user_permissions[user_id]:
            self.user_permissions[user_id].remove(permission)
            self._save_permissions()
            logger.info(f"Revoked {permission.value} permission from user {user_id}")
    
    def add_to_whitelist(self, operation_type: str, resource: str):
        """Add an operation/resource to whitelist"""
        if operation_type not in self.operation_whitelist:
            self.operation_whitelist[operation_type] = []
        
        if resource not in self.operation_whitelist[operation_type]:
            self.operation_whitelist[operation_type].append(resource)
            self._save_permissions()
            logger.info(f"Added {resource} to {operation_type} whitelist")
    
    def add_to_blacklist(self, operation_type: str, resource: str):
        """Add an operation/resource to blacklist"""
        if operation_type not in self.operation_blacklist:
            self.operation_blacklist[operation_type] = []
        
        if resource not in self.operation_blacklist[operation_type]:
            self.operation_blacklist[operation_type].append(resource)
            self._save_permissions()
            logger.warning(f"Added {resource} to {operation_type} blacklist")
    
    def request_user_confirmation(self, confirmation_message: str, 
                                  timeout: int = 30) -> bool:
        """
        Request user confirmation for an operation
        
        Args:
            confirmation_message: Message to display to user
            timeout: Timeout in seconds
            
        Returns:
            True if user confirms, False otherwise
        """
        # This is a placeholder - actual implementation would integrate with UI
        # For now, we'll log the request
        logger.warning(f"USER CONFIRMATION REQUIRED: {confirmation_message}")
        
        # In a real implementation, this would:
        # 1. Send message to frontend via WebSocket
        # 2. Wait for user response with timeout
        # 3. Return user's decision
        
        # For testing purposes, return False (deny by default)
        return False


# Global permission system instance
_permission_system_instance: Optional[PermissionSystem] = None


def get_permission_system() -> PermissionSystem:
    """Get global permission system instance (singleton)"""
    global _permission_system_instance
    if _permission_system_instance is None:
        _permission_system_instance = PermissionSystem()
    return _permission_system_instance


def require_permission(operation_type: str, risk_level: RiskLevel = RiskLevel.MEDIUM):
    """
    Decorator to require permission for a function
    
    Usage:
        @require_permission("file_delete", RiskLevel.HIGH)
        def delete_file(path: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            permission_system = get_permission_system()
            
            # Extract resource from function arguments
            resource = str(args[0]) if args else "unknown"
            
            request = OperationRequest(
                operation_type=operation_type,
                resource=resource,
                permission_level=PermissionLevel.EXECUTE,
                risk_level=risk_level,
                description=f"{func.__name__} on {resource}"
            )
            
            result = permission_system.check_permission(request)
            
            if result.requires_confirmation:
                if not permission_system.request_user_confirmation(result.confirmation_message):
                    raise PermissionError(f"User denied permission for {operation_type}")
            
            if not result.granted:
                raise PermissionError(f"Permission denied: {result.reason}")
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
