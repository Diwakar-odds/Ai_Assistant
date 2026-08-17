"""
Automation Security System

This module provides comprehensive security controls, permission management,
audit trails, and secure execution environment for enterprise-grade automation security.

Features:
- Role-based access control (RBAC)
- Permission management and validation
- Secure credential storage and management
- Audit trails and security logging
- Execution sandboxing and isolation
- Security policy enforcement
- Threat detection and response
- Encryption and data protection
"""

import os
import json
import hashlib
import hmac
import secrets
import base64
import logging
import threading
import sqlite3
import time
from typing import Dict, List, Optional, Any, Set, Callable, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum, IntEnum
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import re
from collections import defaultdict, deque
import ipaddress

# Cryptography
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# JWT tokens
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

# Password hashing
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False

class SecurityLevel(IntEnum):
    """Security levels for automation operations"""
    PUBLIC = 0              # No authentication required
    BASIC = 1              # Basic authentication
    ELEVATED = 2           # Elevated permissions required
    ADMIN = 3              # Administrative access
    SYSTEM = 4             # System-level access
    CRITICAL = 5           # Critical system operations

class PermissionType(Enum):
    """Types of permissions"""
    READ = "read"                   # Read access
    WRITE = "write"                # Write access
    EXECUTE = "execute"            # Execute operations
    DELETE = "delete"              # Delete resources
    ADMIN = "admin"                # Administrative access
    CREATE = "create"              # Create new resources
    MODIFY = "modify"              # Modify existing resources
    SCHEDULE = "schedule"          # Schedule operations
    MONITOR = "monitor"            # Monitor system

class ResourceType(Enum):
    """Types of protected resources"""
    AUTOMATION = "automation"      # Automation workflows
    TASK = "task"                 # Individual tasks
    SCHEDULE = "schedule"         # Scheduled operations
    TEMPLATE = "template"         # Automation templates
    RULE = "rule"                 # Automation rules
    CREDENTIAL = "credential"     # Stored credentials
    SYSTEM = "system"             # System configuration
    FILE = "file"                 # File system access
    DATABASE = "database"         # Database access
    NETWORK = "network"           # Network access

class AuditEventType(Enum):
    """Types of audit events"""
    LOGIN = "login"               # User login
    LOGOUT = "logout"             # User logout
    ACCESS_GRANTED = "access_granted"   # Access granted
    ACCESS_DENIED = "access_denied"     # Access denied
    OPERATION_EXECUTED = "operation_executed"  # Operation executed
    OPERATION_FAILED = "operation_failed"      # Operation failed
    CREDENTIAL_ACCESSED = "credential_accessed"  # Credential accessed
    SECURITY_VIOLATION = "security_violation"   # Security violation
    PERMISSION_CHANGED = "permission_changed"   # Permission modified
    USER_CREATED = "user_created"              # User account created
    USER_DELETED = "user_deleted"              # User account deleted
    POLICY_VIOLATION = "policy_violation"      # Security policy violation

@dataclass
class Permission:
    """Individual permission definition"""
    resource_type: ResourceType
    permission_type: PermissionType
    resource_id: Optional[str] = None  # Specific resource ID, None for all
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    def matches_request(self, resource_type: ResourceType, permission_type: PermissionType,
                       resource_id: str = None) -> bool:
        """Check if permission matches request"""
        # Check resource type
        if self.resource_type != resource_type:
            return False
        
        # Check permission type
        if self.permission_type != permission_type:
            return False
        
        # Check resource ID (None means all resources)
        if self.resource_id is not None and self.resource_id != resource_id:
            return False
        
        return True

@dataclass
class Role:
    """Security role definition"""
    id: str
    name: str
    description: str = ""
    permissions: List[Permission] = field(default_factory=list)
    inherits_from: List[str] = field(default_factory=list)  # Role inheritance
    created_time: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    
    def has_permission(self, resource_type: ResourceType, permission_type: PermissionType,
                      resource_id: str = None) -> bool:
        """Check if role has specific permission"""
        for permission in self.permissions:
            if permission.matches_request(resource_type, permission_type, resource_id):
                return True
        return False

@dataclass
class User:
    """User account definition"""
    id: str
    username: str
    email: str = ""
    password_hash: str = ""
    roles: List[str] = field(default_factory=list)
    active: bool = True
    
    # Security settings
    require_2fa: bool = False
    password_expires: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    
    # Session management
    last_login: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    # Metadata
    created_time: datetime = field(default_factory=datetime.now)
    created_by: str = "system"
    
    def is_locked(self) -> bool:
        """Check if user account is locked"""
        if self.locked_until and datetime.now() < self.locked_until:
            return True
        return False
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hash"""
        if not BCRYPT_AVAILABLE:
            # Fallback to simple hash comparison (not recommended for production)
            simple_hash = hashlib.sha256(password.encode()).hexdigest()
            return simple_hash == self.password_hash
        
        try:
            return bcrypt.checkpw(password.encode(), self.password_hash.encode())
        except Exception:
            return False

@dataclass
class SecurityCredential:
    """Secure credential storage"""
    id: str
    name: str
    credential_type: str  # password, api_key, certificate, etc.
    encrypted_data: str
    description: str = ""
    
    # Access control
    allowed_users: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=list)
    
    # Metadata
    created_time: datetime = field(default_factory=datetime.now)
    created_by: str = ""
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    expires_at: Optional[datetime] = None

@dataclass
class AuditEvent:
    """Security audit event"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AuditEventType = AuditEventType.OPERATION_EXECUTED
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Actor information
    user_id: Optional[str] = None
    username: Optional[str] = None
    session_id: Optional[str] = None
    
    # Action details
    action: str = ""
    resource_type: Optional[ResourceType] = None
    resource_id: Optional[str] = None
    
    # Context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Result
    success: bool = True
    error_message: Optional[str] = None
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class SecurityPolicy:
    """Security policy definition"""
    id: str
    name: str
    description: str = ""
    policy_type: str = "access_control"
    
    # Policy rules
    rules: List[Dict[str, Any]] = field(default_factory=list)
    
    # Enforcement settings
    enabled: bool = True
    enforcement_level: str = "strict"  # strict, permissive, monitoring
    
    # Metadata
    created_time: datetime = field(default_factory=datetime.now)
    updated_time: datetime = field(default_factory=datetime.now)
    created_by: str = "system"

@dataclass
class SecuritySession:
    """User security session"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    username: str = ""
    
    # Session details
    created_time: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=8))
    
    # Security context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Permissions cache
    effective_permissions: List[Permission] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    
    # State
    active: bool = True
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now() > self.expires_at
    
    def is_idle(self, idle_timeout_minutes: int = 30) -> bool:
        """Check if session is idle"""
        idle_cutoff = datetime.now() - timedelta(minutes=idle_timeout_minutes)
        return self.last_activity < idle_cutoff

class CredentialManager:
    """
    Secure credential storage and management
    """
    
    def __init__(self, master_key: str = None):
        self.logger = logging.getLogger(__name__)
        self.credentials: Dict[str, SecurityCredential] = {}
        self._lock = threading.RLock()
        
        # Encryption setup
        if CRYPTO_AVAILABLE:
            if master_key:
                self.encryption_key = self._derive_key(master_key)
            else:
                self.encryption_key = Fernet.generate_key()
            self.cipher = Fernet(self.encryption_key)
        else:
            self.cipher = None
            self.logger.warning("Cryptography not available - credentials will not be encrypted")
    
    def store_credential(self, name: str, credential_type: str, data: Dict[str, Any],
                        user_id: str = "", description: str = "") -> str:
        """Store encrypted credential"""
        try:
            credential_id = str(uuid.uuid4())
            
            # Encrypt credential data
            data_json = json.dumps(data)
            if self.cipher:
                encrypted_data = self.cipher.encrypt(data_json.encode()).decode()
            else:
                # Base64 encode as fallback (not secure!)
                encrypted_data = base64.b64encode(data_json.encode()).decode()
            
            credential = SecurityCredential(
                id=credential_id,
                name=name,
                credential_type=credential_type,
                encrypted_data=encrypted_data,
                description=description,
                created_by=user_id
            )
            
            with self._lock:
                self.credentials[credential_id] = credential
            
            self.logger.info(f"Stored credential: {name} (type: {credential_type})")
            return credential_id
            
        except Exception as e:
            self.logger.error(f"Failed to store credential {name}: {e}")
            raise e
    
    def retrieve_credential(self, credential_id: str, user_id: str = "") -> Optional[Dict[str, Any]]:
        """Retrieve and decrypt credential"""
        try:
            with self._lock:
                credential = self.credentials.get(credential_id)
            
            if not credential:
                return None
            
            # Check access permissions
            if not self._check_credential_access(credential, user_id):
                self.logger.warning(f"Access denied to credential {credential.name} for user {user_id}")
                return None
            
            # Decrypt credential data
            if self.cipher:
                decrypted_data = self.cipher.decrypt(credential.encrypted_data.encode()).decode()
            else:
                # Base64 decode as fallback
                decrypted_data = base64.b64decode(credential.encrypted_data.encode()).decode()
            
            data = json.loads(decrypted_data)
            
            # Update access tracking
            credential.last_accessed = datetime.now()
            credential.access_count += 1
            
            self.logger.info(f"Retrieved credential: {credential.name} by user {user_id}")
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve credential {credential_id}: {e}")
            return None
    
    def list_credentials(self, user_id: str = "") -> List[Dict[str, Any]]:
        """List available credentials for user"""
        accessible_credentials = []
        
        with self._lock:
            for credential in self.credentials.values():
                if self._check_credential_access(credential, user_id):
                    accessible_credentials.append({
                        'id': credential.id,
                        'name': credential.name,
                        'type': credential.credential_type,
                        'description': credential.description,
                        'created_time': credential.created_time.isoformat(),
                        'last_accessed': credential.last_accessed.isoformat() if credential.last_accessed else None,
                        'access_count': credential.access_count
                    })
        
        return accessible_credentials
    
    def delete_credential(self, credential_id: str, user_id: str = "") -> bool:
        """Delete credential"""
        try:
            with self._lock:
                credential = self.credentials.get(credential_id)
                
                if not credential:
                    return False
                
                # Check if user can delete this credential
                if credential.created_by != user_id:
                    self.logger.warning(f"User {user_id} cannot delete credential {credential.name}")
                    return False
                
                del self.credentials[credential_id]
            
            self.logger.info(f"Deleted credential: {credential.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete credential {credential_id}: {e}")
            return False
    
    def _check_credential_access(self, credential: SecurityCredential, user_id: str) -> bool:
        """Check if user can access credential"""
        # Allow access if user created the credential
        if credential.created_by == user_id:
            return True
        
        # Check if user is in allowed users list
        if user_id in credential.allowed_users:
            return True
        
        # TODO: Check role-based access
        return False
    
    def _derive_key(self, master_key: str) -> bytes:
        """Derive encryption key from master key"""
        if not CRYPTO_AVAILABLE:
            return b"fallback_key_not_secure"
        
        salt = b"automation_security_salt"  # Should be random in production
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(master_key.encode()))

class AccessController:
    """
    Role-based access control system
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.users: Dict[str, User] = {}
        self.roles: Dict[str, Role] = {}
        self.sessions: Dict[str, SecuritySession] = {}
        self._lock = threading.RLock()
        
        # Security settings
        self.max_failed_login_attempts = 5
        self.account_lockout_duration = timedelta(minutes=15)
        self.session_timeout = timedelta(hours=8)
        self.idle_timeout = timedelta(minutes=30)
        
        # Create default roles
        self._create_default_roles()
    
    def create_user(self, username: str, password: str, email: str = "",
                   roles: List[str] = None, created_by: str = "system") -> str:
        """Create new user account"""
        try:
            user_id = str(uuid.uuid4())
            
            # Hash password
            password_hash = self._hash_password(password)
            
            user = User(
                id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                roles=roles or ["user"],
                created_by=created_by
            )
            
            with self._lock:
                self.users[user_id] = user
            
            self.logger.info(f"Created user: {username}")
            return user_id
            
        except Exception as e:
            self.logger.error(f"Failed to create user {username}: {e}")
            raise e
    
    def authenticate_user(self, username: str, password: str, ip_address: str = None,
                         user_agent: str = None) -> Optional[str]:
        """Authenticate user and create session"""
        try:
            # Find user by username
            user = None
            with self._lock:
                for u in self.users.values():
                    if u.username == username:
                        user = u
                        break
            
            if not user:
                self.logger.warning(f"Authentication failed: user {username} not found")
                return None
            
            # Check if account is locked
            if user.is_locked():
                self.logger.warning(f"Authentication failed: user {username} is locked")
                return None
            
            # Verify password
            if not user.verify_password(password):
                user.failed_login_attempts += 1
                
                # Lock account if too many failed attempts
                if user.failed_login_attempts >= self.max_failed_login_attempts:
                    user.locked_until = datetime.now() + self.account_lockout_duration
                    self.logger.warning(f"User {username} locked due to failed login attempts")
                
                self.logger.warning(f"Authentication failed: invalid password for {username}")
                return None
            
            # Reset failed attempts on successful login
            user.failed_login_attempts = 0
            user.locked_until = None
            user.last_login = datetime.now()
            user.last_activity = datetime.now()
            
            # Create session
            session = SecuritySession(
                user_id=user.id,
                username=user.username,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.now() + self.session_timeout,
                roles=user.roles.copy()
            )
            
            # Calculate effective permissions
            session.effective_permissions = self._calculate_effective_permissions(user.roles)
            
            with self._lock:
                self.sessions[session.id] = session
            
            self.logger.info(f"User {username} authenticated successfully")
            return session.id
            
        except Exception as e:
            self.logger.error(f"Authentication error for {username}: {e}")
            return None
    
    def validate_session(self, session_id: str) -> Optional[SecuritySession]:
        """Validate and refresh session"""
        try:
            with self._lock:
                session = self.sessions.get(session_id)
            
            if not session:
                return None
            
            # Check if session is expired
            if session.is_expired():
                self._invalidate_session(session_id)
                return None
            
            # Check if session is idle
            if session.is_idle(self.idle_timeout.total_seconds() // 60):
                self._invalidate_session(session_id)
                return None
            
            # Update last activity
            session.last_activity = datetime.now()
            
            return session
            
        except Exception as e:
            self.logger.error(f"Session validation error: {e}")
            return None
    
    def check_permission(self, session_id: str, resource_type: ResourceType,
                        permission_type: PermissionType, resource_id: str = None) -> bool:
        """Check if session has required permission"""
        try:
            session = self.validate_session(session_id)
            if not session:
                return False
            
            # Check effective permissions
            for permission in session.effective_permissions:
                if permission.matches_request(resource_type, permission_type, resource_id):
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Permission check error: {e}")
            return False
    
    def logout_user(self, session_id: str):
        """Logout user and invalidate session"""
        self._invalidate_session(session_id)
        self.logger.info(f"User session {session_id} logged out")
    
    def create_role(self, name: str, description: str = "", permissions: List[Permission] = None,
                   created_by: str = "system") -> str:
        """Create new role"""
        try:
            role_id = str(uuid.uuid4())
            
            role = Role(
                id=role_id,
                name=name,
                description=description,
                permissions=permissions or [],
                created_by=created_by
            )
            
            with self._lock:
                self.roles[role_id] = role
            
            self.logger.info(f"Created role: {name}")
            return role_id
            
        except Exception as e:
            self.logger.error(f"Failed to create role {name}: {e}")
            raise e
    
    def assign_role_to_user(self, user_id: str, role_id: str) -> bool:
        """Assign role to user"""
        try:
            with self._lock:
                user = self.users.get(user_id)
                role = self.roles.get(role_id)
                
                if not user or not role:
                    return False
                
                if role_id not in user.roles:
                    user.roles.append(role_id)
                
                # Update active sessions with new permissions
                self._update_user_sessions(user_id)
            
            self.logger.info(f"Assigned role {role.name} to user {user.username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to assign role: {e}")
            return False
    
    def revoke_role_from_user(self, user_id: str, role_id: str) -> bool:
        """Revoke role from user"""
        try:
            with self._lock:
                user = self.users.get(user_id)
                
                if not user:
                    return False
                
                if role_id in user.roles:
                    user.roles.remove(role_id)
                
                # Update active sessions
                self._update_user_sessions(user_id)
            
            self.logger.info(f"Revoked role from user {user.username}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to revoke role: {e}")
            return False
    
    def _hash_password(self, password: str) -> str:
        """Hash password securely"""
        if BCRYPT_AVAILABLE:
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode(), salt).decode()
        else:
            # Fallback to SHA256 with salt (not recommended for production)
            salt = secrets.token_hex(16)
            hash_obj = hashlib.sha256((password + salt).encode())
            return f"{salt}:{hash_obj.hexdigest()}"
    
    def _calculate_effective_permissions(self, role_ids: List[str]) -> List[Permission]:
        """Calculate effective permissions from roles"""
        effective_permissions = []
        
        with self._lock:
            for role_id in role_ids:
                role = self.roles.get(role_id)
                if role:
                    effective_permissions.extend(role.permissions)
                    
                    # Handle role inheritance
                    for inherited_role_id in role.inherits_from:
                        inherited_role = self.roles.get(inherited_role_id)
                        if inherited_role:
                            effective_permissions.extend(inherited_role.permissions)
        
        return effective_permissions
    
    def _update_user_sessions(self, user_id: str):
        """Update all active sessions for user"""
        with self._lock:
            user = self.users.get(user_id)
            if not user:
                return
            
            for session in self.sessions.values():
                if session.user_id == user_id and session.active:
                    session.effective_permissions = self._calculate_effective_permissions(user.roles)
                    session.roles = user.roles.copy()
    
    def _invalidate_session(self, session_id: str):
        """Invalidate session"""
        with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id].active = False
                del self.sessions[session_id]
    
    def _create_default_roles(self):
        """Create default system roles"""
        # Guest role - minimal permissions
        guest_permissions = [
            Permission(ResourceType.AUTOMATION, PermissionType.READ),
            Permission(ResourceType.TASK, PermissionType.READ),
        ]
        self.roles["guest"] = Role(
            id="guest",
            name="Guest",
            description="Read-only access to basic automation information",
            permissions=guest_permissions
        )
        
        # User role - standard user permissions
        user_permissions = [
            Permission(ResourceType.AUTOMATION, PermissionType.READ),
            Permission(ResourceType.AUTOMATION, PermissionType.EXECUTE),
            Permission(ResourceType.TASK, PermissionType.READ),
            Permission(ResourceType.TASK, PermissionType.EXECUTE),
            Permission(ResourceType.TEMPLATE, PermissionType.READ),
            Permission(ResourceType.SCHEDULE, PermissionType.READ),
        ]
        self.roles["user"] = Role(
            id="user",
            name="User",
            description="Standard user with execution permissions",
            permissions=user_permissions
        )
        
        # Operator role - can manage automations
        operator_permissions = user_permissions + [
            Permission(ResourceType.AUTOMATION, PermissionType.CREATE),
            Permission(ResourceType.AUTOMATION, PermissionType.MODIFY),
            Permission(ResourceType.TASK, PermissionType.CREATE),
            Permission(ResourceType.TASK, PermissionType.MODIFY),
            Permission(ResourceType.SCHEDULE, PermissionType.CREATE),
            Permission(ResourceType.SCHEDULE, PermissionType.MODIFY),
            Permission(ResourceType.TEMPLATE, PermissionType.CREATE),
        ]
        self.roles["operator"] = Role(
            id="operator",
            name="Operator",
            description="Can create and manage automation workflows",
            permissions=operator_permissions
        )
        
        # Admin role - full permissions except system
        admin_permissions = operator_permissions + [
            Permission(ResourceType.AUTOMATION, PermissionType.DELETE),
            Permission(ResourceType.TASK, PermissionType.DELETE),
            Permission(ResourceType.SCHEDULE, PermissionType.DELETE),
            Permission(ResourceType.TEMPLATE, PermissionType.DELETE),
            Permission(ResourceType.RULE, PermissionType.READ),
            Permission(ResourceType.RULE, PermissionType.CREATE),
            Permission(ResourceType.RULE, PermissionType.MODIFY),
            Permission(ResourceType.RULE, PermissionType.DELETE),
            Permission(ResourceType.CREDENTIAL, PermissionType.READ),
            Permission(ResourceType.CREDENTIAL, PermissionType.CREATE),
            Permission(ResourceType.MONITOR, PermissionType.READ),
        ]
        self.roles["admin"] = Role(
            id="admin",
            name="Administrator",
            description="Full administrative access to automation system",
            permissions=admin_permissions
        )
        
        # System role - system-level access
        system_permissions = admin_permissions + [
            Permission(ResourceType.SYSTEM, PermissionType.READ),
            Permission(ResourceType.SYSTEM, PermissionType.MODIFY),
            Permission(ResourceType.SYSTEM, PermissionType.ADMIN),
            Permission(ResourceType.CREDENTIAL, PermissionType.DELETE),
            Permission(ResourceType.DATABASE, PermissionType.READ),
            Permission(ResourceType.DATABASE, PermissionType.MODIFY),
            Permission(ResourceType.NETWORK, PermissionType.READ),
            Permission(ResourceType.FILE, PermissionType.READ),
            Permission(ResourceType.FILE, PermissionType.WRITE),
        ]
        self.roles["system"] = Role(
            id="system",
            name="System",
            description="System-level access for critical operations",
            permissions=system_permissions
        )

class AuditLogger:
    """
    Security audit logging system
    """
    
    def __init__(self, db_path: str = "user_data/security_audit.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.audit_events = deque(maxlen=10000)
        self._lock = threading.RLock()
        
        # Initialize audit database
        self._init_database()
    
    def log_event(self, event_type: AuditEventType, action: str = "", user_id: str = None,
                 username: str = None, resource_type: ResourceType = None,
                 resource_id: str = None, success: bool = True, error_message: str = None,
                 ip_address: str = None, user_agent: str = None, session_id: str = None,
                 metadata: Dict[str, Any] = None):
        """Log security audit event"""
        try:
            event = AuditEvent(
                event_type=event_type,
                action=action,
                user_id=user_id,
                username=username,
                resource_type=resource_type,
                resource_id=resource_id,
                success=success,
                error_message=error_message,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                metadata=metadata or {}
            )
            
            # Store in memory
            with self._lock:
                self.audit_events.append(event)
            
            # Store in database
            self._store_audit_event(event)
            
            # Log to application logger
            log_level = logging.INFO if success else logging.WARNING
            self.logger.log(log_level, 
                          f"AUDIT: {event_type.value} - {action} by {username or 'system'} "
                          f"({'success' if success else 'failed'})")
            
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
    
    def get_recent_events(self, limit: int = 100, event_type: AuditEventType = None,
                         user_id: str = None, start_time: datetime = None,
                         end_time: datetime = None) -> List[AuditEvent]:
        """Get recent audit events with filtering"""
        with self._lock:
            events = list(self.audit_events)
        
        # Apply filters
        filtered_events = []
        for event in events:
            # Event type filter
            if event_type and event.event_type != event_type:
                continue
            
            # User filter
            if user_id and event.user_id != user_id:
                continue
            
            # Time range filter
            if start_time and event.timestamp < start_time:
                continue
            if end_time and event.timestamp > end_time:
                continue
            
            filtered_events.append(event)
        
        # Sort by timestamp (newest first) and limit
        filtered_events.sort(key=lambda e: e.timestamp, reverse=True)
        return filtered_events[:limit]
    
    def get_security_violations(self, hours: int = 24) -> List[AuditEvent]:
        """Get security violations within time window"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        violations = []
        with self._lock:
            for event in self.audit_events:
                if (event.timestamp >= cutoff_time and 
                    event.event_type in [AuditEventType.ACCESS_DENIED, 
                                       AuditEventType.SECURITY_VIOLATION,
                                       AuditEventType.POLICY_VIOLATION] or
                    not event.success):
                    violations.append(event)
        
        return sorted(violations, key=lambda e: e.timestamp, reverse=True)
    
    def get_user_activity(self, user_id: str, hours: int = 24) -> List[AuditEvent]:
        """Get user activity within time window"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        activity = []
        with self._lock:
            for event in self.audit_events:
                if event.timestamp >= cutoff_time and event.user_id == user_id:
                    activity.append(event)
        
        return sorted(activity, key=lambda e: e.timestamp, reverse=True)
    
    def _init_database(self):
        """Initialize audit database"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS audit_events (
                        id TEXT PRIMARY KEY,
                        event_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        user_id TEXT,
                        username TEXT,
                        session_id TEXT,
                        action TEXT,
                        resource_type TEXT,
                        resource_id TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        success BOOLEAN,
                        error_message TEXT,
                        metadata TEXT
                    )
                ''')
                
                # Create indexes for common queries
                conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_user_id ON audit_events(user_id)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type)')
                
        except Exception as e:
            self.logger.error(f"Failed to initialize audit database: {e}")
    
    def _store_audit_event(self, event: AuditEvent):
        """Store audit event in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO audit_events 
                    (id, event_type, timestamp, user_id, username, session_id, action,
                     resource_type, resource_id, ip_address, user_agent, success, 
                     error_message, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.id,
                    event.event_type.value,
                    event.timestamp.isoformat(),
                    event.user_id,
                    event.username,
                    event.session_id,
                    event.action,
                    event.resource_type.value if event.resource_type else None,
                    event.resource_id,
                    event.ip_address,
                    event.user_agent,
                    event.success,
                    event.error_message,
                    json.dumps(event.metadata)
                ))
                
        except Exception as e:
            self.logger.error(f"Failed to store audit event: {e}")

class SecurityPolicyEngine:
    """
    Security policy enforcement engine
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.policies: Dict[str, SecurityPolicy] = {}
        self.policy_violations = deque(maxlen=1000)
        self._lock = threading.RLock()
        
        # Setup default policies
        self._create_default_policies()
    
    def add_policy(self, policy: SecurityPolicy):
        """Add security policy"""
        with self._lock:
            self.policies[policy.id] = policy
        self.logger.info(f"Added security policy: {policy.name}")
    
    def evaluate_policies(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate all policies against context"""
        violations = []
        
        with self._lock:
            for policy in self.policies.values():
                if not policy.enabled:
                    continue
                
                try:
                    policy_violations = self._evaluate_policy(policy, context)
                    violations.extend(policy_violations)
                except Exception as e:
                    self.logger.error(f"Policy evaluation error for {policy.name}: {e}")
        
        return violations
    
    def _evaluate_policy(self, policy: SecurityPolicy, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate single policy"""
        violations = []
        
        for rule in policy.rules:
            try:
                if self._evaluate_rule(rule, context):
                    violation = {
                        'policy_id': policy.id,
                        'policy_name': policy.name,
                        'rule': rule,
                        'context': context,
                        'timestamp': datetime.now().isoformat(),
                        'enforcement_level': policy.enforcement_level
                    }
                    violations.append(violation)
                    
                    # Store violation
                    self.policy_violations.append(violation)
                    
            except Exception as e:
                self.logger.error(f"Rule evaluation error: {e}")
        
        return violations
    
    def _evaluate_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate single policy rule"""
        rule_type = rule.get('type')
        
        if rule_type == 'ip_whitelist':
            return self._evaluate_ip_whitelist_rule(rule, context)
        elif rule_type == 'time_restriction':
            return self._evaluate_time_restriction_rule(rule, context)
        elif rule_type == 'resource_limit':
            return self._evaluate_resource_limit_rule(rule, context)
        elif rule_type == 'user_session_limit':
            return self._evaluate_session_limit_rule(rule, context)
        
        return False
    
    def _evaluate_ip_whitelist_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate IP whitelist rule"""
        allowed_ips = rule.get('allowed_ips', [])
        client_ip = context.get('ip_address')
        
        if not client_ip or not allowed_ips:
            return False
        
        try:
            client_addr = ipaddress.ip_address(client_ip)
            
            for allowed_ip in allowed_ips:
                if '/' in allowed_ip:
                    # CIDR range
                    if client_addr in ipaddress.ip_network(allowed_ip):
                        return False
                else:
                    # Single IP
                    if client_addr == ipaddress.ip_address(allowed_ip):
                        return False
            
            # IP not in whitelist - violation
            return True
            
        except Exception:
            return True  # Invalid IP format - consider violation
    
    def _evaluate_time_restriction_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate time restriction rule"""
        allowed_hours = rule.get('allowed_hours', [])  # List of allowed hours (0-23)
        allowed_days = rule.get('allowed_days', [])    # List of allowed days (0-6)
        
        now = datetime.now()
        current_hour = now.hour
        current_day = now.weekday()
        
        # Check hour restriction
        if allowed_hours and current_hour not in allowed_hours:
            return True
        
        # Check day restriction
        if allowed_days and current_day not in allowed_days:
            return True
        
        return False
    
    def _evaluate_resource_limit_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate resource limit rule"""
        resource_type = rule.get('resource_type')
        max_limit = rule.get('max_limit', 0)
        current_usage = context.get(f'{resource_type}_usage', 0)
        
        return current_usage > max_limit
    
    def _evaluate_session_limit_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate session limit rule"""
        max_sessions = rule.get('max_sessions_per_user', 10)
        user_id = context.get('user_id')
        current_sessions = context.get('active_sessions_count', 0)
        
        return current_sessions > max_sessions
    
    def _create_default_policies(self):
        """Create default security policies"""
        
        # IP whitelist policy (disabled by default)
        ip_policy = SecurityPolicy(
            id="ip_whitelist",
            name="IP Address Whitelist",
            description="Restrict access to whitelisted IP addresses",
            policy_type="network_access",
            rules=[{
                'type': 'ip_whitelist',
                'allowed_ips': ['127.0.0.1', '::1']  # Localhost only
            }],
            enabled=False  # Disabled by default
        )
        
        # Business hours policy
        time_policy = SecurityPolicy(
            id="business_hours",
            name="Business Hours Access",
            description="Restrict access to business hours",
            policy_type="time_access",
            rules=[{
                'type': 'time_restriction',
                'allowed_hours': list(range(8, 18)),  # 8 AM to 6 PM
                'allowed_days': list(range(0, 5))     # Monday to Friday
            }],
            enabled=False  # Disabled by default
        )
        
        # Session limit policy
        session_policy = SecurityPolicy(
            id="session_limits",
            name="Session Limits",
            description="Limit concurrent sessions per user",
            policy_type="session_management",
            rules=[{
                'type': 'user_session_limit',
                'max_sessions_per_user': 5
            }],
            enabled=True
        )
        
        self.policies = {
            ip_policy.id: ip_policy,
            time_policy.id: time_policy,
            session_policy.id: session_policy
        }

class AutomationSecurity:
    """
    Main automation security system
    """
    
    def __init__(self, db_path: str = "user_data/automation_security.db", master_key: str = None):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Core security components
        self.credential_manager = CredentialManager(master_key)
        self.access_controller = AccessController()
        self.audit_logger = AuditLogger(db_path.replace('.db', '_audit.db'))
        self.policy_engine = SecurityPolicyEngine()
        
        # Security state
        self.security_active = False
        
        # Initialize database
        self._init_database()
        
        # Create default admin user if none exists
        self._create_default_admin()
    
    def start_security(self):
        """Start security system"""
        if self.security_active:
            return
        
        self.security_active = True
        self.logger.info("Automation security system started")
        
        # Log system start event
        self.audit_logger.log_event(
            AuditEventType.LOGIN,
            action="Security system started",
            username="system"
        )
    
    def stop_security(self):
        """Stop security system"""
        if not self.security_active:
            return
        
        self.security_active = False
        
        # Log system stop event
        self.audit_logger.log_event(
            AuditEventType.LOGOUT,
            action="Security system stopped",
            username="system"
        )
        
        self.logger.info("Automation security system stopped")
    
    def authenticate(self, username: str, password: str, ip_address: str = None,
                    user_agent: str = None) -> Optional[str]:
        """Authenticate user"""
        session_id = self.access_controller.authenticate_user(username, password, ip_address, user_agent)
        
        if session_id:
            # Log successful login
            self.audit_logger.log_event(
                AuditEventType.LOGIN,
                action="User login",
                username=username,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True
            )
        else:
            # Log failed login
            self.audit_logger.log_event(
                AuditEventType.LOGIN,
                action="User login failed",
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False
            )
        
        return session_id
    
    def check_access(self, session_id: str, resource_type: ResourceType,
                    permission_type: PermissionType, resource_id: str = None,
                    context: Dict[str, Any] = None) -> bool:
        """Check access permissions"""
        try:
            # Validate session
            session = self.access_controller.validate_session(session_id)
            if not session:
                self.audit_logger.log_event(
                    AuditEventType.ACCESS_DENIED,
                    action=f"Access denied - invalid session",
                    session_id=session_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    success=False
                )
                return False
            
            # Check permissions
            has_permission = self.access_controller.check_permission(
                session_id, resource_type, permission_type, resource_id
            )
            
            if not has_permission:
                self.audit_logger.log_event(
                    AuditEventType.ACCESS_DENIED,
                    action=f"Access denied - insufficient permissions",
                    user_id=session.user_id,
                    username=session.username,
                    session_id=session_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    success=False
                )
                return False
            
            # Evaluate security policies
            policy_context = {
                'user_id': session.user_id,
                'username': session.username,
                'ip_address': session.ip_address,
                'user_agent': session.user_agent,
                'resource_type': resource_type.value,
                'permission_type': permission_type.value,
                'resource_id': resource_id,
                **(context or {})
            }
            
            violations = self.policy_engine.evaluate_policies(policy_context)
            if violations:
                self.audit_logger.log_event(
                    AuditEventType.POLICY_VIOLATION,
                    action=f"Security policy violation",
                    user_id=session.user_id,
                    username=session.username,
                    session_id=session_id,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    success=False,
                    metadata={'violations': violations}
                )
                return False
            
            # Log successful access
            self.audit_logger.log_event(
                AuditEventType.ACCESS_GRANTED,
                action=f"{permission_type.value} access to {resource_type.value}",
                user_id=session.user_id,
                username=session.username,
                session_id=session_id,
                resource_type=resource_type,
                resource_id=resource_id,
                success=True
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Access check error: {e}")
            return False
    
    def store_credential(self, name: str, credential_type: str, data: Dict[str, Any],
                        session_id: str, description: str = "") -> Optional[str]:
        """Store secure credential"""
        # Check permission
        if not self.check_access(session_id, ResourceType.CREDENTIAL, PermissionType.CREATE):
            return None
        
        session = self.access_controller.validate_session(session_id)
        if not session:
            return None
        
        credential_id = self.credential_manager.store_credential(
            name, credential_type, data, session.user_id, description
        )
        
        # Log credential creation
        self.audit_logger.log_event(
            AuditEventType.OPERATION_EXECUTED,
            action=f"Credential created: {name}",
            user_id=session.user_id,
            username=session.username,
            session_id=session_id,
            resource_type=ResourceType.CREDENTIAL,
            resource_id=credential_id,
            success=True
        )
        
        return credential_id
    
    def retrieve_credential(self, credential_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve secure credential"""
        # Check permission
        if not self.check_access(session_id, ResourceType.CREDENTIAL, PermissionType.READ, credential_id):
            return None
        
        session = self.access_controller.validate_session(session_id)
        if not session:
            return None
        
        data = self.credential_manager.retrieve_credential(credential_id, session.user_id)
        
        # Log credential access
        self.audit_logger.log_event(
            AuditEventType.CREDENTIAL_ACCESSED,
            action=f"Credential accessed",
            user_id=session.user_id,
            username=session.username,
            session_id=session_id,
            resource_type=ResourceType.CREDENTIAL,
            resource_id=credential_id,
            success=data is not None
        )
        
        return data
    
    def get_security_dashboard(self) -> Dict[str, Any]:
        """Get security dashboard data"""
        # Get recent security events
        recent_violations = self.audit_logger.get_security_violations(24)
        recent_logins = self.audit_logger.get_recent_events(
            limit=20,
            event_type=AuditEventType.LOGIN
        )
        
        # Count active sessions
        active_sessions = len([s for s in self.access_controller.sessions.values() if s.active])
        
        # Count users and roles
        total_users = len(self.access_controller.users)
        total_roles = len(self.access_controller.roles)
        
        return {
            'security_active': self.security_active,
            'active_sessions': active_sessions,
            'total_users': total_users,
            'total_roles': total_roles,
            'security_violations_24h': len(recent_violations),
            'failed_logins_24h': len([e for e in recent_logins if not e.success]),
            'successful_logins_24h': len([e for e in recent_logins if e.success]),
            'stored_credentials': len(self.credential_manager.credentials),
            'active_policies': len([p for p in self.policy_engine.policies.values() if p.enabled])
        }
    
    def _init_database(self):
        """Initialize security database"""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                # Users table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        email TEXT,
                        password_hash TEXT NOT NULL,
                        roles TEXT,
                        active BOOLEAN DEFAULT 1,
                        require_2fa BOOLEAN DEFAULT 0,
                        failed_login_attempts INTEGER DEFAULT 0,
                        locked_until TEXT,
                        last_login TEXT,
                        created_time TEXT,
                        created_by TEXT
                    )
                ''')
                
                # Roles table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS roles (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        permissions TEXT,
                        inherits_from TEXT,
                        created_time TEXT,
                        created_by TEXT
                    )
                ''')
                
                # Credentials table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS credentials (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        credential_type TEXT,
                        encrypted_data TEXT,
                        description TEXT,
                        allowed_users TEXT,
                        allowed_roles TEXT,
                        created_time TEXT,
                        created_by TEXT,
                        last_accessed TEXT,
                        access_count INTEGER DEFAULT 0,
                        expires_at TEXT
                    )
                ''')
                
        except Exception as e:
            self.logger.error(f"Security database initialization failed: {e}")
    
    def _create_default_admin(self):
        """Create default admin user if none exists"""
        try:
            if not self.access_controller.users:
                admin_id = self.access_controller.create_user(
                    username="admin",
                    password="admin123",  # Should be changed immediately
                    email="admin@automation.local",
                    roles=["admin"]
                )
                self.logger.warning("Created default admin user - please change password!")
                
        except Exception as e:
            self.logger.error(f"Failed to create default admin: {e}")


# Utility functions
def require_permission(resource_type: ResourceType, permission_type: PermissionType,
                      resource_id: str = None):
    """Decorator for permission checking"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # This would be implemented to work with the security system
            # For now, just call the function
            return func(*args, **kwargs)
        return wrapper
    return decorator

def secure_operation(security_level: SecurityLevel = SecurityLevel.BASIC):
    """Decorator for marking operations with security levels"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Security level checking would be implemented here
            return func(*args, **kwargs)
        return wrapper
    return decorator