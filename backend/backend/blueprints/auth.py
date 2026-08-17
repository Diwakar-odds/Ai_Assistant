"""
Authentication Blueprint

Handles user authentication, registration, and token verification.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)
from werkzeug.security import generate_password_hash, check_password_hash
import os
import secrets

# In-memory user database (should be replaced with proper DB in production)
# Loaded from ADMIN_USERS env var (JSON string) or empty (registration-only)
USERS_DB = {}

def create_blueprint(assistant):
    """Create and configure the auth blueprint"""
    bp = Blueprint('auth', __name__, url_prefix='/api/auth')
    
    # Import validation functions from parent module
    from ai_assistant.utils.backend_utils import validate_input
    
    @bp.route('/register', methods=['POST'])
    def register():
        """Register a new user"""
        try:
            data = request.get_json()
            
            # Validate input
            is_valid, error = validate_input(data, 'username', 'username')
            if not is_valid:
                return jsonify({"error": error}), 400
            
            if 'password' not in data:
                return jsonify({"error": "Password is required"}), 400
            
            username = data['username']
            password = data['password']
            
            # Check password strength
            if len(password) < 6:
                return jsonify({"error": "Password must be at least 6 characters"}), 400
            
            # Check if user already exists
            if username in USERS_DB:
                return jsonify({"error": "Username already exists"}), 409
            
            # Create new user
            USERS_DB[username] = {
                "password_hash": generate_password_hash(password),
                "role": "user"
            }
            
            # Create tokens
            access_token = create_access_token(
                identity=username,
                additional_claims={"role": "user"}
            )
            
            return jsonify({
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 86400,
                "user": {
                    "username": username,
                    "role": "user"
                },
                "message": "Registration successful"
            }), 201
            
        except Exception as e:
            return jsonify({"error": "Registration failed"}), 500
    
    @bp.route('/login', methods=['POST'])
    def login():
        """Authenticate user with PIN and return JWT token"""
        try:
            data = request.get_json()
            
            # Validate PIN input
            if 'pin' not in data:
                return jsonify({"error": "PIN is required"}), 400
            
            pin = str(data['pin']).strip()
            
            # Validate PIN format
            if not pin:
                return jsonify({"error": "PIN cannot be empty"}), 400
                
            if len(pin) < 4:
                return jsonify({"error": "PIN must be at least 4 digits"}), 400
                
            if not pin.isdigit():
                return jsonify({"error": "PIN must contain only numbers"}), 400
            
            # Check PIN against environment variable (required)
            valid_pin = os.getenv('ADMIN_PIN')
            if not valid_pin:
                return jsonify({"error": "Server configuration error: ADMIN_PIN not set"}), 500

            if not secrets.compare_digest(pin, valid_pin):
                return jsonify({"error": "Invalid PIN"}), 401
            
            # Create JWT token for authenticated user
            access_token = create_access_token(
                identity="assistant_user",
                additional_claims={"role": "user"}
            )
            
            return jsonify({
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 86400,  # 24 hours
                "user": {
                    "username": "assistant_user",
                    "role": "user"
                }
            }), 200
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/verify', methods=['GET'])
    @jwt_required()
    def verify_token():
        """Verify JWT token is valid"""
        current_user = get_jwt_identity()
        user = USERS_DB.get(current_user)
        
        return jsonify({
            "valid": True,
            "user": {
                "username": current_user,
                "role": user['role'] if user else "user"
            }
        }), 200
    
    return bp
