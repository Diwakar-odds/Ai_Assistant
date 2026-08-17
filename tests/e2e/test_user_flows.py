"""
E2E (End-to-End) tests for critical user flows.
"""

import pytest
import time

class TestChatFlow:
    """Test complete chat conversation flow"""
    
    def test_multi_turn_conversation(self, app_client):
        """Test multiple chat turns"""
        # Turn 1
        response1 = app_client.post('/api/chat', json={'message': 'hello'})
        assert response1.status_code == 200
        
        # Turn 2
        response2 = app_client.post('/api/chat', json={'message': 'who are you'})
        assert response2.status_code == 200
        
        # Turn 3
        response3 = app_client.post('/api/chat', json={'message': 'goodbye'})
        assert response3.status_code == 200

class TestAuthFlow:
    """Test authentication flow"""
    
    def test_login_and_use_token(self, app_client):
        """Test login then use token for authenticated requests"""
        # Login
        response = app_client.post('/api/auth/login', json={'pin': '1234'})
        assert response.status_code == 200
        data = response.get_json()
        token = data['access_token']
        
        # Use token
        headers = {'Authorization': f'Bearer {token}'}
        verify_response = app_client.get('/api/auth/verify', headers=headers)
        assert verify_response.status_code == 200

class TestVoiceFlow:
    """Test voice interaction flow"""
    
    def test_voice_status_check(self, app_client):
        """Test checking voice status"""
        response = app_client.get('/api/voice/status')
        assert response.status_code == 200
        data = response.get_json()
        assert 'available' in data

class TestSystemFlow:
    """Test system monitoring flow"""
    
    def test_system_health_check(self, app_client):
        """Test complete system health check"""
        # Check status
        status = app_client.get('/api/status')
        assert status.status_code == 200
        
        # Check initialization
        init_status = app_client.get('/api/status/initialization')
        assert init_status.status_code == 200
        
        # Check features
        features = app_client.get('/api/features')
        assert features.status_code == 200
