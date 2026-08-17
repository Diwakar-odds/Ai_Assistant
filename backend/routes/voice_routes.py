from flask import Blueprint, jsonify, request, send_from_directory, render_template, Response, stream_with_context
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity, verify_jwt_in_request
import os, json, sys, time, datetime
try:
    from backend.modern_web_backend import logger, api_logger, get_current_context
except ImportError:
    pass
    

voice_bp = Blueprint('voice', __name__)


try:
    from backend.modern_web_backend import *
except ImportError:
    from modern_web_backend import *
@voice_bp.route('/api/voice/history')
@jwt_required()
def api_voice_history():
    """Get voice command history - PROTECTED"""
    history = [
        "Play my favorite playlist",
        "What's the weather like today?",
        "Schedule a meeting for 3 PM",
        "Open Chrome browser"
    ]
    return jsonify(history)

@voice_bp.route('/api/voice/status')
def api_voice_status():
    """Get voice system status - PUBLIC"""
    try:
        voice_available = VOICE_AVAILABLE and assistant.voice_recognizer is not None
        return jsonify({
            "connected": True,
            "voice_available": voice_available,
            "features": {
                "speech_recognition": assistant.voice_recognizer is not None,
                "text_to_speech": assistant.tts_engine is not None,
                "wake_word_detection": assistant.wake_word_detector is not None
            },
            "listening": getattr(assistant, 'voice_listening', False),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "connected": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@voice_bp.route('/api/voice/start', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def api_start_voice():
    """Start voice listening - PROTECTED"""
    try:
        result = assistant.start_voice_listening()
        if "error" in result:
            return jsonify(result), 500
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Failed to start voice listening"}), 500

@voice_bp.route('/api/voice/stop', methods=['POST'])
@jwt_required()
def api_stop_voice():
    """Stop voice listening - PROTECTED"""
    try:
        result = assistant.stop_voice_listening()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Failed to stop voice listening"}), 500

@voice_bp.route('/api/voice/speak', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute")
def api_speak():
    """Convert text to speech - PROTECTED"""
    try:
        data = request.get_json()
        
        # Validate input
        is_valid, error = validate_input(data, 'text', 'command')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        text = data['text']
        
        if not text:
            return jsonify({"error": "No text provided"}), 400
        
        success = assistant.speak_text(text)
        return jsonify({"success": success, "text": text})
    except Exception as e:
        logging.error(f"Error in api_speak: {str(e)}")
        return jsonify({"error": "Failed to process text-to-speech"}), 500

@voice_bp.route('/api/voice/list', methods=['GET'])
def api_list_voices():
    """Get list of available AI voices"""
    try:
        return jsonify({
            "success": True,
            "voices": AVAILABLE_VOICES,
            "default": "en-US-AriaNeural"
        })
    except Exception as e:
        logging.error(f"Error fetching voice list: {str(e)}")
        return jsonify({"error": "Failed to fetch voices"}), 500

@voice_bp.route('/api/voice/preview', methods=['POST'])
@limiter.limit("10 per minute")
def api_preview_voice():
    """Generate preview audio for a voice"""
    try:
        data = request.get_json()
        voice_id = data.get('voice_id', 'en-US-AriaNeural')
        sample_text = data.get('text', "Hello! This is a sample of my voice. I'm here to assist you with anything you need.")
        
        # Find voice info
        voice_info = next((v for v in AVAILABLE_VOICES if v['id'] == voice_id), None)
        if not voice_info:
            return jsonify({"error": "Voice not found"}), 404
        
        # Generate audio using Edge-TTS
        if VOICE_AVAILABLE:
            try:
                import edge_tts
                import tempfile
                
                # Create temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                output_path = temp_file.name
                temp_file.close()
                
                # Generate audio
                async def generate():
                    communicate = edge_tts.Communicate(sample_text, voice_id)
                    await communicate.save(output_path)
                
                # Run async function
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                loop.run_until_complete(generate())
                
                # Read and encode as base64
                with open(output_path, 'rb') as f:
                    audio_data = f.read()
                
                import base64
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                
                # Clean up
                os.unlink(output_path)
                
                return jsonify({
                    "success": True,
                    "voice_id": voice_id,
                    "voice_name": voice_info['name'],
                    "audio_data": f"data:audio/mp3;base64,{audio_base64}"
                })
                
            except Exception as e:
                logging.error(f"Edge-TTS preview failed: {str(e)}")
                return jsonify({"error": f"Preview generation failed: {str(e)}"}), 500
        else:
            return jsonify({"error": "Voice synthesis not available"}), 503
            
    except Exception as e:
        logging.error(f"Voice preview error: {str(e)}")
        return jsonify({"error": "Failed to generate preview"}), 500

@voice_bp.route('/api/voice/process', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute")
def api_process_voice():
    """Process voice audio data - PROTECTED"""
    try:
        current_user = get_jwt_identity()
        data = request.get_json()
        audio_data = data.get('audio_data', '')
        
        if not audio_data:
            return jsonify({"error": "No audio data provided"}), 400
        
        result = assistant.process_voice_audio(audio_data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": "Failed to process voice"}), 500

@voice_bp.route('/api/voice/chain', methods=['POST'])
@jwt_required()
def api_voice_to_chain():
    """Convert voice transcript directly to a Chain of Actions"""
    try:
        data = request.get_json()
        command = data.get('command')
        if not command:
            return jsonify({"error": "No command provided"}), 400
            
        if not MULTI_AGENT_AVAILABLE:
            return jsonify({"error": "Multi-Agent System not available"}), 503
            
        manager = get_chain_manager()
        import asyncio
        import threading
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        chain = loop.run_until_complete(manager.create_chain(command))
        
        def run_chain_background(chain_obj):
            async def _run():
                await manager.decompose_command(chain_obj)
                await manager.identify_executors(chain_obj)
                await manager.execute_chain(chain_obj.id)
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            new_loop.run_until_complete(_run())
            new_loop.close()
            
        thread = threading.Thread(target=run_chain_background, args=(chain,))
        thread.start()
        
        return jsonify({
            "success": True,
            "chain_id": chain.id,
            "message": f"Started chain execution for voice command: {command}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500