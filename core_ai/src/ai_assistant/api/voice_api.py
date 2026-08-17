"""
Voice API Blueprint - RESTful endpoints for voice functionality
Provides TTS, STT, wake word detection, and voice management APIs
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import base64
import asyncio
from pathlib import Path

try:
    from ai_assistant.services.voice_service import get_voice_service
    VOICE_SERVICE_AVAILABLE = True
except ImportError:
    VOICE_SERVICE_AVAILABLE = False

# Create blueprint
voice_api = Blueprint('voice_api', __name__, url_prefix='/api/voice')

# Get logger
try:
    from utils.logging_config import get_logger
    logger = get_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


# ============================================
# Voice System Status
# ============================================

@voice_api.route('/status', methods=['GET'])
def get_voice_status():
    """
    Get voice system status
    Returns information about available engines and current state
    """
    try:
        if not VOICE_SERVICE_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'Voice service not available',
                'available': False
            }), 503
        
        service = get_voice_service()
        status = service.get_status()
        
        return jsonify({
            'success': True,
            'available': True,
            **status
        })
    
    except Exception as e:
        logger.error(f"Error getting voice status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@voice_api.route('/config', methods=['GET'])
@jwt_required()
def get_voice_config():
    """Get current voice configuration"""
    try:
        service = get_voice_service()
        return jsonify({
            'success': True,
            'config': service.config
        })
    except Exception as e:
        logger.error(f"Error getting voice config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# Text-to-Speech (TTS) Endpoints
# ============================================

@voice_api.route('/speak', methods=['POST'])
@jwt_required()
def speak_text():
    """
    Convert text to speech
    Body: {
        "text": "Text to speak",
        "voice": "en-US-AriaNeural" (optional),
        "speed": 1.0 (optional),
        "volume": 0.9 (optional)
    }
    """
    try:
        if not VOICE_SERVICE_AVAILABLE:
            return jsonify({'success': False, 'error': 'Voice service not available'}), 503
        
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'success': False, 'error': 'No text provided'}), 400
        
        voice = data.get('voice')
        speed = data.get('speed', 1.0)
        volume = data.get('volume', 0.9)
        
        service = get_voice_service()
        success = service.speak(text, voice=voice, speed=speed, volume=volume)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Speech generated successfully',
                'text': text
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to generate speech'}), 500
    
    except Exception as e:
        logger.error(f"Error in speak endpoint: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@voice_api.route('/voices', methods=['GET'])
def get_available_voices():
    """Get list of available TTS voices"""
    try:
        if not VOICE_SERVICE_AVAILABLE:
            return jsonify({'success': False, 'error': 'Voice service not available'}), 503
        
        service = get_voice_service()
        voices = service.get_available_voices()
        
        return jsonify({
            'success': True,
            'voices': voices,
            'count': len(voices)
        })
    
    except Exception as e:
        logger.error(f"Error getting voices: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@voice_api.route('/preview', methods=['POST'])
def preview_voice():
    """
    Generate preview audio for a voice
    Body: {
        "voice_id": "en-US-AriaNeural",
        "text": "Sample text" (optional)
    }
    """
    try:
        if not VOICE_SERVICE_AVAILABLE:
            return jsonify({'success': False, 'error': 'Voice service not available'}), 503
        
        data = request.get_json()
        voice_id = data.get('voice_id', 'en-US-AriaNeural')
        sample_text = data.get('text', "Hello! This is a sample of my voice.")
        
        service = get_voice_service()
        
        # Generate audio asynchronously
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        output_path = temp_file.name
        temp_file.close()
        
        # Use async TTS
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        success = loop.run_until_complete(service.speak_async(sample_text, voice=voice_id))
        
        if success:
            # Read and encode audio
            import os
            if os.path.exists(output_path):
                with open(output_path, 'rb') as f:
                    audio_data = f.read()
                
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                os.unlink(output_path)
                
                return jsonify({
                    'success': True,
                    'voice_id': voice_id,
                    'audio_data': f"data:audio/mp3;base64,{audio_base64}"
                })
        
        return jsonify({'success': False, 'error': 'Failed to generate preview'}), 500
    
    except Exception as e:
        logger.error(f"Error generating preview: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# Speech-to-Text (STT) Endpoints
# ============================================

@voice_api.route('/listen', methods=['POST'])
@jwt_required()
def listen_for_speech():
    """
    Listen for speech and return transcribed text
    Body: {
        "timeout": 10 (optional),
        "phrase_time_limit": 15 (optional)
    }
    """
    try:
        if not VOICE_SERVICE_AVAILABLE:
            return jsonify({'success': False, 'error': 'Voice service not available'}), 503
        
        data = request.get_json() or {}
        timeout = data.get('timeout', 10)
        phrase_time_limit = data.get('phrase_time_limit', 15)
        
        service = get_voice_service()
        text = service.listen(timeout=timeout, phrase_time_limit=phrase_time_limit)
        
        if text:
            return jsonify({
                'success': True,
                'text': text,
                'timestamp': service.voice_history[-1]['timestamp'] if service.voice_history else None
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No speech detected'
            }), 400
    
    except Exception as e:
        logger.error(f"Error in listen endpoint: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@voice_api.route('/transcribe', methods=['POST'])
@jwt_required()
def transcribe_audio():
    """
    Transcribe audio data
    Body: {
        "audio_data": "base64 encoded audio",
        "format": "wav" (optional)
    }
    """
    try:
        if not VOICE_SERVICE_AVAILABLE:
            return jsonify({'success': False, 'error': 'Voice service not available'}), 503
        
        data = request.get_json()
        audio_data = data.get('audio_data', '')
        
        if not audio_data:
            return jsonify({'success': False, 'error': 'No audio data provided'}), 400
        
        # Decode base64 audio
        audio_bytes = base64.b64decode(audio_data)
        
        # Process with speech recognition
        # This is a placeholder - actual implementation would use the service
        
        return jsonify({
            'success': True,
            'text': 'Transcription feature coming soon',
            'confidence': 0.95
        })
    
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# Wake Word Detection
# ============================================

@voice_api.route('/wake-word/start', methods=['POST'])
@jwt_required()
def start_wake_word():
    """Start wake word detection"""
    try:
        if not VOICE_SERVICE_AVAILABLE:
            return jsonify({'success': False, 'error': 'Voice service not available'}), 503
        
        service = get_voice_service()
        
        # Start detection with callback
        def on_wake_word_detected():
            logger.info("Wake word detected!")
            # Emit socket event or trigger action
        
        service.start_wake_word_detection(on_wake_word_detected)
        
        return jsonify({
            'success': True,
            'message': 'Wake word detection started'
        })
    
    except Exception as e:
        logger.error(f"Error starting wake word: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@voice_api.route('/wake-word/stop', methods=['POST'])
@jwt_required()
def stop_wake_word():
    """Stop wake word detection"""
    try:
        if not VOICE_SERVICE_AVAILABLE:
            return jsonify({'success': False, 'error': 'Voice service not available'}), 503
        
        service = get_voice_service()
        service.stop_wake_word_detection()
        
        return jsonify({
            'success': True,
            'message': 'Wake word detection stopped'
        })
    
    except Exception as e:
        logger.error(f"Error stopping wake word: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@voice_api.route('/wake-word/config', methods=['GET', 'POST'])
@jwt_required()
def configure_wake_word():
    """Get or update wake word configuration"""
    try:
        if not VOICE_SERVICE_AVAILABLE:
            return jsonify({'success': False, 'error': 'Voice service not available'}), 503
        
        service = get_voice_service()
        
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'config': service.config.get('wake_word', {})
            })
        
        else:  # POST
            data = request.get_json()
            # Update configuration
            service.config['wake_word'].update(data)
            
            return jsonify({
                'success': True,
                'message': 'Wake word configuration updated',
                'config': service.config['wake_word']
            })
    
    except Exception as e:
        logger.error(f"Error configuring wake word: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# Voice History and Management
# ============================================

@voice_api.route('/history', methods=['GET'])
@jwt_required()
def get_voice_history():
    """Get voice command history"""
    try:
        if not VOICE_SERVICE_AVAILABLE:
            return jsonify({'success': False, 'error': 'Voice service not available'}), 503
        
        limit = request.args.get('limit', 10, type=int)
        
        service = get_voice_service()
        history = service.get_history(limit=limit)
        
        return jsonify({
            'success': True,
            'history': history,
            'count': len(history)
        })
    
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@voice_api.route('/cache/clear', methods=['POST'])
@jwt_required()
def clear_audio_cache():
    """Clear audio cache"""
    try:
        if not VOICE_SERVICE_AVAILABLE:
            return jsonify({'success': False, 'error': 'Voice service not available'}), 503
        
        service = get_voice_service()
        service.audio_cache.clear()
        
        return jsonify({
            'success': True,
            'message': 'Audio cache cleared'
        })
    
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@voice_api.route('/cache/stats', methods=['GET'])
def get_cache_stats():
    """Get audio cache statistics"""
    try:
        if not VOICE_SERVICE_AVAILABLE:
            return jsonify({'success': False, 'error': 'Voice service not available'}), 503
        
        service = get_voice_service()
        
        return jsonify({
            'success': True,
            'cache_size': len(service.audio_cache),
            'cache_items': list(service.audio_cache.keys())
        })
    
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# Health Check
# ============================================

@voice_api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for voice service"""
    try:
        if not VOICE_SERVICE_AVAILABLE:
            return jsonify({
                'success': False,
                'status': 'unavailable',
                'message': 'Voice service not initialized'
            }), 503
        
        service = get_voice_service()
        status = service.get_status()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'engines': status.get('engines', {})
        })
    
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'success': False,
            'status': 'error',
            'error': str(e)
        }), 500


# Export blueprint
__all__ = ['voice_api']
