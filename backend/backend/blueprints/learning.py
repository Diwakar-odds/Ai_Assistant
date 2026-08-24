# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

"""
Learning Blueprint

Handles AI learning system endpoints including statistics, databases, and advanced AI features.
"""

from flask import Blueprint, request, jsonify
from datetime import datetime

def create_blueprint(assistant):
    """Create and configure the learning blueprint"""
    bp = Blueprint('learning', __name__, url_prefix='/api/learning')
    
    @bp.route('/stats')
    def stats():
        """Get learning statistics"""
        try:
            from learning_integration import get_learning_stats
            stats = get_learning_stats()
            return jsonify(stats)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/stats/all')
    def stats_all():
        """Get all learning system statistics"""
        try:
            from learning_integration import get_all_learning_stats
            stats = get_all_learning_stats()
            return jsonify({
                "success": True,
                "stats": stats,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @bp.route('/dashboard')
    def dashboard():
        """Get learning dashboard data"""
        try:
            from learning_integration import get_learning_dashboard_data
            data = get_learning_dashboard_data()
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/databases')
    def databases():
        """Get list of learning databases"""
        try:
            from learning_integration import get_databases
            databases = get_databases()
            return jsonify({"databases": databases})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/database/<db_name>/<table_name>')
    def database_table(db_name, table_name):
        """Get data from specific database table"""
        try:
            from learning_integration import get_table_data
            data = get_table_data(db_name, table_name)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/memory/search')
    def memory_search():
        """Search learning memory"""
        try:
            query = request.args.get('query', '')
            from learning_integration import search_memory
            results = search_memory(query)
            return jsonify({"results": results})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/documentation')
    def documentation():
        """Get learning system documentation"""
        try:
            from learning_integration import get_documentation
            docs = get_documentation()
            return jsonify(docs)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @bp.route('/smart-commands/predict', methods=['POST'])
    def predict_command():
        """Predict next command using AI"""
        try:
            data = request.get_json()
            context = data.get('context', {})
            
            from learning_integration import predict_next_command
            prediction = predict_next_command(context)
            
            return jsonify({
                "success": True,
                "prediction": prediction,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @bp.route('/context/generate', methods=['POST'])
    def generate_context():
        """Generate intelligent context"""
        try:
            data = request.get_json()
            message = data.get('message', '')
            
            from learning_integration import generate_intelligent_context
            context = generate_intelligent_context(message)
            
            return jsonify({
                "success": True,
                "context": context,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @bp.route('/workflow/recommend', methods=['POST'])
    def recommend_workflow():
        """Recommend workflow based on task"""
        try:
            data = request.get_json()
            task_description = data.get('task_description', '')
            
            from learning_integration import recommend_workflow
            workflow = recommend_workflow(task_description)
            
            return jsonify({
                "success": True,
                "workflow": workflow,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @bp.route('/system/<system_name>/stats')
    def system_stats(system_name):
        """Get stats for specific learning system"""
        try:
            from learning_integration import get_system_stats
            stats = get_system_stats(system_name)
            return jsonify({
                "success": True,
                "system": system_name,
                "stats": stats,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    return bp

