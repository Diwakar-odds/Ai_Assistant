"""
Universal App Controller
Controls ANY Windows application without app-specific code.
Uses generic automation, computer vision, and AI understanding.
"""

import logging
import time
from typing import Dict, Optional, Any, List
from pathlib import Path

# Import existing modules
from ai_assistant.automation.app_discovery import smart_open_application, app_discovery
from ai_assistant.automation.window_manager import (
    find_window_by_name,
    bring_window_to_foreground,
    close_window_gracefully,
    is_window_foreground
)
try:
    import win32gui
    import win32process
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

logger = logging.getLogger(__name__)


class UniversalAppController:
    """
    Universal controller that works with ANY Windows application.
    
    Features:
    - Open any app using existing AppDiscovery
    - Track which apps are currently open
    - Execute actions on any app using multiple strategies
    - Plugin system for app-specific optimizations (optional)
    - Fallback to generic automation when no plugin available
    
    Usage:
        controller = UniversalAppController()
        
        # Works with any app!
        controller.execute_action("WhatsApp", "send_message", {
            "contact": "Mom",
            "message": "Hello"
        })
        
        controller.execute_action("Telegram", "send_message", {
            "contact": "Friend",
            "message": "Hi"
        })
        
        controller.execute_action("Notepad", "type_text", {
            "text": "Hello World"
        })
    """
    
    def __init__(self):
        """Initialize Universal App Controller"""
        logger.info("Initializing Universal App Controller")
        
        # Track active apps
        self.active_apps: Dict[str, Any] = {}
        
        # Import automation engine (lazy loading)
        self._automation_engine = None
        
        # Plugin manager (lazy loading)
        self._plugin_manager = None
        
        # Vision engine (lazy loading)
        self._vision_engine = None
        
        # Learning system (lazy loading)
        self._learning_system = None
        
        logger.info("Universal App Controller initialized successfully")
    
    @property
    def automation_engine(self):
        """Lazy load automation engine"""
        if self._automation_engine is None:
            try:
                from ai_assistant.automation.automation_engine import SmartAutomationEngine
                self._automation_engine = SmartAutomationEngine()
            except Exception as e:
                logger.warning(f"Automation engine not available: {e}")
                self._automation_engine = None
        return self._automation_engine
    
    @property
    def plugin_manager(self):
        """Lazy load plugin manager"""
        if self._plugin_manager is None:
            try:
                from ai_assistant.automation.plugin_manager import PluginManager
                self._plugin_manager = PluginManager()
            except ImportError:
                logger.warning("Plugin manager not available, using generic automation only")
                self._plugin_manager = None
        return self._plugin_manager
    
    @property
    def vision_engine(self):
        """Lazy load vision engine"""
        if self._vision_engine is None:
            try:
                from ai_assistant.automation.vision_engine import VisionEngine
                self._vision_engine = VisionEngine()
            except ImportError:
                logger.warning("Vision engine not available")
                self._vision_engine = None
        return self._vision_engine
    
    @property
    def learning_system(self):
        """Lazy load learning system"""
        if self._learning_system is None:
            try:
                from ai_assistant.automation.learning_system import LearningSystem
                self._learning_system = LearningSystem()
            except ImportError:
                logger.warning("Learning system not available")
                self._learning_system = None
        return self._learning_system
    
    # ===== APP LIFECYCLE MANAGEMENT =====
    
    def open_app(self, app_name: str) -> Dict[str, Any]:
        """
        Open any application dynamically using AppDiscovery and track foreground window status.
        
        Args:
            app_name: Name of the app to open (e.g., "VS Code", "WhatsApp", "Notepad", "Chrome")
        
        Returns:
            Dict with status, hwnd, and app info
        """
        logger.info(f"Opening app: {app_name}")
        
        try:
            # Use dynamic smart_open_application function
            result = smart_open_application(app_name)
            
            # Verify if launch succeeded
            if "❌" in result and "✅" not in result:
                logger.warning(f"smart_open_application failed for {app_name}: {result}")
                return {
                    'success': False,
                    'app_name': app_name,
                    'raw_result': result,
                    'error': result,
                    'message': f"Failed to open {app_name}: {result}"
                }

            # Web/protocol launches open in an existing browser or shell handler asynchronously;
            # skip the 3s blocking native-window poll for them.
            is_web_or_protocol = any(
                tag in result for tag in ("Opened Web App", "Opened Web/Windows App", "Opened Windows App Protocol")
            )
            window = None
            if is_web_or_protocol:
                window = find_window_by_name(app_name)
            else:
                start_poll = time.time()
                while time.time() - start_poll < 3.0:
                    window = find_window_by_name(app_name)
                    if window:
                        break
                    time.sleep(0.3)

            # Enforce foreground visibility
            is_fg = False
            if window:
                bring_window_to_foreground(window)
                is_fg = is_window_foreground(window)
            elif not is_web_or_protocol:
                bring_window_to_foreground(app_name)

            # Extract PID and window title if available
            pid = 0
            window_title = app_name
            if window and WIN32_AVAILABLE:
                try:
                    _, pid = win32process.GetWindowThreadProcessId(window)
                    window_title = win32gui.GetWindowText(window) or app_name
                except Exception:
                    pass

            # Track as active app with handle and foreground status
            self.active_apps[app_name.lower()] = {
                'app_name': app_name,
                'opened_at': time.time(),
                'last_action': 'opened',
                'window': window,
                'hwnd': window,
                'window_title': window_title,
                'pid': pid,
                'is_foreground': is_fg
            }

            return {
                'success': True,
                'app_name': app_name,
                'raw_result': result,
                'hwnd': window,
                'pid': pid,
                'is_foreground': is_fg,
                'message': f"Successfully opened {app_name}"
            }
        
        except Exception as e:
            logger.error(f"Failed to open {app_name}: {e}")
            return {
                'success': False,
                'app_name': app_name,
                'error': str(e),
                'message': f"Failed to open {app_name}"
            }
    
    def is_app_open(self, app_name: str) -> bool:
        """
        Check if app is currently running and verify its window status.
        
        Args:
            app_name: Name of the app
        
        Returns:
            True if app is open, False otherwise
        """
        app_key = app_name.lower()
        # Check cached window handle first
        if app_key in self.active_apps:
            cached_window = self.active_apps[app_key].get('window')
            if cached_window and WIN32_AVAILABLE and win32gui.IsWindow(cached_window):
                self.active_apps[app_key]['is_foreground'] = is_window_foreground(cached_window)
                return True
        
        # Scan current running windows
        window = find_window_by_name(app_name)
        if window:
            is_fg = is_window_foreground(window)
            pid = 0
            title = app_name
            if WIN32_AVAILABLE:
                try:
                    _, pid = win32process.GetWindowThreadProcessId(window)
                    title = win32gui.GetWindowText(window) or app_name
                except Exception:
                    pass
            self.active_apps[app_key] = {
                'app_name': app_name,
                'opened_at': self.active_apps.get(app_key, {}).get('opened_at', time.time()),
                'last_action': 'detected',
                'window': window,
                'hwnd': window,
                'window_title': title,
                'pid': pid,
                'is_foreground': is_fg
            }
            return True
        else:
            if app_key in self.active_apps:
                del self.active_apps[app_key]
            return False
    
    def get_app_window(self, app_name: str):
        """
        Get window handle (HWND) for app.
        
        Args:
            app_name: Name of the app
        
        Returns:
            Window handle HWND or None
        """
        app_key = app_name.lower()
        try:
            # Check cache first
            if app_key in self.active_apps:
                cached_window = self.active_apps[app_key].get('window')
                if cached_window and WIN32_AVAILABLE and win32gui.IsWindow(cached_window):
                    return cached_window
            
            # Find window dynamically
            window = find_window_by_name(app_name)
            
            # Update cache
            if window:
                if app_key not in self.active_apps:
                    self.active_apps[app_key] = {'app_name': app_name, 'opened_at': time.time()}
                self.active_apps[app_key]['window'] = window
                self.active_apps[app_key]['hwnd'] = window
                self.active_apps[app_key]['is_foreground'] = is_window_foreground(window)
            
            return window
        
        except Exception as e:
            logger.error(f"Failed to get window for {app_name}: {e}")
            return None

    def bring_to_foreground(self, app_name_or_hwnd: Any) -> bool:
        """Bring application window to the foreground."""
        success = bring_window_to_foreground(app_name_or_hwnd)
        if isinstance(app_name_or_hwnd, str):
            app_key = app_name_or_hwnd.lower()
            if app_key in self.active_apps:
                self.active_apps[app_key]['is_foreground'] = success
        return success
    
    def close_app(self, app_name: str) -> Dict[str, Any]:
        """
        Close an application gracefully.
        
        Args:
            app_name: Name of the app to close
        
        Returns:
            Dict with status
        """
        logger.info(f"Closing app: {app_name}")
        app_key = app_name.lower()
        
        try:
            window = self.get_app_window(app_name)
            closed = close_window_gracefully(window or app_name)
            
            # Remove from active apps
            if app_key in self.active_apps:
                del self.active_apps[app_key]
            
            if closed:
                return {
                    'success': True,
                    'app_name': app_name,
                    'message': f"Successfully closed {app_name}"
                }
            else:
                return {
                    'success': False,
                    'app_name': app_name,
                    'message': f"Could not close {app_name} or it was already closed"
                }
        
        except Exception as e:
            logger.error(f"Failed to close {app_name}: {e}")
            return {
                'success': False,
                'app_name': app_name,
                'error': str(e)
            }
    
    # ===== ACTION EXECUTION =====
    
    def execute_action(self, app_name: str, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute any action on any app.
        
        This is the MAIN method - works with ANY app!
        
        Args:
            app_name: Name of the app (e.g., "WhatsApp", "Notepad", "Telegram")
            action: Action to perform (e.g., "send_message", "type_text", "click_button")
            params: Parameters for the action
        
        Returns:
            Dict with execution result
        
        Examples:
            # WhatsApp
            execute_action("WhatsApp", "send_message", {
                "contact": "Mom",
                "message": "Hello"
            })
            
            # Telegram (never seen before!)
            execute_action("Telegram", "send_message", {
                "contact": "Friend",
                "message": "Hi"
            })
            
            # Notepad
            execute_action("Notepad", "type_text", {
                "text": "Hello World"
            })
            
            # Any app!
            execute_action("CustomApp", "click_button", {
                "button_text": "Submit"
            })
        """
        if params is None:
            params = {}
        
        logger.info(f"Executing action: {action} on {app_name} with params: {params}")
        
        try:
            # Step 1: Ensure app is open
            if not self.is_app_open(app_name):
                logger.info(f"{app_name} not open, opening now...")
                open_result = self.open_app(app_name)
                if not open_result['success']:
                    return open_result
            
            # Step 2: Get app window
            app_window = self.get_app_window(app_name)
            if not app_window:
                return {
                    'success': False,
                    'app_name': app_name,
                    'action': action,
                    'error': f"Could not get window for {app_name}"
                }
            
            # Step 3: Try plugin first (if available and action is simple)
            if self.plugin_manager and self.plugin_manager.has_plugin(app_name):
                try:
                    logger.info(f"Trying plugin for {app_name}")
                    result = self.plugin_manager.execute_via_plugin(app_name, action, params)
                    return {
                        'success': True,
                        'app_name': app_name,
                        'action': action,
                        'method': 'plugin',
                        'result': result
                    }
                except Exception as e:
                    logger.warning(f"Plugin failed for {app_name}, falling back to generic: {e}")
            
            # Step 4: Try learned workflow (if available)
            if self.learning_system:
                workflow_name = f"{app_name.lower()}_{action}"
                if self.learning_system.has_workflow(workflow_name):
                    try:
                        logger.info(f"Using learned workflow: {workflow_name}")
                        result = self.learning_system.replay_workflow(workflow_name, params)
                        return {
                            'success': True,
                            'app_name': app_name,
                            'action': action,
                            'method': 'learned_workflow',
                            'result': result
                        }
                    except Exception as e:
                        logger.warning(f"Learned workflow failed, falling back to generic: {e}")
            
            # Step 5: Fallback to generic automation
            logger.info(f"Using generic automation for {app_name}")
            result = self.execute_via_automation(app_window, app_name, action, params)
            
            # Update last action
            if app_name.lower() in self.active_apps:
                self.active_apps[app_name.lower()]['last_action'] = action
                self.active_apps[app_name.lower()]['last_action_time'] = time.time()
            
            return result
        
        except Exception as e:
            logger.error(f"Failed to execute {action} on {app_name}: {e}")
            return {
                'success': False,
                'app_name': app_name,
                'action': action,
                'error': str(e)
            }
    
    def execute_via_automation(self, window, app_name: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute action using generic automation strategies.
        
        This is the FALLBACK method that works with any app.
        """
        logger.info(f"Executing {action} via automation engine")
        
        # Map common actions to automation methods
        if action == "type_text":
            text = params.get('text', '')
            success = self.automation_engine.type_in_active_window(text)
            return {
                'success': success,
                'app_name': app_name,
                'action': action,
                'method': 'generic_automation'
            }
        
        elif action == "click_button":
            button_text = params.get('button_text') or params.get('text')
            element = self.automation_engine.find_element(window, "Button", button_text)
            if element:
                success = self.automation_engine.click_element(element)
                return {
                    'success': success,
                    'app_name': app_name,
                    'action': action,
                    'method': 'generic_automation'
                }
            else:
                return {
                    'success': False,
                    'app_name': app_name,
                    'action': action,
                    'error': f"Button '{button_text}' not found"
                }
        
        elif action == "send_message":
            # Generic message sending for ANY messaging app
            contact = params.get('contact', '')
            message = params.get('message', '')
            
            # Use Vision AI to understand the app and suggest steps
            if self.vision_engine:
                steps = self.vision_engine.suggest_action_sequence(
                    app_name,
                    f"send message '{message}' to contact '{contact}'"
                )
                # Execute suggested steps
                # (This will be implemented in vision_engine.py)
            
            # Fallback: Generic approach
            # 1. Try to find search/input field
            # 2. Type contact name
            # 3. Find message field
            # 4. Type message
            # 5. Press Enter or click Send
            
            return {
                'success': False,
                'app_name': app_name,
                'action': action,
                'message': "Generic send_message not yet fully implemented. Please teach me using 'start recording'."
            }
        
        else:
            # Unknown action
            return {
                'success': False,
                'app_name': app_name,
                'action': action,
                'error': f"Unknown action: {action}. Try 'start recording' to teach me this action."
            }
    
    # ===== LEARNING INTERFACE =====
    
    def start_teaching(self, app_name: str, action_name: str) -> Dict[str, Any]:
        """
        Start recording user actions to learn a new workflow.
        
        Usage:
            controller.start_teaching("Telegram", "send_message")
            # User performs actions...
            controller.stop_teaching()
        """
        if not self.learning_system:
            return {
                'success': False,
                'error': "Learning system not available"
            }
        
        workflow_name = f"{app_name.lower()}_{action_name}"
        self.learning_system.start_recording(workflow_name, app_name)
        
        return {
            'success': True,
            'message': f"Recording started for {app_name} - {action_name}. Perform the actions now."
        }
    
    def stop_teaching(self) -> Dict[str, Any]:
        """Stop recording and save the learned workflow."""
        if not self.learning_system:
            return {
                'success': False,
                'error': "Learning system not available"
            }
        
        actions = self.learning_system.stop_recording()
        
        return {
            'success': True,
            'message': f"Recording saved! {len(actions)} actions recorded.",
            'actions_count': len(actions)
        }
    
    def list_learned_workflows(self, app_name: str = None) -> List[str]:
        """List all learned workflows."""
        if not self.learning_system:
            return []
        
        return self.learning_system.list_learned_workflows(app_name)
    
    # ===== UTILITY METHODS =====
    
    def get_active_apps(self) -> List[str]:
        """Get list of currently active apps."""
        return list(self.active_apps.keys())
    
    def get_app_info(self, app_name: str) -> Optional[Dict[str, Any]]:
        """Get information about an app."""
        return self.active_apps.get(app_name.lower())


# Singleton instance
_controller_instance = None

def get_universal_controller() -> UniversalAppController:
    """Get singleton instance of Universal App Controller."""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = UniversalAppController()
    return _controller_instance

