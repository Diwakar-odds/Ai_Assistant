"""
Web API for Secure App Integration Management

Provides REST API endpoints for managing app integrations through the web interface.
Includes proper authentication and security measures.
"""

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import json
import logging
from datetime import datetime
from functools import wraps
import os
import secrets

# Import our security modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.app_integrator import secure_app_integrator
from core.app_security import secure_app_manager

app = Flask(__name__)
app.secret_key = os.getenv('APP_SECRET_KEY', secrets.token_hex(32))

# Configure CORS
CORS(app, origins=[
    'http://localhost:3000',
    'http://localhost:5000', 
    'http://127.0.0.1:3000',
    'http://127.0.0.1:5000'
])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def require_auth(f):
    """Decorator to require authentication for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_password = os.getenv('ADMIN_PASSWORD')
        if not admin_password:
            return jsonify({'error': 'Server configuration error: ADMIN_PASSWORD not set'}), 500

        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            provided_password = auth_header.split(' ')[1]
            if secrets.compare_digest(provided_password, admin_password):
                return f(*args, **kwargs)

        if session.get('authenticated'):
            return f(*args, **kwargs)

        return jsonify({'error': 'Authentication required'}), 401

    return decorated_function

@app.route('/auth/login', methods=['POST'])
def login():
    """Authenticate user for web interface."""
    try:
        data = request.get_json()
        password = data.get('password', '')
        admin_password = os.getenv('ADMIN_PASSWORD')
        if not admin_password:
            return jsonify({'error': 'Server configuration error: ADMIN_PASSWORD not set'}), 500

        if secrets.compare_digest(password, admin_password):
            session['authenticated'] = True
            return jsonify({
                'success': True,
                'message': 'Authentication successful',
                'session_token': session.get('_permanent_id', 'session_active')
            })
        else:
            return jsonify({'error': 'Invalid password'}), 401
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Authentication failed'}), 500

@app.route('/auth/logout', methods=['POST'])
def logout():
    """Logout user."""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/apps', methods=['GET'])
@require_auth
def list_apps():
    """List all registered applications."""
    try:
        registered_apps = secure_app_manager.list_registered_apps()
        running_apps = secure_app_integrator.list_running_apps()
        
        # Combine registration and runtime information
        apps_info = {}
        for app_name, app_config in registered_apps.items():
            status_info = secure_app_integrator.get_app_status(app_name)
            
            apps_info[app_name] = {
                'name': app_name,
                'display_name': app_config.get('display_name'),
                'description': app_config.get('description', ''),
                'category': app_config.get('category'),
                'integration_type': app_config.get('integration_type'),
                'security_level': app_config.get('security_level'),
                'enabled': app_config.get('enabled', True),
                'auto_start': app_config.get('auto_start', False),
                'permissions': app_config.get('permissions', []),
                'registered_at': app_config.get('registered_at'),
                'status': status_info['status'],
                'running_info': running_apps.get(app_name)
            }
        
        return jsonify({
            'success': True,
            'apps': apps_info,
            'total_count': len(apps_info),
            'running_count': len([app for app in apps_info.values() if app['status'] == 'running'])
        })
        
    except Exception as e:
        logger.error(f"Error listing apps: {e}")
        return jsonify({'error': f'Failed to list apps: {str(e)}'}), 500

@app.route('/api/apps', methods=['POST'])
@require_auth
def register_app():
    """Register a new application."""
    try:
        app_config = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'display_name', 'category', 'integration_type']
        for field in required_fields:
            if not app_config.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        success, message = secure_app_integrator.register_app(app_config)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Error registering app: {e}")
        return jsonify({'error': f'Failed to register app: {str(e)}'}), 500

@app.route('/api/apps/<app_name>', methods=['GET'])
@require_auth
def get_app_details(app_name):
    """Get detailed information about a specific app."""
    try:
        status_info = secure_app_integrator.get_app_status(app_name)
        
        if status_info['status'] == 'not_registered':
            return jsonify({'error': f'App {app_name} is not registered'}), 404
        
        # Get registered app info
        registered_apps = secure_app_manager.list_registered_apps()
        app_config = registered_apps.get(app_name.lower(), {})
        
        # Combine all information
        detailed_info = {
            **status_info,
            'description': app_config.get('description', ''),
            'executable_path': app_config.get('executable_path'),
            'api_endpoint': app_config.get('api_endpoint'),
            'startup_args': app_config.get('startup_args', []),
            'startup_delay': app_config.get('startup_delay', 0),
            'auto_start': app_config.get('auto_start', False),
            'registered_at': app_config.get('registered_at'),
            'has_credentials': bool(secure_app_manager.load_app_credentials(app_name))
        }
        
        return jsonify({'success': True, 'app': detailed_info})
        
    except Exception as e:
        logger.error(f"Error getting app details for {app_name}: {e}")
        return jsonify({'error': f'Failed to get app details: {str(e)}'}), 500

@app.route('/api/apps/<app_name>/launch', methods=['POST'])
@require_auth
def launch_app(app_name):
    """Launch an application."""
    try:
        data = request.get_json() or {}
        args = data.get('args', [])
        
        success, message = secure_app_integrator.launch_app(app_name, args)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Error launching app {app_name}: {e}")
        return jsonify({'error': f'Failed to launch app: {str(e)}'}), 500

@app.route('/api/apps/<app_name>/stop', methods=['POST'])
@require_auth
def stop_app(app_name):
    """Stop an application."""
    try:
        success, message = secure_app_integrator.stop_app(app_name)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        logger.error(f"Error stopping app {app_name}: {e}")
        return jsonify({'error': f'Failed to stop app: {str(e)}'}), 500

@app.route('/api/apps/<app_name>', methods=['DELETE'])
@require_auth
def remove_app(app_name):
    """Remove an application registration."""
    try:
        success = secure_app_manager.remove_app(app_name)
        
        if success:
            return jsonify({'success': True, 'message': f'App {app_name} removed successfully'})
        else:
            return jsonify({'error': f'Failed to remove app {app_name}'}), 400
            
    except Exception as e:
        logger.error(f"Error removing app {app_name}: {e}")
        return jsonify({'error': f'Failed to remove app: {str(e)}'}), 500

@app.route('/api/apps/<app_name>/enable', methods=['POST'])
@require_auth
def toggle_app_enabled(app_name):
    """Enable or disable an application."""
    try:
        data = request.get_json()
        enabled = data.get('enabled', True)
        
        # Load current app config
        registered_apps = secure_app_manager.list_registered_apps()
        if app_name.lower() not in registered_apps:
            return jsonify({'error': f'App {app_name} is not registered'}), 404
        
        app_config = registered_apps[app_name.lower()]
        app_config['enabled'] = enabled
        app_config['last_modified'] = datetime.now().isoformat()
        
        # Save updated config
        success = secure_app_manager.register_secure_app(app_config)
        
        if success:
            action = 'enabled' if enabled else 'disabled'
            return jsonify({'success': True, 'message': f'App {app_name} {action} successfully'})
        else:
            return jsonify({'error': f'Failed to update app {app_name}'}), 400
            
    except Exception as e:
        logger.error(f"Error toggling app {app_name}: {e}")
        return jsonify({'error': f'Failed to update app: {str(e)}'}), 500

@app.route('/api/system/autostart', methods=['POST'])
@require_auth
def trigger_autostart():
    """Trigger auto-start for all configured apps."""
    try:
        secure_app_integrator.auto_start_apps()
        return jsonify({'success': True, 'message': 'Auto-start process initiated'})
        
    except Exception as e:
        logger.error(f"Error during auto-start: {e}")
        return jsonify({'error': f'Auto-start failed: {str(e)}'}), 500

@app.route('/api/system/cleanup', methods=['POST'])
@require_auth
def cleanup_processes():
    """Clean up terminated processes."""
    try:
        secure_app_integrator.cleanup_terminated_processes()
        return jsonify({'success': True, 'message': 'Process cleanup completed'})
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return jsonify({'error': f'Cleanup failed: {str(e)}'}), 500

@app.route('/api/system/status', methods=['GET'])
@require_auth
def system_status():
    """Get overall system status."""
    try:
        registered_apps = secure_app_manager.list_registered_apps()
        running_apps = secure_app_integrator.list_running_apps()
        
        # Count apps by category and status
        categories = {}
        security_levels = {'low': 0, 'medium': 0, 'high': 0}
        
        for app_name, app_config in registered_apps.items():
            category = app_config.get('category', 'unknown')
            categories[category] = categories.get(category, 0) + 1
            
            security_level = app_config.get('security_level', 'low')
            security_levels[security_level] += 1
        
        return jsonify({
            'success': True,
            'status': {
                'total_apps': len(registered_apps),
                'running_apps': len(running_apps),
                'enabled_apps': len([app for app in registered_apps.values() if app.get('enabled', True)]),
                'auto_start_apps': len([app for app in registered_apps.values() if app.get('auto_start', False)]),
                'categories': categories,
                'security_levels': security_levels,
                'last_updated': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        return jsonify({'error': f'Failed to get system status: {str(e)}'}), 500

@app.route('/api/config/categories', methods=['GET'])
def get_categories():
    """Get available app categories and their default permissions."""
    return jsonify({
        'success': True,
        'categories': secure_app_integrator.integration_categories
    })

@app.route('/api/config/integration_types', methods=['GET'])
def get_integration_types():
    """Get available integration types."""
    return jsonify({
        'success': True,
        'integration_types': {
            'basic': 'Simple executable launch',
            'api': 'API-based integration',
            'oauth': 'OAuth-based authentication',
            'webhook': 'Webhook-based integration'
        }
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Auto-start configured apps when the API server starts
    try:
        secure_app_integrator.auto_start_apps()
        logger.info("Auto-start process completed")
    except Exception as e:
        logger.error(f"Error during auto-start: {e}")
    
    # Run the Flask app
    port = int(os.getenv('INTEGRATION_API_PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    
    logger.info(f"Starting App Integration API server on {host}:{port}")
    app.run(host=host, port=port, debug=debug)