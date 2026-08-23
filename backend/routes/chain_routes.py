import threading
import asyncio
from flask import Blueprint, jsonify, request
from .common import logger, get_socketio, jwt_required

chain_bp = Blueprint('chain', __name__)

try:
    from ai_assistant.core.chain_of_actions_manager import get_chain_manager, ChainOfActionsManager
    from ai_assistant.core.progress_tracker import get_progress_tracker
    MULTI_AGENT_AVAILABLE = True
except ImportError as e:
    MULTI_AGENT_AVAILABLE = False
    logger.warning(f"Multi-Agent System not available in chain_routes: {e}")

try:
    from backend.modern_web_backend import *
except ImportError:
    from modern_web_backend import *

from ai_assistant.core.chain_optimizer import ChainOptimizer
chain_optimizer = ChainOptimizer()

def _broadcast_chain_progress(progress):
    """Broadcast chain progress via WebSocket"""
    try:
        sio = get_socketio()
        if sio:
            sio.emit(
                'chain_progress',
                progress.to_dict() if hasattr(progress, 'to_dict') else progress,
                namespace='/'
            )
    except Exception as e:
        logger.error(f"WebSocket broadcast error: {e}")
@chain_bp.route('/api/chains/create', methods=['POST'])
@jwt_required()
def create_chain():
    """Create a new action chain from command"""
    if not MULTI_AGENT_AVAILABLE:
        return jsonify({"error": "Multi-Agent System not available"}), 503
        
    data = request.get_json()
    command = data.get("command")
    
    if not command:
        return jsonify({"error": "Command is required"}), 400
        
    try:
        manager = get_chain_manager()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        chain = loop.run_until_complete(manager.create_chain(command))
        
        def run_chain_background(chain_obj):
            async def _run():
                manager.subscribe_progress(chain_obj.id, _broadcast_chain_progress)
                await manager.decompose_command(chain_obj)
                await manager.identify_executors(chain_obj)
                report = await manager.execute_chain(chain_obj.id)
                await manager.notify_completion(report)
                
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            new_loop.run_until_complete(_run())
            new_loop.close()
            
        thread = threading.Thread(target=run_chain_background, args=(chain,))
        thread.start()
        
        return jsonify({
            "status": "started", 
            "message": "Chain execution started",
            "chain_id": chain.id,
            "command": command
        })
        
    except Exception as e:
        logger.error(f"Error getting chain status: {e}")
        return jsonify({"error": str(e)}), 500

@chain_bp.route('/api/chains/<chain_id>/execute', methods=['POST'])
@jwt_required()
def execute_chain(chain_id):
    """Execute a created chain"""
    if not MULTI_AGENT_AVAILABLE:
        return jsonify({"error": "Multi-Agent System not available"}), 503
        
    try:
        import asyncio
        manager = get_chain_manager()
        
        # This is typically an async background task in actual production
        def run_execute():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(manager.execute_chain(chain_id))
            loop.close()
            
        thread = threading.Thread(target=run_execute)
        thread.start()
        
        return jsonify({"status": "executing", "chain_id": chain_id, "message": "Chain execution started"})
    except Exception as e:
        logger.error(f"Error executing chain: {e}")
        return jsonify({"error": str(e)}), 500

@chain_bp.route('/api/chains/<chain_id>/cancel', methods=['POST'])
@jwt_required()
def cancel_chain(chain_id):
    """Cancel a running chain"""
    if not MULTI_AGENT_AVAILABLE:
        return jsonify({"error": "Multi-Agent System not available"}), 503
        
    try:
        manager = get_chain_manager()
        if chain_id in manager.active_chains:
            manager.active_chains[chain_id].status = "CANCELLED"
            # Move to completed if needed
            manager.completed_chains[chain_id] = manager.active_chains.pop(chain_id)
            return jsonify({"status": "cancelled", "chain_id": chain_id})
        return jsonify({"error": "Chain not found or already completed"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@chain_bp.route('/api/chains/optimize', methods=['POST'])
@jwt_required()
def optimize_chain():
    """Optimize a chain plan based on historical execution"""
    data = request.get_json()
    plan = data.get("plan", [])
    
    try:
        optimized_plan = chain_optimizer.optimize_plan(plan)
        success_rate = chain_optimizer.predict_success_rate(optimized_plan)
        
        return jsonify({
            "status": "success",
            "optimized_plan": optimized_plan,
            "predicted_success_rate": success_rate
        })
    except Exception as e:
        logger.error(f"Error optimizing chain: {e}")
        return jsonify({"error": str(e)}), 500

@chain_bp.route('/api/chains/<chain_id>/resume', methods=['POST'])
@jwt_required()
def resume_chain(chain_id):
    """Resume a paused chain with user input/confirmation"""
    if not MULTI_AGENT_AVAILABLE:
        return jsonify({"error": "Multi-Agent System not available"}), 503
        
    data = request.get_json()
    user_input = data.get("input")
    action = data.get("action", "proceed")
    
    return jsonify({"status": "resumed", "message": "Resume signal sent (Not fully implemented)"})

@chain_bp.route('/api/chains/<chain_id>', methods=['GET'])
@jwt_required()
def get_chain_status(chain_id):
    """Get status of an action chain"""
    if not MULTI_AGENT_AVAILABLE:
        return jsonify({"error": "Multi-Agent System not available"}), 503
        
    try:
        manager = get_chain_manager()
        chain = manager.get_chain(chain_id)
        
        if not chain:
            return jsonify({"error": "Chain not found"}), 404
            
        return jsonify(chain.to_dict())
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chain_bp.route('/api/chains/history', methods=['GET'])
@jwt_required()
def get_chain_history():
    """Get history of action chains"""
    if not MULTI_AGENT_AVAILABLE:
        return jsonify({"error": "Multi-Agent System not available"}), 503
        
    try:
        tracker = get_progress_tracker()
        history = tracker.get_recent_chains(limit=20)
        return jsonify({"chains": history})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500