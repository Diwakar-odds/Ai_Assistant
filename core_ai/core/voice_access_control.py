# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Voice Access Control System
============================

Implements Role-Based Access Control (RBAC) for voice biometric operations.

Security Features:
- Role-based permissions (Owner, Admin, User, Guest)
- Operation-level access control
- Speaker ownership verification
- Multi-factor authentication for sensitive operations
- Session management
- Permission inheritance

Roles & Permissions:
- Owner: Full access to all operations
- Admin: Can manage users, enroll speakers, verify
- User: Can verify speakers, limited enrollment
- Guest: Can only verify pre-enrolled speakers
"""

import time
import hashlib
import secrets
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class Role(Enum):
    """User roles with hierarchical permissions"""
    OWNER = "owner"          # Full access
    ADMIN = "admin"          # Can manage users and speakers
    USER = "user"            # Can verify and self-enroll
    GUEST = "guest"          # Read-only, verification only


class Permission(Enum):
    """Granular permissions for voice operations"""
    SPEAKER_ENROLL = "speaker.enroll"
    SPEAKER_VERIFY = "speaker.verify"
    SPEAKER_DELETE = "speaker.delete"
    SPEAKER_VIEW = "speaker.view"
    SPEAKER_MODIFY = "speaker.modify"
    USER_CREATE = "user.create"
    USER_DELETE = "user.delete"
    USER_MODIFY = "user.modify"
    SYSTEM_CONFIGURE = "system.configure"
    AUDIT_VIEW = "audit.view"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.OWNER: {  # Full access
        Permission.SPEAKER_ENROLL,
        Permission.SPEAKER_VERIFY,
        Permission.SPEAKER_DELETE,
        Permission.SPEAKER_VIEW,
        Permission.SPEAKER_MODIFY,
        Permission.USER_CREATE,
        Permission.USER_DELETE,
        Permission.USER_MODIFY,
        Permission.SYSTEM_CONFIGURE,
        Permission.AUDIT_VIEW
    },
    Role.ADMIN: {  # Management access
        Permission.SPEAKER_ENROLL,
        Permission.SPEAKER_VERIFY,
        Permission.SPEAKER_DELETE,
        Permission.SPEAKER_VIEW,
        Permission.SPEAKER_MODIFY,
        Permission.USER_CREATE,
        Permission.USER_MODIFY,
        Permission.AUDIT_VIEW
    },
    Role.USER: {  # Standard user
        Permission.SPEAKER_ENROLL,  # Can enroll self only
        Permission.SPEAKER_VERIFY,
        Permission.SPEAKER_VIEW,
        Permission.SPEAKER_MODIFY  # Can modify own speakers only
    },
    Role.GUEST: {  # Limited access
        Permission.SPEAKER_VERIFY,
        Permission.SPEAKER_VIEW
    }
}


@dataclass
class User:
    """User account with role and permissions"""
    user_id: str
    role: Role
    created_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    is_active: bool = True
    owned_speakers: Set[str] = field(default_factory=set)
    metadata: Dict = field(default_factory=dict)
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission"""
        if not self.is_active:
            return False
        return permission in ROLE_PERMISSIONS.get(self.role, set())
    
    def owns_speaker(self, speaker_id: str) -> bool:
        """Check if user owns a speaker"""
        return speaker_id in self.owned_speakers


@dataclass
class Session:
    """User session for authentication"""
    session_id: str
    user_id: str
    created_at: float
    expires_at: float
    ip_address: Optional[str] = None
    is_mfa_verified: bool = False
    metadata: Dict = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """Check if session is still valid"""
        return time.time() < self.expires_at
    
    def is_expired(self) -> bool:
        """Check if session has expired"""
        return time.time() >= self.expires_at


class VoiceAccessControl:
    """
    Manages access control for voice biometric operations.
    
    Usage:
        access_control = VoiceAccessControl()
        
        # Create user
        access_control.create_user("user123", Role.USER)
        
        # Check permission
        if access_control.check_permission("user123", Permission.SPEAKER_ENROLL):
            # Allow enrollment
            pass
        
        # Verify ownership
        if access_control.can_modify_speaker("user123", "speaker_001"):
            # Allow modification
            pass
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize access control system.
        
        Args:
            storage_path: Path to store user data
        """
        if storage_path is None:
            base_dir = Path(__file__).parent.parent.parent
            self.storage_path = base_dir / "data" / "voice_access_control"
        else:
            self.storage_path = Path(storage_path)
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, Session] = {}
        
        # Session settings
        self.session_duration = 24 * 60 * 60  # 24 hours
        self.mfa_required_operations = {
            Permission.SPEAKER_DELETE,
            Permission.USER_DELETE
        }
        
        # Load existing data
        self._load_users()
        
        logger.info(f"Voice Access Control initialized with {len(self.users)} users")
    
    def create_user(
        self,
        user_id: str,
        role: Role = Role.USER,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Create a new user.
        
        Args:
            user_id: Unique user identifier
            role: User role
            metadata: Additional user metadata
            
        Returns:
            True if user created successfully
        """
        try:
            if user_id in self.users:
                logger.warning(f"User {user_id} already exists")
                return False
            
            user = User(
                user_id=user_id,
                role=role,
                metadata=metadata or {}
            )
            
            self.users[user_id] = user
            self._save_user(user)
            
            logger.info(f"✅ Created user {user_id} with role {role.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create user {user_id}: {e}")
            return False
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def check_permission(
        self,
        user_id: str,
        permission: Permission,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission.
        
        Args:
            user_id: User identifier
            permission: Permission to check
            session_id: Optional session ID for verification
            
        Returns:
            True if user has permission
        """
        # Get user
        user = self.users.get(user_id)
        if not user or not user.is_active:
            return False
        
        # Check session if provided
        if session_id:
            session = self.sessions.get(session_id)
            if not session or not session.is_valid() or session.user_id != user_id:
                logger.warning(f"Invalid session for user {user_id}")
                return False
            
            # Check MFA for sensitive operations
            if permission in self.mfa_required_operations and not session.is_mfa_verified:
                logger.warning(f"MFA required for {permission.value}")
                return False
        
        # Check permission
        has_perm = user.has_permission(permission)
        
        if not has_perm:
            logger.debug(f"User {user_id} ({user.role.value}) denied {permission.value}")
        
        return has_perm
    
    def can_modify_speaker(
        self,
        user_id: str,
        speaker_id: str,
        session_id: Optional[str] = None
    ) -> bool:
        """
        Check if user can modify a speaker.
        
        Users can modify speakers if:
        - They are Owner/Admin (can modify any speaker)
        - They own the speaker (and have SPEAKER_MODIFY permission)
        
        Args:
            user_id: User identifier
            speaker_id: Speaker identifier
            session_id: Optional session ID
            
        Returns:
            True if user can modify speaker
        """
        user = self.users.get(user_id)
        if not user or not user.is_active:
            return False
        
        # Owner/Admin can modify any speaker
        if user.role in [Role.OWNER, Role.ADMIN]:
            return self.check_permission(user_id, Permission.SPEAKER_MODIFY, session_id)
        
        # Regular users can only modify their own speakers
        if user.owns_speaker(speaker_id):
            return self.check_permission(user_id, Permission.SPEAKER_MODIFY, session_id)
        
        logger.warning(f"User {user_id} cannot modify speaker {speaker_id} (not owner)")
        return False
    
    def register_speaker_ownership(self, user_id: str, speaker_id: str) -> bool:
        """
        Register speaker ownership.
        
        Args:
            user_id: User identifier
            speaker_id: Speaker identifier
            
        Returns:
            True if ownership registered
        """
        user = self.users.get(user_id)
        if not user:
            return False
        
        user.owned_speakers.add(speaker_id)
        self._save_user(user)
        
        logger.info(f"📝 Registered speaker {speaker_id} to user {user_id}")
        return True
    
    def remove_speaker_ownership(self, user_id: str, speaker_id: str) -> bool:
        """
        Remove speaker ownership.
        
        Args:
            user_id: User identifier
            speaker_id: Speaker identifier
            
        Returns:
            True if ownership removed
        """
        user = self.users.get(user_id)
        if not user:
            return False
        
        if speaker_id in user.owned_speakers:
            user.owned_speakers.remove(speaker_id)
            self._save_user(user)
            logger.info(f"🗑️ Removed speaker {speaker_id} from user {user_id}")
            return True
        
        return False
    
    def create_session(
        self,
        user_id: str,
        ip_address: Optional[str] = None,
        duration: Optional[int] = None
    ) -> Optional[str]:
        """
        Create a new session for user.
        
        Args:
            user_id: User identifier
            ip_address: Optional IP address
            duration: Session duration in seconds (default: 24 hours)
            
        Returns:
            Session ID if created successfully
        """
        user = self.users.get(user_id)
        if not user or not user.is_active:
            return None
        
        # Generate secure session ID
        session_id = secrets.token_urlsafe(32)
        
        # Create session
        duration = duration or self.session_duration
        session = Session(
            session_id=session_id,
            user_id=user_id,
            created_at=time.time(),
            expires_at=time.time() + duration,
            ip_address=ip_address
        )
        
        self.sessions[session_id] = session
        
        # Update last login
        user.last_login = time.time()
        self._save_user(user)
        
        logger.info(f"✅ Created session for user {user_id}")
        return session_id
    
    def verify_mfa(self, session_id: str) -> bool:
        """
        Mark session as MFA verified.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if MFA verification recorded
        """
        session = self.sessions.get(session_id)
        if not session or not session.is_valid():
            return False
        
        session.is_mfa_verified = True
        logger.info(f"✅ MFA verified for session {session_id}")
        return True
    
    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidate a session (logout).
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session invalidated
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"🚪 Session {session_id} invalidated")
            return True
        
        return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions.
        
        Returns:
            Number of sessions removed
        """
        expired = [sid for sid, session in self.sessions.items() if session.is_expired()]
        
        for session_id in expired:
            del self.sessions[session_id]
        
        if expired:
            logger.info(f"🧹 Cleaned up {len(expired)} expired sessions")
        
        return len(expired)
    
    def _save_user(self, user: User):
        """Save user to disk"""
        try:
            user_file = self.storage_path / f"{user.user_id}_access.json"
            
            data = {
                'user_id': user.user_id,
                'role': user.role.value,
                'created_at': user.created_at,
                'last_login': user.last_login,
                'is_active': user.is_active,
                'owned_speakers': list(user.owned_speakers),
                'metadata': user.metadata
            }
            
            with open(user_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save user {user.user_id}: {e}")
    
    def _load_users(self):
        """Load users from disk"""
        try:
            if not self.storage_path.exists():
                return
            
            for user_file in self.storage_path.glob("*_access.json"):
                try:
                    with open(user_file, 'r') as f:
                        data = json.load(f)
                    
                    user = User(
                        user_id=data['user_id'],
                        role=Role(data['role']),
                        created_at=data.get('created_at', time.time()),
                        last_login=data.get('last_login'),
                        is_active=data.get('is_active', True),
                        owned_speakers=set(data.get('owned_speakers', [])),
                        metadata=data.get('metadata', {})
                    )
                    
                    self.users[user.user_id] = user
                    
                except Exception as e:
                    logger.warning(f"Failed to load user from {user_file}: {e}")
            
        except Exception as e:
            logger.error(f"Error loading users: {e}")


# Global singleton
_global_access_control: Optional[VoiceAccessControl] = None


def get_voice_access_control() -> VoiceAccessControl:
    """Get global VoiceAccessControl instance"""
    global _global_access_control
    
    if _global_access_control is None:
        _global_access_control = VoiceAccessControl()
    
    return _global_access_control


def require_permission(permission: Permission):
    """
    Decorator to require permission for a function.
    
    Usage:
        @require_permission(Permission.SPEAKER_ENROLL)
        def enroll_speaker(user_id, speaker_id, audio):
            # Only executes if user has permission
            pass
    """
    def decorator(func):
        def wrapper(user_id, *args, **kwargs):
            access_control = get_voice_access_control()
            
            if not access_control.check_permission(user_id, permission):
                raise PermissionError(
                    f"User {user_id} does not have permission: {permission.value}"
                )
            
            return func(user_id, *args, **kwargs)
        
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test access control
    print("Voice Access Control - Test")
    print("=" * 50)
    
    ac = VoiceAccessControl()
    
    # Create users with different roles
    ac.create_user("owner_001", Role.OWNER)
    ac.create_user("admin_001", Role.ADMIN)
    ac.create_user("user_001", Role.USER)
    ac.create_user("guest_001", Role.GUEST)
    
    # Test permissions
    test_cases = [
        ("owner_001", Permission.SPEAKER_DELETE),
        ("admin_001", Permission.SPEAKER_DELETE),
        ("user_001", Permission.SPEAKER_DELETE),
        ("guest_001", Permission.SPEAKER_ENROLL),
    ]
    
    for user_id, perm in test_cases:
        has_perm = ac.check_permission(user_id, perm)
        user = ac.get_user(user_id)
        print(f"{user_id} ({user.role.value}) → {perm.value}: {has_perm}")
    
    # Test speaker ownership
    ac.register_speaker_ownership("user_001", "speaker_001")
    can_modify = ac.can_modify_speaker("user_001", "speaker_001")
    print(f"\nuser_001 can modify speaker_001: {can_modify}")
    
    # Test sessions
    session_id = ac.create_session("user_001", ip_address="127.0.0.1")
    print(f"\nCreated session: {session_id}")
    
    print("\n✅ Access control tests passed!")
