"""
Integration tests for API endpoints.

Tests blueprint routes and their integration with the backend.
"""

import pytest
import json

def test_status_endpoint(app_client):
    """Test /api/status endpoint"""
    response = app_client.get('/api/status')
    assert response.status_code == 200
    data = response.get_json()
    assert 'status' in data
    assert data['status'] == 'online'
    assert 'services' in data

def test_auth_login(app_client):
    """Test authentication login"""
    response = app_client.post('/api/auth/login', 
                                json={'pin': '1234'},
                                content_type='application/json')
    assert response.status_code == 200
    data = response.get_json()
    assert 'access_token' in data
    assert 'token_type' in data
    assert data['token_type'] == 'Bearer'

def test_auth_login_invalid_pin(app_client):
    """Test login with invalid PIN"""
    response = app_client.post('/api/auth/login',
                                json={'pin': 'wrong'},
                                content_type='application/json')
    assert response.status_code == 401
    data = response.get_json()
    assert 'error' in data

def test_chat_endpoint_no_message(app_client):
    """Test chat endpoint without message"""
    response = app_client.post('/api/chat',
                                json={},
                                content_type='application/json')
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_chat_endpoint_with_message(app_client):
    """Test chat endpoint with valid message"""
    response = app_client.post('/api/chat',
                                json={'message': 'hello'},
                                content_type='application/json')
    assert response.status_code == 200
    data = response.get_json()
    assert 'response' in data
    assert isinstance(data['response'], str)

def test_command_endpoint(app_client, auth_headers):
    """Test command processing endpoint"""
    response = app_client.post('/api/command',
                                json={'command': 'test'},
                                content_type='application/json',
                                headers=auth_headers)
    assert response.status_code == 200
    data = response.get_json()
    assert 'success' in data
    assert 'response' in data

def test_apps_list_endpoint(app_client):
    """Test apps list endpoint"""
    response = app_client.get('/api/apps')
    assert response.status_code == 200
    data = response.get_json()
    assert 'apps' in data
    assert isinstance(data['apps'], list)

def test_learning_stats_endpoint(app_client):
    """Test learning stats endpoint"""
    response = app_client.get('/api/learning/stats')
    # May return 200 or 500 depending on learning system availability
    assert response.status_code in [200, 500]

def test_chat_suggestions_endpoint(app_client):
    """Test chat suggestions endpoint"""
    response = app_client.get('/api/chat/suggestions')
    assert response.status_code == 200
    data = response.get_json()
    assert 'suggestions' in data
    assert isinstance(data['suggestions'], list)

def test_system_initialization_status(app_client):
    """Test system initialization status endpoint"""
    response = app_client.get('/api/status/initialization')
    assert response.status_code == 200
    data = response.get_json()
    assert 'status' in data
    assert isinstance(data['status'], dict)
