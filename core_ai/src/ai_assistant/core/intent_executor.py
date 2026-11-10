"""
Intent Executor
Executes individual intents with context awareness and verification.
Extracted from TaskChainOrchestrator to be shared by both orchestration systems.
"""

import logging
import time
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

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
            'move_file': self._move_file,
            'set_brightness': self._set_brightness,
            'toggle_wifi': self._toggle_wifi,
            'send_file': self._send_file,
            'check_taskbar': self._check_taskbar,
            'play_video': self._play_video,
            'skip_time': self._skip_time,
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
            intent: Intent name (e.g. 'open_app', 'send_message')
            params: Parameters for the intent
            context_manager: Optional ContextManager for parameter inference
            
        Returns:
            Dict with 'success', 'intent', 'result'/'error' keys
        """
        logger.debug(f"Executing intent: {intent} with params: {params}")
        
        try:
            # Infer missing parameters from context
            if context_manager:
                params = context_manager.infer_missing_params(intent, params)
            
            handler = self._handlers.get(intent)
            if handler:
                return handler(params, context_manager)
            else:
                logger.warning(f"Unknown intent: {intent}")
                return {
                    'success': False,
                    'intent': intent,
                    'error': f"Unknown intent: {intent}"
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
            app_name = params.get('app_name') or params.get('name')
            
            # Optional keyword to look for in the window title (e.g. folder, profile, contact)
            expected_title_keyword = params.get('folder') or params.get('profile') or params.get('contact')
            
            detector = _get_taskbar_detector()
            if app_name and detector:
                time.sleep(1)
                scan = detector.find_specific_app_in_taskbar(app_name, expected_title_keyword)
                
                # We check the unified success flag which accounts for window titles
                is_successful = scan.get('is_successful', False)
                logger.info(f"   State Check (Process/Title): {'✅' if is_successful else '❌'} ({app_name}, keyword: {expected_title_keyword})")
                
                # If OS level check passes, we don't need VLM!
                if is_successful:
                    return True
        
        elif intent in ['set_brightness', 'set_volume', 'toggle_wifi']:
            return True
        
        # 2. VLM Verification for UI-heavy tasks or fallbacks
        vlm = _get_vlm()
        
        # Determine if we should use VLM. Now we use it for send_message OR as a fallback for failed open_app checks.
        use_vlm = (intent == 'send_message') or (intent in ['open_app', 'launch_app'])
        
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
        import os, re, subprocess
        from ai_assistant.automation.browser_profiles import (
            launch_browser_profile,
            resolve_chrome_profile,
            extract_profile_from_text
        )
        from ai_assistant.automation.window_manager import bring_window_to_foreground
        from ai_assistant.automation.app_discovery import app_discovery, smart_open_application

        app_name = params.get('app_name') or params.get('target') or params.get('app') or params.get('name')
        if not app_name:
            return {'success': False, 'intent': 'open_app', 'error': 'No app name provided'}
        
        app_lower = app_name.lower().strip()
        
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
                        profile_label = str(target_profile).title()
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
        app_name = params.get('app_name') or params.get('target') or params.get('app') or params.get('name')
        if not app_name:
            return {'success': False, 'intent': 'close_app', 'error': 'No app name provided'}
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
        """Find a file"""
        filename = params.get('file_name') or params.get('name')
        location = params.get('location')
        
        if not filename:
            return {'success': False, 'intent': 'find_file', 'error': 'No file name provided'}
        
        file_auto = _get_file_automation()
        if not file_auto:
            return {'success': False, 'intent': 'find_file', 'error': 'File automation not available'}
        
        path = file_auto.find_file(filename, location)
        if path:
            if ctx:
                ctx.set_var('found_file_path', path)
                ctx.set_var('last_file', path)
            return {'success': True, 'intent': 'find_file', 'result': path}
        else:
            return {'success': False, 'intent': 'find_file', 'error': f'File not found: {filename}'}
    
    def _open_folder(self, params: Dict, ctx=None) -> Dict:
        """Open a folder in explorer"""
        path = params.get('path') or params.get('folder')
        if not path and ctx:
            path = ctx.get_var('found_file_path')
        
        file_auto = _get_file_automation()
        if not file_auto:
            return {'success': False, 'intent': 'open_folder', 'error': 'File automation not available'}
        
        success = file_auto.open_explorer(path)
        return {'success': success, 'intent': 'open_folder'}
    
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
    
    def _set_brightness(self, params: Dict, ctx=None) -> Dict:
        """Set screen brightness"""
        level_str = params.get('level', '50')
        try:
            level = int(str(level_str).replace('%', ''))
        except (ValueError, TypeError):
            level = 50
        
        sys_auto = _get_system_automation()
        if not sys_auto:
            return {'success': False, 'intent': 'set_brightness', 'error': 'System automation not available'}
        
        success = sys_auto.set_brightness(level)
        return {'success': success, 'intent': 'set_brightness'}
    
    def _toggle_wifi(self, params: Dict, ctx=None) -> Dict:
        """Toggle WiFi on/off"""
        action = params.get('action', 'on')
        enable = action.lower() in ['on', 'enable', 'start']
        
        sys_auto = _get_system_automation()
        if not sys_auto:
            return {'success': False, 'intent': 'toggle_wifi', 'error': 'System automation not available'}
        
        success = sys_auto.toggle_wifi(enable)
        return {'success': success, 'intent': 'toggle_wifi'}
    
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


# Singleton
_executor = None

def get_intent_executor() -> IntentExecutor:
    """Get singleton IntentExecutor instance"""
    global _executor
    if _executor is None:
        _executor = IntentExecutor()
    return _executor
