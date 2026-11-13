"""
Intent Executor
Executes individual intents with context awareness and verification.
Extracted from TaskChainOrchestrator to be shared by both orchestration systems.
"""

import asyncio
import concurrent.futures
import logging
import time
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


_agent_coordinator = None


def _run_async_coro(coro, timeout: float = 120.0):
    """Run an async coroutine safely from sync code, even inside a running event loop."""
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result(timeout=timeout)
    except RuntimeError:
        return asyncio.run(coro)


def _get_multi_agent_coordinator():
    """Lazy-load shared MultiAgentCoordinator with registered agent definitions."""
    global _agent_coordinator
    if _agent_coordinator is not None:
        return _agent_coordinator
    try:
        import ai_assistant.core.multi_agent_coordinator as mac_mod
        getter = getattr(mac_mod, "get_multi_agent_coordinator", None)
        if callable(getter):
            _agent_coordinator = getter()
            return _agent_coordinator

        from ai_assistant.agents.registry import AgentRegistry
        from ai_assistant.agents.loader import AgentLoader
        registry = AgentRegistry()
        AgentLoader.register_agent_definitions(registry)
        _agent_coordinator = mac_mod.MultiAgentCoordinator(registry)
        return _agent_coordinator
    except Exception as exc:
        logger.warning(f"MultiAgentCoordinator unavailable in IntentExecutor: {exc}")
        return None


def _is_gemini_active_and_configured() -> bool:
    """Only allow cloud Gemini VLM calls when active provider is Gemini and API key is configured."""
    try:
        import sys
        from pathlib import Path
        backend_dir = str(Path(__file__).resolve().parents[4] / 'backend')
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from settings_manager import get_provider, get_api_key
        return (get_provider() or "").lower() == "gemini" and bool(get_api_key("gemini"))
    except Exception:
        return bool(os.getenv("GEMINI_API_KEY"))


def _check_security_permission(getter_name: str, default: bool = True) -> bool:
    """Check runtime security permission flags from unified settings_manager."""
    try:
        try:
            import settings_manager
        except ImportError:
            import sys
            from pathlib import Path
            backend_dir = str(Path(__file__).resolve().parents[4] / 'backend')
            if backend_dir not in sys.path:
                sys.path.insert(0, backend_dir)
            import settings_manager
        getter = getattr(settings_manager, getter_name, None)
        if callable(getter):
            return bool(getter())
    except Exception:
        pass
    return default


def _normalize_app_target(app_name: str) -> str:
    """Normalize Hinglish/Devanagari app names using shared normalizer."""
    text = str(app_name or "").strip()
    try:
        from ai_assistant.core.local_command_normalizer import normalize_hinglish_devanagari
        text = normalize_hinglish_devanagari(text)
    except Exception:
        pass
    lowered = text.lower().strip()
    if lowered.endswith(" app") and lowered not in {"whatsapp", "cash app", "app store"}:
        text = text[:-4].strip()
    return text

# Lazy imports for automation modules
_app_controller = None
_file_automation = None
_system_automation = None
_whatsapp_automation = None
_taskbar_detector = None
_vlm = None
_visual_verifier = None


def _get_app_controller():
    global _app_controller
    if _app_controller is None:
        try:
            from ai_assistant.core.universal_app_controller import get_universal_controller
            _app_controller = get_universal_controller()
        except ImportError:
            logger.warning("⚠️ UniversalAppController not available")
    return _app_controller


def _get_file_automation():
    global _file_automation
    if _file_automation is None:
        try:
            from ai_assistant.automation.file_automation import FileAutomation
            _file_automation = FileAutomation()
        except ImportError:
            logger.warning("⚠️ FileAutomation not available")
    return _file_automation


def _get_system_automation():
    global _system_automation
    if _system_automation is None:
        try:
            from ai_assistant.automation.system_automation import SystemAutomation
            _system_automation = SystemAutomation()
        except ImportError:
            logger.warning("⚠️ SystemAutomation not available")
    return _system_automation


def _get_whatsapp_automation():
    global _whatsapp_automation
    if _whatsapp_automation is None:
        try:
            from ai_assistant.automation.app_automation import WhatsAppAutomation
            _whatsapp_automation = WhatsAppAutomation()
        except ImportError:
            pass
    return _whatsapp_automation


def _get_taskbar_detector():
    global _taskbar_detector
    if _taskbar_detector is None:
        try:
            from ai_assistant.automation.taskbar_detection import TaskbarDetector
            _taskbar_detector = TaskbarDetector()
        except ImportError:
            pass
    return _taskbar_detector


def _get_vlm():
    global _vlm
    if _vlm is None:
        try:
            from ai_assistant.multimodal import MultiModalAI
            _vlm = MultiModalAI()
        except ImportError:
            pass
    return _vlm


def _get_visual_verifier():
    global _visual_verifier
    if _visual_verifier is None:
        try:
            from ai_assistant.automation.visual_verification import get_visual_verifier
            _visual_verifier = get_visual_verifier()
        except ImportError:
            pass
    return _visual_verifier


class IntentExecutor:
    """
    Executes individual intents with context awareness and verification.
    
    Extracted from TaskChainOrchestrator so both the sync orchestrator
    and the async ChainOfActionsManager can share the same execution logic.
    """
    
    def __init__(self):
        """Initialize with lazy-loaded components"""
        self._handlers = {
            'open_app': self._open_app,
            'launch_app': self._open_app,
            'close_app': self._close_app,
            'send_message': self._send_message,
            'type_text': self._type_text,
            'find_file': self._find_file,
            'open_folder': self._open_folder,
            'open_explorer': self._open_folder,
            'setup_project': self._setup_project,
            'start_meeting': self._handle_meeting,
            'stop_meeting': self._handle_meeting,
            'meeting_recorder': self._handle_meeting,
            'read_email': self._handle_email,
            'read_gmail': self._handle_email,
            'move_file': self._move_file,
            'set_brightness': self._set_brightness,
            'brightness_control': self._set_brightness,
            'dark_mode_toggle': self._toggle_dark_mode,
            'toggle_wifi': self._toggle_wifi,
            'wifi_toggle': self._toggle_wifi,
            'bluetooth_toggle': self._toggle_bluetooth,
            'volume_control': self._volume_control,
            'battery_status': self._battery_status,
            'list_running_apps': self._list_running_apps,
            'open_settings': self._open_settings,
            'youtube_search': self._youtube_search,
            'youtube_history': self._youtube_history,
            'search_web': self._search_web,
            'play_media': self._play_media,
            'media_control': self._media_control,
            'analyze_screen': self._analyze_screen,
            'system_control': self._system_control,
            'send_file': self._send_file,
            'check_taskbar': self._check_taskbar,
            'play_video': self._play_video,
            'skip_time': self._skip_time,
            'create_document': self._create_document,
            'create_folder': self._create_folder,
            'download_media': self._download_media,
            'wait': self._wait,
            'say': self._say,
            'notify': self._say,
            'agent_task': self._agent_task_handler,
            'agent_productivity': self._agent_task_handler,
            'agent_research': self._agent_task_handler,
            'agent_deep_research': self._agent_task_handler,
            'agent_writer': self._agent_task_handler,
            'agent_video': self._agent_task_handler,
            'agent_creative': self._agent_task_handler,
            'agent_data': self._agent_task_handler,
            'agent_database': self._agent_task_handler,
            'agent_communication': self._agent_task_handler,
            'agent_web': self._agent_task_handler,
            'agent_student': self._agent_task_handler,
            'agent_file': self._agent_task_handler,
            'agent_audio': self._agent_task_handler,
            'agent_autonomous': self._agent_task_handler,
        }
        logger.info("IntentExecutor initialized")

    @property
    def supported_intents(self):
        return list(self._handlers.keys())

    def execute(self, intent: str, params: Dict[str, Any],
                context_manager=None) -> Dict[str, Any]:
        """
        Execute a single intent.

        Args:
            intent: Intent name (e.g. 'open_app', 'send_message', 'agent_research')
            params: Parameters for the intent
            context_manager: Optional ContextManager for parameter inference

        Returns:
            Dict with 'success', 'intent', 'result'/'error' keys
        """
        logger.debug(f"Executing intent: {intent} with params: {params}")

        try:
            params = dict(params or {})
            if context_manager and hasattr(context_manager, 'infer_missing_params'):
                params = context_manager.infer_missing_params(intent, params)

            handler = self._handlers.get(intent)
            if handler:
                if intent == 'agent_task' or intent.startswith('agent_'):
                    return self._execute_agent_task(intent, params, context_manager)
                return handler(params, context_manager)
            elif params.get('execution_target') == 'agent' or params.get('agent_id') or params.get('capability'):
                return self._execute_agent_task(intent, params, context_manager)
            else:
                logger.warning(f"Unknown intent: {intent}")
                return {
                    'success': False,
                    'intent': intent,
                    'error': f"Unknown intent: {intent}",
                    'no_retry': True,
                }
        except Exception as e:
            logger.error(f"Intent execution failed: {e}", exc_info=True)
            return {
                'success': False,
                'intent': intent,
                'error': str(e)
            }
    
    PROMPT_TEMPLATES = {
        'open_app': "Is the application '{app_name}' currently open and visible on the screen?",
        'open_folder_in_app': "Is the application '{app_name}' open and is the folder or workspace '{folder}' visible inside it?",
        'send_message': "Is there a chat or messaging window open for '{contact}' and is the message '{message}' visible?",
        'find_file': "Do you see a file named '{filename}' or a search result indicating it was found?",
        'default': "I just tried to perform this action: '{intent}' with params {params}. Please verify if it looks successful."
    }
    
    def verify(self, intent: str, result: Dict, params: Dict) -> bool:
        """
        Verify that an intent was ACTUALLY successful using 3-layer check:
        1. Code Return (already checked by caller)
        2. System State (os.exists, process list, window titles)
        3. Visual VLM (optional, using dynamic templates)
        """
        logger.info(f"🕵️ Verifying intent: {intent}")
        
        # 1. System State Verification
        if intent in ['find_file', 'open_folder', 'move_file']:
            path = result.get('result')
            if intent == 'move_file':
                return True  # shutil is reliable
            if isinstance(path, str) and (':' in path or '/' in path):
                exists = os.path.exists(path)
                logger.info(f"   State Check (File): {'✅' if exists else '❌'} ({path})")
                return exists
        
        elif intent == 'check_taskbar':
            return True
        
        elif intent in ['open_app', 'launch_app']:
            app_name = params.get('app_name') or params.get('target') or params.get('name')
            app_norm = _normalize_app_target(app_name).lower() if app_name else ""

            res_payload = result.get('result')
            if isinstance(res_payload, dict):
                raw_msg = str(res_payload.get('raw_result') or res_payload.get('message') or '')
            else:
                raw_msg = str(res_payload or '')

            known_web_apps = {
                'youtube music', 'yt music', 'ytmusic', 'youtube', 'gmail',
                'google drive', 'google docs', 'google sheets', 'google maps',
                'chatgpt', 'claude', 'perplexity', 'netflix', 'prime video',
                'hotstar', 'amazon', 'flipkart', 'github', 'stackoverflow',
                'linkedin', 'reddit', 'twitter', 'x', 'instagram', 'facebook',
                'canva', 'figma', 'notion', 'whatsapp web',
            }
            if (
                (isinstance(res_payload, dict) and res_payload.get('profile'))
                or any(marker in raw_msg for marker in (
                    'Opened Web App',
                    'Opened Web/Windows App',
                    'Opened Windows App Protocol',
                ))
                or app_norm in known_web_apps
                or app_norm.startswith(('http://', 'https://', 'www.'))
                or app_norm in {'settings', 'windows settings', 'whatsapp', 'calculator', 'calc', 'spotify'}
            ):
                logger.info(f"   State Check (Web/Protocol App): ✅ ({app_name})")
                return True

            # Optional keyword to look for in the window title (e.g. folder, profile, contact)
            expected_title_keyword = params.get('folder') or params.get('profile') or params.get('contact')
            
            detector = _get_taskbar_detector()
            if app_name and detector:
                time.sleep(1)
                scan = detector.find_specific_app_in_taskbar(app_norm or app_name, expected_title_keyword)
                
                # We check the unified success flag which accounts for window titles
                is_successful = scan.get('is_successful', False)
                logger.info(f"   State Check (Process/Title): {'✅' if is_successful else '❌'} ({app_name}, keyword: {expected_title_keyword})")
                
                # If OS level check passes, we don't need VLM!
                if is_successful:
                    return True
        
        elif intent in ['create_document', 'create_folder']:
            out_path = result.get('output_path') or result.get('result')
            if isinstance(out_path, str) and (':' in out_path or '/' in out_path or '\\' in out_path):
                exists = os.path.exists(out_path)
                logger.info(f"   State Check (Artifact): {'✅' if exists else '❌'} ({out_path})")
                return exists
            return bool(result.get('success', False))

        elif intent in [
            'set_brightness', 'brightness_control', 'dark_mode_toggle',
            'set_volume', 'volume_control',
            'toggle_wifi', 'wifi_toggle', 'bluetooth_toggle',
            'battery_status', 'list_running_apps', 'open_settings',
            'youtube_search', 'youtube_history', 'search_web',
            'play_media', 'media_control', 'system_control', 'close_app', 'analyze_screen',
            'send_message', 'type_text', 'send_file', 'play_video', 'skip_time',
            'download_media', 'wait', 'say', 'notify', 'agent_task',
        ] or intent.startswith('agent_'):
            out_path = result.get('output_path')
            if isinstance(out_path, str) and (':' in out_path or '/' in out_path or '\\' in out_path):
                if os.path.exists(out_path):
                    return True
            return bool(result.get('success', False))

        # 2. VLM Verification fallback for failed OS app launches (ONLY when Gemini is active & configured;
        # never force VLM retry on send_message to prevent duplicate sends)
        vlm = _get_vlm()
        use_vlm = (intent in ['open_app', 'launch_app']) and _is_gemini_active_and_configured()
        
        if use_vlm and vlm:
            logger.info("   👁️ Running Visual Verification (VLM Fallback)...")
            try:
                # Select the right dynamic template
                if intent in ['open_app', 'launch_app'] and params.get('folder'):
                    template_name = 'open_folder_in_app'
                elif intent in self.PROMPT_TEMPLATES:
                    template_name = intent
                else:
                    template_name = 'default'
                    
                # Format the dynamic prompt safely
                raw_template = self.PROMPT_TEMPLATES.get(template_name, self.PROMPT_TEMPLATES['default'])
                
                # Safely format using kwargs, falling back to string rep of params if missing
                try:
                    # Prepare safe formatting dict
                    format_dict = {
                        'app_name': params.get('app_name', params.get('name', 'Unknown App')),
                        'folder': params.get('folder', 'Unknown Folder'),
                        'contact': params.get('contact', 'Unknown Contact'),
                        'message': params.get('message', ''),
                        'filename': params.get('file_name', params.get('name', 'Unknown File')),
                        'intent': intent,
                        'params': params
                    }
                    prompt = raw_template.format(**format_dict)
                except Exception as format_err:
                    logger.warning(f"Template formatting failed: {format_err}, using default")
                    prompt = self.PROMPT_TEMPLATES['default'].format(intent=intent, params=params)
                
                prompt += "\nRead the text on the screen carefully. Return 'YES' if successful, 'NO' if failed."
                
                analysis = vlm.analyze_screen(prompt=prompt)
                is_success = "YES" in str(analysis.get('analysis', '')).upper()
                logger.info(f"   VLM Verdict: {'✅' if is_success else '❌'}")
                return is_success
            except Exception as e:
                logger.warning(f"   VLM Verification failed: {e}")
                return True  # Fallback to trusting code result
        
        # Default: Trust the method's return code
        return True
    
    # ===== Intent Handlers =====
    
    def _open_app(self, params: Dict, ctx=None) -> Dict:
        """Open an application dynamically with support for browser profiles, protocols, and discovery"""
        if not _check_security_permission('is_app_execution_allowed', True):
            return {'success': False, 'intent': 'open_app', 'error': 'Application execution is disabled by Security -> Permissions settings.'}
        import os, re, subprocess
        from ai_assistant.automation.browser_profiles import (
            launch_browser_profile,
            resolve_chrome_profile,
            extract_profile_from_text
        )
        from ai_assistant.automation.window_manager import bring_window_to_foreground
        from ai_assistant.automation.app_discovery import app_discovery, smart_open_application

        raw_app_name = params.get('app_name') or params.get('target') or params.get('app') or params.get('name')
        if not raw_app_name:
            return {'success': False, 'intent': 'open_app', 'error': 'No app name provided'}

        app_name = _normalize_app_target(raw_app_name)
        app_lower = app_name.lower().strip()
        
        # 0. Check if there is a pending project setup waiting for an IDE selection
        if ctx and ctx.get_var('pending_project_setup'):
            if app_lower in ('antigravity', 'vscode', 'vs code', 'code', 'both', 'dono'):
                return self._setup_project({'ide': app_lower}, ctx=ctx)
        
        # 1. Check for browser profile launches (e.g. 'chrome rancho', 'Rancho', 'rancho profile', 'open rancho')
        target_profile = params.get('profile') or params.get('browser_profile')
        if not target_profile:
            if app_lower not in ['chrome', 'google chrome', 'browser', 'web browser']:
                extracted, _ = extract_profile_from_text(app_name)
                target_profile = extracted or resolve_chrome_profile(app_name)
            elif any(b in app_lower for b in ['chrome', 'browser', 'google chrome']):
                extracted, _ = extract_profile_from_text(app_name)
                target_profile = extracted

        if target_profile:
            resolved_dir = resolve_chrome_profile(target_profile)
            if resolved_dir:
                try:
                    ok = launch_browser_profile('chrome', profile_query=resolved_dir)
                    if ok:
                        bring_window_to_foreground('chrome')
                        from ai_assistant.automation.browser_profiles import get_chrome_profiles
                        p_info = get_chrome_profiles().get(resolved_dir, {})
                        p_email = p_info.get('email', '')
                        clean_label = re.sub(
                            r'\b(mere|meri|mera|ki|ka|ke|chrome|profile|open|kholo)\b', '', str(target_profile), flags=re.IGNORECASE
                        ).strip()
                        profile_label = (clean_label or str(target_profile)).title()
                        if p_email:
                            profile_label = f"{profile_label} ({p_email})"
                        msg = f"Opened Chrome with profile {profile_label}"
                        if ctx:
                            ctx.set_var('current_app', 'chrome')
                            ctx.set_var('current_browser_profile', resolved_dir)
                            ctx.set_var('last_action', 'opened_app')
                        return {
                            'success': True,
                            'intent': 'open_app',
                            'result': {'success': True, 'message': msg, 'profile': resolved_dir}
                        }
                except Exception as e:
                    logger.error(f"Failed to launch Chrome profile: {e}")

        # 2. Check protocol schemes directly (like 'whatsapp:', 'calculator:', 'spotify:', 'ms-settings:')
        protocol_schemes = {
            'whatsapp': 'whatsapp:',
            'calculator': 'calculator:',
            'calc': 'calculator:',
            'spotify': 'spotify:',
            'settings': 'ms-settings:',
            'windows settings': 'ms-settings:',
            'clock': 'ms-clock:',
            'edge': 'microsoft-edge:'
        }
        target_proto = protocol_schemes.get(app_lower)
        if not target_proto and (app_lower.endswith(':') and re.fullmatch(r'[A-Za-z][A-Za-z0-9+.-]*:', app_lower)):
            target_proto = app_lower

        if target_proto:
            try:
                if hasattr(os, 'startfile'):
                    os.startfile(target_proto)
                bring_window_to_foreground(app_name)
                msg = f"Successfully opened {app_name.title()}"
                if ctx:
                    ctx.set_var('current_app', app_lower)
                    ctx.set_var('last_action', 'opened_app')
                return {'success': True, 'intent': 'open_app', 'result': {'success': True, 'message': msg}}
            except Exception as e:
                logger.warning(f"Protocol launch failed for {target_proto}: {e}")

        # 3. Generic Chrome launch without a specific profile mentioned
        if app_lower in ['chrome', 'google chrome', 'browser']:
            try:
                active_prof = ctx.get_var('current_browser_profile') if ctx else None
                ok = launch_browser_profile('chrome', profile_query=active_prof)
                if ok:
                    bring_window_to_foreground('chrome')
                    msg = "Successfully opened Chrome" + (f" with profile {active_prof}" if active_prof else "")
                    if ctx:
                        ctx.set_var('current_app', 'chrome')
                        ctx.set_var('last_action', 'opened_app')
                    return {'success': True, 'intent': 'open_app', 'result': {'success': True, 'message': msg}}
            except Exception as e:
                logger.warning(f"Generic Chrome launch failed: {e}")

        # 4. Dynamic application launch via UniversalAppController & dynamic AppDiscovery
        controller = _get_app_controller()
        if controller:
            result = controller.open_app(app_name)
            if result.get('success'):
                bring_window_to_foreground(result.get('hwnd') or app_name)
                if ctx:
                    ctx.set_var('current_app', app_name.lower())
                    ctx.set_var('last_action', 'opened_app')
                return {'success': True, 'intent': 'open_app', 'result': result}

        # 5. Fallback directly to smart_open_application
        launch_msg = smart_open_application(app_name)
        bring_window_to_foreground(app_name)
        success = "✅" in launch_msg or "Opened" in launch_msg
        if ctx and success:
            ctx.set_var('current_app', app_name.lower())
            ctx.set_var('last_action', 'opened_app')
        
        return {
            'success': success,
            'intent': 'open_app',
            'result': {'success': success, 'message': launch_msg}
        }

    def _close_app(self, params: Dict, ctx=None) -> Dict:
        """Close an application gracefully by process name or window title"""
        if not _check_security_permission('is_app_execution_allowed', True):
            return {'success': False, 'intent': 'close_app', 'error': 'Application execution is disabled by Security -> Permissions settings.'}
        raw_app_name = params.get('app_name') or params.get('target') or params.get('app') or params.get('name')
        if not raw_app_name:
            return {'success': False, 'intent': 'close_app', 'error': 'No app name provided'}
        app_name = _normalize_app_target(raw_app_name)
        try:
            # 1. Try UniversalAppController to update active tracking and gracefully close
            controller = _get_app_controller()
            if controller:
                res = controller.close_app(app_name)
                if res.get('success'):
                    if ctx:
                        ctx.set_var('last_action', 'closed_app')
                    return {'success': True, 'intent': 'close_app', 'result': f"Closed {app_name}"}

            # 2. Try AppAutomation graceful close
            from ai_assistant.automation.app_automation import AppAutomation
            auto = AppAutomation()
            success = auto.close_app(app_name)
            if ctx and success:
                ctx.set_var('last_action', 'closed_app')
            return {
                'success': success,
                'intent': 'close_app',
                'result': f"Closed {app_name}" if success else f"Could not close {app_name}"
            }
        except Exception as e:
            return {'success': False, 'intent': 'close_app', 'error': str(e)}
    
    def _send_message(self, params: Dict, ctx=None) -> Dict:
        """Send a message via an app"""
        app_name = params.get('app_name', ctx.get_var('current_app', 'WhatsApp') if ctx else 'WhatsApp')
        contact = params.get('contact')
        message = params.get('message', '')
        
        if not contact:
            return {'success': False, 'intent': 'send_message', 'error': 'No contact specified'}
        
        controller = _get_app_controller()
        if not controller:
            return {'success': False, 'intent': 'send_message', 'error': 'App controller not available'}
        
        result = controller.execute_action(app_name, 'send_message', {
            'contact': contact, 'message': message
        })
        
        if ctx and result.get('success'):
            ctx.set_var('selected_contact', contact)
            ctx.set_var('last_message', message)
            ctx.set_var('last_action', 'sent_message')
        
        return {'success': result.get('success', False), 'intent': 'send_message', 'result': result}
    
    def _type_text(self, params: Dict, ctx=None) -> Dict:
        """Type text in current app"""
        app_name = params.get('app_name', ctx.get_var('current_app') if ctx else None)
        text = params.get('text', '')
        
        if not app_name:
            return {'success': False, 'intent': 'type_text', 'error': 'No app specified and no current app in context'}
        
        controller = _get_app_controller()
        if not controller:
            return {'success': False, 'intent': 'type_text', 'error': 'App controller not available'}
        
        result = controller.execute_action(app_name, 'type_text', {'text': text})
        return {'success': result.get('success', False), 'intent': 'type_text', 'result': result}
    
    def _find_file(self, params: Dict, ctx=None) -> Dict:
        """Find a file or directory"""
        filename = params.get('file_name') or params.get('name')
        location = params.get('location')
        
        if not filename:
            return {'success': False, 'intent': 'find_file', 'error': 'No file name provided'}
        
        file_auto = _get_file_automation()
        if not file_auto:
            return {'success': False, 'intent': 'find_file', 'error': 'File automation not available'}
        
        path = file_auto.find_file(filename, location)
        if not path and hasattr(file_auto, 'resolve_folder_path'):
            search_expr = f"{filename} in {location}" if location else filename
            resolved = file_auto.resolve_folder_path(search_expr)
            if resolved and os.path.exists(resolved):
                path = resolved

        if path:
            contents = []
            if os.path.isdir(path) and hasattr(file_auto, 'list_folder_contents'):
                contents = file_auto.list_folder_contents(path)
            if ctx:
                ctx.set_var('found_file_path', path)
                ctx.set_var('last_file', path)
                if contents:
                    ctx.set_var('folder_contents', contents)
            res_msg = f"Found {path}"
            if contents:
                res_msg += f" with contents: {', '.join(contents[:10])}"
            return {'success': True, 'intent': 'find_file', 'result': res_msg, 'path': path, 'contents': contents}
        else:
            return {'success': False, 'intent': 'find_file', 'error': f'File or folder not found: {filename}'}
    
    def _open_folder(self, params: Dict, ctx=None) -> Dict:
        """Open a folder in explorer and record folder context / contents"""
        path = params.get('path') or params.get('folder')
        if not path and ctx:
            path = ctx.get_var('found_file_path') or ctx.get_var('last_folder')
        
        file_auto = _get_file_automation()
        if not file_auto:
            return {'success': False, 'intent': 'open_folder', 'error': 'File automation not available'}
        
        resolved = file_auto.resolve_folder_path(path) if hasattr(file_auto, 'resolve_folder_path') else None
        target_to_open = resolved or path
        
        success = file_auto.open_explorer(target_to_open)
        if success:
            contents = file_auto.list_folder_contents(target_to_open) if hasattr(file_auto, 'list_folder_contents') else []
            final_path = resolved or target_to_open
            if ctx:
                ctx.set_var('found_file_path', final_path)
                ctx.set_var('last_folder', final_path)
                if contents:
                    ctx.set_var('folder_contents', contents)
            res_msg = f"Opened folder {final_path}"
            if contents:
                res_msg += f" containing: {', '.join(contents[:10])}"
            return {
                'success': True,
                'intent': 'open_folder',
                'path': final_path,
                'contents': contents,
                'result': res_msg,
            }
        else:
            return {
                'success': False,
                'intent': 'open_folder',
                'error': f"Folder not found or could not be opened: {path}",
            }

    def _setup_project(self, params: Dict, ctx=None) -> Dict:
        """
        Setup or open a coding workspace in Antigravity or VS Code.
        Uses existing FileAutomation to resolve projects and launch workspaces.
        """
        project_name = (params.get('project_name') or params.get('query') or '').strip()
        ide_choice = (params.get('ide') or '').strip().lower()

        file_auto = _get_file_automation()
        if not file_auto:
            return {'success': False, 'intent': 'setup_project', 'error': 'File automation not available.'}

        # Check if this is a follow-up answer (e.g. user just said "antigravity" or "vscode" or "dono")
        if not project_name:
            if ctx:
                pending = ctx.get_var('pending_project_setup')
                if pending and isinstance(pending, dict) and pending.get('path'):
                    target_ide = ide_choice or params.get('raw_command', '').strip().lower() or 'antigravity'
                    res = file_auto.open_project(pending['path'], ide=target_ide)
                    ctx.set_var('pending_project_setup', None)
                    if res.get('success'):
                        opened_in = ' & '.join(res.get('launched', ['IDE']))
                        msg = f"Project `{pending['name']}` ko **{opened_in}** me open kar diya gaya hai (`{pending['path']}`)."
                        return {
                            'success': True,
                            'intent': 'setup_project',
                            'project_path': pending['path'],
                            'ide': target_ide,
                            'result': msg,
                            'message': msg
                        }
                    else:
                        return {'success': False, 'intent': 'setup_project', 'error': res.get('message', 'Failed to open project.')}
            # Fallback if no pending project: open the app directly
            if ide_choice:
                return self._open_app({'app_name': ide_choice}, ctx=ctx)
            return {'success': False, 'intent': 'setup_project', 'error': 'No project specified.'}

        matched = file_auto.find_project_path(project_name)
        if not matched:
            return {
                'success': False,
                'intent': 'setup_project',
                'error': f"Mujhe '{project_name}' naam ka koi project folder nahi mila.",
                'message': f"Mujhe '{project_name}' naam ka koi project folder nahi mila. Kya aap folder ka exact naam bata sakte hain?"
            }

        real_name, project_path = matched

        # If user explicitly specified the IDE in their command (e.g. "antigravity me ai assistant kholo")
        if ide_choice:
            res = file_auto.open_project(project_path, ide=ide_choice)
            if res.get('success'):
                opened_in = ' & '.join(res.get('launched', ['IDE']))
                msg = f"Project `{real_name}` ko **{opened_in}** me open kar diya gaya hai (`{project_path}`)."
                return {
                    'success': True,
                    'intent': 'setup_project',
                    'project_path': project_path,
                    'ide': ide_choice,
                    'result': msg,
                    'message': msg
                }
            else:
                return {'success': False, 'intent': 'setup_project', 'error': res.get('message', 'Failed to open project.')}

        # Interactive Dialog: ask user which IDE to open
        if ctx:
            ctx.set_var('pending_project_setup', {'name': real_name, 'path': project_path})

        prompt_msg = (
            f"Project mil gaya: `{real_name}` (`{project_path}`).\n"
            f"Ise kisme kholun — **Antigravity**, **VS Code**, ya **Dono**?"
        )
        return {
            'success': True,
            'intent': 'setup_project',
            'interactive': True,
            'project_name': real_name,
            'project_path': project_path,
            'result': prompt_msg,
            'message': prompt_msg,
            'options': ['Antigravity', 'VS Code', 'Dono']
        }

    def _handle_meeting(self, params: Dict, ctx=None) -> Dict:
        """Handle silent meeting recording and MoM generation."""
        action = str(params.get('action') or '').lower().strip()
        if not action:
            raw_q = str(params.get('query') or '').lower()
            if any(w in raw_q for w in ('stop', 'band', 'khatam', 'roko', 'end', 'mom', 'ओवर', 'खत्म', 'रोको')):
                action = 'stop'
            else:
                action = 'start'

        try:
            try:
                from voice_service import start_silent_meeting, stop_silent_meeting
            except ImportError:
                from backend.voice_service import start_silent_meeting, stop_silent_meeting

            if action == 'stop':
                res = stop_silent_meeting()
                return {
                    'success': res.get('success', False),
                    'intent': 'meeting_recorder',
                    'result': res.get('message') or res.get('mom'),
                    'mom': res.get('mom'),
                    'mom_file': res.get('mom_file'),
                }
            else:
                res = start_silent_meeting()
                return {
                    'success': res.get('success', True),
                    'intent': 'meeting_recorder',
                    'result': res.get('message'),
                }
        except Exception as e:
            logger.error(f"Meeting recorder execution error: {e}")
            return {
                'success': False,
                'intent': 'meeting_recorder',
                'error': f"मीटिंग रिकॉर्डर में त्रुटि: {e}",
            }

    def _handle_email(self, params: Dict, ctx=None) -> Dict:
        """Read and summarize unread emails or open Gmail inbox."""
        import webbrowser
        try:
            from ai_assistant.integrations.email_handler import read_emails, summarize_email, GmailManager
            mgr = GmailManager()
            if mgr.is_authenticated():
                emails = read_emails(max_results=5, unread_only=True)
                if isinstance(emails, list) and emails:
                    summary_lines = [f"📧 आपके पास {len(emails)} नए ईमेल्स हैं:"]
                    for em in emails:
                        summary_lines.append(f"- **{em.get('sender', 'Unknown')}**: {em.get('subject', 'No Subject')}")
                    full_res = "\n".join(summary_lines)
                    return {'success': True, 'intent': 'read_email', 'result': full_res}
                else:
                    return {'success': True, 'intent': 'read_email', 'result': "📧 आपके इनबॉक्स में कोई नया अनरीड ईमेल नहीं मिला।"}
            else:
                webbrowser.open("https://mail.google.com")
                return {
                    'success': True,
                    'intent': 'read_email',
                    'result': "मैंने आपका Gmail इनबॉक्स ब्राउज़र में खोल दिया है ताकि आप तुरंत ईमेल्स देख सकें।",
                }
        except Exception as e:
            webbrowser.open("https://mail.google.com")
            return {
                'success': True,
                'intent': 'read_email',
                'result': f"मैंने ब्राउज़र में Gmail खोल दिया है।",
            }
    
    def _move_file(self, params: Dict, ctx=None) -> Dict:
        """Move a file"""
        src = params.get('source') or (ctx.get_var('found_file_path') if ctx else None)
        dst = params.get('destination')
        
        if not src or not dst:
            return {'success': False, 'intent': 'move_file', 'error': 'Missing source or destination'}
        
        file_auto = _get_file_automation()
        if not file_auto:
            return {'success': False, 'intent': 'move_file', 'error': 'File automation not available'}
        
        success = file_auto.move_file(src, dst)
        return {'success': success, 'intent': 'move_file'}
    
    @staticmethod
    def _record_toggle_context(ctx, intent_name: str, state_val: bool):
        """Record latest hardware/theme toggle so bare follow-ups ('off कर दो') resolve accurately."""
        if ctx is None:
            try:
                from ai_assistant.core.conversation_context import get_context_manager
                ctx = get_context_manager()
            except Exception:
                ctx = None
        if ctx is not None:
            try:
                ctx.set_var('last_toggle_intent', intent_name)
                ctx.set_var('last_toggle_state', bool(state_val))
                ctx.set_var('last_toggle_ts', time.time())
            except Exception:
                pass

    def _set_brightness(self, params: Dict, ctx=None) -> Dict:
        """Check or adjust screen brightness (set/up/down/status)."""
        if not _check_security_permission('is_system_control_allowed', True):
            return {
                'success': False,
                'intent': 'set_brightness',
                'error': 'System control is disabled by Security -> Permissions settings.',
                'no_retry': True,
            }

        sys_auto = _get_system_automation()
        if not sys_auto:
            return {'success': False, 'intent': 'set_brightness', 'error': 'System automation not available', 'no_retry': True}

        action = str(params.get('action') or '').lower().strip()
        level_val = params.get('level')
        if not action:
            action = 'set' if level_val is not None else 'status'

        if action == 'status':
            cur = sys_auto.get_brightness()
            if cur >= 0:
                return {'success': True, 'intent': 'set_brightness', 'result': f"Screen brightness is currently at {cur}%."}
            msg = getattr(sys_auto, 'last_error', '') or "Could not read screen brightness (external monitor may not support WMI brightness control)."
            return {'success': False, 'intent': 'set_brightness', 'error': msg, 'result': msg, 'no_retry': True}

        if action in ('up', 'down'):
            delta = 15 if action == 'up' else -15
            ok, msg, _ = sys_auto.adjust_brightness_with_status(delta)
            res = {'success': ok, 'intent': 'set_brightness', 'result': msg}
            if not ok:
                res['error'] = msg
                res['no_retry'] = True
            return res

        try:
            level = max(0, min(100, int(str(level_val if level_val is not None else 50).replace('%', '').strip())))
        except (ValueError, TypeError):
            return {'success': False, 'intent': 'set_brightness', 'error': f"Invalid brightness level: {level_val}", 'no_retry': True}

        ok, msg = sys_auto.set_brightness_with_status(level)
        res = {'success': ok, 'intent': 'set_brightness', 'result': msg}
        if not ok:
            res['error'] = msg
            res['no_retry'] = True
        return res

    def _toggle_dark_mode(self, params: Dict, ctx=None) -> Dict:
        """Toggle Windows Dark Mode / Light Mode."""
        if not _check_security_permission('is_system_control_allowed', True):
            return {
                'success': False,
                'intent': 'dark_mode_toggle',
                'error': 'System control is disabled by Security -> Permissions settings.',
                'no_retry': True,
            }

        if 'enable' in params and params['enable'] is not None:
            enable = bool(params['enable'])
        else:
            action = str(params.get('action', 'on')).lower()
            enable = action in ['on', 'enable', 'dark', 'chalu', 'start']

        sys_auto = _get_system_automation()
        if not sys_auto:
            return {'success': False, 'intent': 'dark_mode_toggle', 'error': 'System automation not available', 'no_retry': True}

        ok, msg = sys_auto.toggle_dark_mode(enable)
        if ok:
            self._record_toggle_context(ctx, 'dark_mode_toggle', enable)
            return {'success': True, 'intent': 'dark_mode_toggle', 'result': msg}
        return {'success': False, 'intent': 'dark_mode_toggle', 'error': msg, 'result': msg, 'no_retry': True}

    def _toggle_wifi(self, params: Dict, ctx=None) -> Dict:
        """Toggle WiFi on/off via non-admin WinRT Radio API."""
        if not _check_security_permission('is_system_control_allowed', True):
            return {
                'success': False,
                'intent': 'wifi_toggle',
                'error': 'System control is disabled by Security -> Permissions settings.',
                'no_retry': True,
            }
        if 'enable' in params and params['enable'] is not None:
            enable = bool(params['enable'])
        else:
            action = str(params.get('action', 'on')).lower()
            enable = action in ['on', 'enable', 'start', 'chalu', 'chalao']

        sys_auto = _get_system_automation()
        if not sys_auto:
            return {'success': False, 'intent': 'wifi_toggle', 'error': 'System automation not available', 'no_retry': True}

        if hasattr(sys_auto, 'toggle_wifi_with_status'):
            success, msg = sys_auto.toggle_wifi_with_status(enable)
        else:
            success = sys_auto.toggle_wifi(enable)
            state_str = "on" if enable else "off"
            msg = f"Wi-Fi turned {state_str}." if success else (getattr(sys_auto, 'last_error', '') or f"Could not turn Wi-Fi {state_str}.")

        if success:
            self._record_toggle_context(ctx, 'wifi_toggle', enable)
            return {'success': True, 'intent': 'wifi_toggle', 'result': msg}
        return {'success': False, 'intent': 'wifi_toggle', 'error': msg, 'result': msg, 'no_retry': True}

    def _toggle_bluetooth(self, params: Dict, ctx=None) -> Dict:
        """Toggle Bluetooth on/off via non-admin WinRT Radio API."""
        if not _check_security_permission('is_system_control_allowed', True):
            return {
                'success': False,
                'intent': 'bluetooth_toggle',
                'error': 'System control is disabled by Security -> Permissions settings.',
                'no_retry': True,
            }
        if 'enable' in params and params['enable'] is not None:
            enable = bool(params['enable'])
        else:
            action = str(params.get('action', 'on')).lower()
            enable = action in ['on', 'enable', 'start', 'chalu', 'chalao']

        sys_auto = _get_system_automation()
        if not sys_auto:
            return {'success': False, 'intent': 'bluetooth_toggle', 'error': 'System automation not available', 'no_retry': True}

        if hasattr(sys_auto, 'toggle_bluetooth_with_status'):
            success, msg = sys_auto.toggle_bluetooth_with_status(enable)
        else:
            success = sys_auto.toggle_bluetooth(enable)
            state_str = "on" if enable else "off"
            msg = f"Bluetooth turned {state_str}." if success else (getattr(sys_auto, 'last_error', '') or f"Could not turn Bluetooth {state_str}.")

        if success:
            self._record_toggle_context(ctx, 'bluetooth_toggle', enable)
            return {'success': True, 'intent': 'bluetooth_toggle', 'result': msg}
        return {'success': False, 'intent': 'bluetooth_toggle', 'error': msg, 'result': msg, 'no_retry': True}

    def _volume_control(self, params: Dict, ctx=None) -> Dict:
        """Control system volume (up, down, mute, unmute, set, status)."""
        if not _check_security_permission('is_system_control_allowed', True):
            return {
                'success': False,
                'intent': 'volume_control',
                'error': 'System control is disabled by Security -> Permissions settings.',
                'no_retry': True,
            }
        action = str(params.get('action', 'up')).lower().strip()
        level = params.get('level')
        try:
            from ai_assistant.core.core import (
                get_system_volume,
                set_system_volume,
                volume_up,
                volume_down,
                mute_volume,
                unmute_volume,
            )
            if action in ('status', 'get', 'check', 'query'):
                msg = get_system_volume()
            elif action == 'set' or (level is not None and action not in ('up', 'down', 'mute', 'unmute')):
                lvl = max(0, min(100, int(str(level).replace('%', '').strip()))) if level is not None else 50
                msg = set_system_volume(lvl)
            elif action in ('up', 'increase', 'raise', 'turn up', 'zyada', 'jyada', 'badha', 'badhao', 'tez'):
                msg = volume_up(int(params.get('increment', 10) or 10))
            elif action in ('down', 'decrease', 'lower', 'turn down', 'kam', 'dhima', 'dhimi'):
                msg = volume_down(int(params.get('decrement', 10) or 10))
            elif action in ('mute', 'band', 'off'):
                msg = mute_volume()
            elif action in ('unmute', 'on'):
                msg = unmute_volume()
            else:
                return {'success': False, 'intent': 'volume_control', 'error': f'Unsupported volume action: {action}', 'no_retry': True}

            success = not str(msg).startswith(('❌', 'Error'))
            res = {'success': success, 'intent': 'volume_control', 'result': msg}
            if not success:
                res['error'] = msg
                res['no_retry'] = True
            return res
        except Exception as e:
            return {'success': False, 'intent': 'volume_control', 'error': str(e), 'no_retry': True}

    def _battery_status(self, params: Dict, ctx=None) -> Dict:
        """Get system battery status"""
        try:
            from ai_assistant.core.system import get_battery_status
            msg = get_battery_status()
            return {'success': not str(msg).startswith('Error'), 'intent': 'battery_status', 'result': msg}
        except Exception:
            sys_auto = _get_system_automation()
            if sys_auto:
                msg = sys_auto.get_battery_status()
                return {'success': True, 'intent': 'battery_status', 'result': msg}
            return {'success': False, 'intent': 'battery_status', 'error': 'Battery status unavailable'}

    def _list_running_apps(self, params: Dict, ctx=None) -> Dict:
        """List currently open taskbar GUI applications cleanly (with process fallback)."""
        try:
            detector = _get_taskbar_detector()
            if detector and hasattr(detector, 'format_taskbar_open_apps'):
                msg = detector.format_taskbar_open_apps()
                return {'success': True, 'intent': 'list_running_apps', 'result': msg}
            from ai_assistant.core.system import get_running_processes
            limit = int(params.get('limit', 12) or 12)
            msg = get_running_processes(limit=limit)
            return {'success': not str(msg).startswith('Error'), 'intent': 'list_running_apps', 'result': msg}
        except Exception as e:
            return {'success': False, 'intent': 'list_running_apps', 'error': str(e)}

    def _open_settings(self, params: Dict, ctx=None) -> Dict:
        """Open Windows Settings, Control Panel, or a specific ms-settings page."""
        if not _check_security_permission('is_system_control_allowed', True):
            return {
                'success': False,
                'intent': 'open_settings',
                'error': 'System control is disabled by Security -> Permissions settings.',
                'no_retry': True,
            }
        setting = str(params.get('setting') or '').lower().strip()
        page_map = {
            'wifi': 'network-wifi',
            'wi-fi': 'network-wifi',
            'wi fi': 'network-wifi',
            'bluetooth': 'bluetooth',
            'display': 'display',
            'screen': 'display',
            'sound': 'sound',
            'audio': 'sound',
            'volume': 'sound',
            'network': 'network-status',
            'hotspot': 'network-mobilehotspot',
            'mobile hotspot': 'network-mobilehotspot',
            'airplane': 'network-airplanemode',
            'airplane mode': 'network-airplanemode',
            'flight mode': 'network-airplanemode',
            'night light': 'nightlight',
            'battery': 'batterysaver',
            'power': 'powersleep',
            'personalization': 'personalization',
            'theme': 'personalization',
            'privacy': 'privacy',
            'security': 'windowsdefender',
            'update': 'windowsupdate',
            'windows update': 'windowsupdate',
            'storage': 'storagesense',
            'apps': 'appsfeatures',
            'accounts': 'yourinfo',
            'control panel': 'control-panel',
            'control': 'control-panel',
            'settings': '',
            'windows settings': '',
        }
        try:
            page = page_map.get(setting, setting) if setting else ''
            from ai_assistant.core.core import open_settings_page
            msg = open_settings_page(page)
            success = not str(msg).startswith(('❌', 'Error'))
            res = {'success': success, 'intent': 'open_settings', 'result': msg}
            if not success:
                res['error'] = msg
                res['no_retry'] = True
            return res
        except Exception as e:
            return {'success': False, 'intent': 'open_settings', 'error': str(e), 'no_retry': True}

    def _youtube_search(self, params: Dict, ctx=None) -> Dict:
        """Search YouTube in default browser"""
        if not _check_security_permission('is_web_browsing_allowed', True):
            return {'success': False, 'intent': 'youtube_search', 'error': 'Web browsing is disabled by Security -> Permissions settings.'}
        query = (params.get('query') or params.get('target') or '').strip()
        if not query:
            return {'success': False, 'intent': 'youtube_search', 'error': 'No search query provided'}
        try:
            from ai_assistant.core.core import search_youtube
            msg = search_youtube(query)
            if ctx:
                ctx.set_var('last_action', 'youtube_search')
                ctx.set_var('last_query', query)
            return {'success': not str(msg).startswith(('❌', 'Error')), 'intent': 'youtube_search', 'result': msg}
        except Exception as e:
            return {'success': False, 'intent': 'youtube_search', 'error': str(e)}

    def _youtube_history(self, params: Dict, ctx=None) -> Dict:
        """Open YouTube watch history in default browser"""
        if not _check_security_permission('is_web_browsing_allowed', True):
            return {'success': False, 'intent': 'youtube_history', 'error': 'Web browsing is disabled by Security -> Permissions settings.'}
        url = "https://www.youtube.com/feed/history"
        try:
            import webbrowser
            if hasattr(os, 'startfile'):
                try:
                    os.startfile(url)
                except Exception:
                    webbrowser.open(url)
            else:
                webbrowser.open(url)
            return {'success': True, 'intent': 'youtube_history', 'result': 'Opened YouTube watch history'}
        except Exception as e:
            return {'success': False, 'intent': 'youtube_history', 'error': str(e)}

    def _search_web(self, params: Dict, ctx=None) -> Dict:
        """Search Google/web in the browser"""
        if not _check_security_permission('is_web_browsing_allowed', True):
            return {'success': False, 'intent': 'search_web', 'error': 'Web browsing is disabled by Security -> Permissions settings.'}
        query = (params.get('query') or params.get('target') or '').strip()
        _CORRECTION_PHRASES = ("galat", "wrong", "fake", "tmne galat", "tumne galat", "pehle wala")
        if any(w in query.lower() for w in _CORRECTION_PHRASES) or not query:
            if ctx and ctx.get_var('last_query'):
                query = ctx.get_var('last_query')
        if not query:
            return {'success': False, 'intent': 'search_web', 'error': 'No search query provided'}
        try:
            from ai_assistant.core.core import search_google
            msg = search_google(query)
            if ctx:
                ctx.set_var('last_action', 'search_web')
                ctx.set_var('last_query', query)
            return {'success': not str(msg).startswith(('❌', 'Error')), 'intent': 'search_web', 'result': msg}
        except Exception as e:
            return {'success': False, 'intent': 'search_web', 'error': str(e)}

    def _media_control(self, params: Dict, ctx=None) -> Dict:
        """Control media playback (play/pause, next track, previous track)."""
        action = str(params.get('action') or 'play_pause').strip().lower()
        action_map = {
            'pause': 'play_pause',
            'resume': 'play_pause',
            'play': 'play_pause',
            'play_pause': 'play_pause',
            'skip': 'next',
            'next': 'next',
            'prev': 'previous',
            'previous': 'previous',
        }
        mapped = action_map.get(action, 'play_pause')
        try:
            from ai_assistant.integrations.music import control_media_player
            msg = control_media_player(mapped)
            return {'success': not str(msg).startswith('❌'), 'intent': 'media_control', 'result': msg}
        except Exception as e:
            return {'success': False, 'intent': 'media_control', 'error': str(e)}

    def _play_media(self, params: Dict, ctx=None) -> Dict:
        """Play music/media locally via Spotify, YouTube Music, YouTube, or media keys."""
        import urllib.parse
        import webbrowser
        from pathlib import Path

        query = (params.get('query') or params.get('target') or '').strip()
        platform = str(params.get('platform') or '').lower().strip()
        q_lower = query.lower()

        try:
            from ai_assistant.integrations.music import (
                play_youtube_music,
                search_and_play_spotify,
                control_media_player,
            )

            if not query or q_lower in {
                'music', 'song', 'gaana', 'play', 'resume', 'pause',
                'pause song', 'pause music', 'pause video', 'pause playback',
                'resume song', 'resume music', 'resume playback',
                'stop music', 'stop song', 'gaana pause', 'gaana roko',
            }:
                msg = control_media_player('play_pause')
                return {'success': not msg.startswith('❌'), 'intent': 'play_media', 'result': msg}
            if q_lower in {
                'next', 'next song', 'next track', 'skip', 'skip song', 'skip track',
                'agla gaana', 'gaana skip',
            }:
                msg = control_media_player('next')
                return {'success': not msg.startswith('❌'), 'intent': 'play_media', 'result': msg}
            if q_lower in {
                'previous', 'previous song', 'previous track', 'prev', 'prev song',
                'last song', 'pichla gaana', 'pichhla gaana',
            }:
                msg = control_media_player('previous')
                return {'success': not msg.startswith('❌'), 'intent': 'play_media', 'result': msg}

            cleaned_query = query
            if 'on spotify' in q_lower:
                platform = 'spotify'
                cleaned_query = q_lower.replace('on spotify', '').strip() or query
            elif 'on youtube music' in q_lower:
                platform = 'youtube music'
                cleaned_query = q_lower.replace('on youtube music', '').strip() or query
            elif 'on youtube' in q_lower:
                platform = 'youtube'
                cleaned_query = q_lower.replace('on youtube', '').strip() or query

            if 'spotify' in platform:
                msg = search_and_play_spotify(cleaned_query)
                if not msg.startswith('❌'):
                    return {'success': True, 'intent': 'play_media', 'result': msg}

            if 'youtube music' in platform or 'ytmusic' in platform or 'yt music' in platform:
                msg = play_youtube_music(cleaned_query)
                if not msg.startswith(('❌', '🎵 YouTube Music')):
                    return {'success': True, 'intent': 'play_media', 'result': msg}
                url = f"https://music.youtube.com/search?q={urllib.parse.quote_plus(cleaned_query)}"
                webbrowser.open(url)
                return {'success': True, 'intent': 'play_media', 'result': f"Opened YouTube Music search for {cleaned_query}"}

            # Smart platform routing when caller didn't specify one
            is_video_intent = any(
                kw in q_lower for kw in ('video', 'trailer', 'tutorial', 'lecture', 'course', 'vlog', 'podcast', 'explained')
            )
            if not platform and not is_video_intent:
                spotify_ready = False
                try:
                    import psutil
                    if any((p.info.get('name') or '').lower() == 'spotify.exe' for p in psutil.process_iter(['name'])):
                        spotify_ready = (Path.home() / '.pulsar' / '.spotify_cache').exists() and bool(
                            os.environ.get('SPOTIFY_CLIENT_ID') and os.environ.get('SPOTIFY_CLIENT_SECRET')
                        )
                except Exception:
                    spotify_ready = False
                if spotify_ready:
                    sp_msg = search_and_play_spotify(cleaned_query)
                    if not sp_msg.startswith('❌'):
                        return {'success': True, 'intent': 'play_media', 'result': sp_msg}

            if not is_video_intent:
                msg = play_youtube_music(cleaned_query)
                if not msg.startswith(('❌', '🎵 YouTube Music')):
                    return {'success': True, 'intent': 'play_media', 'result': msg}

            from ai_assistant.core.core import search_youtube
            yt_msg = search_youtube(cleaned_query)
            return {'success': not str(yt_msg).startswith(('❌', 'Error')), 'intent': 'play_media', 'result': yt_msg}
        except Exception as e:
            return {'success': False, 'intent': 'play_media', 'error': str(e)}

    def _analyze_screen(self, params: Dict, ctx=None) -> Dict:
        """Analyze screen using VLM (strictly gated behind Gemini provider/key)"""
        if not _is_gemini_active_and_configured():
            return {
                'success': False,
                'intent': 'analyze_screen',
                'error': 'Screen visual analysis requires the Gemini provider with a configured GEMINI_API_KEY.',
            }
        vlm = _get_vlm()
        if not vlm:
            return {'success': False, 'intent': 'analyze_screen', 'error': 'Vision module not available'}
        try:
            question = params.get('question') or "Describe what's currently visible on my screen."
            res = vlm.analyze_screen(prompt=question)
            text = res.get('analysis', '') if isinstance(res, dict) else str(res)
            return {'success': bool(text), 'intent': 'analyze_screen', 'result': text}
        except Exception as e:
            return {'success': False, 'intent': 'analyze_screen', 'error': str(e)}

    def _system_control(self, params: Dict, ctx=None) -> Dict:
        """Execute system power actions (lock, sleep, shutdown, restart)"""
        if not _check_security_permission('is_system_control_allowed', True):
            return {'success': False, 'intent': 'system_control', 'error': 'System control is disabled by Security -> Permissions settings.'}
        import ctypes
        import subprocess
        action = str(params.get('action') or '').lower().strip()
        try:
            if action == 'lock':
                ctypes.windll.user32.LockWorkStation()
                return {'success': True, 'intent': 'system_control', 'result': 'Screen locked'}
            if action == 'sleep':
                subprocess.run(['rundll32.exe', 'powrprof.dll,SetSuspendState', '0,1,0'], check=False)
                return {'success': True, 'intent': 'system_control', 'result': 'Putting system to sleep'}
            if action == 'shutdown':
                subprocess.run(['shutdown', '/s', '/t', '10'], check=False)
                return {'success': True, 'intent': 'system_control', 'result': 'System will shut down in 10 seconds'}
            if action == 'restart':
                subprocess.run(['shutdown', '/r', '/t', '10'], check=False)
                return {'success': True, 'intent': 'system_control', 'result': 'System will restart in 10 seconds'}
            return {'success': False, 'intent': 'system_control', 'error': f'Unsupported system action: {action}'}
        except Exception as e:
            return {'success': False, 'intent': 'system_control', 'error': str(e)}
    
    def _send_file(self, params: Dict, ctx=None) -> Dict:
        """Send a file to a contact"""
        contact = params.get('contact')
        file_path = params.get('file')
        if not file_path and ctx:
            file_path = ctx.get_var('found_file_path') or ctx.get_var('last_file')
        message = params.get('message', 'Sent via AI Assistant')
        app = params.get('app', 'whatsapp').lower()
        
        if not contact or not file_path:
            return {'success': False, 'intent': 'send_file', 'error': 'Missing contact or file path'}
        
        if 'whatsapp' in app:
            wa = _get_whatsapp_automation()
            if wa:
                success = wa.send_with_attachment(contact, message, file_path)
                return {'success': success, 'intent': 'send_file'}
        
        return {'success': False, 'intent': 'send_file', 'error': f'Unsupported app: {app}'}
    
    def _check_taskbar(self, params: Dict, ctx=None) -> Dict:
        """Check taskbar for running apps"""
        app_name = params.get('app_name')
        detector = _get_taskbar_detector()
        
        if not detector:
            return {'success': False, 'intent': 'check_taskbar', 'error': 'Taskbar detection not available'}
        
        if app_name:
            result = detector.find_specific_app_in_taskbar(app_name)
            found = result.get('found_in_processes', False) or (
                result.get('visual_search_result', {}).get('found', False)
            )
            if ctx:
                ctx.set_var('last_taskbar_check', result)
            return {
                'success': True, 'intent': 'check_taskbar',
                'result': result,
                'message': f"Found {app_name}" if found else f"{app_name} not found"
            }
        else:
            if hasattr(detector, 'format_taskbar_open_apps'):
                msg = detector.format_taskbar_open_apps()
                info = detector.get_taskbar_open_apps()
                if ctx:
                    ctx.set_var('desktop_state', info)
                return {'success': True, 'intent': 'check_taskbar', 'result': msg, 'details': info}
            result = detector.get_complete_desktop_analysis()
            if ctx:
                ctx.set_var('desktop_state', result)
            return {'success': True, 'intent': 'check_taskbar', 'result': result}
    
    def _play_video(self, params: Dict, ctx=None) -> Dict:
        """Play a video"""
        app_name = params.get('app_name', 'YouTube')
        query = params.get('query', '')
        
        controller = _get_app_controller()
        if not controller:
            return {'success': False, 'intent': 'play_video', 'error': 'App controller not available'}
        
        result = controller.execute_action(app_name, 'play_video', {'query': query})
        return {'success': result.get('success', False), 'intent': 'play_video', 'result': result}
    
    def _skip_time(self, params: Dict, ctx=None) -> Dict:
        """Skip time in media player"""
        app_name = params.get('app_name', ctx.get_var('current_app', 'YouTube') if ctx else 'YouTube')
        minutes = params.get('minutes', 0)
        
        controller = _get_app_controller()
        if not controller:
            return {'success': False, 'intent': 'skip_time', 'error': 'App controller not available'}
        
        result = controller.execute_action(app_name, 'skip_time', {'minutes': minutes})
        return {'success': result.get('success', False), 'intent': 'skip_time', 'result': result}

    def _wait(self, params: Dict, ctx=None) -> Dict:
        """Wait for a requested duration in seconds inside a workflow."""
        try:
            seconds = max(0.0, min(60.0, float(params.get('seconds', 1.0))))
        except (TypeError, ValueError):
            seconds = 1.0
        time.sleep(seconds)
        msg = f"Waited {seconds:.2f}s" if seconds % 1 else f"Waited {int(seconds)}s"
        return {'success': True, 'intent': 'wait', 'result': msg, 'output': msg}

    def _say(self, params: Dict, ctx=None) -> Dict:
        """Produce a formatted message/announcement in a chain."""
        text = str(params.get('text') or params.get('message') or '').strip()
        return {'success': True, 'intent': 'say', 'result': text, 'output': text}

    def _create_folder(self, params: Dict, ctx=None) -> Dict:
        """Create a directory/folder safely on the filesystem."""
        if not _check_security_permission('is_file_operation_allowed', True):
            return {'success': False, 'intent': 'create_folder', 'error': 'File operations are disabled by Security -> Permissions settings.', 'no_retry': True}
        raw_name = str(params.get('name') or params.get('folder') or '').strip().strip('"\'')
        if not raw_name:
            return {'success': False, 'intent': 'create_folder', 'error': 'No folder name provided', 'no_retry': True}
        base_path = params.get('path')
        try:
            p = Path(raw_name).expanduser()
            if p.is_absolute():
                target = p
            elif base_path:
                target = Path(str(base_path).strip().strip('"\'')).expanduser() / raw_name
            else:
                target = Path.home() / "Documents" / raw_name
            target.mkdir(parents=True, exist_ok=True)
            resolved = str(target.resolve())
            if ctx:
                ctx.set_var('last_folder', resolved)
                ctx.set_var('found_file_path', resolved)
            return {
                'success': True,
                'intent': 'create_folder',
                'result': resolved,
                'output': resolved,
                'output_path': resolved,
            }
        except Exception as e:
            return {'success': False, 'intent': 'create_folder', 'error': str(e)}

    def _create_document(self, params: Dict, ctx=None) -> Dict:
        """Create a Word/PPT/PDF/Text document using ProductivityAgent or local file writers."""
        if not _check_security_permission('is_file_operation_allowed', True):
            return {'success': False, 'intent': 'create_document', 'error': 'File operations are disabled by Security -> Permissions settings.', 'no_retry': True}

        doc_type = str(params.get('doc_type') or 'document').lower().strip()
        title = str(params.get('title') or params.get('topic') or 'Pulsar_Document').strip()
        content = str(params.get('content') or params.get('text_body') or (ctx.get_var('last_output') if ctx else '') or f"# {title}\n").strip()

        # First attempt via ProductivityAgent / MultiAgentCoordinator if available
        coord = _get_multi_agent_coordinator()
        if coord is not None:
            agent_res = self._execute_agent_task(
                'agent_productivity',
                {
                    **params,
                    'agent_id': 'productivity-001',
                    'capability': 'create_powerpoint' if doc_type in ('ppt', 'pptx', 'powerpoint', 'presentation') else 'create_word_document',
                    'description': f"Create {doc_type} titled '{title}': {content[:500]}",
                    'title': title,
                    'content': content,
                },
                ctx,
            )
            if agent_res.get('success') and agent_res.get('output_path'):
                agent_res['intent'] = 'create_document'
                return agent_res

        # Deterministic local fallback writer
        try:
            ext_map = {
                'ppt': '.pptx',
                'pptx': '.pptx',
                'powerpoint': '.pptx',
                'presentation': '.pptx',
                'word': '.docx',
                'doc': '.docx',
                'docx': '.docx',
                'pdf': '.pdf',
                'document': '.txt',
            }
            ext = ext_map.get(doc_type, '.txt')
            safe_slug = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in title)[:60].strip('_') or 'document'
            explicit_out = params.get('output_path')
            if explicit_out:
                out_file = Path(str(explicit_out)).expanduser()
            else:
                out_dir = Path.home() / "Documents" / "Pulsar"
                out_dir.mkdir(parents=True, exist_ok=True)
                out_file = out_dir / f"{safe_slug}{ext}"

            out_file.parent.mkdir(parents=True, exist_ok=True)

            if ext == '.docx':
                try:
                    import docx
                    doc = docx.Document()
                    doc.add_heading(title, level=1)
                    for para in content.splitlines():
                        doc.add_paragraph(para)
                    doc.save(str(out_file))
                except ImportError:
                    out_file = out_file.with_suffix('.txt')
                    out_file.write_text(f"{title}\n\n{content}", encoding='utf-8')
            elif ext == '.pptx':
                try:
                    from pptx import Presentation
                    prs = Presentation()
                    slide = prs.slides.add_slide(prs.slide_layouts[0])
                    if slide.shapes.title:
                        slide.shapes.title.text = title
                    if len(slide.placeholders) > 1:
                        slide.placeholders[1].text = content[:500]
                    prs.save(str(out_file))
                except ImportError:
                    out_file = out_file.with_suffix('.txt')
                    out_file.write_text(f"{title}\n\n{content}", encoding='utf-8')
            else:
                out_file.write_text(f"{title}\n\n{content}", encoding='utf-8')

            resolved = str(out_file.resolve())
            if ctx:
                ctx.set_var('found_file_path', resolved)
                ctx.set_var('last_file', resolved)
            return {
                'success': True,
                'intent': 'create_document',
                'result': resolved,
                'output': f"Created document at {resolved}",
                'output_path': resolved,
            }
        except Exception as e:
            return {'success': False, 'intent': 'create_document', 'error': str(e)}

    def _download_media(self, params: Dict, ctx=None) -> Dict:
        """Download audio/video via youtube_ops integration when permitted."""
        if not _check_security_permission('is_web_browsing_allowed', True):
            return {'success': False, 'intent': 'download_media', 'error': 'Web browsing is disabled by Security -> Permissions settings.', 'no_retry': True}
        query = (params.get('query') or params.get('url') or '').strip()
        if not query:
            return {'success': False, 'intent': 'download_media', 'error': 'No query or URL provided', 'no_retry': True}
        try:
            from ai_assistant.integrations.youtube_ops import YouTubeDownloader
            dl = YouTubeDownloader()
            if hasattr(dl, 'download_audio') and 'audio' in str(params.get('text', '')).lower():
                res = dl.download_audio(query)
            elif hasattr(dl, 'download_video'):
                res = dl.download_video(query)
            else:
                return {'success': False, 'intent': 'download_media', 'error': 'YouTube downloader method unavailable', 'no_retry': True}
            ok = bool(res) and not str(res).startswith(('❌', 'Error'))
            return {'success': ok, 'intent': 'download_media', 'result': res, 'output': res}
        except Exception as e:
            return {'success': False, 'intent': 'download_media', 'error': str(e), 'no_retry': True}

    def _agent_task_handler(self, params: Dict, ctx=None) -> Dict:
        """Direct handler entry for agent_task (execute() preserves concrete agent_* intent name)."""
        return self._execute_agent_task(params.get('intent', 'agent_task'), params, ctx)

    def _execute_agent_task(self, intent: str, params: Dict, ctx=None) -> Dict:
        """
        Execute an intent via MultiAgentCoordinator & specialized BaseAgent registry.
        Compatible with both the upgraded `#12` `coordinator.execute_step(...)`
        and legacy `coordinator.execute_task(...)` / `registry.get_agent(...)`.
        """
        coord = _get_multi_agent_coordinator()
        if coord is None:
            return {
                'success': False,
                'intent': intent,
                'error': 'MultiAgentCoordinator is unavailable',
                'no_retry': True,
            }

        preferred_agent_id = params.get('agent_id')
        capability = params.get('capability')
        if intent and intent.startswith('agent_') and (not preferred_agent_id or not capability):
            try:
                from ai_assistant.ai.intent_router import AGENT_INTENT_METADATA
                if intent in AGENT_INTENT_METADATA:
                    meta_aid, meta_cap = AGENT_INTENT_METADATA[intent]
                    preferred_agent_id = preferred_agent_id or meta_aid
                    capability = capability or meta_cap
            except Exception:
                pass

        description = (
            params.get('description')
            or params.get('topic')
            or params.get('task')
            or params.get('prompt')
            or params.get('query')
            or params.get('text')
            or intent
        )

        chain_ctx = {}
        if ctx is not None:
            try:
                if hasattr(ctx, 'key_vars'):
                    chain_ctx.update(dict(ctx.key_vars))
                elif hasattr(ctx, 'get_summary'):
                    chain_ctx.update(ctx.get_summary().get('key_vars', {}))
            except Exception:
                pass

        try:
            if hasattr(coord, 'execute_step'):
                task_result = _run_async_coro(
                    coord.execute_step(
                        description=str(description),
                        params=params,
                        preferred_agent_id=preferred_agent_id,
                        capability=capability,
                        chain_context=chain_ctx,
                        chain_id=params.get('chain_id'),
                    )
                )
            else:
                from ai_assistant.agents.models import Task
                task = Task(
                    description=str(description),
                    params=dict(params),
                    target_agent_id=preferred_agent_id,
                    required_capabilities=[capability] if capability else [],
                    context=chain_ctx,
                    chain_id=params.get('chain_id'),
                )
                if preferred_agent_id and hasattr(coord, 'execute_agent'):
                    task_result = _run_async_coro(coord.execute_agent(preferred_agent_id, task))
                elif preferred_agent_id and getattr(coord, 'registry', None):
                    agent = coord.registry.get_agent(preferred_agent_id)
                    if agent is not None:
                        task_result = _run_async_coro(agent.execute(task))
                    else:
                        task_result = _run_async_coro(coord.execute_task(task))
                else:
                    task_result = _run_async_coro(coord.execute_task(task))

            ok = bool(getattr(task_result, 'success', False))
            data = dict(getattr(task_result, 'data', None) or {})
            out_path = getattr(task_result, 'output_path', None) or data.get('output_path')
            output_val = (
                data.get('output')
                or data.get('summary')
                or data.get('text')
                or data.get('message')
                or out_path
                or (data if data else None)
            )
            used_agent_id = getattr(task_result, 'agent_id', None) or preferred_agent_id
            err_val = getattr(task_result, 'error', None)

            if ctx is not None and ok:
                try:
                    if used_agent_id:
                        ctx.set_var('last_agent', used_agent_id)
                    if output_val is not None:
                        ctx.set_var('last_output', output_val)
                    if out_path:
                        ctx.set_var('found_file_path', out_path)
                        ctx.set_var('last_file', out_path)
                except Exception:
                    pass

            res = {
                'success': ok,
                'intent': intent,
                'agent_id': used_agent_id,
                'result': output_val if output_val is not None else data,
                'output': output_val,
                'output_path': out_path,
                'data': data,
            }
            if err_val:
                res['error'] = err_val
            return res
        except Exception as exc:
            logger.error(f"Agent task execution failed ({intent}): {exc}", exc_info=True)
            return {
                'success': False,
                'intent': intent,
                'agent_id': preferred_agent_id,
                'error': str(exc),
            }


# Singleton
_executor = None

def get_intent_executor() -> IntentExecutor:
    """Get singleton IntentExecutor instance"""
    global _executor
    if _executor is None:
        _executor = IntentExecutor()
    return _executor
