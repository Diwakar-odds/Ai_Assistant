"""
Global Emergency Stop Handler & Listener
Provides system-wide emergency halting across all automation, chains, and inputs.

Triggers:
1. Keyboard Shortcuts:
   - Double `Esc` within 400ms
   - `Ctrl + Shift + Q` (or `Ctrl + Shift + X`)
2. Programmatic / UI Signal:
   - `trigger_emergency_stop(reason)`
   - `CommandBrain.handle_executive(CommandClassification.EXECUTIVE_STOP)`

Actions on Trigger:
- Halts any active TaskChainOrchestrator execution loop immediately.
- Calls CommandBrain.handle_executive(CommandClassification.EXECUTIVE_STOP).
- Forcibly releases all mouse buttons and modifier keys (pyautogui failsafe/mouseUp/keyUp).
- Emits real-time notification to Socket.IO / Web UI.
"""

import time
import logging
import threading
from typing import Optional, Callable, List

logger = logging.getLogger(__name__)

# Global state
_listener_thread: Optional[threading.Thread] = None
_stop_listener_event = threading.Event()
_is_active = False
_last_esc_time: float = 0.0
_esc_threshold_seconds: float = 0.45  # double Esc window

# Extra callbacks to invoke on emergency stop
_emergency_callbacks: List[Callable[[str], None]] = []
_last_stop_trigger_time: float = 0.0
_last_stop_result: dict = {}
_stop_trigger_lock = threading.Lock()


def register_emergency_callback(callback: Callable[[str], None]):
    """Register an additional callback to invoke when emergency stop triggers."""
    if callback not in _emergency_callbacks:
        _emergency_callbacks.append(callback)


def release_system_inputs():
    """
    Forcibly release all mouse buttons and keyboard modifier keys
    to ensure the user regains immediate physical control of their machine.
    """
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.mouseUp()
        for key in ['ctrl', 'shift', 'alt', 'win', 'esc', 'tab', 'enter', 'space']:
            try:
                pyautogui.keyUp(key)
            except Exception:
                pass
        logger.info("🛑 [EMERGENCY STOP] Released all mouse/keyboard inputs via PyAutoGUI")
    except Exception as e:
        logger.debug(f"Input release notice: {e}")


def trigger_emergency_stop(reason: str = "Global Emergency Stop Activated") -> dict:
    """
    Primary programmatic trigger for the Emergency Stop system.
    Immediately halts execution chains, notifies CommandBrain, and releases OS inputs.
    Includes 1000ms debouncing to prevent duplicate REST and WebSocket event storms.
    """
    global _last_stop_trigger_time, _last_stop_result
    with _stop_trigger_lock:
        now = time.time()
        if now - _last_stop_trigger_time < 1.0 and _last_stop_result:
            logger.info(f"🛑 [EMERGENCY STOP] Debouncing rapid duplicate trigger within 1000ms: '{reason}'")
            return dict(_last_stop_result)
        _last_stop_trigger_time = now

        logger.warning(f"🚨 ========================================================")
        logger.warning(f"🚨 [EMERGENCY STOP TRIGGERED]: {reason}")
        logger.warning(f"🚨 ========================================================")

        # 0. Cut off active TTS speech immediately
        try:
            from ai_assistant.voice.tts_output_service import get_tts_service
            get_tts_service().stop(reason=reason)
        except Exception:
            pass

        # 1. Forcibly release mouse & keyboard control
        release_system_inputs()

        # 2. Halt TaskChainOrchestrator
        try:
            from ai_assistant.core.task_chain_orchestrator import get_orchestrator
            orchestrator = get_orchestrator()
            orchestrator.emergency_stop(reason=reason)
        except Exception as orch_e:
            logger.error(f"Failed to halt orchestrator: {orch_e}")

        # 3. Halt CommandBrain & Active Chains (emit_notice=False to prevent duplicate chat items)
        try:
            from ai_assistant.core.command_brain import get_executive_brain, CommandClassification
            brain = get_executive_brain()
            brain.handle_executive(CommandClassification.EXECUTIVE_STOP, reason, emit_notice=False)
        except Exception as brain_e:
            logger.error(f"Failed to signal Executive Brain: {brain_e}")

        # 4. Clear context execution state
        try:
            from ai_assistant.core.conversation_context import get_context_manager, ExecutionState
            ctx = get_context_manager()
            ctx.clear_task_chain()
            ctx.set_state(ExecutionState.IDLE)
            ctx.set_var('emergency_stopped_at', time.time())
        except Exception:
            pass

        # 5. Notify registered callbacks
        for cb in _emergency_callbacks:
            try:
                cb(reason)
            except Exception as cb_e:
                logger.error(f"Emergency callback error: {cb_e}")

        # 6. Canonical single broadcast via Socket.IO
        try:
            import sys
            from datetime import datetime
            if 'backend.voice_service' in sys.modules or 'voice_service' in sys.modules:
                try:
                    from voice_service import safe_emit
                except ImportError:
                    from backend.voice_service import safe_emit
                
                safe_emit('emergency_stop', {
                    'active': True,
                    'reason': reason,
                    'timestamp': datetime.now().isoformat()
                })
                safe_emit('command_response', {
                    'success': False,
                    'response': f"🛑 Emergency Stop: Live automation halted immediately. ({reason})",
                    'command': 'emergency_stop',
                    'source': 'emergency_stop_system',
                    'timestamp': datetime.now().isoformat(),
                    'skip_tts': True
                })
        except Exception as emit_e:
            logger.debug(f"SocketIO broadcast notice: {emit_e}")

        res = {
            'status': 'stopped',
            'reason': reason,
            'timestamp': time.time()
        }
        _last_stop_result = res
        return res


def _pynput_listener_worker():
    """
    Global keyboard listener using pynput.
    Detects double Esc and Ctrl+Shift+Q.
    """
    global _last_esc_time, _is_active
    try:
        from pynput import keyboard

        current_keys = set()

        def on_press(key):
            global _last_esc_time
            if _stop_listener_event.is_set():
                return False

            try:
                current_keys.add(key)

                # Check 1: Double Escape
                if key == keyboard.Key.esc:
                    now = time.time()
                    if now - _last_esc_time <= _esc_threshold_seconds:
                        logger.warning("🚨 [HOTKEY] Double 'Esc' detected -> Triggering Emergency Stop!")
                        _last_esc_time = 0.0
                        trigger_emergency_stop("Double Esc pressed")
                    else:
                        _last_esc_time = now

                # Check 2: Ctrl + Shift + Q or Ctrl + Shift + X
                ctrl_pressed = any(k in current_keys for k in [keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r])
                shift_pressed = any(k in current_keys for k in [keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r])

                if ctrl_pressed and shift_pressed:
                    try:
                        if hasattr(key, 'char') and key.char and key.char.lower() in ('q', 'x'):
                            logger.warning(f"🚨 [HOTKEY] Ctrl+Shift+{key.char.upper()} detected -> Triggering Emergency Stop!")
                            trigger_emergency_stop(f"Ctrl+Shift+{key.char.upper()} pressed")
                    except Exception:
                        pass

            except Exception as e:
                logger.debug(f"Hotkey listener error: {e}")

        def on_release(key):
            try:
                current_keys.discard(key)
            except Exception:
                pass
            if _stop_listener_event.is_set():
                return False

        logger.info("🛡️ Global Emergency Stop Listener active (pynput: Double 'Esc' or Ctrl+Shift+Q)")
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            while not _stop_listener_event.is_set():
                time.sleep(0.1)
            listener.stop()

    except Exception as e:
        logger.warning(f"pynput listener failed: {e}. Falling back to polling...")
        _win32_polling_worker()


def _win32_polling_worker():
    """
    Fallback global listener using win32api.GetAsyncKeyState or ctypes.
    """
    global _last_esc_time
    try:
        import win32api
        import win32con

        VK_ESCAPE = win32con.VK_ESCAPE
        VK_CONTROL = win32con.VK_CONTROL
        VK_SHIFT = win32con.VK_SHIFT
        VK_Q = 0x51
        VK_X = 0x58

        logger.info("🛡️ Global Emergency Stop Listener active (win32api polling)")

        was_esc_down = False
        was_combo_down = False

        while not _stop_listener_event.is_set():
            time.sleep(0.04)

            # Check ESC
            esc_down = (win32api.GetAsyncKeyState(VK_ESCAPE) & 0x8000) != 0
            if esc_down and not was_esc_down:
                now = time.time()
                if now - _last_esc_time <= _esc_threshold_seconds:
                    logger.warning("🚨 [HOTKEY] Double 'Esc' detected -> Triggering Emergency Stop!")
                    _last_esc_time = 0.0
                    trigger_emergency_stop("Double Esc pressed")
                else:
                    _last_esc_time = now
            was_esc_down = esc_down

            # Check Ctrl+Shift+Q or X
            ctrl_down = (win32api.GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0
            shift_down = (win32api.GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0
            q_down = (win32api.GetAsyncKeyState(VK_Q) & 0x8000) != 0
            x_down = (win32api.GetAsyncKeyState(VK_X) & 0x8000) != 0

            combo = ctrl_down and shift_down and (q_down or x_down)
            if combo and not was_combo_down:
                logger.warning("🚨 [HOTKEY] Ctrl+Shift+Q/X detected -> Triggering Emergency Stop!")
                trigger_emergency_stop("Ctrl+Shift+Q/X pressed")
            was_combo_down = combo

    except Exception as e:
        logger.error(f"Win32 polling emergency listener error: {e}")


def start_emergency_stop_listener():
    """Start the background global hotkey emergency stop listener thread."""
    global _listener_thread, _is_active
    if _is_active and _listener_thread and _listener_thread.is_alive():
        return

    _stop_listener_event.clear()
    _is_active = True

    try:
        import pynput
        target_fn = _pynput_listener_worker
    except ImportError:
        target_fn = _win32_polling_worker

    _listener_thread = threading.Thread(target=target_fn, name="GlobalEmergencyStopListener", daemon=True)
    _listener_thread.start()
    logger.info("✅ Global Emergency Stop background listener started.")


def stop_emergency_stop_listener():
    """Stop the background listener thread."""
    global _is_active
    _stop_listener_event.set()
    _is_active = False
    logger.info("Global Emergency Stop listener stopped.")


def is_emergency_stop_listener_active() -> bool:
    """Check if emergency stop listener is running."""
    return _is_active and _listener_thread is not None and _listener_thread.is_alive()
