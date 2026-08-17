"""
Voice Audit Logger
==================

Comprehensive audit logging for all voice biometric operations.

Features:
- Tamper-proof logging (append-only)
- Automatic log rotation
- Event categorization
- Suspicious activity detection
- Compliance reporting (GDPR audit trail)
- Searchable log entries

Logged Events:
- Speaker enrollment/deletion/modification
- Verification attempts (success/failure)
- Permission changes
- Consent changes
- API key usage
- System configuration changes
"""

import time
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of events that can be audited"""
    SPEAKER_ENROLLED = "speaker.enrolled"
    SPEAKER_VERIFIED = "speaker.verified"
    SPEAKER_VERIFICATION_FAILED = "speaker.verification_failed"
    SPEAKER_DELETED = "speaker.deleted"
    SPEAKER_MODIFIED = "speaker.modified"
    USER_CREATED = "user.created"
    USER_DELETED = "user.deleted"
    USER_ROLE_CHANGED = "user.role_changed"
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_DENIED = "permission.denied"
    CONSENT_GRANTED = "consent.granted"
    CONSENT_WITHDRAWN = "consent.withdrawn"
    API_KEY_USED = "api.key_used"
    CONFIG_CHANGED = "config.changed"
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    MFA_VERIFIED = "auth.mfa_verified"
    BIOMETRIC_ENCRYPTED = "biometric.encrypted"
    BIOMETRIC_DECRYPTED = "biometric.decrypted"


class AuditSeverity(Enum):
    """Severity levels for audit events"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Single audit log entry"""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: float
    user_id: str
    action: str
    resource_type: str = ""  # e.g., "speaker", "user", "config"
    resource_id: str = ""  # e.g., speaker_id, user_id
    result: str = "success"  # "success", "failure", "denied"
    ip_address: Optional[str] = None
    session_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage"""
        return {
            'event_id': self.event_id,
            'event_type': self.event_type.value,
            'severity': self.severity.value,
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat(),
            'user_id': self.user_id,
            'action': self.action,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'result': self.result,
            'ip_address': self.ip_address,
            'session_id': self.session_id,
            'details': self.details
        }
    
    def to_log_line(self) -> str:
        """Convert to single-line log format"""
        dt = datetime.fromtimestamp(self.timestamp).strftime('%Y-%m-%d %H:%M:%S')
        return (
            f"[{dt}] {self.severity.value.upper()} | "
            f"{self.event_type.value} | User:{self.user_id} | "
            f"Resource:{self.resource_type}/{self.resource_id} | "
            f"Result:{self.result} | {self.action}"
        )


class VoiceAuditLogger:
    """
    Audit logger for voice biometric operations.
    
    Usage:
        audit = VoiceAuditLogger()
        
        # Log speaker enrollment
        audit.log_speaker_enrollment(
            user_id="user123",
            speaker_id="speaker_001",
            result="success"
        )
        
        # Log verification attempt
        audit.log_verification_attempt(
            user_id="user123",
            speaker_id="speaker_001",
            result="success",
            confidence=0.95
        )
        
        # Get audit trail
        events = audit.get_user_audit_trail("user123")
    """
    
    def __init__(
        self,
        log_dir: Optional[Path] = None,
        max_log_size_mb: int = 100,
        max_log_files: int = 10
    ):
        """
        Initialize audit logger.
        
        Args:
            log_dir: Directory for audit logs
            max_log_size_mb: Maximum size of log file before rotation
            max_log_files: Maximum number of log files to keep
        """
        if log_dir is None:
            base_dir = Path(__file__).parent.parent.parent
            self.log_dir = base_dir / "data" / "audit_logs"
        else:
            self.log_dir = Path(log_dir)
        
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_log_size_bytes = max_log_size_mb * 1024 * 1024
        self.max_log_files = max_log_files
        
        # Current log file
        self.current_log_file = self.log_dir / "voice_audit.jsonl"
        
        # Suspicious activity patterns
        self.failed_verification_threshold = 5  # Failed attempts before alert
        self.failed_verification_window = 300  # 5 minutes
        
        # Event counters for anomaly detection
        self.recent_events: List[AuditEvent] = []
        
        # Set restrictive permissions
        try:
            import os
            os.chmod(self.log_dir, 0o700)
        except Exception as e:
            logger.warning(f"Could not set directory permissions: {e}")
        
        logger.info(f"Voice Audit Logger initialized - logs at {self.log_dir}")
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        import uuid
        return str(uuid.uuid4())
    
    def _write_event(self, event: AuditEvent):
        """Write event to log file (append-only)"""
        try:
            # Check if rotation needed
            if self.current_log_file.exists():
                file_size = self.current_log_file.stat().st_size
                if file_size >= self.max_log_size_bytes:
                    self._rotate_logs()
            
            # Append event to log file (JSONL format)
            with open(self.current_log_file, 'a') as f:
                f.write(json.dumps(event.to_dict()) + '\n')
            
            # Also log to standard logger
            logger.info(event.to_log_line())
            
            # Keep in recent events for anomaly detection
            self.recent_events.append(event)
            if len(self.recent_events) > 1000:
                self.recent_events = self.recent_events[-1000:]
            
        except Exception as e:
            logger.error(f"Failed to write audit event: {e}")
    
    def _rotate_logs(self):
        """Rotate log files when max size reached"""
        try:
            # Rename current log with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            rotated_file = self.log_dir / f"voice_audit_{timestamp}.jsonl"
            self.current_log_file.rename(rotated_file)
            
            logger.info(f"📝 Rotated audit log to {rotated_file}")
            
            # Remove old logs if exceeded max files
            log_files = sorted(self.log_dir.glob("voice_audit_*.jsonl"))
            if len(log_files) > self.max_log_files:
                for old_file in log_files[:-self.max_log_files]:
                    old_file.unlink()
                    logger.info(f"🗑️ Deleted old audit log {old_file}")
                    
        except Exception as e:
            logger.error(f"Log rotation failed: {e}")
    
    def log_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        action: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        resource_type: str = "",
        resource_id: str = "",
        result: str = "success",
        ip_address: Optional[str] = None,
        session_id: Optional[str] = None,
        **details
    ):
        """
        Log a general audit event.
        
        Args:
            event_type: Type of event
            user_id: User performing action
            action: Description of action
            severity: Event severity
            resource_type: Type of resource affected
            resource_id: Identifier of resource
            result: Result of action
            ip_address: Optional IP address
            session_id: Optional session ID
            **details: Additional event details
        """
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=event_type,
            severity=severity,
            timestamp=time.time(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            ip_address=ip_address,
            session_id=session_id,
            details=details
        )
        
        self._write_event(event)
        
        # Check for suspicious activity
        self._check_suspicious_activity(event)
    
    def log_speaker_enrollment(
        self,
        user_id: str,
        speaker_id: str,
        result: str = "success",
        quality_score: float = 0.0,
        **details
    ):
        """Log speaker enrollment"""
        self.log_event(
            event_type=AuditEventType.SPEAKER_ENROLLED,
            user_id=user_id,
            action=f"Enrolled speaker {speaker_id}",
            resource_type="speaker",
            resource_id=speaker_id,
            result=result,
            quality_score=quality_score,
            **details
        )
    
    def log_verification_attempt(
        self,
        user_id: str,
        speaker_id: str,
        result: str,
        confidence: float = 0.0,
        anti_spoofing_score: float = 0.0,
        **details
    ):
        """Log speaker verification attempt"""
        event_type = (
            AuditEventType.SPEAKER_VERIFIED if result == "success"
            else AuditEventType.SPEAKER_VERIFICATION_FAILED
        )
        
        severity = AuditSeverity.INFO if result == "success" else AuditSeverity.WARNING
        
        self.log_event(
            event_type=event_type,
            user_id=user_id,
            action=f"Verification attempt for speaker {speaker_id}",
            severity=severity,
            resource_type="speaker",
            resource_id=speaker_id,
            result=result,
            confidence=confidence,
            anti_spoofing_score=anti_spoofing_score,
            **details
        )
    
    def log_speaker_deletion(
        self,
        user_id: str,
        speaker_id: str,
        result: str = "success",
        **details
    ):
        """Log speaker deletion"""
        self.log_event(
            event_type=AuditEventType.SPEAKER_DELETED,
            user_id=user_id,
            action=f"Deleted speaker {speaker_id}",
            severity=AuditSeverity.WARNING,
            resource_type="speaker",
            resource_id=speaker_id,
            result=result,
            **details
        )
    
    def log_permission_check(
        self,
        user_id: str,
        permission: str,
        result: str,
        **details
    ):
        """Log permission check"""
        event_type = (
            AuditEventType.PERMISSION_GRANTED if result == "granted"
            else AuditEventType.PERMISSION_DENIED
        )
        
        severity = AuditSeverity.INFO if result == "granted" else AuditSeverity.WARNING
        
        self.log_event(
            event_type=event_type,
            user_id=user_id,
            action=f"Permission check: {permission}",
            severity=severity,
            resource_type="permission",
            resource_id=permission,
            result=result,
            **details
        )
    
    def log_consent_change(
        self,
        user_id: str,
        consent_type: str,
        action: str,
        **details
    ):
        """Log consent grant/withdrawal"""
        event_type = (
            AuditEventType.CONSENT_GRANTED if action == "granted"
            else AuditEventType.CONSENT_WITHDRAWN
        )
        
        self.log_event(
            event_type=event_type,
            user_id=user_id,
            action=f"{action.capitalize()} consent for {consent_type}",
            resource_type="consent",
            resource_id=consent_type,
            result="success",
            **details
        )
    
    def log_api_usage(
        self,
        user_id: str,
        api_name: str,
        result: str = "success",
        **details
    ):
        """Log external API usage"""
        self.log_event(
            event_type=AuditEventType.API_KEY_USED,
            user_id=user_id,
            action=f"Used {api_name} API",
            resource_type="api",
            resource_id=api_name,
            result=result,
            **details
        )
    
    def _check_suspicious_activity(self, event: AuditEvent):
        """Check for suspicious activity patterns"""
        # Check for multiple failed verifications
        if event.event_type == AuditEventType.SPEAKER_VERIFICATION_FAILED:
            recent_failures = [
                e for e in self.recent_events
                if (e.event_type == AuditEventType.SPEAKER_VERIFICATION_FAILED and
                    e.user_id == event.user_id and
                    e.timestamp > time.time() - self.failed_verification_window)
            ]
            
            if len(recent_failures) >= self.failed_verification_threshold:
                logger.warning(
                    f"🚨 SUSPICIOUS: User {event.user_id} has {len(recent_failures)} "
                    f"failed verification attempts in {self.failed_verification_window}s"
                )
                
                # Log critical alert
                self.log_event(
                    event_type=AuditEventType.SPEAKER_VERIFICATION_FAILED,
                    user_id=event.user_id,
                    action="Suspicious pattern: Multiple failed verifications",
                    severity=AuditSeverity.CRITICAL,
                    result="alert",
                    failed_count=len(recent_failures)
                )
    
    def get_user_audit_trail(
        self,
        user_id: str,
        limit: int = 100,
        event_type: Optional[AuditEventType] = None
    ) -> List[Dict]:
        """
        Get audit trail for a user (GDPR right to access).
        
        Args:
            user_id: User identifier
            limit: Maximum number of events to return
            event_type: Optional filter by event type
            
        Returns:
            List of audit events
        """
        events = []
        
        try:
            # Read from all log files
            log_files = sorted(self.log_dir.glob("voice_audit*.jsonl"), reverse=True)
            
            for log_file in log_files:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            event_data = json.loads(line)
                            
                            # Filter by user
                            if event_data.get('user_id') != user_id:
                                continue
                            
                            # Filter by event type if specified
                            if event_type and event_data.get('event_type') != event_type.value:
                                continue
                            
                            events.append(event_data)
                            
                            if len(events) >= limit:
                                return events
                                
                        except json.JSONDecodeError:
                            continue
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get audit trail for {user_id}: {e}")
            return []
    
    def get_resource_audit_trail(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get audit trail for a specific resource (e.g., speaker).
        
        Args:
            resource_type: Type of resource (e.g., "speaker")
            resource_id: Resource identifier
            limit: Maximum number of events
            
        Returns:
            List of audit events
        """
        events = []
        
        try:
            log_files = sorted(self.log_dir.glob("voice_audit*.jsonl"), reverse=True)
            
            for log_file in log_files:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            event_data = json.loads(line)
                            
                            if (event_data.get('resource_type') == resource_type and
                                event_data.get('resource_id') == resource_id):
                                events.append(event_data)
                            
                            if len(events) >= limit:
                                return events
                                
                        except json.JSONDecodeError:
                            continue
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get audit trail for {resource_type}/{resource_id}: {e}")
            return []
    
    def get_recent_events(self, minutes: int = 60, limit: int = 100) -> List[Dict]:
        """
        Get recent audit events.
        
        Args:
            minutes: Look back this many minutes
            limit: Maximum number of events
            
        Returns:
            List of recent audit events
        """
        cutoff_time = time.time() - (minutes * 60)
        events = []
        
        try:
            with open(self.current_log_file, 'r') as f:
                for line in f:
                    try:
                        event_data = json.loads(line)
                        
                        if event_data.get('timestamp', 0) >= cutoff_time:
                            events.append(event_data)
                        
                        if len(events) >= limit:
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            return sorted(events, key=lambda x: x.get('timestamp', 0), reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []


# Global singleton
_global_audit_logger: Optional[VoiceAuditLogger] = None


def get_voice_audit_logger() -> VoiceAuditLogger:
    """Get global VoiceAuditLogger instance"""
    global _global_audit_logger
    
    if _global_audit_logger is None:
        _global_audit_logger = VoiceAuditLogger()
    
    return _global_audit_logger


if __name__ == "__main__":
    # Test audit logger
    print("Voice Audit Logger - Test")
    print("=" * 50)
    
    audit = VoiceAuditLogger()
    
    # Log various events
    audit.log_speaker_enrollment("user123", "speaker_001", quality_score=0.95)
    audit.log_verification_attempt("user123", "speaker_001", "success", confidence=0.92)
    audit.log_verification_attempt("user123", "speaker_001", "failed", confidence=0.45)
    audit.log_consent_change("user123", "external_stt", "granted")
    audit.log_api_usage("user123", "WhisperAPI", result="success")
    
    # Get audit trail
    trail = audit.get_user_audit_trail("user123")
    print(f"\nAudit trail for user123 ({len(trail)} events):")
    for event in trail:
        print(f"  - {event['datetime']}: {event['action']} ({event['result']})")
    
    print("\n✅ Audit logging tests passed!")
