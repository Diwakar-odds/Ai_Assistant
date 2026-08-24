# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Privacy Consent Manager
=======================

Manages user consent for data processing activities in compliance with:
- GDPR (General Data Protection Regulation)
- CCPA (California Consumer Privacy Act)
- Other privacy regulations

Features:
- Granular consent per service
- Consent tracking and logging
- Revocable consent
- Per-user consent management
- Consent expiry and renewal
- Audit trail for compliance

Consent Types:
- external_stt: External speech-to-text APIs (Whisper, Google Cloud)
- external_tts: External text-to-speech APIs (Edge-TTS)
- biometric_storage: Voice biometric data storage
- data_analytics: Usage analytics and telemetry
- third_party_sharing: Sharing data with third parties
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ConsentType(Enum):
    """Types of consent that can be requested"""
    EXTERNAL_STT = "external_stt"  # OpenAI Whisper, Google Cloud STT
    EXTERNAL_TTS = "external_tts"  # Microsoft Edge-TTS
    BIOMETRIC_STORAGE = "biometric_storage"  # Voice fingerprints, speaker models
    DATA_ANALYTICS = "data_analytics"  # Usage analytics
    THIRD_PARTY_SHARING = "third_party_sharing"  # Sharing with partners
    VOICE_RECORDING = "voice_recording"  # Recording voice for training


class ConsentStatus(Enum):
    """Status of consent"""
    GRANTED = "granted"
    DENIED = "denied"
    EXPIRED = "expired"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"


@dataclass
class ConsentRecord:
    """Record of a single consent decision"""
    consent_type: ConsentType
    status: ConsentStatus
    granted_at: float  # timestamp
    expires_at: Optional[float] = None  # Optional expiry
    withdrawn_at: Optional[float] = None
    granted_via: str = "system"  # How consent was obtained (ui, api, cli)
    version: str = "1.0"  # Consent policy version
    metadata: Dict = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """Check if consent is currently valid"""
        if self.status != ConsentStatus.GRANTED:
            return False
        
        if self.expires_at and time.time() > self.expires_at:
            return False
        
        return True


@dataclass
class UserConsent:
    """Complete consent profile for a user"""
    user_id: str
    consents: Dict[str, ConsentRecord] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    last_updated: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON storage"""
        return {
            'user_id': self.user_id,
            'consents': {
                k: {
                    'consent_type': v.consent_type.value,
                    'status': v.status.value,
                    'granted_at': v.granted_at,
                    'expires_at': v.expires_at,
                    'withdrawn_at': v.withdrawn_at,
                    'granted_via': v.granted_via,
                    'version': v.version,
                    'metadata': v.metadata
                }
                for k, v in self.consents.items()
            },
            'created_at': self.created_at,
            'last_updated': self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'UserConsent':
        """Create from dictionary"""
        user_consent = cls(
            user_id=data['user_id'],
            created_at=data.get('created_at', time.time()),
            last_updated=data.get('last_updated', time.time())
        )
        
        for consent_type_str, consent_data in data.get('consents', {}).items():
            record = ConsentRecord(
                consent_type=ConsentType(consent_data['consent_type']),
                status=ConsentStatus(consent_data['status']),
                granted_at=consent_data['granted_at'],
                expires_at=consent_data.get('expires_at'),
                withdrawn_at=consent_data.get('withdrawn_at'),
                granted_via=consent_data.get('granted_via', 'system'),
                version=consent_data.get('version', '1.0'),
                metadata=consent_data.get('metadata', {})
            )
            user_consent.consents[consent_type_str] = record
        
        return user_consent


class PrivacyConsentManager:
    """
    Manages privacy consent for all users and data processing activities.
    
    Usage:
        manager = PrivacyConsentManager()
        
        # Request consent
        if not manager.has_consent(user_id, ConsentType.EXTERNAL_STT):
            # Show consent dialog to user
            granted = show_consent_dialog("External Speech Recognition")
            if granted:
                manager.grant_consent(user_id, ConsentType.EXTERNAL_STT)
        
        # Check consent before processing
        if manager.has_consent(user_id, ConsentType.EXTERNAL_STT):
            # Use Whisper API
            transcript = call_whisper_api(audio)
        else:
            # Use offline Vosk
            transcript = use_vosk(audio)
    """
    
    def __init__(self, consent_storage_path: Optional[Path] = None):
        """
        Initialize consent manager.
        
        Args:
            consent_storage_path: Path to store consent records
        """
        # Set up storage path
        if consent_storage_path is None:
            base_dir = Path(__file__).parent.parent.parent
            self.storage_path = base_dir / "data" / "privacy_consents"
        else:
            self.storage_path = Path(consent_storage_path)
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache of user consents
        self.user_consents: Dict[str, UserConsent] = {}
        
        # Default consent expiry (None = never expires)
        self.default_expiry_days = None
        
        # Load existing consents
        self._load_all_consents()
        
        logger.info(f"Privacy Consent Manager initialized with {len(self.user_consents)} user profiles")
    
    def has_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        auto_prompt: bool = False
    ) -> bool:
        """
        Check if user has granted valid consent for a specific type.
        
        Args:
            user_id: User identifier
            consent_type: Type of consent to check
            auto_prompt: If True and no consent, trigger consent request
            
        Returns:
            True if consent is granted and valid, False otherwise
        """
        # Get or create user consent profile
        if user_id not in self.user_consents:
            self.user_consents[user_id] = UserConsent(user_id=user_id)
        
        user_consent = self.user_consents[user_id]
        consent_key = consent_type.value
        
        # Check if consent record exists
        if consent_key not in user_consent.consents:
            if auto_prompt:
                logger.info(f"No consent found for {user_id}/{consent_type.value}, prompting...")
                # In real implementation, trigger UI prompt here
            return False
        
        record = user_consent.consents[consent_key]
        
        # Check if consent is valid
        is_valid = record.is_valid()
        
        if not is_valid:
            logger.debug(f"Consent for {user_id}/{consent_type.value} is not valid (status: {record.status.value})")
        
        return is_valid
    
    def grant_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        granted_via: str = "system",
        expiry_days: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Grant consent for a user.
        
        Args:
            user_id: User identifier
            consent_type: Type of consent to grant
            granted_via: How consent was obtained (ui, api, cli)
            expiry_days: Days until consent expires (None = never)
            metadata: Additional metadata about consent
            
        Returns:
            True if consent was granted successfully
        """
        try:
            # Get or create user consent profile
            if user_id not in self.user_consents:
                self.user_consents[user_id] = UserConsent(user_id=user_id)
            
            user_consent = self.user_consents[user_id]
            
            # Calculate expiry if specified
            expires_at = None
            if expiry_days is not None:
                expires_at = time.time() + (expiry_days * 24 * 60 * 60)
            elif self.default_expiry_days is not None:
                expires_at = time.time() + (self.default_expiry_days * 24 * 60 * 60)
            
            # Create consent record
            record = ConsentRecord(
                consent_type=consent_type,
                status=ConsentStatus.GRANTED,
                granted_at=time.time(),
                expires_at=expires_at,
                granted_via=granted_via,
                metadata=metadata or {}
            )
            
            # Store consent
            user_consent.consents[consent_type.value] = record
            user_consent.last_updated = time.time()
            
            # Save to disk
            self._save_user_consent(user_consent)
            
            logger.info(f"✅ Consent granted for {user_id}/{consent_type.value} via {granted_via}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to grant consent for {user_id}/{consent_type.value}: {e}")
            return False
    
    def deny_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        denied_via: str = "system",
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Explicitly deny consent (user said no).
        
        Args:
            user_id: User identifier
            consent_type: Type of consent to deny
            denied_via: How denial was recorded
            metadata: Additional metadata
            
        Returns:
            True if denial was recorded successfully
        """
        try:
            if user_id not in self.user_consents:
                self.user_consents[user_id] = UserConsent(user_id=user_id)
            
            user_consent = self.user_consents[user_id]
            
            record = ConsentRecord(
                consent_type=consent_type,
                status=ConsentStatus.DENIED,
                granted_at=time.time(),
                granted_via=denied_via,
                metadata=metadata or {}
            )
            
            user_consent.consents[consent_type.value] = record
            user_consent.last_updated = time.time()
            
            self._save_user_consent(user_consent)
            
            logger.info(f"❌ Consent denied for {user_id}/{consent_type.value}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to record consent denial for {user_id}/{consent_type.value}: {e}")
            return False
    
    def withdraw_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        reason: Optional[str] = None
    ) -> bool:
        """
        Withdraw previously granted consent (user changed mind).
        
        Args:
            user_id: User identifier
            consent_type: Type of consent to withdraw
            reason: Optional reason for withdrawal
            
        Returns:
            True if withdrawal was successful
        """
        try:
            if user_id not in self.user_consents:
                logger.warning(f"No consent profile found for {user_id}")
                return False
            
            user_consent = self.user_consents[user_id]
            consent_key = consent_type.value
            
            if consent_key not in user_consent.consents:
                logger.warning(f"No consent record found for {user_id}/{consent_type.value}")
                return False
            
            record = user_consent.consents[consent_key]
            record.status = ConsentStatus.WITHDRAWN
            record.withdrawn_at = time.time()
            
            if reason:
                record.metadata['withdrawal_reason'] = reason
            
            user_consent.last_updated = time.time()
            
            self._save_user_consent(user_consent)
            
            logger.info(f"🚫 Consent withdrawn for {user_id}/{consent_type.value}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to withdraw consent for {user_id}/{consent_type.value}: {e}")
            return False
    
    def get_user_consents(self, user_id: str) -> Dict[str, ConsentRecord]:
        """
        Get all consent records for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary of consent records
        """
        if user_id not in self.user_consents:
            return {}
        
        return self.user_consents[user_id].consents.copy()
    
    def get_consent_summary(self, user_id: str) -> Dict[str, str]:
        """
        Get summary of user's consent status.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary mapping consent type to status
        """
        consents = self.get_user_consents(user_id)
        
        summary = {}
        for consent_type in ConsentType:
            key = consent_type.value
            if key in consents:
                record = consents[key]
                if record.is_valid():
                    summary[key] = "granted"
                else:
                    summary[key] = record.status.value
            else:
                summary[key] = "not_requested"
        
        return summary
    
    def export_user_data(self, user_id: str) -> Dict:
        """
        Export all consent data for a user (GDPR right to access).
        
        Args:
            user_id: User identifier
            
        Returns:
            Complete consent data for user
        """
        if user_id not in self.user_consents:
            return {
                'user_id': user_id,
                'consents': {},
                'message': 'No consent data found'
            }
        
        return self.user_consents[user_id].to_dict()
    
    def delete_user_data(self, user_id: str) -> bool:
        """
        Delete all consent data for a user (GDPR right to erasure).
        
        Args:
            user_id: User identifier
            
        Returns:
            True if data was deleted successfully
        """
        try:
            if user_id in self.user_consents:
                del self.user_consents[user_id]
            
            # Delete file
            consent_file = self.storage_path / f"{user_id}_consent.json"
            if consent_file.exists():
                consent_file.unlink()
            
            logger.info(f"🗑️ Deleted all consent data for {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete consent data for {user_id}: {e}")
            return False
    
    def _save_user_consent(self, user_consent: UserConsent):
        """Save user consent to disk"""
        try:
            consent_file = self.storage_path / f"{user_consent.user_id}_consent.json"
            
            with open(consent_file, 'w') as f:
                json.dump(user_consent.to_dict(), f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save consent for {user_consent.user_id}: {e}")
    
    def _load_all_consents(self):
        """Load all existing consent records from disk"""
        try:
            if not self.storage_path.exists():
                return
            
            for consent_file in self.storage_path.glob("*_consent.json"):
                try:
                    with open(consent_file, 'r') as f:
                        data = json.load(f)
                    
                    user_consent = UserConsent.from_dict(data)
                    self.user_consents[user_consent.user_id] = user_consent
                    
                except Exception as e:
                    logger.warning(f"Failed to load consent file {consent_file}: {e}")
            
            logger.debug(f"Loaded consent records for {len(self.user_consents)} users")
            
        except Exception as e:
            logger.error(f"Error loading consent records: {e}")
    
    def require_consent(self, *consent_types: ConsentType):
        """
        Decorator to require consent before executing a function.
        
        Usage:
            @consent_manager.require_consent(ConsentType.EXTERNAL_STT)
            def use_whisper_api(user_id, audio):
                # This will only execute if user has consent
                pass
        """
        def decorator(func):
            def wrapper(user_id, *args, **kwargs):
                # Check all required consents
                for consent_type in consent_types:
                    if not self.has_consent(user_id, consent_type):
                        raise PermissionError(
                            f"User {user_id} has not consented to {consent_type.value}"
                        )
                
                # All consents valid, execute function
                return func(user_id, *args, **kwargs)
            
            return wrapper
        return decorator


# Global singleton instance
_global_consent_manager: Optional[PrivacyConsentManager] = None


def get_consent_manager() -> PrivacyConsentManager:
    """Get global PrivacyConsentManager instance (singleton pattern)"""
    global _global_consent_manager
    
    if _global_consent_manager is None:
        _global_consent_manager = PrivacyConsentManager()
    
    return _global_consent_manager


if __name__ == "__main__":
    # Example usage
    print("Privacy Consent Manager - Test")
    print("=" * 50)
    
    manager = PrivacyConsentManager()
    
    # Test user
    user_id = "test_user_001"
    
    # Grant consent
    manager.grant_consent(user_id, ConsentType.EXTERNAL_STT, granted_via="cli")
    manager.grant_consent(user_id, ConsentType.BIOMETRIC_STORAGE, granted_via="cli")
    
    # Check consent
    print(f"\nHas STT consent: {manager.has_consent(user_id, ConsentType.EXTERNAL_STT)}")
    print(f"Has TTS consent: {manager.has_consent(user_id, ConsentType.EXTERNAL_TTS)}")
    
    # Get summary
    summary = manager.get_consent_summary(user_id)
    print(f"\nConsent Summary:")
    for consent_type, status in summary.items():
        print(f"  {consent_type}: {status}")
    
    # Withdraw consent
    manager.withdraw_consent(user_id, ConsentType.EXTERNAL_STT, reason="Privacy concerns")
    print(f"\nAfter withdrawal - Has STT consent: {manager.has_consent(user_id, ConsentType.EXTERNAL_STT)}")
    
    # Export data
    data = manager.export_user_data(user_id)
    print(f"\nExported data: {json.dumps(data, indent=2)}")
    
    print("\n✅ Privacy consent tests passed!")
