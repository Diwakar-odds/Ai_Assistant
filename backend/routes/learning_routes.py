from flask import Blueprint, jsonify, request, send_from_directory, render_template, Response, stream_with_context
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request
import os, json, sys, time, datetime
try:
    from backend.modern_web_backend import logger, api_logger, get_current_context
except ImportError:
    try:
        from modern_web_backend import logger, api_logger, get_current_context
    except ImportError:
        pass

learning_bp = Blueprint('learning', __name__)

# In case of missing globals, you may need to import them locally or add them here.
try:
    from backend.modern_web_backend import *
except ImportError:
    try:
        from modern_web_backend import *
    except ImportError:
        pass 
@learning_bp.route('/api/learning/stats')
@jwt_required(optional=True)
def api_learning_stats():
    """Get stats from all learning systems"""
    try:
        from learning_integration import get_learning_stats, LEARNING_SYSTEMS_AVAILABLE
        
        if not LEARNING_SYSTEMS_AVAILABLE:
            return jsonify({"error": "Learning systems not available"}), 503
        
        stats = get_learning_stats()
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Learning stats error: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/learning/dashboard')
@jwt_required(optional=True)
def api_learning_dashboard():
    """Get complete learning dashboard data"""
    try:
        if not DASHBOARD_API_AVAILABLE or not dashboard_api:
            return jsonify({"error": "Dashboard API not available"}), 503
        
        data = dashboard_api.get_dashboard_data()
        return jsonify({
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Dashboard API error: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/learning/databases')
@jwt_required(optional=True)
def api_learning_databases():
    """Get list of all learning databases with stats"""
    try:
        if not DASHBOARD_API_AVAILABLE or not dashboard_api:
            return jsonify({"error": "Dashboard API not available"}), 503
        
        databases = dashboard_api.get_database_stats()
        return jsonify({
            "success": True,
            "databases": databases,
            "total": len(databases)
        })
    except Exception as e:
        logger.error(f"Databases API error: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/learning/database/<db_name>/<table_name>')
@jwt_required(optional=True)
def api_database_content(db_name, table_name):
    """Get content from a specific database table"""
    try:
        if not DASHBOARD_API_AVAILABLE or not dashboard_api:
            return jsonify({"error": "Dashboard API not available"}), 503
        
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        content = dashboard_api.get_database_content(db_name, table_name, limit, offset)
        return jsonify({
            "success": True,
            "database": db_name,
            "table": table_name,
            "content": content
        })
    except Exception as e:
        logger.error(f"Database content error: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/learning/memory/search')
@jwt_required(optional=True)
def api_memory_search():
    """Search memory database"""
    try:
        if not DASHBOARD_API_AVAILABLE or not dashboard_api:
            return jsonify({"error": "Dashboard API not available"}), 503
        
        query = request.args.get('q', '')
        limit = request.args.get('limit', 20, type=int)
        
        if not query:
            return jsonify({"error": "Query parameter 'q' required"}), 400
        
        results = dashboard_api.search_memory(query, limit)
        return jsonify({
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        })
    except Exception as e:
        logger.error(f"Memory search error: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/learning/documentation')
@jwt_required(optional=True)
def api_learning_documentation():
    """Serve HOW_AI_LEARNS.md documentation"""
    try:
        doc_path = Path(__file__).parent.parent.parent / 'HOW_AI_LEARNS.md'
        
        if not doc_path.exists():
            return jsonify({"error": "Documentation not found"}), 404
        
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            "success": True,
            "content": content,
            "format": "markdown"
        })
    except Exception as e:
        logger.error(f"Documentation API error: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/learning/stats/all')
@jwt_required(optional=True)
def api_all_learning_stats():
    """Get stats from all 27 learning systems"""
    try:
        from learning_integration import get_learning_stats, LEARNING_SYSTEMS_AVAILABLE
        
        if not LEARNING_SYSTEMS_AVAILABLE:
            logger.warning("Learning systems not available")
            return jsonify({
                "success": False,
                "error": "Learning systems not available",
                "systems": {},
                "total_systems": 0
            }), 200  # Return 200 with error flag instead of 503
        
        stats = get_learning_stats()
        return jsonify({
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "systems": stats,
            "total_systems": len(stats)
        })
    except ImportError as e:
        logger.error(f"Learning stats import error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Learning module not found",
            "systems": {},
            "total_systems": 0
        }), 200
    except Exception as e:
        logger.error(f"Learning stats error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "systems": {},
            "total_systems": 0
        }), 200

@learning_bp.route('/api/learning/smart-commands/predict', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("120 per minute")
def api_smart_command_predict():
    """Predict next command based on context"""
    try:
        from learning_integration import LEARNING_SYSTEMS_AVAILABLE
        if not LEARNING_SYSTEMS_AVAILABLE:
            return jsonify({"error": "Learning systems not available"}), 503
        
        from ai_assistant.ai.smart_command_prediction import SmartCommandPredictor
        predictor = SmartCommandPredictor()
        
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        context = data.get('context', {})
        recent_commands = data.get('recent_commands', [])
        recent_outputs = data.get('recent_outputs', [])
        
        prediction = predictor.predict_command(user_id, context, recent_commands, recent_outputs)
        
        return jsonify({
            "success": True,
            "prediction": prediction
        })
    except Exception as e:
        logger.error(f"Smart command prediction error: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/learning/context/generate', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("120 per minute")
def api_context_generate():
    """Generate context-aware response"""
    try:
        from learning_integration import LEARNING_SYSTEMS_AVAILABLE
        if not LEARNING_SYSTEMS_AVAILABLE:
            return jsonify({"error": "Learning systems not available"}), 503
        
        from ai_assistant.ai.context_aware_response import ContextAwareResponseGenerator
        generator = ContextAwareResponseGenerator()
        
        data = request.get_json()
        query = data.get('query', '')
        conversation_history = data.get('conversation_history', [])
        user_profile = data.get('user_profile', {})
        
        response = generator.generate_response(query, conversation_history, user_profile)
        
        return jsonify({
            "success": True,
            "response": response
        })
    except Exception as e:
        logger.error(f"Context generation error: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/learning/workflow/recommend', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("60 per minute")
def api_workflow_recommend():
    """Get workflow recommendations"""
    try:
        from learning_integration import LEARNING_SYSTEMS_AVAILABLE
        if not LEARNING_SYSTEMS_AVAILABLE:
            return jsonify({"error": "Learning systems not available"}), 503
        
        from ai_assistant.ai.workflow_recommender import WorkflowRecommender
        recommender = WorkflowRecommender()
        
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        current_task = data.get('current_task', '')
        context = data.get('context', {})
        
        recommendations = recommender.recommend_workflows(user_id, current_task, context)
        
        return jsonify({
            "success": True,
            "recommendations": recommendations
        })
    except Exception as e:
        logger.error(f"Workflow recommendation error: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/learning/anomaly/detect', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("120 per minute")
def api_anomaly_detect():
    """Detect anomalies in system behavior"""
    try:
        from learning_integration import LEARNING_SYSTEMS_AVAILABLE
        if not LEARNING_SYSTEMS_AVAILABLE:
            return jsonify({"error": "Learning systems not available"}), 503
        
        from ai_assistant.ai.anomaly_detection import AnomalyDetector
        detector = AnomalyDetector()
        
        data = request.get_json()
        features = data.get('features', [])
        
        result = detector.detect(features)
        
        return jsonify({
            "success": True,
            "is_anomaly": result['is_anomaly'],
            "anomaly_score": result.get('anomaly_score', 0)
        })
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/learning/causal/query', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("60 per minute")
def api_causal_query():
    """Query causal relationships"""
    try:
        from learning_integration import LEARNING_SYSTEMS_AVAILABLE
        if not LEARNING_SYSTEMS_AVAILABLE:
            return jsonify({"error": "Learning systems not available"}), 503
        
        from ai_assistant.ai.causal_inference import CausalInference
        causal = CausalInference()
        
        data = request.get_json()
        action = data.get('action', '')
        target = data.get('target', '')
        
        # Add edge if both provided
        if action and target:
            causal.add_edge(action, target, strength=data.get('strength', 0.5))
        
        stats = causal.get_stats()
        
        return jsonify({
            "success": True,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Causal query error: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/learning/knowledge-graph/query', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("120 per minute")
def api_knowledge_graph_query():
    """Query personal knowledge graph"""
    try:
        from learning_integration import LEARNING_SYSTEMS_AVAILABLE
        if not LEARNING_SYSTEMS_AVAILABLE:
            return jsonify({"error": "Learning systems not available"}), 503
        
        from ai_assistant.ai.enhanced_learning import PersonalKnowledgeGraph
        kg = PersonalKnowledgeGraph(db_path="data/knowledge_graph.db")
        
        data = request.get_json()
        query_type = data.get('type', 'stats')
        
        if query_type == 'stats':
            result = kg.get_stats()
        elif query_type == 'export':
            result = kg.export_graph_data()
        else:
            result = {"error": "Unknown query type"}
        
        return jsonify({
            "success": True,
            "data": result
        })
    except Exception as e:
        logger.error(f"Knowledge graph query error: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/learning/adaptive-voice/log', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("200 per minute")
def api_adaptive_voice_log():
    """Log voice recognition for adaptation"""
    try:
        from learning_integration import LEARNING_SYSTEMS_AVAILABLE
        if not LEARNING_SYSTEMS_AVAILABLE:
            return jsonify({"error": "Learning systems not available"}), 503
        
        from ai_assistant.ai.adaptive_voice import AdaptiveVoiceRecognition
        voice = AdaptiveVoiceRecognition()
        
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        transcription = data.get('transcription', '')
        intended_text = data.get('intended_text', None)
        confidence = data.get('confidence', 1.0)
        
        voice.log_recognition(user_id, transcription, intended_text, confidence)
        
        return jsonify({
            "success": True,
            "message": "Recognition logged"
        })
    except Exception as e:
        logger.error(f"Adaptive voice log error: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/learning/rl/action', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("120 per minute")
def api_rl_select_action():
    """Select action using reinforcement learning"""
    try:
        from learning_integration import LEARNING_SYSTEMS_AVAILABLE
        if not LEARNING_SYSTEMS_AVAILABLE:
            return jsonify({"error": "Learning systems not available"}), 503
        
        from ai_assistant.ai.full_rl_system import PPOAgent
        agent = PPOAgent(state_dim=10, action_dim=5)
        
        data = request.get_json()
        state = data.get('state', [0] * 10)
        
        action = agent.select_action(state)
        
        return jsonify({
            "success": True,
            "action": int(action),
            "state": state
        })
    except Exception as e:
        logger.error(f"RL action selection error: {e}")
        return jsonify({"error": str(e)}), 500

@learning_bp.route('/api/learning/system/<system_name>/stats')
@jwt_required(optional=True)
def api_single_system_stats(system_name):
    """Get stats for a single learning system"""
    try:
        from learning_integration import get_learning_stats, LEARNING_SYSTEMS_AVAILABLE
        
        if not LEARNING_SYSTEMS_AVAILABLE:
            return jsonify({"error": "Learning systems not available"}), 503
        
        all_stats = get_learning_stats()
        
        if system_name not in all_stats:
            return jsonify({"error": f"System '{system_name}' not found"}), 404
        
        return jsonify({
            "success": True,
            "system": system_name,
            "stats": all_stats[system_name]
        })
    except Exception as e:
        logger.error(f"Single system stats error: {e}")