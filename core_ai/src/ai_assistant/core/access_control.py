"""
Access Control System for AI Assistant

Implements role-based access control (RBAC) with fine-grained permissions
for system operations, API endpoints, and sensitive functions.
"""

import json
import os
import threading
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from core.audit_logger import audit_security_event, SeverityLevel
    AUDIT_AVAILABLE = True
except ImportError:
    AUDIT_AVAILABLE = False


class Permission(Enum):
    """System permissions"""
    # System operations
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_RESTART = "system.restart"
    SYSTEM_CONFIG_READ = "system.config.read"
    SYSTEM_CONFIG_WRITE = "system.config.write"
    SYSTEM_COMMAND_EXEC = "system.command.exec"
    SYSTEM_FILE_READ = "system.file.read"
    SYSTEM_FILE_WRITE = "system.file.write"
    SYSTEM_FILE_DELETE = "system.file.delete"
    SYSTEM_APP_LAUNCH = "system.app.launch"
    SYSTEM_PROCESS_KILL = "system.process.kill"
    
    # Data operations
    DATA_MEMORY_READ = "data.memory.read"
    DATA_MEMORY_WRITE = "data.memory.write"
    DATA_MEMORY_DELETE = "data.memory.delete"
    DATA_CONVERSATION_READ = "data.conversation.read"
    DATA_CONVERSATION_WRITE = "data.conversation.write"
    DATA_CONVERSATION_DELETE = "data.conversation.delete"
    DATA_USER_SETTINGS_READ = "data.user_settings.read"
    DATA_USER_SETTINGS_WRITE = "data.user_settings.write"
    DATA_BACKUP_CREATE = "data.backup.create"
    DATA_BACKUP_RESTORE = "data.backup.restore"
    
    # API operations
    API_ADMIN_ACCESS = "api.admin.access"
    API_USER_MANAGEMENT = "api.user.management"
    API_SYSTEM_INFO = "api.system.info"
    API_LOGS_ACCESS = "api.logs.access"
    API_ANALYTICS_READ = "api.analytics.read"
    
    # Automation operations
    AUTOMATION_WORKFLOW_CREATE = "automation.workflow.create"
    AUTOMATION_WORKFLOW_EXECUTE = "automation.workflow.execute"
    AUTOMATION_WORKFLOW_DELETE = "automation.workflow.delete"
    AUTOMATION_SCHEDULE_MANAGE = "automation.schedule.manage"
    
    # Integration operations
    INTEGRATION_CALENDAR_ACCESS = "integration.calendar.access"
    INTEGRATION_EMAIL_SEND = "integration.email.send"
    INTEGRATION_WEB_SEARCH = "integration.web.search"
    INTEGRATION_API_KEYS_MANAGE = "integration.api_keys.manage"
    
    # Security operations
    SECURITY_AUDIT_LOGS_READ = "security.audit_logs.read"
    SECURITY_AUTH_MANAGE = "security.auth.manage"
    SECURITY_PERMISSIONS_MANAGE = "security.permissions.manage"
    SECURITY_ENCRYPTION_MANAGE = "security.encryption.manage"


class Role(Enum):
    """User roles with predefined permission sets"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    AUTOMATION = "automation"
    API_CLIENT = "api_client"


@dataclass
class User:
    """User with role and permissions"""
    user_id: str
    role: Role
    custom_permissions: Set[Permission]
    session_id: Optional[str] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None
    is_active: bool = True
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission"""
        # Admin has all permissions
        if self.role == Role.ADMIN:
            return True
        
        # Check role-based permissions
        role_permissions = get_role_permissions(self.role)
        if permission in role_permissions:
            return True
        
        # Check custom permissions
        return permission in self.custom_permissions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['role'] = self.role.value
        result['custom_permissions'] = [p.value for p in self.custom_permissions]
        return result


class AccessControlManager:
    """
    Central access control manager for the AI Assistant
    
    Features:
    - Role-based permission checking
    - Session management
    - Permission inheritance
    - Audit logging of access attempts
    - Dynamic permission updates
    """
    
    def __init__(self, config_path: str = "config/access_control.json"):
        """Initialize access control manager"""
        self.config_path = Path(config_path)
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, str] = {}  # session_id -> user_id
        self.lock = threading.RLock()
        
        # Load configuration
        self._load_config()
        
        # Create default admin user if none exists
        self._ensure_admin_user()
        
        logger.info("Access control manager initialized")
    
    def _load_config(self):
        """Load access control configuration"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                
                # Load users
                for user_data in config.get('users', []):
                    user = User(
                        user_id=user_data['user_id'],
                        role=Role(user_data['role']),
                        custom_permissions={Permission(p) for p in user_data.get('custom_permissions', [])},
                        created_at=user_data.get('created_at'),
                        last_login=user_data.get('last_login'),
                        is_active=user_data.get('is_active', True)
                    )
                    self.users[user.user_id] = user
                
                logger.info(f"Loaded {len(self.users)} users from config")
            else:
                logger.info("No access control config found, using defaults")
                
        except Exception as e:
            logger.error(f"Failed to load access control config: {e}")
    
    def _save_config(self):
        """Save access control configuration"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config = {
                'users': [user.to_dict() for user in self.users.values()],
                'version': '1.0'
            }
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save access control config: {e}")
    
    def _ensure_admin_user(self):
        """Ensure at least one admin user exists"""
        admin_users = [u for u in self.users.values() if u.role == Role.ADMIN]
        
        if not admin_users:
            # Create default admin user
            admin_user = User(
                user_id="admin",
                role=Role.ADMIN,
                custom_permissions=set(),
                created_at=str(datetime.datetime.now()),
                is_active=True
            )
            self.users["admin"] = admin_user
            self._save_config()
            logger.info("Created default admin user")
    
    def create_user(self, user_id: str, role: Role, 
                   custom_permissions: Optional[Set[Permission]] = None) -> bool:
        """Create a new user"""
        try:
            with self.lock:
                if user_id in self.users:
                    logger.warning(f"User {user_id} already exists")
                    return False
                
                user = User(
                    user_id=user_id,
                    role=role,
                    custom_permissions=custom_permissions or set(),
                    created_at=str(datetime.datetime.now()),
                    is_active=True
                )
                
                self.users[user_id] = user
                self._save_config()
                
                if AUDIT_AVAILABLE:
                    audit_security_event(
                        f"User created: {user_id} with role {role.value}",
                        SeverityLevel.INFO
                    )
                
                logger.info(f"Created user {user_id} with role {role.value}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create user {user_id}: {e}")
            return False
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_by_session(self, session_id: str) -> Optional[User]:
        """Get user by session ID"""
        user_id = self.sessions.get(session_id)
        return self.users.get(user_id) if user_id else None
    
    def create_session(self, user_id: str, session_id: str) -> bool:
        """Create user session"""
        try:
            with self.lock:
                user = self.users.get(user_id)
                if not user or not user.is_active:
                    return False
                
                self.sessions[session_id] = user_id
                user.session_id = session_id
                user.last_login = str(datetime.datetime.now())
                
                if AUDIT_AVAILABLE:
                    audit_security_event(
                        f"Session created for user {user_id}",
                        SeverityLevel.INFO
                    )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to create session for {user_id}: {e}")
            return False
    
    def end_session(self, session_id: str) -> bool:
        """End user session"""
        try:
            with self.lock:
                user_id = self.sessions.pop(session_id, None)
                
                if user_id and user_id in self.users:
                    self.users[user_id].session_id = None
                    
                    if AUDIT_AVAILABLE:
                        audit_security_event(
                            f"Session ended for user {user_id}",
                            SeverityLevel.INFO
                        )
                    
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            return False
    
    def check_permission(self, user_id: str, permission: Permission, 
                        session_id: Optional[str] = None) -> bool:
        """Check if user has specific permission"""
        try:
            with self.lock:
                user = self.users.get(user_id)
                
                if not user or not user.is_active:
                    if AUDIT_AVAILABLE:
                        audit_security_event(
                            f"Permission denied: User {user_id} not found or inactive",
                            SeverityLevel.MEDIUM
                        )
                    return False
                
                # Validate session if provided
                if session_id and user.session_id != session_id:
                    if AUDIT_AVAILABLE:
                        audit_security_event(
                            f"Permission denied: Invalid session for user {user_id}",
                            SeverityLevel.MEDIUM
                        )
                    return False
                
                # Check permission
                has_permission = user.has_permission(permission)
                
                if not has_permission and AUDIT_AVAILABLE:
                    audit_security_event(
                        f"Permission denied: User {user_id} lacks {permission.value}",
                        SeverityLevel.MEDIUM
                    )
                
                return has_permission
                
        except Exception as e:
            logger.error(f"Error checking permission for {user_id}: {e}")
            if AUDIT_AVAILABLE:
                audit_security_event(
                    f"Permission check error for user {user_id}: {str(e)}",
                    SeverityLevel.HIGH
                )
            return False
    
    def grant_permission(self, user_id: str, permission: Permission) -> bool:
        """Grant custom permission to user"""
        try:
            with self.lock:
                user = self.users.get(user_id)
                if not user:
                    return False
                
                user.custom_permissions.add(permission)
                self._save_config()
                
                if AUDIT_AVAILABLE:
                    audit_security_event(
                        f"Permission granted: {permission.value} to user {user_id}",
                        SeverityLevel.INFO
                    )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to grant permission to {user_id}: {e}")
            return False
    
    def revoke_permission(self, user_id: str, permission: Permission) -> bool:
        """Revoke custom permission from user"""
        try:
            with self.lock:
                user = self.users.get(user_id)
                if not user:
                    return False
                
                user.custom_permissions.discard(permission)
                self._save_config()
                
                if AUDIT_AVAILABLE:
                    audit_security_event(
                        f"Permission revoked: {permission.value} from user {user_id}",
                        SeverityLevel.INFO
                    )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to revoke permission from {user_id}: {e}")
            return False
    
    def change_user_role(self, user_id: str, new_role: Role) -> bool:
        """Change user role"""
        try:
            with self.lock:
                user = self.users.get(user_id)
                if not user:
                    return False
                
                old_role = user.role
                user.role = new_role
                self._save_config()
                
                if AUDIT_AVAILABLE:
                    audit_security_event(
                        f"Role changed for user {user_id}: {old_role.value} -> {new_role.value}",
                        SeverityLevel.INFO
                    )
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to change role for {user_id}: {e}")
            return False


def get_role_permissions(role: Role) -> Set[Permission]:
    """Get default permissions for a role"""
    role_permissions = {
        Role.ADMIN: {
            # Admin has all permissions (handled in User.has_permission)
        },
        Role.USER: {
            Permission.DATA_MEMORY_READ,
            Permission.DATA_MEMORY_WRITE,
            Permission.DATA_CONVERSATION_READ,
            Permission.DATA_CONVERSATION_WRITE,
            Permission.DATA_USER_SETTINGS_READ,
            Permission.DATA_USER_SETTINGS_WRITE,
            Permission.SYSTEM_FILE_READ,
            Permission.SYSTEM_APP_LAUNCH,
            Permission.INTEGRATION_CALENDAR_ACCESS,
            Permission.INTEGRATION_EMAIL_SEND,
            Permission.INTEGRATION_WEB_SEARCH,
            Permission.AUTOMATION_WORKFLOW_CREATE,
            Permission.AUTOMATION_WORKFLOW_EXECUTE,
        },
        Role.GUEST: {
            Permission.DATA_MEMORY_READ,
            Permission.DATA_CONVERSATION_READ,
            Permission.SYSTEM_FILE_READ,
            Permission.INTEGRATION_WEB_SEARCH,
        },
        Role.AUTOMATION: {
            Permission.SYSTEM_APP_LAUNCH,
            Permission.SYSTEM_FILE_READ,
            Permission.SYSTEM_FILE_WRITE,
            Permission.AUTOMATION_WORKFLOW_EXECUTE,
            Permission.INTEGRATION_CALENDAR_ACCESS,
            Permission.INTEGRATION_EMAIL_SEND,
        },
        Role.API_CLIENT: {
            Permission.DATA_MEMORY_READ,
            Permission.DATA_CONVERSATION_READ,
            Permission.API_SYSTEM_INFO,
            Permission.INTEGRATION_WEB_SEARCH,
        }
    }
    
    return role_permissions.get(role, set())


# Global access control manager
_access_control = None

def get_access_control() -> AccessControlManager:
    """Get global access control manager"""
    global _access_control
    if _access_control is None:
        _access_control = AccessControlManager()
    return _access_control


def require_permission(permission: Permission, user_id_param: str = 'user_id', 
                      session_id_param: str = 'session_id'):
    """
    Decorator to require permission for function execution
    
    Args:
        permission: Required permission
        user_id_param: Name of parameter containing user ID
        session_id_param: Name of parameter containing session ID
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract user_id and session_id from parameters
            user_id = kwargs.get(user_id_param)
            session_id = kwargs.get(session_id_param)
            
            # Check if user_id is in positional args
            if not user_id and len(args) > 0:
                # Try to get from first argument if it's a string
                if isinstance(args[0], str):
                    user_id = args[0]
            
            if not user_id:
                logger.error(f"No user_id provided for permission check: {permission.value}")
                raise PermissionError("User ID required for access control")
            
            # Check permission
            access_control = get_access_control()
            if not access_control.check_permission(user_id, permission, session_id):
                logger.warning(f"Permission denied for user {user_id}: {permission.value}")
                raise PermissionError(f"Insufficient permissions: {permission.value}")
            
            # Execute function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# Convenience decorators for common permissions
def require_admin(func: Callable) -> Callable:
    """Require admin role"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # This is a shortcut - admin users have all permissions
        user_id = kwargs.get('user_id') or (args[0] if args and isinstance(args[0], str) else None)
        if not user_id:
            raise PermissionError("User ID required")
        
        access_control = get_access_control()
        user = access_control.get_user(user_id)
        
        if not user or user.role != Role.ADMIN:
            logger.warning(f"Admin access denied for user {user_id}")
            raise PermissionError("Admin access required")
        
        return func(*args, **kwargs)
    return wrapper


def require_system_access(func: Callable) -> Callable:
    """Require system command execution permission"""
    return require_permission(Permission.SYSTEM_COMMAND_EXEC)(func)


def require_file_write(func: Callable) -> Callable:
    """Require file write permission"""
    return require_permission(Permission.SYSTEM_FILE_WRITE)(func)


def require_data_access(func: Callable) -> Callable:
    """Require data read permission"""
    return require_permission(Permission.DATA_MEMORY_READ)(func)


if __name__ == "__main__":
    # Test access control system
    print("Testing access control system...")
    
    import datetime
    
    # Create access control manager
    acm = AccessControlManager()
    
    # Create test users
    acm.create_user("test_admin", Role.ADMIN)
    acm.create_user("test_user", Role.USER)
    acm.create_user("test_guest", Role.GUEST)
    
    # Test permissions
    print(f"Admin system access: {acm.check_permission('test_admin', Permission.SYSTEM_COMMAND_EXEC)}")
    print(f"User system access: {acm.check_permission('test_user', Permission.SYSTEM_COMMAND_EXEC)}")
    print(f"Guest system access: {acm.check_permission('test_guest', Permission.SYSTEM_COMMAND_EXEC)}")
    
    # Test session management
    acm.create_session("test_user", "session_123")
    print(f"User with session: {acm.check_permission('test_user', Permission.DATA_MEMORY_READ, 'session_123')}")
    
    # Test decorator
    @require_permission(Permission.SYSTEM_COMMAND_EXEC)
    def test_system_command(user_id: str):
        return f"System command executed by {user_id}"
    
    try:
        result = test_system_command(user_id="test_admin")
        print(f"Admin command result: {result}")
    except PermissionError as e:
        print(f"Admin command failed: {e}")
    
    try:
        result = test_system_command(user_id="test_guest")
        print(f"Guest command result: {result}")
    except PermissionError as e:
        print(f"Guest command failed: {e}")
    
    print("✅ Access control test completed!")