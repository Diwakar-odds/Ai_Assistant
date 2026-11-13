"""
Security Audit Logging System for AI Assistant

Provides comprehensive logging of security events, user actions, and system operations.
Includes log analysis, alerting, and compliance reporting capabilities.
"""

import json
import datetime
import os
import hashlib
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Enum, Union
from dataclasses import dataclass, asdict
from queue import Queue, Empty
import sqlite3
from contextlib import contextmanager

try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

try:
    from core.encryption import get_encryption
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    logger.warning("Encryption not available for audit logs")


class EventType(Enum):
    """Types of audit events"""
    # Authentication events
    AUTH_LOGIN_SUCCESS = "auth.login.success"
    AUTH_LOGIN_FAILURE = "auth.login.failure"
    AUTH_LOGOUT = "auth.logout"
    AUTH_PIN_CHANGE = "auth.pin.change"
    AUTH_SESSION_EXPIRED = "auth.session.expired"
    
    # System operations
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_CONFIG_CHANGE = "system.config.change"
    SYSTEM_FILE_ACCESS = "system.file.access"
    SYSTEM_COMMAND_EXEC = "system.command.exec"
    SYSTEM_APP_LAUNCH = "system.app.launch"
    
    # API operations
    API_REQUEST = "api.request"
    API_ERROR = "api.error"
    API_RATE_LIMIT = "api.rate_limit"
    API_KEY_USAGE = "api.key.usage"
    
    # Data operations
    DATA_ACCESS = "data.access"
    DATA_MODIFICATION = "data.modification"
    DATA_DELETION = "data.deletion"
    DATA_EXPORT = "data.export"
    
    # Security events
    SECURITY_INTRUSION_ATTEMPT = "security.intrusion.attempt"
    SECURITY_PERMISSION_DENIED = "security.permission.denied"
    SECURITY_ENCRYPTION_ERROR = "security.encryption.error"
    SECURITY_SUSPICIOUS_ACTIVITY = "security.suspicious.activity"
    
    # User interactions
    USER_COMMAND = "user.command"
    USER_CHAT_MESSAGE = "user.chat.message"
    USER_SETTINGS_CHANGE = "user.settings.change"
    USER_PREFERENCE_UPDATE = "user.preference.update"


class SeverityLevel(Enum):
    """Event severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class AuditEvent:
    """Audit event structure"""
    event_id: str
    timestamp: datetime.datetime
    event_type: EventType
    severity: SeverityLevel
    user_id: str
    session_id: Optional[str]
    source_ip: Optional[str]
    user_agent: Optional[str]
    message: str
    details: Dict[str, Any]
    success: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        result['event_type'] = self.event_type.value
        result['severity'] = self.severity.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditEvent':
        """Create from dictionary"""
        data['timestamp'] = datetime.datetime.fromisoformat(data['timestamp'])
        data['event_type'] = EventType(data['event_type'])
        data['severity'] = SeverityLevel(data['severity'])
        return cls(**data)


class AuditLogger:
    """
    Comprehensive audit logging system
    
    Features:
    - Structured event logging with encryption
    - Real-time threat detection
    - Compliance reporting
    - Log integrity verification
    - Automatic log rotation and archival
    """
    
    def __init__(self, log_dir: str = "logs/security", encrypt_logs: bool = True):
        """
        Initialize audit logger
        
        Args:
            log_dir: Directory for audit logs
            encrypt_logs: Whether to encrypt sensitive log data
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.encrypt_logs = encrypt_logs and ENCRYPTION_AVAILABLE
        
        # Database for structured logging
        self.db_path = self.log_dir / "audit.db"
        self._init_database()
        
        # Event queue for asynchronous logging
        self.event_queue = Queue(maxsize=10000)
        self.processing_thread = None
        self.running = True
        
        # Alert thresholds
        self.alert_thresholds = {
            EventType.AUTH_LOGIN_FAILURE: 3,  # 3 failed logins
            EventType.SECURITY_INTRUSION_ATTEMPT: 1,  # Any intrusion attempt
            EventType.API_ERROR: 10,  # 10 API errors
        }
        
        # Recent events cache for pattern detection
        self.recent_events = []
        self.cache_lock = threading.Lock()
        
        # Start background processing
        self.start_processing()
        
        logger.info(f"Audit logger initialized at {self.log_dir}")
    
    def _init_database(self):
        """Initialize audit database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Audit events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_events (
                        event_id TEXT PRIMARY KEY,
                        timestamp DATETIME,
                        event_type TEXT,
                        severity TEXT,
                        user_id TEXT,
                        session_id TEXT,
                        source_ip TEXT,
                        user_agent TEXT,
                        message TEXT,
                        details TEXT,
                        success BOOLEAN,
                        encrypted BOOLEAN DEFAULT FALSE,
                        checksum TEXT
                    )
                """)
                
                # Indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_events(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_event_type ON audit_events(event_type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON audit_events(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_severity ON audit_events(severity)")
                
                # Alert history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS security_alerts (
                        alert_id TEXT PRIMARY KEY,
                        timestamp DATETIME,
                        alert_type TEXT,
                        severity TEXT,
                        message TEXT,
                        event_count INTEGER,
                        resolved BOOLEAN DEFAULT FALSE,
                        resolved_at DATETIME
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize audit database: {e}")
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        timestamp = datetime.datetime.now().isoformat()
        return hashlib.sha256(f"{timestamp}{os.urandom(16).hex()}".encode()).hexdigest()[:16]
    
    def _calculate_checksum(self, event_data: str) -> str:
        """Calculate integrity checksum for event data"""
        return hashlib.sha256(event_data.encode()).hexdigest()
    
    def log_event(self, 
                  event_type: EventType,
                  message: str,
                  severity: SeverityLevel = SeverityLevel.INFO,
                  user_id: str = "system",
                  session_id: Optional[str] = None,
                  source_ip: Optional[str] = None,
                  user_agent: Optional[str] = None,
                  details: Optional[Dict[str, Any]] = None,
                  success: bool = True) -> str:
        """
        Log an audit event
        
        Args:
            event_type: Type of event
            message: Human-readable message
            severity: Event severity
            user_id: User identifier
            session_id: Session identifier
            source_ip: Source IP address
            user_agent: User agent string
            details: Additional event details
            success: Whether the operation was successful
            
        Returns:
            Event ID
        """
        try:
            event_id = self._generate_event_id()
            timestamp = datetime.datetime.now()
            
            event = AuditEvent(
                event_id=event_id,
                timestamp=timestamp,
                event_type=event_type,
                severity=severity,
                user_id=user_id,
                session_id=session_id,
                source_ip=source_ip,
                user_agent=user_agent,
                message=message,
                details=details or {},
                success=success
            )
            
            # Add to queue for processing
            if not self.event_queue.full():
                self.event_queue.put(event)
            else:
                logger.warning("Audit event queue full, dropping event")
            
            # Add to recent events cache for pattern detection
            with self.cache_lock:
                self.recent_events.append(event)
                # Keep only last 1000 events
                if len(self.recent_events) > 1000:
                    self.recent_events = self.recent_events[-1000:]
            
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            return ""
    
    def start_processing(self):
        """Start background event processing"""
        if self.processing_thread is None or not self.processing_thread.is_alive():
            self.processing_thread = threading.Thread(target=self._process_events, daemon=True)
            self.processing_thread.start()
    
    def _process_events(self):
        """Background thread for processing audit events"""
        while self.running:
            try:
                # Get event from queue with timeout
                event = self.event_queue.get(timeout=1.0)
                
                # Store in database
                self._store_event(event)
                
                # Check for security patterns
                self._check_security_patterns(event)
                
                # Write to file log
                self._write_file_log(event)
                
                self.event_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing audit event: {e}")
    
    def _store_event(self, event: AuditEvent):
        """Store event in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Prepare event data
                details_json = json.dumps(event.details)
                event_data = f"{event.event_id}{event.timestamp.isoformat()}{event.event_type.value}{event.message}{details_json}"
                checksum = self._calculate_checksum(event_data)
                
                # Encrypt sensitive details if enabled
                encrypted = False
                if self.encrypt_logs and event.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
                    try:
                        from core.encryption import encrypt_sensitive_data
                        details_json = encrypt_sensitive_data(details_json, "audit_log")
                        encrypted = True
                    except Exception as e:
                        logger.warning(f"Failed to encrypt audit log: {e}")
                
                cursor.execute("""
                    INSERT INTO audit_events 
                    (event_id, timestamp, event_type, severity, user_id, session_id, 
                     source_ip, user_agent, message, details, success, encrypted, checksum)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id,
                    event.timestamp,
                    event.event_type.value,
                    event.severity.value,
                    event.user_id,
                    event.session_id,
                    event.source_ip,
                    event.user_agent,
                    event.message,
                    details_json,
                    event.success,
                    encrypted,
                    checksum
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store audit event: {e}")
    
    def _write_file_log(self, event: AuditEvent):
        """Write event to daily log file"""
        try:
            date_str = event.timestamp.strftime("%Y-%m-%d")
            log_file = self.log_dir / f"audit_{date_str}.log"
            
            log_entry = {
                "timestamp": event.timestamp.isoformat(),
                "event_id": event.event_id,
                "type": event.event_type.value,
                "severity": event.severity.value,
                "user": event.user_id,
                "session": event.session_id,
                "ip": event.source_ip,
                "message": event.message,
                "success": event.success
            }
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\
")
                
        except Exception as e:
            logger.error(f"Failed to write file log: {e}")
    
    def _check_security_patterns(self, event: AuditEvent):
        """Check for security patterns and generate alerts"""
        try:
            # Count recent events of same type
            current_time = datetime.datetime.now()
            recent_window = current_time - datetime.timedelta(minutes=5)
            
            with self.cache_lock:
                recent_count = sum(1 for e in self.recent_events 
                                 if e.event_type == event.event_type and 
                                    e.timestamp >= recent_window)
            
            # Check if threshold exceeded
            threshold = self.alert_thresholds.get(event.event_type)
            if threshold and recent_count >= threshold:
                self._generate_security_alert(
                    event.event_type,
                    f"Threshold exceeded: {recent_count} {event.event_type.value} events in 5 minutes",
                    SeverityLevel.HIGH,
                    recent_count
                )
                
        except Exception as e:
            logger.error(f"Failed to check security patterns: {e}")
    
    def _generate_security_alert(self, event_type: EventType, message: str, 
                               severity: SeverityLevel, event_count: int):
        """Generate security alert"""
        try:
            alert_id = self._generate_event_id()
            timestamp = datetime.datetime.now()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO security_alerts 
                    (alert_id, timestamp, alert_type, severity, message, event_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    alert_id,
                    timestamp,
                    event_type.value,
                    severity.value,
                    message,
                    event_count
                ))
                conn.commit()
            
            # Log the alert as an audit event
            self.log_event(
                EventType.SECURITY_SUSPICIOUS_ACTIVITY,
                f"SECURITY ALERT: {message}",
                severity,
                details={"alert_id": alert_id, "event_count": event_count}
            )
            
            logger.warning(f"SECURITY ALERT: {message}")
            
        except Exception as e:
            logger.error(f"Failed to generate security alert: {e}")
    
    def query_events(self, 
                    start_time: Optional[datetime.datetime] = None,
                    end_time: Optional[datetime.datetime] = None,
                    event_types: Optional[List[EventType]] = None,
                    user_id: Optional[str] = None,
                    severity: Optional[SeverityLevel] = None,
                    limit: int = 1000) -> List[Dict[str, Any]]:
        """Query audit events with filters"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Build query
                conditions = []
                params = []
                
                if start_time:
                    conditions.append("timestamp >= ?")
                    params.append(start_time)
                
                if end_time:
                    conditions.append("timestamp <= ?")
                    params.append(end_time)
                
                if event_types:
                    type_placeholders = ",".join(["?"] * len(event_types))
                    conditions.append(f"event_type IN ({type_placeholders})")
                    params.extend([et.value for et in event_types])
                
                if user_id:
                    conditions.append("user_id = ?")
                    params.append(user_id)
                
                if severity:
                    conditions.append("severity = ?")
                    params.append(severity.value)
                
                where_clause = " AND ".join(conditions) if conditions else "1=1"
                query = f"""
                    SELECT * FROM audit_events 
                    WHERE {where_clause} 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # Convert to dictionaries and decrypt if needed
                events = []
                for row in rows:
                    event_dict = dict(row)
                    
                    # Decrypt details if encrypted
                    if event_dict.get('encrypted'):
                        try:
                            from core.encryption import decrypt_sensitive_data
                            event_dict['details'] = decrypt_sensitive_data(
                                event_dict['details'], "audit_log"
                            )
                        except Exception as e:
                            logger.warning(f"Failed to decrypt audit log: {e}")
                    
                    events.append(event_dict)
                
                return events
                
        except Exception as e:
            logger.error(f"Failed to query audit events: {e}")
            return []
    
    def get_security_alerts(self, resolved: Optional[bool] = None) -> List[Dict[str, Any]]:
        """Get security alerts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if resolved is not None:
                    cursor.execute("""
                        SELECT * FROM security_alerts 
                        WHERE resolved = ? 
                        ORDER BY timestamp DESC
                    """, (resolved,))
                else:
                    cursor.execute("""
                        SELECT * FROM security_alerts 
                        ORDER BY timestamp DESC
                    """)
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get security alerts: {e}")
            return []
    
    def generate_compliance_report(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate compliance report for given date range"""
        try:
            start_dt = datetime.datetime.fromisoformat(start_date)
            end_dt = datetime.datetime.fromisoformat(end_date)
            
            events = self.query_events(start_time=start_dt, end_time=end_dt, limit=100000)
            
            # Analyze events
            report = {
                "period": {"start": start_date, "end": end_date},
                "total_events": len(events),
                "event_breakdown": {},
                "severity_breakdown": {},
                "auth_events": 0,
                "failed_auth_attempts": 0,
                "system_events": 0,
                "api_events": 0,
                "security_events": 0,
                "unique_users": set(),
                "alerts_generated": len(self.get_security_alerts())
            }
            
            for event in events:
                event_type = event['event_type']
                severity = event['severity']
                
                # Count by type
                report['event_breakdown'][event_type] = report['event_breakdown'].get(event_type, 0) + 1
                
                # Count by severity
                report['severity_breakdown'][severity] = report['severity_breakdown'].get(severity, 0) + 1
                
                # Category counts
                if event_type.startswith('auth.'):
                    report['auth_events'] += 1
                    if event_type == 'auth.login.failure':
                        report['failed_auth_attempts'] += 1
                elif event_type.startswith('system.'):
                    report['system_events'] += 1
                elif event_type.startswith('api.'):
                    report['api_events'] += 1
                elif event_type.startswith('security.'):
                    report['security_events'] += 1
                
                # Unique users
                if event['user_id']:
                    report['unique_users'].add(event['user_id'])
            
            report['unique_users'] = len(report['unique_users'])
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            return {}
    
    def cleanup_old_logs(self, days_to_keep: int = 90):
        """Clean up old audit logs"""
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_to_keep)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Archive old events to file before deletion
                cursor.execute(
                    "SELECT * FROM audit_events WHERE timestamp < ?", 
                    (cutoff_date,)
                )
                
                old_events = cursor.fetchall()
                if old_events:
                    archive_file = self.log_dir / f"archived_events_{cutoff_date.strftime('%Y%m%d')}.json"
                    with open(archive_file, 'w') as f:
                        json.dump([dict(zip([col[0] for col in cursor.description], row)) 
                                  for row in old_events], f, default=str)
                
                # Delete old events
                cursor.execute("DELETE FROM audit_events WHERE timestamp < ?", (cutoff_date,))
                
                # Delete old alerts
                cursor.execute(
                    "DELETE FROM security_alerts WHERE timestamp < ? AND resolved = ?", 
                    (cutoff_date, True)
                )
                
                conn.commit()
                
                logger.info(f"Cleaned up {len(old_events)} old audit events")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")
    
    def stop(self):
        """Stop audit logging"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=5.0)


# Global audit logger instance
_audit_logger = None

def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance"""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


# Convenience functions for common audit events
def audit_auth_success(user_id: str, session_id: str, source_ip: str = None):
    """Log successful authentication"""
    get_audit_logger().log_event(
        EventType.AUTH_LOGIN_SUCCESS,
        f"User {user_id} authenticated successfully",
        SeverityLevel.INFO,
        user_id=user_id,
        session_id=session_id,
        source_ip=source_ip
    )

def audit_auth_failure(user_id: str, reason: str, source_ip: str = None):
    """Log failed authentication"""
    get_audit_logger().log_event(
        EventType.AUTH_LOGIN_FAILURE,
        f"Authentication failed for {user_id}: {reason}",
        SeverityLevel.MEDIUM,
        user_id=user_id,
        source_ip=source_ip,
        success=False
    )

def audit_system_command(command: str, user_id: str, success: bool = True):
    """Log system command execution"""
    get_audit_logger().log_event(
        EventType.SYSTEM_COMMAND_EXEC,
        f"System command executed: {command}",
        SeverityLevel.MEDIUM,
        user_id=user_id,
        success=success,
        details={"command": command}
    )

def audit_api_request(endpoint: str, user_id: str, source_ip: str = None, success: bool = True):
    """Log API request"""
    get_audit_logger().log_event(
        EventType.API_REQUEST,
        f"API request to {endpoint}",
        SeverityLevel.LOW,
        user_id=user_id,
        source_ip=source_ip,
        success=success,
        details={"endpoint": endpoint}
    )

def audit_data_access(data_type: str, user_id: str, operation: str = "read"):
    """Log data access"""
    get_audit_logger().log_event(
        EventType.DATA_ACCESS,
        f"Data access: {operation} {data_type}",
        SeverityLevel.LOW,
        user_id=user_id,
        details={"data_type": data_type, "operation": operation}
    )

def audit_security_event(message: str, severity: SeverityLevel = SeverityLevel.HIGH, 
                        user_id: str = "system", details: Dict[str, Any] = None):
    """Log security event"""
    get_audit_logger().log_event(
        EventType.SECURITY_SUSPICIOUS_ACTIVITY,
        message,
        severity,
        user_id=user_id,
        details=details or {}
    )


if __name__ == "__main__":
    # Test audit logging
    logger.debug("Testing audit logging system...")
    
    audit_logger = AuditLogger()
    
    # Test various events
    audit_auth_success("test_user", "session_123", "127.0.0.1")
    audit_auth_failure("test_user", "Invalid PIN", "127.0.0.1")
    audit_system_command("ls -la", "test_user")
    audit_api_request("/api/chat", "test_user", "127.0.0.1")
    
    # Wait for processing
    import time
    time.sleep(2)
    
    # Query events
    events = audit_logger.query_events(limit=10)
    print(f"Found {len(events)} events")
    
    # Generate report
    report = audit_logger.generate_compliance_report(
        (datetime.datetime.now() - datetime.timedelta(days=1)).isoformat(),
        datetime.datetime.now().isoformat()
    )
    print(f"Compliance report: {report}")
    
    audit_logger.stop()
    logger.info("✅ Audit logging test completed!")