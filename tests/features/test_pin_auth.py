"""
Test suite for PIN authentication system.
"""

import pytest
import sys
import os
import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_assistant.auth.pin_auth import PINAuth


class TestPINHashing:
    """Tests for PIN hashing functionality."""
    
    def test_hash_pin(self):
        """Test PIN hashing."""
        auth = PINAuth()
        pin = "1234"
        salt = "test_salt"
        
        hash1 = auth._hash_pin(pin, salt)
        hash2 = auth._hash_pin(pin, salt)
        
        # Same PIN and salt should produce same hash
        assert hash1 == hash2
        assert len(hash1) > 0
    
    def test_different_salts_different_hashes(self):
        """Test that different salts produce different hashes."""
        auth = PINAuth()
        pin = "1234"
        
        hash1 = auth._hash_pin(pin, "salt1")
        hash2 = auth._hash_pin(pin, "salt2")
        
        assert hash1 != hash2


class TestPINVerification:
    """Tests for PIN verification."""
    
    def test_verify_correct_pin(self):
        """Test verification of correct PIN."""
        auth = PINAuth()
        pin = "1234"
        
        # Set up PIN
        auth.salt = "test_salt"
        auth.pin_hash = auth._hash_pin(pin, auth.salt)
        
        # Verify
        assert auth.verify_pin(pin) is True
    
    def test_verify_incorrect_pin(self):
        """Test verification of incorrect PIN."""
        auth = PINAuth()
        
        # Set up PIN
        auth.salt = "test_salt"
        auth.pin_hash = auth._hash_pin("1234", auth.salt)
        
        # Verify wrong PIN
        assert auth.verify_pin("5678") is False


class TestRateLimiting:
    """Tests for rate limiting functionality."""
    
    def test_failed_attempt_tracking(self):
        """Test that failed attempts are tracked."""
        auth = PINAuth()
        auth.salt = "test_salt"
        auth.pin_hash = auth._hash_pin("1234", auth.salt)
        
        initial_count = len(auth.failed_attempts)
        
        # Make failed attempt
        auth.verify_pin("wrong")
        
        # Should have one more failed attempt
        assert len(auth.failed_attempts) > initial_count
    
    def test_lockout_after_max_attempts(self):
        """Test lockout after maximum failed attempts."""
        auth = PINAuth()
        auth.salt = "test_salt"
        auth.pin_hash = auth._hash_pin("1234", auth.salt)
        auth.MAX_FAILED_ATTEMPTS = 3
        
        # Make 3 failed attempts
        for _ in range(3):
            auth.verify_pin("wrong")
        
        # Should be locked out
        assert auth._is_locked_out() is True
    
    def test_lockout_clears_after_duration(self):
        """Test that lockout clears after duration."""
        auth = PINAuth()
        auth.LOCKOUT_DURATION_SECONDS = 1  # 1 second for testing
        auth.failed_attempts = [time.time() - 2] * 5  # Old attempts
        
        # Should not be locked out (attempts are old)
        assert auth._is_locked_out() is False
    
    def test_successful_login_clears_attempts(self):
        """Test that successful login clears failed attempts."""
        auth = PINAuth()
        auth.salt = "test_salt"
        auth.pin_hash = auth._hash_pin("1234", auth.salt)
        
        # Make some failed attempts
        auth.verify_pin("wrong")
        auth.verify_pin("wrong")
        
        assert len(auth.failed_attempts) > 0
        
        # Successful login
        auth.verify_pin("1234")
        
        # Failed attempts should be cleared
        assert len(auth.failed_attempts) == 0


class TestLockoutState:
    """Tests for lockout state persistence."""
    
    def test_save_lockout_state(self):
        """Test saving lockout state to file."""
        auth = PINAuth()
        auth.failed_attempts = [time.time(), time.time() - 10]
        
        with patch('builtins.open', mock_open()) as mock_file:
            auth._save_lockout_state()
            mock_file.assert_called_once()
    
    def test_load_lockout_state(self):
        """Test loading lockout state from file."""
        test_data = json.dumps({
            'failed_attempts': [time.time(), time.time() - 10]
        })
        
        with patch('builtins.open', mock_open(read_data=test_data)):
            with patch('pathlib.Path.exists', return_value=True):
                auth = PINAuth()
                auth._load_lockout_state()
                
                assert len(auth.failed_attempts) == 2


class TestPINSetup:
    """Tests for PIN setup functionality."""
    
    @patch('getpass.getpass')
    def test_setup_pin_success(self, mock_getpass):
        """Test successful PIN setup."""
        mock_getpass.side_effect = ["1234", "1234"]  # Matching PINs
        
        auth = PINAuth()
        
        with patch('builtins.open', mock_open()):
            result = auth.setup_pin()
            assert result is True
    
    @patch('getpass.getpass')
    def test_setup_pin_mismatch(self, mock_getpass):
        """Test PIN setup with mismatched PINs."""
        mock_getpass.side_effect = ["1234", "5678", "1234", "1234"]  # First mismatch, then match
        
        auth = PINAuth()
        
        with patch('builtins.open', mock_open()):
            result = auth.setup_pin()
            # Should eventually succeed after retry
            assert result is True


class TestEdgeCases:
    """Tests for edge cases."""
    
    def test_empty_pin(self):
        """Test handling of empty PIN."""
        auth = PINAuth()
        auth.salt = "test_salt"
        auth.pin_hash = auth._hash_pin("1234", auth.salt)
        
        assert auth.verify_pin("") is False
    
    def test_none_pin(self):
        """Test handling of None PIN."""
        auth = PINAuth()
        auth.salt = "test_salt"
        auth.pin_hash = auth._hash_pin("1234", auth.salt)
        
        # Should handle gracefully
        try:
            result = auth.verify_pin(None)
            assert result is False
        except:
            pytest.fail("Should handle None PIN gracefully")
    
    def test_very_long_pin(self):
        """Test handling of very long PIN."""
        auth = PINAuth()
        long_pin = "1" * 1000
        
        # Should handle without error
        hash_result = auth._hash_pin(long_pin, "salt")
        assert len(hash_result) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
