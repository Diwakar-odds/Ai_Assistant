from pathlib import Path
import os
import sys
import time
from datetime import datetime
from flask import Blueprint, jsonify, request
from .common import (
    logger, api_logger, limiter, validate_input, get_assistant,
    jwt_required, get_jwt_identity, verify_jwt_in_request,
    ENABLE_VOICE, ENABLE_MULTIMODAL, ENABLE_CONVERSATIONAL_AI, ENABLE_SYSTEM_MONITORING
)

system_bp = Blueprint('system', __name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from ai_assistant.automation.app_discovery import get_apps_for_web, refresh_app_database
    from ai_assistant.automation.automation_tools_new import (
        smart_open_application, get_spotify_status,
        spotify_play_pause, spotify_next_track, spotify_previous_track
    )
    AUTOMATION_AVAILABLE = True
except ImportError:
    AUTOMATION_AVAILABLE = False

MULTIMODAL_AVAILABLE = ENABLE_MULTIMODAL
CONVERSATIONAL_AI_AVAILABLE = ENABLE_CONVERSATIONAL_AI
MULTILINGUAL_AVAILABLE = True
VOICE_AVAILABLE = ENABLE_VOICE
ENHANCED_AI_AVAILABLE = True
USAGE_ANALYZER_AVAILABLE = True

@system_bp.route('/api/status')
def api_status():
    """API status endpoint - Public"""
    authenticated = False
    try:
        verify_jwt_in_request(optional=True)
        authenticated = bool(get_jwt_identity())
    except Exception:
        pass
    
    learning_systems_available = False
    try:
        from learning_integration import LEARNING_SYSTEMS_AVAILABLE
        learning_systems_available = LEARNING_SYSTEMS_AVAILABLE
    except ImportError:
        pass

    boot_id = None
    active_session_id = None
    try:
        try:
            from utils.chat_session_store import get_session_store
        except ImportError:
            from backend.utils.chat_session_store import get_session_store
        store = get_session_store()
        boot_id = store.get_boot_id()
        active_session_id = store.get_current_session().get("id")
    except Exception:
        pass
    
    return jsonify({
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "authenticated": authenticated,
        "boot_id": boot_id,
        "active_session_id": active_session_id,
        "services": {
            "automation": AUTOMATION_AVAILABLE,
            "multimodal": MULTIMODAL_AVAILABLE,
            "conversational_ai": CONVERSATIONAL_AI_AVAILABLE,
            "voice": VOICE_AVAILABLE,
            "system_monitoring": PSUTIL_AVAILABLE,
            "learning_systems": learning_systems_available,
            "enhanced_ai": ENHANCED_AI_AVAILABLE,
            "usage_analyzer": USAGE_ANALYZER_AVAILABLE,
            "multi_agent": True,
            "chains": True,
        }
    })

@system_bp.route('/api/startup/sequence', methods=['GET'])
@limiter.limit("10 per minute")
def api_startup_sequence():
    """Get complete startup sequence data (JARVIS-style)"""
    try:
        from startup_sequence import get_startup_sequence
        startup = get_startup_sequence()
        data = startup.get_startup_sequence_data()
        return jsonify({
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Startup sequence error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to generate startup sequence",
            "timestamp": datetime.now().isoformat()
        }), 500

@system_bp.route('/api/startup/diagnostics', methods=['GET'])
@limiter.limit("20 per minute")
def api_startup_diagnostics():
    """Get system diagnostics for startup sequence"""
    try:
        from startup_sequence import get_startup_sequence
        startup = get_startup_sequence()
        diagnostics = startup.get_system_diagnostics()
        return jsonify({
            "success": True,
            "diagnostics": diagnostics,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Startup diagnostics error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to get system diagnostics",
            "timestamp": datetime.now().isoformat()
        }), 500

@system_bp.route('/api/startup/briefing', methods=['GET'])
@limiter.limit("20 per minute")
def api_startup_briefing():
    """Get contextual briefing for startup sequence"""
    try:
        from startup_sequence import get_startup_sequence
        startup = get_startup_sequence()
        briefing = startup.get_contextual_briefing()
        return jsonify({
            "success": True,
            "briefing": briefing,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Startup briefing error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to get briefing",
            "timestamp": datetime.now().isoformat()
        }), 500

@system_bp.route('/api/system/stats')
@jwt_required()
@limiter.limit("60 per minute")
def api_system_stats():
    """Get real-time system statistics - PROTECTED"""
    try:
        assistant = get_assistant()
        if assistant and hasattr(assistant, 'get_real_time_system_stats'):
            stats = assistant.get_real_time_system_stats()
            return jsonify(stats)
        return jsonify({
            "cpu_percent": 0,
            "memory_percent": 0,
            "disk_percent": 0,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve system stats: {e}"}), 500


@system_bp.route('/api/system/details', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
@limiter.limit("30 per minute")
def api_system_details():
    """Detailed OS, uptime, process/thread, resource, and active agent/chain telemetry."""
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        import platform
        os_name = f"{platform.system()} {platform.release()}".strip()
        uptime_seconds = 0
        uptime_str = "--"
        processes = 0
        threads = 0
        cpu_info = {"percent": 0.0, "cores_physical": os.cpu_count() or 1, "cores_logical": os.cpu_count() or 1}
        mem_info = {"total_gb": 0.0, "used_gb": 0.0, "available_gb": 0.0, "percent": 0.0}
        disk_info = {"total_gb": 0.0, "used_gb": 0.0, "free_gb": 0.0, "percent": 0.0}
        power_info = {"status": "AC / Unknown", "percent": None, "plugged_in": None, "secs_left": None}

        if PSUTIL_AVAILABLE:
            try:
                boot_ts = psutil.boot_time()
                uptime_seconds = max(0, int(time.time() - boot_ts))
                days, rem = divmod(uptime_seconds, 86400)
                hours, rem = divmod(rem, 3600)
                mins, _ = divmod(rem, 60)
                parts = []
                if days:
                    parts.append(f"{days}d")
                if hours or days:
                    parts.append(f"{hours}h")
                parts.append(f"{mins}m")
                uptime_str = " ".join(parts)
            except Exception:
                pass

            try:
                pids = psutil.pids()
                processes = len(pids)
            except Exception:
                processes = 0

            try:
                total_threads = 0
                for proc in psutil.process_iter(['num_threads']):
                    try:
                        nt = proc.info.get('num_threads')
                        if isinstance(nt, int):
                            total_threads += nt
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                threads = total_threads
            except Exception:
                threads = 0

            try:
                freq = psutil.cpu_freq()
                cpu_info = {
                    "percent": round(float(psutil.cpu_percent(interval=0)), 1),
                    "cores_physical": psutil.cpu_count(logical=False) or (os.cpu_count() or 1),
                    "cores_logical": psutil.cpu_count(logical=True) or (os.cpu_count() or 1),
                    "freq_mhz": round(float(freq.current), 0) if freq else None,
                }
            except Exception:
                pass

            try:
                vm = psutil.virtual_memory()
                gb = 1024 ** 3
                mem_info = {
                    "total_gb": round(vm.total / gb, 2),
                    "used_gb": round(vm.used / gb, 2),
                    "available_gb": round(vm.available / gb, 2),
                    "percent": round(float(vm.percent), 1),
                }
            except Exception:
                pass

            try:
                du = psutil.disk_usage('C:\\' if os.name == 'nt' else '/')
                gb = 1024 ** 3
                disk_info = {
                    "total_gb": round(du.total / gb, 2),
                    "used_gb": round(du.used / gb, 2),
                    "free_gb": round(du.free / gb, 2),
                    "percent": round(float(du.percent), 1),
                }
            except Exception:
                pass

            try:
                batt = psutil.sensors_battery()
                if batt is not None:
                    plugged = bool(batt.power_plugged)
                    pct = round(float(batt.percent), 1) if batt.percent is not None else None
                    power_info = {
                        "status": f"{'AC Plugged' if plugged else 'Battery'} ({pct}%)" if pct is not None else ("AC Plugged" if plugged else "Battery"),
                        "percent": pct,
                        "plugged_in": plugged,
                        "secs_left": None if batt.secsleft in (-1, -2, psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN) else int(batt.secsleft),
                    }
                else:
                    power_info = {"status": "AC Power", "percent": 100, "plugged_in": True, "secs_left": None}
            except Exception:
                pass

        agents_summary = {"total": 0, "busy": 0, "loaded": 0}
        try:
            try:
                from routes.agent_routes import get_agents_snapshot_payload
            except ImportError:
                from backend.routes.agent_routes import get_agents_snapshot_payload
            snap = get_agents_snapshot_payload()
            agents_summary = {
                "total": snap.get("total", 0),
                "busy": snap.get("busy_count", 0),
                "loaded": snap.get("active_count", 0),
            }
        except Exception:
            pass

        chains_active = 0
        try:
            try:
                from routes.chain_routes import list_active_chains_dto
            except ImportError:
                from backend.routes.chain_routes import list_active_chains_dto
            chains_active = len(list_active_chains_dto())
        except Exception:
            pass

        payload = {
            "success": True,
            "os": os_name,
            "os_name": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "uptime": uptime_str,
            "uptime_seconds": uptime_seconds,
            "processes": processes,
            "threads": threads,
            "cpu_count": os.cpu_count() or 1,
            "memory_total_gb": mem_info.get("total_gb", 0.0),
            "cpu": cpu_info,
            "memory": mem_info,
            "disk": disk_info,
            "power": power_info,
            "agents": agents_summary,
            "chains_active": chains_active,
            "timestamp": datetime.now().isoformat(),
        }
        payload["details"] = dict(payload)
        return jsonify(payload)
    except Exception as e:
        logger.error(f"Failed to retrieve system details: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@system_bp.route('/api/features', methods=['GET'])
def api_features():
    """Get list of all available features and their status"""
    features = {
        "conversational_ai": CONVERSATIONAL_AI_AVAILABLE,
        "multimodal_ai": MULTIMODAL_AVAILABLE,
        "multilingual": MULTILINGUAL_AVAILABLE,
        "automation": AUTOMATION_AVAILABLE,
        "voice_recognition": VOICE_AVAILABLE,
        "modules": {
            "smart_automation": True,
            "enhanced_learning": True,
            "advanced_integration": True,
            "file_operations": True,
            "web_scraping": True,
            "music_control": True,
            "email_handler": True,
            "calendar_integration": True,
            "document_ocr": True,
            "memory_system": True,
            "system_monitoring": True,
            "taskbar_detection": True
        }
    }
    return jsonify(features)

@system_bp.route('/api/apps', methods=['GET'])
@limiter.limit("30 per minute")
def api_apps():
    """Get list of installed applications - PUBLIC"""
    try:
        if AUTOMATION_AVAILABLE:
            apps = get_apps_for_web()
            if not isinstance(apps, list):
                apps = []
        else:
            apps = [
                {"name": "Chrome", "path": "chrome.exe", "category": "Browser", "usage": 89, "description": "Google Chrome web browser"},
                {"name": "Mail", "path": "mail.exe", "category": "Communication", "usage": 76, "description": "Email application"},
                {"name": "Documents", "path": "word.exe", "category": "Productivity", "usage": 65, "description": "Document editor"},
                {"name": "Photos", "path": "photos.exe", "category": "Media", "usage": 52, "description": "Photo viewer"},
                {"name": "Videos", "path": "vlc.exe", "category": "Media", "usage": 43, "description": "Video player"},
                {"name": "Code", "path": "code.exe", "category": "Development", "usage": 92, "description": "Code editor"},
                {"name": "Terminal", "path": "cmd.exe", "category": "System Tools", "usage": 78, "description": "Command line interface"},
                {"name": "Calculator", "path": "calc.exe", "category": "System Tools", "usage": 45, "description": "Windows calculator"},
                {"name": "Notepad", "path": "notepad.exe", "category": "System Tools", "usage": 30, "description": "Simple text editor"}
            ]
        return jsonify(apps)
    except Exception as e:
        logger.error(f"Failed to get apps: {e}")
        return jsonify([]), 500

@system_bp.route('/api/apps/refresh', methods=['POST'])
@limiter.limit("5 per minute")
def api_refresh_apps():
    """Refresh/rescan installed applications"""
    try:
        if AUTOMATION_AVAILABLE:
            result = refresh_app_database()
            apps = get_apps_for_web()
            return jsonify({
                "success": True,
                "message": result,
                "total": len(apps),
                "apps": apps
            })
        else:
            return jsonify({"success": False, "message": "App discovery not available"}), 503
    except Exception as e:
        logger.error(f"Failed to refresh apps: {e}")
        return jsonify({"error": str(e)}), 500

@system_bp.route('/api/apps/launch', methods=['POST'])
@jwt_required(optional=True)
@limiter.limit("20 per minute")
def api_launch_app():
    """Launch an application"""
    try:
        current_user = get_jwt_identity() or "demo_user"
        data = request.get_json() or {}
        
        is_valid, error = validate_input(data, 'app_name', 'app_name')
        if not is_valid:
            return jsonify({"error": error}), 400
        
        app_name = data['app_name']
        
        try:
            if AUTOMATION_AVAILABLE:
                result = smart_open_application(app_name)
                if "Error" in result or "not found" in result.lower():
                    if "youtube music" in app_name.lower():
                        import webbrowser
                        webbrowser.open('https://music.youtube.com')
                        result = "Opened YouTube Music in web browser"
                    elif "spotify" in app_name.lower():
                        import webbrowser
                        webbrowser.open('https://open.spotify.com')
                        result = "Opened Spotify in web browser"
                    else:
                        result = f"Attempted to launch {app_name} (result: {result})"
            else:
                result = f"Launched {app_name} (simulation mode)"
        except Exception as launch_error:
            result = f"Could not launch {app_name} directly: {launch_error}"
        
        return jsonify({
            "success": True,
            "message": result,
            "app_name": app_name,
            "user": current_user
        })
    except Exception as e:
        logger.error(f"Launch error: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to launch {data.get('app_name', 'application')}: {str(e)}"
        }), 500

@system_bp.route('/api/spotify/status')
@jwt_required()
@limiter.limit("30 per minute")
def api_spotify_status():
    """Get Spotify status - PROTECTED"""
    try:
        if AUTOMATION_AVAILABLE:
            status = get_spotify_status()
        else:
            status = {
                "is_playing": True,
                "track_name": "Midnight Dreams",
                "artist_name": "Synthwave Collective",
                "progress": 65,
                "duration": 240
            }
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": "Failed to retrieve Spotify status"}), 500

@system_bp.route('/api/spotify/control', methods=['POST'])
@jwt_required()
@limiter.limit("30 per minute")
def api_spotify_control():
    """Control Spotify playback - PROTECTED"""
    try:
        current_user = get_jwt_identity()
        data = request.get_json() or {}
        action = data.get('action', '')
        
        if not action:
            return jsonify({"error": "No action provided"}), 400
        
        if AUTOMATION_AVAILABLE:
            if action == 'play_pause':
                result = spotify_play_pause()
            elif action == 'next':
                result = spotify_next_track()
            elif action == 'previous':
                result = spotify_previous_track()
            else:
                return jsonify({"error": "Unknown action"}), 400
        else:
            result = f"Spotify {action} executed (simulation mode)"
        
        return jsonify({
            "success": True,
            "message": result,
            "action": action,
            "user": current_user
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Failed to control Spotify: {e}"
        }), 500

def _get_store():
    try:
        from utils.chat_session_store import get_session_store
    except ImportError:
        from backend.utils.chat_session_store import get_session_store
    return get_session_store()


@system_bp.route('/api/activity')
@jwt_required(optional=True)
def api_activity():
    """Get unified live session activity feed (Glowing Orb + WebUI)"""
    try:
        store = _get_store()
        limit = request.args.get('limit', default=100, type=int) or 100
        sess = store.get_current_session()
        activities = store.get_current_activities(limit=limit)
        return jsonify({
            "success": True,
            "boot_id": store.get_boot_id(),
            "session_id": sess.get("id"),
            "activities": activities,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "activities": []}), 500


# ============================================================
# Unified Session & Activity History Endpoints
# ============================================================
@system_bp.route('/api/sessions/current', methods=['GET', 'OPTIONS'])
def api_sessions_current():
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        store = _get_store()
        return jsonify({
            "success": True,
            "boot_id": store.get_boot_id(),
            "session": store.get_current_session(),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@system_bp.route('/api/sessions/history', methods=['GET', 'OPTIONS'])
def api_sessions_history():
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        store = _get_store()
        limit = request.args.get('limit', default=50, type=int) or 50
        return jsonify({
            "success": True,
            "boot_id": store.get_boot_id(),
            "sessions": store.get_history(limit=limit),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "sessions": []}), 500


@system_bp.route('/api/sessions/<session_id>', methods=['GET', 'DELETE', 'OPTIONS'])
def api_session_item(session_id):
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        store = _get_store()
        if request.method == 'DELETE':
            deleted = store.delete_session(session_id)
            return jsonify({"success": bool(deleted), "deleted": bool(deleted), "session_id": session_id}), (200 if deleted else 404)
        sess = store.get_session(session_id)
        if not sess:
            return jsonify({"success": False, "error": "Session not found"}), 404
        return jsonify({"success": True, "boot_id": store.get_boot_id(), "session": sess}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@system_bp.route('/api/sessions/new', methods=['POST', 'OPTIONS'])
def api_sessions_new():
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        data = request.get_json(force=True, silent=True) or {}
        source = str(data.get("source") or "webui_new_session")
        reason = str(data.get("reason") or "manual")
        speak_flag = bool(data.get("speak", False))
        lang_hint = data.get("language_hint")

        store = _get_store()
        prev_sess_id = store.get_current_session().get("id")

        # Cancel any in-flight turn, brain execution, TTS speech, and cached LLM conversations before switching sessions
        try:
            from ai_assistant.core.jarvis_persona import get_lifecycle_coordinator
            get_lifecycle_coordinator().cancel_all(reason="new_session")
        except Exception:
            pass
        try:
            from ai_assistant.core.command_brain import get_executive_brain
            brain = get_executive_brain()
            if brain.is_busy():
                brain._cancel_all_active(reason="new_session", emit_notice=False)
        except Exception:
            pass
        try:
            from ai_assistant.voice.tts_output_service import get_tts_service
            get_tts_service().stop(reason="new_session")
        except Exception:
            pass
        for mod_name in ("voice_service", "backend.voice_service"):
            vs_mod = sys.modules.get(mod_name)
            if vs_mod is not None and hasattr(vs_mod, "reset_llm_sessions"):
                try:
                    vs_mod.reset_llm_sessions()
                except Exception:
                    pass
                break
        try:
            from routes.chat_routes import clear_chat_sessions
            clear_chat_sessions()
        except Exception:
            try:
                from backend.routes.chat_routes import clear_chat_sessions
                clear_chat_sessions()
            except Exception:
                pass
        try:
            from routes.common import get_socketio
            sio = get_socketio()
            if sio and prev_sess_id:
                sio.emit("chat_stream_end", {"aborted": True, "reason": "new_session", "session_id": prev_sess_id})
        except Exception:
            pass

        greeting = ""
        try:
            from ai_assistant.core.jarvis_persona import generate_session_greeting
            greeting = str(generate_session_greeting(kind="new_session", language_hint=lang_hint) or "").strip()
        except Exception:
            greeting = "Naya session ready hai Boss — batayein kis cheez pe kaam karein?"

        new_sess = store.start_new_session(
            reason=reason,
            greeting_text=greeting,
            source=source,
            emit_event=True,
        )

        spoken = False
        if speak_flag and greeting:
            try:
                from ai_assistant.voice.tts_output_service import get_tts_service
                spoken = bool(get_tts_service().speak(greeting, interrupt=True, wait=False, source=source))
            except Exception:
                pass

        return jsonify({
            "success": True,
            "boot_id": store.get_boot_id(),
            "session": new_sess,
            "greeting": greeting,
            "queued": spoken,
            "spoken": spoken,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@system_bp.route('/api/sessions/clear', methods=['POST', 'OPTIONS'])
def api_sessions_clear():
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        store = _get_store()
        removed = store.clear_history()
        return jsonify({"success": True, "removed": removed}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ============================================================
# Desktop Floating Companion Mascot Routes
# ============================================================
COMPANION_PROCESS = None


def spawn_companion_process(port=5000):
    global COMPANION_PROCESS
    if os.environ.get('PULSAR_DISABLE_COMPANION') == '1':
        return False, "Companion disabled via PULSAR_DISABLE_COMPANION"
    if COMPANION_PROCESS is not None and COMPANION_PROCESS.poll() is None:
        logger.info("[COMPANION] Companion process is already running (PID %s)", COMPANION_PROCESS.pid)
        return True, "Companion already active"

    is_frozen = bool(getattr(sys, 'frozen', False))
    try:
        import subprocess
        env = os.environ.copy()
        env['PULSAR_PORT'] = str(port)
        env['PULSAR_DASHBOARD_URL'] = f'http://127.0.0.1:{port}'

        creationflags = 0
        if sys.platform == 'win32':
            creationflags = subprocess.CREATE_NO_WINDOW

        if is_frozen:
            cmd = [sys.executable, '--companion', str(port)]
            cwd_path = str(Path(sys.executable).parent)
        else:
            project_root = Path(__file__).resolve().parent.parent.parent
            venv_py = project_root / 'venv' / 'Scripts' / 'python.exe'
            py_exe = str(venv_py) if venv_py.exists() else sys.executable
            script_path = str(project_root / 'desktop' / 'companion_app.py')
            if not os.path.exists(script_path):
                logger.error("[COMPANION] Script not found at %s", script_path)
                return False, f"Script not found at {script_path}"
            cmd = [py_exe, script_path, str(port)]
            cwd_path = str(project_root)

        COMPANION_PROCESS = subprocess.Popen(
            cmd,
            cwd=cwd_path,
            env=env,
            creationflags=creationflags
        )
        logger.info("[COMPANION] Spawned floating companion process (PID %s, port=%s)", COMPANION_PROCESS.pid, port)
        return True, "Companion started"
    except Exception as e:
        logger.error("[COMPANION] Failed to spawn companion: %s", e)
        return False, str(e)


def stop_companion_process():
    global COMPANION_PROCESS
    if COMPANION_PROCESS is not None:
        try:
            COMPANION_PROCESS.terminate()
            COMPANION_PROCESS.wait(timeout=2.0)
        except Exception:
            try:
                COMPANION_PROCESS.kill()
            except Exception:
                pass
        COMPANION_PROCESS = None


@system_bp.route('/api/desktop/companion/toggle', methods=['GET', 'POST', 'OPTIONS'])
@system_bp.route('/api/desktop/companion/minimize', methods=['GET', 'POST', 'OPTIONS'])
@system_bp.route('/api/desktop/companion/spawn', methods=['GET', 'POST', 'OPTIONS'])
def api_desktop_companion_toggle():
    if request.method == 'OPTIONS':
        return ('', 204)

    bridge = getattr(sys, '_active_desktop_bridge', None)
    if bridge:
        try:
            bridge.minimize_to_companion()
            return jsonify({"success": True, "mode": "bridge"})
        except Exception as e:
            logger.warning(f"Bridge toggle failed: {e}")

    port = int(os.environ.get('PORT', 5000))
    success, msg = spawn_companion_process(port=port)

    try:
        from voice_service import update_overlay_state
    except ImportError:
        try:
            from backend.voice_service import update_overlay_state
        except ImportError:
            update_overlay_state = None

    if update_overlay_state:
        try:
            update_overlay_state(app_minimized=True, source="system_route")
            req_data = request.get_json(force=True, silent=True) or {}
            if req_data.get('activate'):
                update_overlay_state(state='listening', source='toggle')
        except Exception:
            pass

    return jsonify({"success": success, "message": msg, "mode": "spawn"})


@system_bp.route('/api/desktop/companion/restore', methods=['GET', 'POST', 'OPTIONS'])
def api_desktop_companion_restore():
    if request.method == 'OPTIONS':
        return ('', 204)
    bridge = getattr(sys, '_active_desktop_bridge', None)
    if bridge:
        try:
            bridge.restore_dashboard()
            return jsonify({"success": True, "mode": "bridge"})
        except Exception as e:
            logger.warning(f"Bridge restore failed: {e}")
    return jsonify({"success": True, "message": "Dashboard restore signal processed"})


@system_bp.route('/api/desktop/companion/status', methods=['GET', 'OPTIONS'])
def api_desktop_companion_status():
    if request.method == 'OPTIONS':
        return ('', 204)
    global COMPANION_PROCESS
    is_active = False
    if getattr(sys, '_active_desktop_bridge', None):
        is_active = True
    elif COMPANION_PROCESS is not None and COMPANION_PROCESS.poll() is None:
        is_active = True
    return jsonify({"active": is_active})


@system_bp.route('/api/desktop/overlay/state', methods=['GET', 'POST', 'OPTIONS'])
def api_desktop_overlay_state():
    """Get or update live 4D orb overlay state across WebUI, backend, and desktop companion."""
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        from voice_service import get_overlay_state, update_overlay_state
    except ImportError:
        from backend.voice_service import get_overlay_state, update_overlay_state

    if request.method == 'POST':
        data = request.get_json(force=True, silent=True) or {}
        state = update_overlay_state(
            state=data.get('state'),
            audio_level=data.get('audio_level'),
            app_minimized=data.get('app_minimized'),
            transcript=data.get('transcript'),
            error_message=data.get('error_message'),
            source=data.get('source', 'api'),
            webui_mic_active=data.get('webui_mic_active'),
        )
        return jsonify({"success": True, "overlay": state})

    return jsonify({"success": True, "overlay": get_overlay_state()})


# ============================================================
# Agent Brain & Notification Endpoints (Companion Mascot API)
# ============================================================
def execute_companion_voice_command(data: dict) -> dict:
    """Execute a companion / in-process voice command through Agent Brain and Unified Persona."""
    try:
        from agent_brain import get_agent_brain
        from ai_assistant.core.jarvis_persona import (
            get_lifecycle_coordinator,
            should_speak_for_request,
        )
        try:
            from voice_service import get_overlay_state, update_overlay_state, _schedule_overlay_idle, _socketio
        except ImportError:
            from backend.voice_service import get_overlay_state, update_overlay_state, _schedule_overlay_idle, _socketio

        command = data.get('command', '')
        include_screen = data.get('include_screen', False)
        source = str(data.get('source', 'COMPANION_MASCOT') or 'COMPANION_MASCOT')

        from ai_assistant.core.local_command_normalizer import is_noise_fragment
        if is_noise_fragment(command):
            logger.info(f"Dropped noise/hallucination fragment in companion command: '{command}'")
            return {'success': True, 'response': '', 'tts': '', 'silent': True, 'dropped_noise': True}

        store = _get_store()
        sess_id = store.get_current_session().get('id')
        boot_id = store.get_boot_id()
        user_msg_id = str(data.get('client_message_id') or '').strip() or store.next_message_id('orb_user')
        ai_msg_id = store.next_message_id('orb_ai')

        if command:
            store.record_message(
                'user',
                command,
                source=source,
                is_voice=True,
                message_id=user_msg_id,
            )

        tts_svc = None
        try:
            from ai_assistant.voice.tts_output_service import get_tts_service
            tts_svc = get_tts_service()
            if command:
                tts_svc.stop(reason='agent_command_barge_in')
        except Exception:
            pass

        coordinator = get_lifecycle_coordinator()
        wants_speak = should_speak_for_request(data, default_for_chat=False)
        turn_id = coordinator.begin_turn(command, source=source, speak=wants_speak)

        # Mirror user voice command to WebUI immediately
        if _socketio and command:
            try:
                _socketio.emit('voice_transcript', {
                    'text': command,
                    'confidence': 0.95,
                    'source': source,
                    'message_id': user_msg_id,
                    'session_id': sess_id,
                    'boot_id': boot_id,
                })
            except Exception:
                pass

        # Pre-execution natural acknowledgment (skipped automatically for wake-only / voice-control toggles)
        pre_report = coordinator.emit_pre_report(
            turn_id,
            command,
            source=source,
            speak=wants_speak,
            wait_brief=False,
        )
        if pre_report:
            try:
                store.record_activity(
                    'pre_report',
                    'Companion pre-report',
                    pre_report,
                    source=source,
                    status='running',
                )
            except Exception:
                pass

        brain = get_agent_brain()
        raw_prov = str(data.get('provider') or '').strip().lower()
        req_model = data.get('model')
        offline_mode = bool(data.get('offline_mode', False))
        if offline_mode and raw_prov not in ('gguf', 'local', 'offline'):
            raw_prov = 'gguf'
        model_pref = (
            {'provider': raw_prov or None, 'model': req_model, 'offline_mode': offline_mode}
            if (raw_prov or req_model or offline_mode)
            else None
        )
        res = brain.process_command(
            command,
            include_screen=include_screen,
            source=source,
            model_preference=model_pref,
            agent_id=data.get('agent_id'),
        )

        is_ok = bool(res.get('success', True)) if isinstance(res, dict) else True
        resp_msg = str(res.get('response', '')) if isinstance(res, dict) else str(res)
        tts_text = str(res.get('tts') or resp_msg) if isinstance(res, dict) else resp_msg
        res_intent = res.get('intent') if isinstance(res, dict) else None
        meta = res.get('execution_meta', {}) if isinstance(res, dict) else {}
        prov_used = (meta.get('provider_used') if isinstance(meta, dict) else None) or raw_prov or None
        model_used = (meta.get('model_used') if isinstance(meta, dict) else None) or req_model or None

        formatted_resp, was_active = coordinator.complete_turn(
            turn_id,
            command,
            resp_msg,
            success=is_ok,
            intent=res_intent,
            source=source,
            speak=wants_speak,
            tts_text_override=tts_text if res_intent in ('wake_greeting', 'voice_control') else None,
        )
        final_text = formatted_resp or resp_msg

        ov = get_overlay_state()
        minimized = bool(ov.get('app_minimized', False))
        reply_source = 'companion_voice' if minimized else 'companion_voice_webui'

        req_conf = bool(res.get('requires_confirmation', False)) if isinstance(res, dict) else False
        action_id = res.get('action_id') if isinstance(res, dict) else None
        chain_id = res.get('chain_id') if isinstance(res, dict) else None
        agent_id_used = res.get('agent_id') if isinstance(res, dict) else None
        orchestrated = bool(res.get('orchestrated', False)) if isinstance(res, dict) else False
        card = res.get('card') if isinstance(res, dict) else None

        if isinstance(res, dict):
            if formatted_resp:
                res['response'] = formatted_resp
                res['tts'] = formatted_resp
            if pre_report:
                res['pre_report'] = pre_report
            res['message_id'] = ai_msg_id
            res['user_message_id'] = user_msg_id
            res['session_id'] = sess_id
            res['boot_id'] = boot_id
            if prov_used:
                res['provider'] = prov_used
            if model_used:
                res['model'] = model_used

        if command and was_active and final_text:
            store.record_message(
                'ai',
                final_text,
                source=reply_source,
                is_voice=False,
                message_id=ai_msg_id,
                provider=prov_used,
                model=model_used,
                intent=res_intent,
                success=is_ok,
            )

        # Mirror companion voice commands & responses into WebUI conversation history without duplicate client TTS
        if _socketio and command and was_active:
            try:
                _socketio.emit('command_response', {
                    'success': is_ok,
                    'command': command,
                    'response': final_text,
                    'source': reply_source,
                    'message_id': ai_msg_id,
                    'user_message_id': user_msg_id,
                    'session_id': sess_id,
                    'boot_id': boot_id,
                    'provider': prov_used,
                    'model': model_used,
                    'intent': res_intent,
                    'requires_confirmation': req_conf,
                    'action_id': action_id,
                    'chain_id': chain_id,
                    'agent_id': agent_id_used,
                    'orchestrated': orchestrated,
                    'card': card,
                    'skip_tts': True,
                })
                if req_conf and action_id:
                    _socketio.emit('danger_action_pending', {
                        'id': action_id,
                        'action_id': action_id,
                        'command': command,
                        'description': final_text,
                        'card': card,
                    })
            except Exception:
                pass

        return res if isinstance(res, dict) else {'success': is_ok, 'response': str(res)}
    except Exception as e:
        logger.error(f'execute_companion_voice_command failed: {e}', exc_info=True)
        err_msg = f'Error executing command: {str(e)}'
        try:
            store = _get_store()
            err_id = store.next_message_id('orb_err')
            store.record_message(
                'ai',
                err_msg,
                source='companion_error',
                is_voice=False,
                message_id=err_id,
                success=False,
            )
            sess_id = store.get_current_session().get('id')
            boot_id = store.get_boot_id()
        except Exception:
            err_id = None
            sess_id = None
            boot_id = None
        try:
            from voice_service import update_overlay_state, _schedule_overlay_idle, _socketio
        except ImportError:
            from backend.voice_service import update_overlay_state, _schedule_overlay_idle, _socketio
        snap = update_overlay_state(state='error', error_message=str(e), source='agent_command_error')
        _schedule_overlay_idle(3.5, snap['updated_at'])
        if _socketio:
            try:
                _socketio.emit('command_response', {
                    'success': False,
                    'response': err_msg,
                    'error': str(e),
                    'source': 'companion_error',
                    'message_id': err_id,
                    'session_id': sess_id,
                    'boot_id': boot_id,
                    'skip_tts': True,
                })
            except Exception:
                pass
        return {'success': False, 'response': err_msg, 'error': str(e), 'message_id': err_id, 'session_id': sess_id, 'boot_id': boot_id}


@system_bp.route('/api/agent/command', methods=['POST', 'OPTIONS'])
@system_bp.route('/api/companion/command', methods=['POST', 'OPTIONS'])
def api_agent_command():
    if request.method == 'OPTIONS':
        return ('', 204)
    data = request.get_json(force=True, silent=True) or {}
    res = execute_companion_voice_command(data)
    status_code = 500 if (not res.get('success', True) and res.get('error')) else 200
    return jsonify(res), status_code


@system_bp.route('/api/agent/notifications', methods=['GET', 'OPTIONS'])
def api_agent_notifications():
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        from notification_monitor import get_notification_monitor
        monitor = get_notification_monitor()
        notifications = monitor.get_pending()
        return jsonify({'notifications': notifications})
    except Exception as e:
        return jsonify({'notifications': []})


@system_bp.route('/api/agent/confirm', methods=['POST', 'OPTIONS'])
def api_agent_confirm():
    if request.method == 'OPTIONS':
        return ('', 204)
    try:
        from agent_brain import get_agent_brain
        data = request.get_json(force=True, silent=True) or {}
        action_id = data.get('action_id', '')
        confirmed = data.get('confirmed', False)
        brain = get_agent_brain()
        res = brain.confirm_action_by_id(action_id, confirmed)
        is_ok = bool(res.get('success', True)) if isinstance(res, dict) else True
        try:
            from ai_assistant.core.jarvis_persona import format_post_task_report, should_speak_for_request
            from ai_assistant.voice.tts_output_service import get_tts_service
            raw_msg = str((res.get('tts') or res.get('response')) or '') if isinstance(res, dict) else ''
            formatted_msg = format_post_task_report(
                command=f"confirm {action_id}" if confirmed else f"cancel {action_id}",
                raw_result=raw_msg,
                success=is_ok,
            )
            if isinstance(res, dict) and formatted_msg:
                res['response'] = formatted_msg
                res['tts'] = formatted_msg
            if formatted_msg and should_speak_for_request(data, default_for_chat=True):
                get_tts_service().speak(str(formatted_msg), interrupt=True, source='agent_confirm')
        except Exception:
            formatted_msg = str(res.get('response') or '') if isinstance(res, dict) else str(res)

        try:
            store = _get_store()
            final_confirm_msg = str((res.get('response') if isinstance(res, dict) else formatted_msg) or '')
            store.record_activity(
                'action',
                f"Action {'confirmed' if confirmed else 'cancelled'}",
                f"{action_id}: {final_confirm_msg}".strip(': '),
                source='agent_confirm',
                status='success' if is_ok else 'error',
            )
            if final_confirm_msg:
                msg_id = store.next_message_id('confirm_ai')
                store.record_message(
                    'ai',
                    final_confirm_msg,
                    source='agent_confirm',
                    is_voice=False,
                    message_id=msg_id,
                    success=is_ok,
                    also_record_activity=False,
                )
                if isinstance(res, dict):
                    res['message_id'] = msg_id
                    res['session_id'] = store.get_current_session().get('id')
                    res['boot_id'] = store.get_boot_id()
        except Exception:
            pass
        try:
            from .common import get_socketio
            sio = get_socketio()
            if sio:
                sio.emit('danger_action_resolved', {
                    'action_id': action_id,
                    'confirmed': bool(confirmed),
                    'success': is_ok,
                    'response': res.get('response') if isinstance(res, dict) else '',
                }, namespace='/')
        except Exception:
            pass
        return jsonify(res)
    except Exception as e:
        return jsonify({'success': False, 'response': str(e)}), 500
