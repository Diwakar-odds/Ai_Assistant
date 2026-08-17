from flask import Blueprint, jsonify, request, send_from_directory, render_template, Response, stream_with_context
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request
import os, json, sys, time, datetime
try:
    from backend.modern_web_backend import logger, api_logger, get_current_context
except ImportError:
    pass
    

auth_bp = Blueprint('auth', __name__)


try:
    from backend.modern_web_backend import *
except ImportError:
    from modern_web_backend import *
@auth_bp.route('/api/user/preferences', methods=['GET'])
@limiter.limit("20 per minute")
def get_user_preferences():
    """Get user preferences"""
    try:
        from user_preferences import get_preferences_manager
        
        # Get user from auth token or use 'default'
        user_id = request.args.get('user_id', 'default')
        
        prefs_manager = get_preferences_manager()
        preferences = prefs_manager.get_preferences(user_id)
        
        return jsonify({
            "success": True,
            "preferences": preferences
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@auth_bp.route('/api/user/profile/status', methods=['GET'])
def get_user_profile_status():
    """Check if the user profile is set up."""
    try:
        from ai_assistant.core.database_config import get_db_path
        import sqlite3
        import json
        
        db_path = get_db_path('personal_knowledge')
        if not db_path.exists():
            return jsonify({"setup_complete": False, "exists": False})
            
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='knowledge_nodes'")
            if not cursor.fetchone():
                return jsonify({"setup_complete": False, "exists": True, "reason": "no_tables"})
                
            cursor.execute("SELECT content, metadata FROM knowledge_nodes WHERE node_type='person'")
            rows = cursor.fetchall()
            
            for content, meta_json in rows:
                meta = json.loads(meta_json) if meta_json else {}
                if meta.get('is_primary_user'):
                    return jsonify({
                        "setup_complete": True, 
                        "name": content,
                        "role": meta.get('role'),
                        "has_deep_profile": meta.get('full_profile_complete', False)
                    })
                    
            # Fallback
            if rows:
                return jsonify({"setup_complete": True, "name": rows[0][0], "message": "basic_profile_only"})
                
        except Exception as e:
            logger.error(f"DB Error checking profile: {e}")
            return jsonify({"setup_complete": False, "error": str(e)})
        finally:
            conn.close()
            
        return jsonify({"setup_complete": False})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@auth_bp.route('/api/user/profile/setup', methods=['POST'])
def setup_user_profile():
    """Setup or update the user profile."""
    try:
        from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
        from ai_assistant.core.database_config import get_db_path
        
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
            
        name = data.get('name')
        if not name:
             return jsonify({"success": False, "error": "Name is required"}), 400
             
        # Extract fields
        role = data.get('role', 'User')
        location = data.get('location')
        style = data.get('communication_style', 'Concise')
        interests = data.get('interests', [])
        skills = data.get('skills', [])
        goals = data.get('goals', [])
        work_pattern = data.get('work_pattern')
        
        # Init DB
        db_path = get_db_path('personal_knowledge')
        
        # Ensure tables exist
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS knowledge_nodes (node_id TEXT PRIMARY KEY, content TEXT NOT NULL, node_type TEXT NOT NULL, metadata TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP, importance_score REAL DEFAULT 0.5)")
        cursor.execute("CREATE TABLE IF NOT EXISTS knowledge_edges (edge_id TEXT PRIMARY KEY, source_node TEXT NOT NULL, target_node TEXT NOT NULL, relationship_type TEXT NOT NULL, strength REAL DEFAULT 1.0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (source_node) REFERENCES knowledge_nodes (node_id), FOREIGN KEY (target_node) REFERENCES knowledge_nodes (node_id))")
        conn.commit()
        conn.close()
        
        # Use direct KG methods if available, else manual DB insert
        # Re-import to be safe
        from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
        kg = PersonalKnowledgeGraph(str(db_path))
        
        # Add User Node
        user_metadata = {
            "role": role,
            "is_primary_user": True,
            "interests": interests,
            "location": location,
            "communication_style": style,
            "skills": skills,
            "goals": goals,
            "work_pattern": work_pattern,
            "full_profile_complete": True
        }
        
        user_node_id = kg.add_knowledge_node(name, "person", user_metadata)
        
        # Add basic relations
        role_node_id = kg.add_knowledge_node(role, "role", {})
        kg.add_relationship(user_node_id, role_node_id, "has_role", strength=1.0)
        
        for interest in interests:
            if interest:
                i_node = kg.add_knowledge_node(interest, "topic", {})
                kg.add_relationship(user_node_id, i_node, "interested_in", strength=0.8)
                
        for skill in skills:
            if skill:
                s_node = kg.add_knowledge_node(skill, "skill", {})
                kg.add_relationship(user_node_id, s_node, "has_skill", strength=0.9)
                
        logger.info(f"Ã¢Å“â€¦ Created/Updated profile for {name}")
        
        return jsonify({"success": True, "message": "Profile setup complete"})
        
    except Exception as e:
        logger.error(f"Profile setup failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@auth_bp.route('/api/user/preferences', methods=['POST'])
@limiter.limit("10 per minute")
def save_user_preferences():
    """Save user preferences"""
    try:
        from user_preferences import get_preferences_manager
        
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        preferences = data.get('preferences', {})
        
        prefs_manager = get_preferences_manager()
        success = prefs_manager.save_preferences(user_id, preferences)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Preferences saved successfully"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to save preferences"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@auth_bp.route('/api/status/initialization', methods=['GET'])
@limiter.limit("30 per minute")
def get_initialization_status():
    """Get initialization status of all components"""
    try:
        if hasattr(assistant, 'get_init_status'):
            status = assistant.get_init_status()
            
            # Calculate overall readiness
            ready_count = sum(1 for v in status.values() if v == 'ready')
            total_count = len(status)
            overall_ready = (ready_count == total_count)
            
            return jsonify({
                "success": True,
                "overall_ready": overall_ready,
                "ready_percentage": int((ready_count / total_count) * 100),
                "components": status,
                "config": {
                    "lazy_init": LAZY_INIT,
                    "background_init": BACKGROUND_INIT,
                    "voice_enabled": ENABLE_VOICE,
                    "multimodal_enabled": ENABLE_MULTIMODAL,
                    "conversational_ai_enabled": ENABLE_CONVERSATIONAL_AI,
                    "system_monitoring_enabled": ENABLE_SYSTEM_MONITORING
                }
            })
        else:
            return jsonify({
                "success": False,
                "error": "Assistant does not support init status tracking"
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@auth_bp.route('/api/auth/register', methods=['POST'])
@limiter.limit("3 per hour")  # Prevent abuse
def api_register():
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

@auth_bp.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")  # Prevent brute force
def api_login():
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
            logger.error("ADMIN_PIN environment variable not set")
            return jsonify({"error": "Server configuration error"}), 500
        
        # SECURITY: Use constant-time comparison to prevent timing attacks
        import hmac
        if not hmac.compare_digest(pin, valid_pin):
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

@auth_bp.route('/api/auth/verify', methods=['GET'])
@jwt_required()
def api_verify_token():
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