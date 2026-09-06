from flask import Blueprint, jsonify, request, send_from_directory, render_template, Response, stream_with_context
import os, json, sys, time, datetime
from .common import (
    logger, api_logger, limiter, validate_input, sanitize_command,
    assistant, socketio, learning_router, get_current_context,
    jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request,
    ENABLE_VOICE, ENABLE_MULTIMODAL, ENABLE_CONVERSATIONAL_AI
)
from .local_ai_routes import local_ai_manager, local_ai_initialized

chat_bp = Blueprint('chat', __name__)
@chat_bp.route('/api/chat', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("60 per minute")
def api_chat():
    """Enhanced chat endpoint with full AI integration and learning"""
    start_time = time.time()
    try:
        current_user = get_jwt_identity() or "anonymous"
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'message', 'command')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        message = sanitize_command(data['message'])
        context = data.get('context', {})
        image_data = data.get('image', None)
        
        if not message and not image_data:
            return jsonify({"error": "No message or image provided"}), 400
        
        # === NEW: Multi-step Task Chain Orchestration ===
        try:
            from ai_assistant.integrations.orchestrator_integration import should_use_orchestrator, process_with_orchestrator
            
            if should_use_orchestrator(message):
                logger.info(f" Multi-step command detected: {message}")
                orch_result = process_with_orchestrator(message, context)
                
                if orch_result['success']:
                    return jsonify({
                        "message": message,
                        "response": orch_result['response'],
                        "orchestrated": True,
                        "steps_completed": orch_result['steps_completed'],
                        "total_steps": orch_result['total_steps'],
                        "features_used": ["multi_step_orchestration"],
                        "user": current_user,
                        "timestamp": datetime.now().isoformat()
                    })
                elif not orch_result.get('fallback'):
                    # Hard error, don't fallback
                    return jsonify({
                        "error": orch_result.get('error', 'Multi-step execution failed'),
                        "orchestrated": True,
                        "timestamp": datetime.now().isoformat()
                    }), 500
                else:
                    logger.warning("Orchestrator unavailable/failed, using fallback")
                    # Continue to normal processing below
        except Exception as orch_error:
            logger.warning(f"Orchestrator error, falling back: {orch_error}")
            # Continue to normal processing
        # === END: Multi-step Orchestration ===
        
        # Extract preferences
        model_preference = data.get('model')
        provider_preference = data.get('provider')
        
        # Apply learning-enhanced response generation
        try:
            from ai_assistant.integrations.learning_integration import get_learning_assistant
            learning_assistant = get_learning_assistant(current_user)
            if learning_assistant.systems_active:
                # Enhance message with context-aware generation
                message = learning_assistant.generate_intelligent_response(message, context)
                logger.info("Applied learning-enhanced response generation")
        except Exception as e:
            logger.warning(f"Learning enhancement skipped: {e}")
        
        try:
            # Process with full AI capabilities
            response = assistant.process_enhanced_chat(
                message, context, image_data,
                model_preference=model_preference,
                provider_preference=provider_preference
            )
            
            return jsonify({
                "message": message,
                "response": response["response"],
                "features_used": response["features_used"],
                "suggestions": response.get("suggestions", []),
                "mood": response.get("mood", "neutral"),
                "context_id": response.get("context_id"),
                "provider": response.get("provider"),
                "model": response.get("model"),
                "user": current_user,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as fallback_error:
            logger.error(f"Fallback error in api_chat: {fallback_error}")
            return jsonify({
                "message": message,
                "response": f"I'm sorry, I encountered an internal error. Please check the logs.",
                "features_used": ["safe_fallback"],
                "provider": "offline",
                "model": "error",
                "suggestions": [],
                "user": current_user,
                "timestamp": datetime.now().isoformat()
            })
                
    except Exception as e:
        logging.error(f"Chat API error: {str(e)}")
        return jsonify({"error": f"Chat processing failed: {str(e)[:200]}"}), 500

@chat_bp.route('/api/command', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_command():
    """Process text command - Protected"""
    try:
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'command', 'command')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        command = sanitize_command(data['command'])
        
        if not command:
            return jsonify({"error": "No command provided"}), 400
        
        # === NEW: Multi-step Task Chain Orchestration ===
        try:
            from ai_assistant.integrations.orchestrator_integration import should_use_orchestrator, process_with_orchestrator
            
            if should_use_orchestrator(command):
                logger.info(f" Multi-step command detected: {command}")
                orch_result = process_with_orchestrator(command, {})
                
                if orch_result['success']:
                    return jsonify({
                        "success": True,
                        "command": command,
                        "response": orch_result['response'],
                        "orchestrated": True,
                        "steps_completed": orch_result['steps_completed'],
                        "total_steps": orch_result['total_steps'],
                        "timestamp": datetime.now().isoformat()
                    })
                elif not orch_result.get('fallback'):
                    # Hard error, don't fallback
                    return jsonify({
                        "success": False,
                        "error": orch_result.get('error', 'Multi-step execution failed'),
                        "orchestrated": True,
                        "command": command,
                        "timestamp": datetime.now().isoformat()
                    }), 500
                else:
                    logger.warning("Orchestrator unavailable/failed, using fallback")
                    # Continue to normal processing below
        except Exception as orch_error:
            logger.warning(f"Orchestrator error, falling back: {orch_error}")
            # Continue to normal processing
        # === END: Multi-step Orchestration ===
        
        # Check if user wants to use local AI
        use_local_ai = data.get('use_local_ai', False) or data.get('offline_mode', False)
        
        # DEBUG: Log the offline mode request
        logger.info(f" Command received: {command[:30]}...")
        logger.info(f" offline_mode flag in request: {data.get('offline_mode')}")
        logger.info(f" use_local_ai: {use_local_ai}")
        logger.info(f" local_ai_initialized: {local_ai_initialized}")
        logger.info(f" local_ai_manager exists: {local_ai_manager is not None}")
        
        if use_local_ai and local_ai_initialized and local_ai_manager:
            # Use local Ollama model
            try:
                logger.info(f"Using local AI for command: {command[:50]}...")
                local_response = local_ai_manager.chat(command, max_tokens=512)
                
                return jsonify({
                    "success": True,
                    "command": command,
                    "response": local_response,
                    "model": local_ai_manager.current_model,
                    "offline_mode": True,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as local_error:
                logger.error(f"Local AI error: {local_error}, falling back to cloud")
                # Fall through to cloud AI below
        
        # Process command with cloud AI (default)
        try:
            # Extract provider/model preference
            preferred_provider = data.get('provider')
            preferred_model = data.get('model')
            
            if preferred_provider or preferred_model:
                try:
                    response = assistant.process_command(command, model_preference={'provider': preferred_provider, 'model': preferred_model})
                except TypeError:
                    response = assistant.process_command(command)
            else:
                response = assistant.process_command(command)
            
            return jsonify({
                "success": True,
                "command": command,
                "response": response,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as cmd_error:
            # If cloud fails and local AI is available, try local fallback
            if local_ai_initialized and local_ai_manager:
                logger.warning(f"Cloud AI failed ({str(cmd_error)[:100]}), using local AI fallback")
                try:
                    local_response = local_ai_manager.chat(command, max_tokens=512)
                    
                    return jsonify({
                        "success": True,
                        "command": command,
                        "response": local_response,
                        "model": local_ai_manager.current_model,
                        "offline_mode": True,
                        "fallback": True,
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as local_error:
                    logger.error(f"Local AI fallback also failed: {local_error}")
                    # Re-raise original cloud error
                    raise cmd_error
            else:
                # No local AI available, return error
                raise cmd_error
                
        except Exception as cmd_error:
            return jsonify({
                "success": False,
                "error": f"Command processing failed: {str(cmd_error)}",
                "command": command,
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        api_logger.error(f"Command API error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@chat_bp.route('/api/enhanced/chat', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("60 per minute")
async def api_enhanced_chat():
    """Enhanced chat with all advanced features: caching, routing, streaming, emotion detection"""
    try:
        if not ENHANCED_AI_AVAILABLE:
            return jsonify({
                "error": "Enhanced AI not available. Run: pip install diskcache sentence-transformers",
                "fallback": True
            }), 503
        
        current_user = get_jwt_identity() or "anonymous"
        data = request.get_json()
        
        message = data.get('message', '')
        if not message:
            return jsonify({"error": "No message provided"}), 400
        
        # Optional parameters
        enable_cache = data.get('enable_cache', True)
        enable_streaming = data.get('enable_streaming', False)
        audio_path = data.get('audio_path', None)  # For emotion detection
        context = data.get('context', {})
        
        # Process with enhanced AI
        result = await enhanced_ai.process_query(
            query=message,
            context=context,
            enable_cache=enable_cache,
            enable_streaming=enable_streaming,
            audio_path=audio_path
        )
        
        # Log for learning
        if LEARNING_ROUTER_AVAILABLE and learning_router:
            learning_router.route_conversation(message, result['text'], current_user)
        
        return jsonify({
            "success": True,
            "message": message,
            "response": result['text'],
            "metadata": {
                "model": result['model'],
                "cached": result['cached'],
                "emotion": result.get('emotion'),
                "complexity": result.get('complexity', 0),
                "time_ms": result['time_ms'],
                "tokens": result.get('tokens', 0),
                "cost_usd": result.get('cost_usd', 0)
            },
            "features_used": ["enhanced_ai", "semantic_cache", "model_routing"],
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Enhanced chat error: {e}")
        return jsonify({
            "error": str(e),
            "success": False
        }), 500

@chat_bp.route('/api/enhanced/stats', methods=['GET'])
@limiter.limit("30 per minute")
def api_enhanced_stats():
    """Get comprehensive stats for all advanced features"""
    try:
        if not ENHANCED_AI_AVAILABLE:
            return jsonify({"error": "Enhanced AI not available"}), 503
        
        stats = enhanced_ai.get_stats()
        
        return jsonify({
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Enhanced stats error: {e}")
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/enhanced/cache/clear', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def api_clear_cache():
    """Clear the semantic response cache"""
    try:
        if not ENHANCED_AI_AVAILABLE:
            return jsonify({"error": "Enhanced AI not available"}), 503
        
        if enhanced_ai.cache:
            enhanced_ai.cache.invalidate()  # Clear all cache
            
            return jsonify({
                "success": True,
                "message": "Cache cleared successfully",
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({"error": "Cache not available"}), 503
        
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/usage-analysis', methods=['GET'])
@jwt_required(optional=True)
@limiter.limit("10 per minute")
def api_usage_analysis():
    """Get usage pattern analysis and training data"""
    try:
        if not USAGE_ANALYZER_AVAILABLE:
            return jsonify({"error": "Usage analyzer not available"}), 503
        
        days_back = int(request.args.get('days', 30))
        
        # Run analysis
        results = usage_analyzer.analyze_all(days_back=days_back)
        
        return jsonify({
            "success": True,
            "analysis": {
                "common_commands": results.get('common_commands', [])[:10],
                "frequent_topics": results.get('frequent_topics', [])[:10],
                "time_patterns": results.get('time_patterns', {}),
                "app_usage": results.get('app_usage', {}),
                "command_sequences": results.get('command_sequences', [])[:5],
                "preferences": results.get('preferences', {}),
                "training_data_count": len(results.get('training_data', []))
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Usage analysis error: {e}")
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/usage-analysis/export', methods=['POST'])
@jwt_required()
@limiter.limit("5 per minute")
def api_export_training_data():
    """Export training data for fine-tuning"""
    try:
        if not USAGE_ANALYZER_AVAILABLE:
            return jsonify({"error": "Usage analyzer not available"}), 503
        
        data = request.get_json()
        format_type = data.get('format', 'openai')  # 'openai' or 'huggingface'
        days_back = data.get('days', 30)
        
        # Analyze
        results = usage_analyzer.analyze_all(days_back=days_back)
        
        # Export
        output_path = f"data/training/finetuning_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        exported_file = usage_analyzer.export_for_finetuning(output_path, format=format_type)
        
        return jsonify({
            "success": True,
            "file_path": exported_file,
            "examples_count": len(results.get('training_data', [])),
            "format": format_type,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Export training data error: {e}")
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/automation/verify', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
async def api_verify_automation():
    """Verify automation action using visual verification"""
    try:
        if not ENHANCED_AI_AVAILABLE:
            return jsonify({"error": "Visual verification not available"}), 503
        
        data = request.get_json()
        action_name = data.get('action_name', 'automation')
        app_name = data.get('app_name', None)
        
        # Verify automation
        result = await enhanced_ai.verify_automation(action_name, app_name)
        
        return jsonify({
            "success": result['success'],
            "verification": result,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Automation verification error: {e}")
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/chat/stream', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_chat_stream():
    """
    Stream chat response token-by-token via Server-Sent Events.
    Provides real-time response generation with response count tracking.
    """
    try:
        current_user = get_jwt_identity() or "anonymous"
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'message', 'command')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        message = sanitize_command(data['message'])
        session_id = data.get('session_id', f"{current_user}_{int(time.time())}")
        
        if not message:
            return jsonify({"error": "No message provided"}), 400
        
        logger.info(f"[INFO] Streaming chat for user: {current_user}, session: {session_id}")
        
        def generate_stream():
            """Generate streaming response tokens"""
            try:
                # Get or create chat session
                with chat_session_lock:
                    if session_id not in chat_sessions:
                        if LLM_PROVIDER_AVAILABLE:
                            chat_sessions[session_id] = UnifiedChatInterface()
                            chat_sessions[session_id].add_system_message(
                                "You are a helpful AI assistant. Respond concisely and accurately."
                            )
                        else:
                            # Fallback if LLM not available
                            yield f"data: {json.dumps({'error': 'LLM provider not available'})}\n\n# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

\n"
                            return
                    
                    chat = chat_sessions[session_id]
                
                # Stream the response
                start_time = time.time()
                tokens = 0
                full_response = ""
                
                logger.debug(f"Starting stream for message: {message[:50]}...")
                
                try:
                    # Get streaming response
                    for token in chat.chat(message, stream=True):
                        tokens += 1
                        full_response += token
                        
                        # Emit token with count
                        token_data = json.dumps({
                            'token': token,
                            'count': tokens,
                            'partial': full_response
                        })
                        yield f"data: {token_data}\n\n"
                        
                        # Small delay to prevent overwhelming client
                        time.sleep(0.001)
                except Exception as stream_error:
                    logger.error(f"Streaming error: {stream_error}")
                    error_data = json.dumps({'error': f'Streaming failed: {str(stream_error)}'})
                    yield f"data: {error_data}\n\n"
                    return
                
                # Send completion stats
                duration = time.time() - start_time
                completion_data = json.dumps({
                    'done': True,
                    'tokens': tokens,
                    'duration': round(duration, 2),
                    'tokens_per_second': round(tokens / duration, 2) if duration > 0 else 0,
                    'full_response': full_response,
                    'user': current_user,
                    'timestamp': datetime.now().isoformat()
                })
                yield f"data: {completion_data}\n\n"
                
                logger.info(f"[OK] Stream complete: {tokens} tokens in {duration:.2f}s ({tokens/duration:.1f} tok/s)")
                
            except Exception as e:
                logger.error(f"Stream generation error: {e}")
                error_msg = json.dumps({'error': str(e)})
                yield f"data: {error_msg}\n\n"
        
        return Response(generate_stream(), mimetype='text/event-stream')
    
    except Exception as e:
        logger.error(f"Chat stream endpoint error: {str(e)}")
        return jsonify({"error": f"Chat streaming failed: {str(e)}"}), 500

@chat_bp.route('/api/chat/sessions/<session_id>', methods=['GET'])
@jwt_required(optional=True)
def api_get_session(session_id):
    """Get information about a chat session"""
    try:
        if session_id not in chat_sessions:
            return jsonify({"error": "Session not found"}), 404
        
        chat = chat_sessions[session_id]
        stats = {
            "session_id": session_id,
            "messages": len(chat.conversation_history),
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/chat/sessions/<session_id>', methods=['DELETE'])
@jwt_required(optional=True)
def api_delete_session(session_id):
    """Delete a chat session"""
    try:
        with chat_session_lock:
            if session_id in chat_sessions:
                del chat_sessions[session_id]
                return jsonify({"success": True, "message": "Session deleted"})
        
        return jsonify({"error": "Session not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/api/chat/context', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("20 per minute")
def api_create_context():
    """Create new conversation context"""
    try:
        if not assistant.conversational_ai:
            return jsonify({"error": "Conversational AI not available"}), 503
        
        data = request.get_json()
        name = data.get('name', 'New Conversation')
        topic = data.get('topic', 'General Chat')
        initial_message = data.get('initial_message', '')
        
        context_id = assistant.conversational_ai.create_context(name, topic, initial_message)
        
        return jsonify({
            "context_id": context_id,
            "name": name,
            "topic": topic,
            "created_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Failed to create context: {str(e)}"}), 500

@chat_bp.route('/api/chat/suggestions', methods=['GET'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_get_suggestions():
    """Get AI-powered suggestions for next actions"""
    try:
        if not assistant.conversational_ai:
            return jsonify({"suggestions": []})
        
        suggestions = assistant.conversational_ai.suggest_next_actions()
        return jsonify({"suggestions": suggestions})
    except Exception as e:
        return jsonify({"error": f"Failed to get suggestions: {str(e)}"}), 500

@chat_bp.route('/api/multimodal/analyze', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("10 per minute")
def api_multimodal_analyze():
    """Analyze image with AI"""
    try:
        if not assistant.multimodal_ai:
            return jsonify({"error": "Multimodal AI not available"}), 503
        
        data = request.get_json()
        image_data = data.get('image')
        prompt = data.get('prompt', 'What do you see in this image?')
        
        if not image_data:
            return jsonify({"error": "No image provided"}), 400
        
        analysis = assistant.multimodal_ai.analyze_image_from_base64(image_data, prompt)
        
        return jsonify({
            "analysis": analysis,
            "prompt": prompt,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Image analysis failed: {str(e)}"}), 500

@chat_bp.route('/api/screen/analyze', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("5 per minute")
def api_analyze_screen():
    """Analyze current screen using multimodal AI"""
    try:
        data = request.get_json()
        prompt = data.get('prompt', 'What is on the screen?')
        
        analysis = assistant.analyze_screen(prompt)
        
        return jsonify({
            "analysis": analysis,
            "prompt": prompt,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Screen analysis failed: {str(e)}"}), 500

@chat_bp.route('/api/automation/workflows', methods=['GET'])
@jwt_required(optional=True)
@limiter.limit("20 per minute")
def api_get_workflows():
    """Get available automation workflows"""
    try:
        if not AUTOMATION_AVAILABLE:
            return jsonify({"workflows": []})
        
        from ai_assistant.automation.automation_engine import SmartAutomationEngine
        automation_engine = SmartAutomationEngine()
        workflows = automation_engine.get_available_workflows()
        
        return jsonify({"workflows": workflows})
    except Exception as e:
        return jsonify({"error": f"Failed to get workflows: {str(e)}"}), 500

@chat_bp.route('/api/automation/execute', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("10 per minute")
def api_execute_workflow():
    """Execute automation workflow"""
    try:
        if not AUTOMATION_AVAILABLE:
            return jsonify({"error": "Automation not available"}), 503
        
        data = request.get_json()
        workflow_name = data.get('workflow_name')
        
        if not workflow_name:
            return jsonify({"error": "Workflow name required"}), 400
        
        from ai_assistant.automation.automation_engine import SmartAutomationEngine
        automation_engine = SmartAutomationEngine()
        result = automation_engine.execute_workflow_by_name(workflow_name)
        
        return jsonify({
            "result": result,
            "workflow_name": workflow_name,
            "executed_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Workflow execution failed: {str(e)}"}), 500

@chat_bp.route('/api/memory/save', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_save_memory():
    """Save information to memory system"""
    try:
        if not AUTOMATION_AVAILABLE:
            return jsonify({"error": "Memory system not available"}), 503
        
        data = request.get_json()
        category = data.get('category', 'user')
        content = data.get('content')
        
        if not content:
            return jsonify({"error": "Content required"}), 400
        
        result = save_to_memory(category, content)
        
        return jsonify({
            "result": result,
            "category": category,
            "saved_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Failed to save memory: {str(e)}"}), 500

@chat_bp.route('/api/memory/search', methods=['GET'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_search_memory():
    """Search memory system"""
    try:
        if not AUTOMATION_AVAILABLE:
            return jsonify({"results": []})
        
        query = request.args.get('query', '')
        if not query:
            return jsonify({"error": "Search query required"}), 400
        
        results = search_memory(query)
        
        return jsonify({
            "results": results,
            "query": query,
            "searched_at": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Memory search failed: {str(e)}"}), 500

@chat_bp.route('/api/visual/question', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def api_visual_question():
    """Answer visual questions about screen content - PROTECTED"""
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'question', 'command')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        question = data['question']
        
        answer = assistant.answer_visual_question(question)
        return jsonify({
            "question": question,
            "answer": answer,
            "user": current_user,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": "Failed to answer visual question"}), 500