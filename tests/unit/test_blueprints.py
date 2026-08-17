"""
Unit tests for blueprint routes.

Tests auth, chat, system, learning, apps, voice, multimodal, preferences, memory, and utilities blueprints.
"""

import pytest

class TestAuthBlueprint:
    """Tests for authentication blueprint"""
    
    def test_login_success(self, app_client):
        response = app_client.post('/api/auth/login', json={'pin': '1234'})
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
    
    def test_login_invalid_pin(self, app_client):
        response = app_client.post('/api/auth/login', json={'pin': 'wrong'})
        assert response.status_code == 401
    
    def test_verify_token(self, app_client, auth_headers):
        response = app_client.get('/api/auth/verify', headers=auth_headers)
        assert response.status_code == 200

class TestChatBlueprint:
    """Tests for chat blueprint"""
    
    def test_chat_basic(self, app_client):
        response = app_client.post('/api/chat', json={'message': 'hello'})
        assert response.status_code == 200
        data = response.get_json()
        assert 'response' in data
    
    def test_chat_no_message(self, app_client):
        response = app_client.post('/api/chat', json={})
        assert response.status_code == 400
    
    def test_command_endpoint(self, app_client, auth_headers):
        response = app_client.post('/api/command', json={'command': 'test'}, headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert 'success' in data
    
    def test_chat_suggestions(self, app_client):
        response = app_client.get('/api/chat/suggestions')
        assert response.status_code == 200
        data = response.get_json()
        assert 'suggestions' in data
        assert isinstance(data['suggestions'], list)

class TestSystemBlueprint:
    """Tests for system blueprint"""
    
    def test_status_endpoint(self, app_client):
        response = app_client.get('/api/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'online'
        assert 'services' in data
    
    def test_initialization_status(self, app_client):
        response = app_client.get('/api/status/initialization')
        assert response.status_code == 200
        data = response.get_json()
        assert 'status' in data

class TestAppsBlueprint:
    """Tests for apps blueprint"""
    
    def test_list_apps(self, app_client):
        response = app_client.get('/api/apps')
        assert response.status_code == 200
        data = response.get_json()
        assert 'apps' in data
    
    def test_launch_app(self, app_client):
        response = app_client.post('/api/apps/launch', json={'app_name': 'notepad'})
        assert response.status_code in [200, 503]

class TestVoiceBlueprint:
    """Tests for voice blueprint"""
    
    def test_voice_status(self, app_client):
        response = app_client.get('/api/voice/status')
        assert response.status_code == 200
        data = response.get_json()
        assert 'available' in data
    
    def test_voice_settings_get(self, app_client):
        response = app_client.get('/api/voice/settings')
        assert response.status_code == 200

class TestMultimodalBlueprint:
    """Tests for multimodal blueprint"""
    
    def test_multimodal_no_image(self, app_client):
        response = app_client.post('/api/multimodal/analyze', json={})
        assert response.status_code == 400

class TestPreferencesBlueprint:
    """Tests for preferences blueprint"""
    
    def test_get_preferences(self, app_client):
        response = app_client.get('/api/user/preferences')
        assert response.status_code == 200
        data = response.get_json()
        assert 'preferences' in data
    
    def test_update_preferences(self, app_client):
        response = app_client.post('/api/user/preferences', json={'theme': 'light'})
        assert response.status_code == 200

class TestUtilitiesBlueprint:
    """Tests for utilities blueprint"""
    
    def test_weather(self, app_client):
        response = app_client.get('/api/weather')
        assert response.status_code == 200
        data = response.get_json()
        assert 'temperature' in data or 'location' in data
    
    def test_features(self, app_client):
        response = app_client.get('/api/features')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, dict)
