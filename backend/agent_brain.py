try:
    from telemetry_tracer import telemetry
except ImportError:
    class DummyTelemetry:
        @staticmethod
        def log_inbound(*a, **k): pass
        @staticmethod
        def log_router(*a, **k): pass
        @staticmethod
        def log_compute(*a, **k): pass
        @staticmethod
        def log_dispatch(*a, **k): pass
        @staticmethod
        def log_screen_action(*a, **k): pass
        @staticmethod
        def log_notification(*a, **k): pass
    telemetry = DummyTelemetry

#!/usr/bin/env python3
"""
Pulsar AI Assistant - Agent Brain
=================================
The central autonomous reasoning and execution engine for the Ambient Desktop Agent:
- Understands natural language commands (English, Hindi, Hinglish).
- Perceives screen context (active app, UI elements, text content).
- Dispatches actions across UI automation, communication, media, and system control.
- Enforces safety tiers with confirmation prompts for destructive actions.
- Runs background tasks (web research) while the user works uninterrupted.
"""

import sys
import os
import time
import json
import re
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

# Ensure project paths are available (supports both dev and frozen PyInstaller modes)
if getattr(sys, 'frozen', False):
    project_root = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent)).resolve()
else:
    project_root = Path(__file__).resolve().parent.parent

for _p in (
    str(project_root),
    str(project_root / "backend"),
    str(project_root / "core_ai" / "src"),
    str(project_root / "shared"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from ai_assistant.core.local_command_normalizer import ensure_project_ffmpeg_in_path
    ensure_project_ffmpeg_in_path(project_root)
except Exception:
    pass

from dotenv import load_dotenv
try:
    from settings_manager import get_env_file
    _ab_env = get_env_file()
    if _ab_env.exists():
        load_dotenv(_ab_env, override=False)
    else:
        load_dotenv(project_root / ".env", override=False)
except Exception:
    load_dotenv(project_root / ".env", override=False)

from utils.logging_config import get_logger
logger = get_logger(__name__, log_category="app")

# Win32 APIs for window & media key automation
try:
    import win32gui
    import win32process
    import win32api
    import win32con
    import psutil
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.2
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False


class AgentBrain:
    """
    Central Agent Brain coordinating Perception, Reasoning, and Action.
    Singleton pattern for efficient tool re-use.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AgentBrain, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        logger.info("🧠 Initializing Pulsar Agent Brain...")
        self.multimodal_ai = None
        self.visual_automation = None
        self.app_automation = None
        self.gmail_manager = None
        self.calendar_manager = None

        # Pending confirmation store for Tier 3 actions
        self.pending_actions: Dict[str, Dict[str, Any]] = {}
        self._pref_tls = threading.local()

        # Lazy init modules in background
        threading.Thread(target=self._init_submodules, daemon=True).start()

    def _init_submodules(self):
        """Warm up heavy submodules asynchronously"""
        try:
            from ai_assistant.vision.multimodal import MultiModalAI
            self.multimodal_ai = MultiModalAI()
            logger.info("✅ MultiModalAI loaded into Agent Brain")
        except Exception as e:
            logger.warning(f"Could not load MultiModalAI: {e}")

        try:
            from ai_assistant.automation.app_automation import AppAutomation
            self.app_automation = AppAutomation()
            logger.info("✅ AppAutomation loaded into Agent Brain")
        except Exception as e:
            logger.warning(f"Could not load AppAutomation: {e}")

        try:
            from ai_assistant.integrations.email_handler import GmailManager
            self.gmail_manager = GmailManager()
        except Exception:
            pass

        try:
            from ai_assistant.integrations.google_calendar import CalendarManager
            self.calendar_manager = CalendarManager()
        except Exception:
            pass

    # -------------------------------------------------------------
    # 1. Screen Perception & Active Window Awareness
    # -------------------------------------------------------------
    def get_active_window_info(self) -> Dict[str, Any]:
        """Identifies foreground window, application name, process ID, and rect"""
        if not WIN32_AVAILABLE:
            return {"title": "Unknown", "app_name": "Unknown", "rect": (0, 0, 1920, 1080)}

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return {"title": "Desktop", "app_name": "explorer.exe", "rect": (0, 0, 1920, 1080)}

            title = win32gui.GetWindowText(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            app_name = "Unknown"
            try:
                proc = psutil.Process(pid)
                app_name = proc.name()
            except Exception:
                pass

            return {
                "hwnd": hwnd,
                "title": title,
                "app_name": app_name,
                "rect": rect
            }
        except Exception as e:
            logger.warning(f"Error getting active window info: {e}")
            return {"title": "Unknown", "app_name": "Unknown", "rect": (0, 0, 1920, 1080)}

    def _ensure_multimodal_ai(self):
        """Lazy-initialize MultiModalAI safely so vision actions never hit None."""
        if self.multimodal_ai is None:
            from ai_assistant.vision.multimodal import MultiModalAI
            self.multimodal_ai = MultiModalAI()
        return self.multimodal_ai

    def capture_screen(self, region=None):
        """High-speed screen capture via MultiModalAI / mss"""
        return self._ensure_multimodal_ai().capture_screen(region=region, use_cache=False)

    # -------------------------------------------------------------
    # 2. Main Processing & Intent Routing
    # -------------------------------------------------------------
    def _get_current_model_preference(self) -> Optional[Dict[str, Any]]:
        tls = getattr(self, '_pref_tls', None)
        pref = getattr(tls, 'model_preference', None) if tls is not None else None
        if isinstance(pref, dict):
            return pref
        legacy = getattr(self, '_active_model_preference', None)
        return legacy if isinstance(legacy, dict) else None

    def _get_active_provider_name(self) -> str:
        """Resolves active provider from per-request preference or persistent settings."""
        pref = self._get_current_model_preference()
        if pref:
            raw_p = str(pref.get('provider') or '').strip().lower()
            if raw_p == 'google':
                return 'gemini'
            if raw_p == 'local':
                return 'gguf'
            if raw_p in ('gemini', 'openai', 'gguf', 'offline'):
                return raw_p
            if raw_p or pref.get('offline_mode'):
                return 'gguf'
        try:
            from settings_manager import get_provider
            prov = (get_provider() or 'gemini').strip().lower()
            if prov == 'google':
                return 'gemini'
            if prov not in ('gemini', 'openai', 'gguf'):
                return 'gguf'
            return prov
        except Exception:
            return 'gemini'

    def _get_active_model_name(self) -> str:
        """Resolves active model from per-request preference or persistent settings."""
        active_p = self._get_active_provider_name()
        pref = self._get_current_model_preference()
        if pref:
            pref_m = str(pref.get('model') or '').strip()
            if pref_m:
                try:
                    from ai_assistant.ai.llm_provider import LLMFactory
                    return LLMFactory.sanitize_model_for_provider(active_p, pref_m)
                except Exception:
                    return pref_m
        try:
            from settings_manager import get_model, get_default_model_for_provider
            from ai_assistant.ai.llm_provider import LLMFactory
            candidate = get_model() or get_default_model_for_provider(active_p)
            return LLMFactory.sanitize_model_for_provider(active_p, candidate)
        except Exception:
            if active_p == 'gguf':
                return 'pulsar-final-q4_k_m'
            if active_p == 'openai':
                return 'gpt-4o-mini'
            return "gemini-2.5-flash"

    def process_command(self, command: str, include_screen: bool = False, source: str = "COMPANION_DESKTOP", model_preference: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Receives user natural language command, perceives context,
        reasons on intent, and executes corresponding tool.
        """
        if not hasattr(self, '_pref_tls'):
            self._pref_tls = threading.local()
        prev_pref = getattr(self._pref_tls, 'model_preference', None)
        self._pref_tls.model_preference = model_preference
        self._active_model_preference = model_preference
        try:
            return self._process_command_inner(command, include_screen=include_screen, source=source)
        finally:
            self._pref_tls.model_preference = prev_pref
            self._active_model_preference = prev_pref

    def _process_command_inner(self, command: str, include_screen: bool = False, source: str = "COMPANION_DESKTOP") -> Dict[str, Any]:
        command = (command or "").strip()
        if not command:
            return {"success": False, "response": "I didn't hear any command. How can I help?"}

        start_time = time.time()
        telemetry.log_inbound(source, command)
        logger.info(f"🧠 Agent Brain processing command: '{command}' (include_screen={include_screen}, source={source})")

        # 1. Check if user is confirming or canceling a pending Tier-3 action
        confirm_match = self._check_pending_confirmation(command)
        if confirm_match:
            lat = (time.time() - start_time) * 1000
            telemetry.log_router("CONFIRMATION_GATING", "Safety Gate (Tier 3 Action)")
            telemetry.log_compute(lat, status="OK")
            telemetry.log_dispatch(["Desktop Screen", "Companion UI", "TTS"], confirm_match.get("response"))
            return confirm_match

        # 2. Get active window context
        window_info = self.get_active_window_info()

        # 3. Fast keyword dispatch for common instant controls (Media, Volume)
        fast_result = self._try_fast_dispatch(command)
        if fast_result is not None:
            lat = (time.time() - start_time) * 1000
            telemetry.log_router("FAST_RULE_DISPATCH", "Local Rules (PyAutoGUI)")
            telemetry.log_compute(lat, status="OK")
            telemetry.log_dispatch(["Desktop Screen", "Companion UI", "TTS"], fast_result.get("response"))
            return fast_result

        # 4. Reason with AI Model (Gemini Vision or Fast LLM)
        classification = self._classify_intent(command, window_info, include_screen=include_screen)

        intent = classification.get("intent", "general_chat")
        action = classification.get("action", "")
        params = classification.get("params", {})
        risk_tier = classification.get("risk_tier", 1)
        engine_used = classification.get("_engine", "Google Gemini 2.5 Flash")

        # Hard opt-in guard: never capture screenshots unless explicitly requested or include_screen=True
        if intent == "screen_action" and not include_screen and not self._explicit_screen_request(command):
            intent = "general_chat"
            action = "chat"

        telemetry.log_router(intent.upper(), engine_used, f"Action: {action} | Tier: {risk_tier}")

        # 5. Handle Gated Tier 3 Actions (Require User Confirmation)
        if risk_tier == 3:
            gated = self._create_pending_confirmation(command, intent, action, params, classification)
            lat = (time.time() - start_time) * 1000
            telemetry.log_compute(lat, status="GATED_CONFIRMATION")
            telemetry.log_dispatch(["Companion Mascot Confirmation Modal"], gated.get("response"))
            return gated

        # 6. Execute Action by Intent
        try:
            if intent == "screen_action":
                res = self.execute_screen_action(action, params, window_info)
            elif intent == "communication":
                res = self.execute_communication(action, params)
            elif intent == "media_control":
                res = self.execute_media_control(action, params)
            elif intent == "system_control":
                res = self.execute_system_control(action, params)
            elif intent == "background_task":
                res = self.execute_background_task(action, params)
            else:
                # General conversation or advice
                res = self._execute_conversational_response(command, window_info, include_screen=include_screen)

            if isinstance(res, dict):
                res.setdefault("intent", intent)
                resp_text = str(res.get("response") or "")
                if resp_text:
                    try:
                        from ai_assistant.knowledge.interaction_learner import record_turn_and_learn_async
                        record_turn_and_learn_async(command, resp_text, source=source, active_window=window_info)
                    except Exception:
                        pass
            lat = (time.time() - start_time) * 1000
            telemetry.log_compute(lat, status="OK" if res.get("success", True) else "FAILED")
            telemetry.log_dispatch(["Desktop Screen", "Companion UI", "TTS"], res.get("response"))
            return res
        except Exception as e:
            logger.error(f"Error executing intent {intent}: {e}", exc_info=True)
            lat = (time.time() - start_time) * 1000
            telemetry.log_compute(lat, status=f"ERROR: {e}")
            return {
                "success": False,
                "response": f"I ran into an issue while doing that: {str(e)}",
                "tts": "I encountered an issue executing your command."
            }

    # -------------------------------------------------------------
    # 3. Fast Intent Dispatcher (Zero Latency for standard controls)
    # -------------------------------------------------------------
    def _try_fast_dispatch(self, command: str) -> Optional[Dict[str, Any]]:
        try:
            from ai_assistant.core.local_command_normalizer import (
                match_and_strip_wake_phrase,
                parse_voice_control_command,
                execute_voice_control_command,
            )

            matched_wake, cleaned_cmd = match_and_strip_wake_phrase(command)
            cmd_to_run = cleaned_cmd if matched_wake else command.strip()

            try:
                from ai_assistant.core.speech_text_crisper import crisp_speech_transcript
                crisped_cmd = crisp_speech_transcript(cmd_to_run)
                if crisped_cmd:
                    cmd_to_run = crisped_cmd
            except Exception:
                pass

            if matched_wake and not cmd_to_run:
                try:
                    from ai_assistant.core.jarvis_persona import generate_wake_acknowledgment
                    wake_msg = generate_wake_acknowledgment(wake_word=matched_wake, raw_transcript=command)
                except Exception:
                    wake_msg = "Haan Boss, bolo — sun rahi hoon."
                return {
                    "success": True,
                    "response": wake_msg,
                    "tts": wake_msg,
                    "intent": "wake_greeting",
                }

            vc_parsed = parse_voice_control_command(cmd_to_run)
            if vc_parsed:
                vc_res = execute_voice_control_command(vc_parsed)
                msg = vc_res.get("response", "")
                return {
                    "success": bool(vc_res.get("success", True)),
                    "response": msg,
                    "tts": str(vc_res.get("tts") or msg)[:180],
                    "intent": vc_res.get("action", "voice_control"),
                    "voice_control": True,
                }

            from ai_assistant.core.conversation_context import get_context_manager
            from ai_assistant.core.local_command_normalizer import resolve_contextual_toggle_command
            ctx = get_context_manager()

            # Check bare contextual toggle follow-up (e.g. "off कर दो" right after "Bluetooth on कर दो")
            resolved_ctx = resolve_contextual_toggle_command(cmd_to_run, ctx)
            if resolved_ctx:
                iname, iparams = resolved_ctx
                from ai_assistant.core.intent_executor import get_intent_executor
                exec_res = get_intent_executor().execute(iname, iparams, context_manager=ctx)
                res_val = exec_res.get("result")
                msg = (
                    str(res_val.get("message") or exec_res.get("message") or res_val)
                    if isinstance(res_val, dict)
                    else str(res_val or exec_res.get("error") or exec_res.get("message") or f"Executed {iname}")
                )
                ok = bool(exec_res.get("success", False))
                return {
                    "success": ok,
                    "response": msg,
                    "tts": msg[:180],
                    "intent": iname,
                }

            from ai_assistant.ai.intent_router import IntentRouter
            intent_res = IntentRouter()._fast_match(cmd_to_run)
            if intent_res:
                iname = intent_res.intent_name
                iparams = intent_res.parameters or {}

                # High-consequence confirmation gates
                if iname == "send_message":
                    contact = iparams.get("contact", "contact")
                    return self._create_pending_confirmation(
                        cmd_to_run,
                        "communication",
                        "whatsapp_message",
                        iparams,
                        {"summary": f"send WhatsApp message to {contact}"},
                    )
                if iname == "system_control" and str(iparams.get("action", "")).lower() in ("shutdown", "restart"):
                    sys_act = str(iparams.get("action", "")).lower()
                    return self._create_pending_confirmation(
                        cmd_to_run,
                        "system_control",
                        sys_act,
                        iparams,
                        {"summary": f"{sys_act} the computer"},
                    )

                local_executor_intents = {
                    "open_app", "close_app", "volume_control",
                    "wifi_toggle", "bluetooth_toggle", "set_brightness",
                    "brightness_control", "dark_mode_toggle", "battery_status",
                    "list_running_apps", "check_taskbar", "open_settings",
                    "youtube_search", "youtube_history", "search_web",
                    "play_media", "media_control", "system_control",
                }
                if iname in local_executor_intents:
                    from ai_assistant.core.intent_executor import get_intent_executor
                    exec_res = get_intent_executor().execute(iname, iparams, context_manager=ctx)
                    res_val = exec_res.get("result")
                    if isinstance(res_val, dict):
                        msg = str(res_val.get("message") or exec_res.get("message") or res_val)
                    elif res_val:
                        msg = str(res_val)
                    else:
                        msg = str(exec_res.get("error") or exec_res.get("message") or f"Executed {iname}")
                    ok = bool(exec_res.get("success", False))
                    if "❌" in msg and "✅" not in msg:
                        ok = False
                    return {
                        "success": ok,
                        "response": msg,
                        "tts": msg[:180],
                        "intent": iname,
                    }
        except Exception as fast_err:
            logger.debug(f"Fast dispatch check warning: {fast_err}")

        c = command.lower()

        # Media Control: Previous
        if any(w in c for w in ["previous song", "prev song", "play previous song", "play prev song", "previous track", "last song", "pichla gaana", "pichhla gaana", "पिछला गाना"]):
            return self.execute_media_control("previous", {})

        # Media Control: Skip / Next
        if any(w in c for w in ["skip song", "next song", "play next song", "play next", "gaana skip", "next track", "skip track", "skip karo", "agla gaana", "अगला गाना"]):
            return self.execute_media_control("next", {})

        # Media Control: Pause
        if any(w in c for w in ["pause song", "pause the song", "pause music", "pause playback", "pause video", "stop the music", "stop music", "gaana pause", "gaana roko", "pause karo", "गाना रोको", "पॉज़ करो"]):
            return self.execute_media_control("pause", {})

        # Media Control: Resume / Play
        if any(w in c for w in ["resume song", "resume the song", "resume music", "resume playback", "gaana chalao", "gaana chalu", "गाना चलाओ", "play song", "play music"]):
            return self.execute_media_control("resume", {})

        # Volume Controls
        if any(w in c for w in ["mute", "awaaz band", "awaaz mute"]):
            return self.execute_system_control("mute", {})
        if any(w in c for w in ["volume up", "awaaz badhao", "sound badhao"]):
            return self.execute_system_control("volume_up", {})
        if any(w in c for w in ["volume down", "awaaz kam karo", "sound kam karo"]):
            return self.execute_system_control("volume_down", {})

        return None

    # -------------------------------------------------------------
    # 4. LLM Intent Classifier
    # -------------------------------------------------------------
    @staticmethod
    def _explicit_screen_request(command: str) -> bool:
        c = (command or "").lower()
        return any(
            k in c
            for k in (
                "screenshot",
                "screen shot",
                "on screen",
                "on my screen",
                "my screen",
                "this screen",
                "the screen",
                "screen dekho",
                "screen padho",
                "screen check",
                "kya dikh raha",
                "check email",
                "check grammar",
                "grammar check",
                "check spelling",
                "explain this code",
                "explain code on screen",
                "read this pdf",
                "summarize pdf",
                "end call",
                "end video call",
                "cut call",
                "call kaat",
                "disconnect call",
                "स्क्रीन",
                "स्क्रीनशॉट",
                "क्या दिख रहा",
                "ग्रामर",
                "पीडीएफ",
            )
        )

    def _classify_intent(self, command: str, window_info: Dict[str, Any], include_screen: bool = False) -> Dict[str, Any]:
        """Uses Gemini (only when active & configured) to classify user intent, parameters, and risk tier"""
        screen_requested = include_screen or self._explicit_screen_request(command)
        window_ctx = (
            f'Active Window: "{window_info.get("title", "Unknown")}" (App: {window_info.get("app_name", "Unknown")})\n'
            if screen_requested
            else ""
        )
        prompt = f"""You are the intent routing engine for Pulsar, an autonomous desktop AI assistant.
User command: "{command}"
{window_ctx}
Classify the command into one of these intents:
1. "screen_action": Interacting with visible screen content (ONLY if user explicitly asks about their screen, checking email grammar on screen, reading PDF on screen, or ending an active video call).
2. "communication": WhatsApp messaging, checking/sending emails via Gmail, Google Calendar events.
3. "media_control": Controlling music/video playback (play, pause, skip, previous, volume).
4. "system_control": App launching, closing apps, volume, brightness, wifi, bluetooth.
5. "background_task": Web search or research to do in the background while user continues working.
6. "general_chat": Q&A, chat, greeting, general advice.

Determine risk_tier:
- 1: Passive/read-only (checking grammar, reading screen, volume, search)
- 2: Low-risk interaction (skip song, pause, focus window, scroll)
- 3: High-consequence action requiring confirmation (sending email, sending WhatsApp message, ending a live video call, deleting files)

Return strict JSON only:
{{
  "intent": "screen_action|communication|media_control|system_control|background_task|general_chat",
  "action": "<specific_action>",
  "params": {{}},
  "risk_tier": 1|2|3,
  "summary": "<short description of action>"
}}"""

        try:
            active_provider = self._get_active_provider_name()
            gemini_key = None
            try:
                from settings_manager import get_api_key
                gemini_key = get_api_key("gemini")
            except Exception:
                gemini_key = os.getenv("GEMINI_API_KEY")

            if active_provider != "gemini" or not gemini_key:
                raise RuntimeError(f"Gemini classifier skipped (provider={active_provider})")

            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            active_model = self._get_active_model_name()
            if "gemini" not in active_model.lower():
                active_model = "gemini-2.5-flash"
            model = genai.GenerativeModel(active_model)
            resp = model.generate_content(prompt)
            raw = resp.text.strip()
            # Clean markdown codeblocks
            raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"^```\s*", "", raw, flags=re.MULTILINE)
            raw = raw.strip()
            parsed = json.loads(raw)
            parsed["_engine"] = f"{active_model} (Cloud)"
            return parsed
        except Exception as e:
            logger.debug(f"LLM classification fallback ({e})")
            try:
                from ai_assistant.ai.intent_router import IntentRouter
                router_res = IntentRouter()._fast_match(command)
                if router_res:
                    ri = router_res.intent_name
                    rp = router_res.parameters or {}
                    if ri in (
                        "volume_control", "wifi_toggle", "bluetooth_toggle",
                        "set_brightness", "brightness_control", "dark_mode_toggle",
                        "open_settings", "battery_status", "list_running_apps",
                        "system_control", "open_app", "close_app",
                    ):
                        tier = 3 if (ri == "system_control" and str(rp.get("action", "")).lower() in ("shutdown", "restart")) else 1
                        return {"intent": "system_control", "action": ri, "params": rp, "risk_tier": tier, "_engine": "IntentRouter Tier-1 Fallback"}
                    if ri == "send_message":
                        return {"intent": "communication", "action": "whatsapp_message", "params": rp, "risk_tier": 3, "_engine": "IntentRouter Tier-1 Fallback"}
                    if ri in ("search_web", "youtube_search"):
                        return {"intent": "background_task", "action": ri, "params": rp, "risk_tier": 1, "_engine": "IntentRouter Tier-1 Fallback"}
            except Exception:
                pass
            c = command.lower()
            engine_tag = "Local Heuristic Fallback"
            if any(k in c for k in ["open ", "launch ", "start ", "kholo", "khol do", "close ", "band karo"]):
                act = "close_app" if any(k in c for k in ["close ", "band karo"]) else "open_app"
                return {"intent": "system_control", "action": act, "params": {"app_name": command}, "risk_tier": 1, "_engine": engine_tag}
            if self._explicit_screen_request(command):
                scr_act = "analyze_or_act"
                if any(k in c for k in ("end call", "end video call", "cut call", "call kaat", "disconnect call")):
                    scr_act = "end_call"
                elif any(k in c for k in ("grammar", "spelling", "check email", "ग्रामर")):
                    scr_act = "check_grammar"
                elif any(k in c for k in ("pdf", "पीडीएफ")):
                    scr_act = "summarize_pdf"
                elif any(k in c for k in ("explain this code", "explain code")):
                    scr_act = "explain_code"
                return {"intent": "screen_action", "action": scr_act, "params": {}, "risk_tier": 1, "_engine": engine_tag}
            elif any(k in c for k in ["whatsapp", "email", "mail", "calendar", "meeting", "message"]):
                return {"intent": "communication", "action": "message", "params": {}, "risk_tier": 2, "_engine": engine_tag}
            elif any(k in c for k in ["search", "google", "website"]):
                return {"intent": "background_task", "action": "web_search", "params": {"query": command}, "risk_tier": 1, "_engine": engine_tag}
            return {"intent": "general_chat", "action": "chat", "params": {}, "risk_tier": 1, "_engine": engine_tag}

    # -------------------------------------------------------------
    # 5. Screen Action Execution (Grammar Check, End Call, PDF, Code)
    # -------------------------------------------------------------
    def execute_screen_action(self, action: str, params: Dict[str, Any], window_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handles screen analysis, editing emails, ending calls, and visual assistance"""
        screenshot = self.capture_screen()
        app_title = window_info.get("title", "")
        app_name = window_info.get("app_name", "").lower()

        # CASE A: End Video Call (e.g., WhatsApp, Zoom, Teams, Meet)
        if any(k in action.lower() for k in ["end_call", "cut_call", "disconnect"]) or \
           any(k in str(params).lower() for k in ["call", "disconnect"]):
            return self._action_end_video_call(screenshot)

        # CASE B: Grammar / Email Correction & Auto-Editing
        if any(k in action.lower() for k in ["grammar", "email", "check", "correct", "edit"]):
            return self._action_check_and_edit_email(screenshot, app_title)

        # CASE C: Explain Code / Screen Content
        if any(k in action.lower() for k in ["code", "explain", "samjhao"]):
            return self._action_explain_screen_content(screenshot, focus="code")

        # CASE D: PDF Reading & Key Insights
        if any(k in action.lower() for k in ["pdf", "highlight", "document"]):
            return self._action_summarize_pdf_screen(screenshot)

        # CASE E: Auto-Type or Insert Corrected Text
        if any(k in action.lower() for k in ["type", "auto_type", "paste", "insert"]):
            text_to_type = params.get("text") or params.get("corrected_text") or ""
            return self.action_auto_type_text(text_to_type)

        # Generic Screen Assistance
        mm = self._ensure_multimodal_ai()
        analysis = mm.analyze_image(
            screenshot,
            prompt="Analyze the screen and address the user's request. Provide a crisp 2-3 sentence answer."
        )
        desc = analysis.get("description", "Screen analyzed.")
        return {
            "success": True,
            "response": desc,
            "tts": desc[:180],
            "card": {"type": "info", "title": "👁️ Screen Analysis", "body": desc}
        }

    def _action_end_video_call(self, screenshot) -> Dict[str, Any]:
        """Locates red 'End Call' / 'Leave' button and clicks it"""
        prompt = """Look at this screen containing a live video/audio call (WhatsApp, Zoom, Teams, or Google Meet).
Locate the red 'End Call', 'Leave Call', or 'Disconnect' button.
Return JSON with coordinates:
{"found": true, "x": <center_x_pixel>, "y": <center_y_pixel>}
If no call button is visible, return {"found": false}"""

        mm = self._ensure_multimodal_ai()
        analysis = mm.analyze_image(screenshot, prompt=prompt)
        text = analysis.get("description", "")

        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                if data.get("found"):
                    x, y = data["x"], data["y"]
                    if PYAUTOGUI_AVAILABLE:
                        pyautogui.click(x, y)
                        return {
                            "success": True,
                            "response": "Disconnected the video call for you.",
                            "tts": "I have ended the video call.",
                            "card": {"type": "action", "title": "📞 Call Ended", "body": f"Clicked disconnect at ({x}, {y})"}
                        }
        except Exception as e:
            logger.warning(f"Coordinate parsing error: {e}")

        # Fallback: Common keyboard shortcuts for video calls
        # WhatsApp Desktop: Alt+F4 if call window is active, or Zoom: Alt+Q + Enter
        return {
            "success": False,
            "response": "I couldn't locate the end call button on screen. Please make sure the call window is visible.",
            "tts": "I could not find the call button on your screen."
        }

    def _action_check_and_edit_email(self, screenshot, app_title: str) -> Dict[str, Any]:
        """Reads draft email from screen, checks grammar, and provides corrected version"""
        prompt = """Inspect the active screen which shows an email draft or document text.
1. Extract the text written by the user.
2. Check for grammatical errors, tone, clarity, and spelling.
3. Provide a corrected, professional version.

Format your response as:
ERRORS: <bullet points of key issues>
CORRECTED VERSION:
<the clean, ready-to-send text>"""

        mm = self._ensure_multimodal_ai()
        analysis = mm.analyze_image(screenshot, prompt=prompt)
        desc = analysis.get("description", "Checked email.")

        speech_summary = "I reviewed your email. I've noted grammar suggestions in the dialog."
        if "No errors found" in desc:
            speech_summary = "Your email looks grammatically correct and ready to send!"

        return {
            "success": True,
            "response": desc,
            "tts": speech_summary,
            "card": {
                "type": "email_review",
                "title": "✍️ Email Grammar Review",
                "body": desc,
                "actions": ["Copy Corrected", "Auto-Type Edit"]
            }
        }

    def action_auto_type_text(self, text_to_type: str, select_all_first: bool = True) -> Dict[str, Any]:
        """Auto-types or pastes text directly into user's active editor/draft"""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "response": "PyAutoGUI not available"}
        try:
            time.sleep(0.3)  # Allow foreground focus to settle
            if select_all_first:
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.08)

            # Fast, reliable Unicode paste via win32clipboard
            try:
                import win32clipboard
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text_to_type, win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
                pyautogui.hotkey('ctrl', 'v')
            except Exception:
                pyautogui.write(text_to_type, interval=0.01)

            return {
                "success": True,
                "response": "Pasted corrected text directly into your editor.",
                "tts": "Corrected text inserted."
            }
        except Exception as e:
            return {"success": False, "response": f"Typing error: {e}"}

    def _action_explain_screen_content(self, screenshot, focus="code") -> Dict[str, Any]:
        """Explains active code, error logs, or application screen"""
        prompt = "Look at the code/content visible on the screen. Explain clearly in 2-3 sentences what this code does and highlight any key logic or errors."
        mm = self._ensure_multimodal_ai()
        analysis = mm.analyze_image(screenshot, prompt=prompt)
        desc = analysis.get("description", "Analysis complete.")
        return {
            "success": True,
            "response": desc,
            "tts": desc[:180],
            "card": {"type": "code", "title": "💻 Screen Code Insight", "body": desc}
        }

    def _action_summarize_pdf_screen(self, screenshot) -> Dict[str, Any]:
        """Summarizes key points from visible document/PDF"""
        prompt = "Look at the document/PDF open on screen. Extract the 3 most important takeaways and bullet points."
        mm = self._ensure_multimodal_ai()
        analysis = mm.analyze_image(screenshot, prompt=prompt)
        desc = analysis.get("description", "Document summary complete.")
        return {
            "success": True,
            "response": desc,
            "tts": "Here are the key takeaways from the document on your screen.",
            "card": {"type": "pdf", "title": "📄 Document Key Takeaways", "body": desc}
        }

    # -------------------------------------------------------------
    # 6. Communication Dispatcher (WhatsApp, Gmail, Calendar)
    # -------------------------------------------------------------
    def execute_communication(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sends WhatsApp messages, checks Gmail inbox, and queries Google Calendar"""
        c_action = action.lower()

        # WhatsApp Message
        if "whatsapp" in c_action or "whatsapp" in str(params).lower():
            contact = params.get("contact") or params.get("name") or "friend"
            message = params.get("message") or params.get("text") or "Hello"
            try:
                from ai_assistant.integrations.whatsapp import send_whatsapp_message
                res = send_whatsapp_message(contact, message)
                return {
                    "success": True,
                    "response": f"Sent WhatsApp message to {contact}: \"{message}\"",
                    "tts": f"Sent WhatsApp message to {contact}.",
                    "card": {"type": "whatsapp", "title": f"💬 WhatsApp to {contact}", "body": message}
                }
            except Exception as e:
                return {"success": False, "response": f"Could not send WhatsApp message: {e}"}

        # Gmail Check
        if "email" in c_action or "mail" in c_action:
            try:
                from ai_assistant.integrations.email_handler import GmailManager
                gm = GmailManager()
                unread = gm.get_unread_count()
                summary = gm.get_inbox_summary(max_emails=3)
                return {
                    "success": True,
                    "response": f"You have {unread} unread emails.\n{summary}",
                    "tts": f"You have {unread} unread emails.",
                    "card": {"type": "email", "title": f"📧 Inbox ({unread} unread)", "body": summary}
                }
            except Exception as e:
                return {"success": False, "response": f"Could not access Gmail: {e}"}

        # Calendar Events
        if "calendar" in c_action or "meeting" in c_action:
            try:
                from ai_assistant.integrations.google_calendar import CalendarManager
                cal = CalendarManager()
                events = cal.get_upcoming_events(days_ahead=3)
                return {
                    "success": True,
                    "response": f"Here are your upcoming calendar events:\n{events}",
                    "tts": "Here is your upcoming schedule.",
                    "card": {"type": "calendar", "title": "📅 Upcoming Schedule", "body": events}
                }
            except Exception as e:
                return {"success": False, "response": f"Could not access Calendar: {e}"}

        return {"success": False, "response": f"Unrecognized communication action: {action}"}

    # -------------------------------------------------------------
    # 7. Media Controller (Spotify, YouTube, Windows Media)
    # -------------------------------------------------------------
    def execute_media_control(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Controls media playback using Spotify API or native Windows media virtual keys"""
        action = action.lower()

        # Virtual Key Codes for Universal Windows Media Control
        VK_MEDIA_NEXT_TRACK = 0xB0
        VK_MEDIA_PREV_TRACK = 0xB1
        VK_MEDIA_PLAY_PAUSE = 0xB3

        def _send_media_key(key_code):
            if WIN32_AVAILABLE:
                win32api.keybd_event(key_code, 0, 0, 0)
                time.sleep(0.05)
                win32api.keybd_event(key_code, 0, win32con.KEYEVENTF_KEYUP, 0)

        if "next" in action or "skip" in action:
            try:
                from ai_assistant.integrations.music import spotify_next_track
                spotify_next_track()
            except Exception:
                pass
            _send_media_key(VK_MEDIA_NEXT_TRACK)
            return {"success": True, "response": "Skipped to next track.", "tts": "Skipping to next track."}

        elif "prev" in action or "previous" in action:
            try:
                from ai_assistant.integrations.music import spotify_previous_track
                spotify_previous_track()
            except Exception:
                pass
            _send_media_key(VK_MEDIA_PREV_TRACK)
            return {"success": True, "response": "Playing previous track.", "tts": "Playing previous track."}

        elif "pause" in action or "play" in action or "play_pause" in action:
            try:
                from ai_assistant.integrations.music import spotify_play_pause
                spotify_play_pause()
            except Exception:
                pass
            _send_media_key(VK_MEDIA_PLAY_PAUSE)
            return {"success": True, "response": "Toggled media playback.", "tts": "Playback toggled."}

        return {"success": False, "response": f"Unknown media action: {action}"}

    # -------------------------------------------------------------
    # 8. System Controls (Volume, Brightness, Apps)
    # -------------------------------------------------------------
    def execute_system_control(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Manages hardware settings and applications"""
        action = str(action or "").lower().strip()
        params = params or {}

        if action in ("volume_control", "volume_set", "volume_up", "volume_down", "mute", "unmute"):
            vol_params = dict(params)
            if action == "volume_set":
                vol_params["action"] = "set"
            elif action == "volume_up":
                vol_params["action"] = "up"
            elif action == "volume_down":
                vol_params["action"] = "down"
            elif action == "mute":
                vol_params["action"] = "mute"
            elif action == "unmute":
                vol_params["action"] = "unmute"
            try:
                from ai_assistant.core.intent_executor import get_intent_executor
                from ai_assistant.core.conversation_context import get_context_manager
                res = get_intent_executor().execute("volume_control", vol_params, context_manager=get_context_manager())
                msg = str(res.get("result") or res.get("error") or f"Executed {action}")
                ok = bool(res.get("success", False)) and not msg.startswith(("❌", "Error"))
                return {"success": ok, "response": msg, "tts": msg[:150]}
            except Exception as e:
                return {"success": False, "response": f"Could not control volume: {e}", "tts": "Failed to control system volume."}

        if action in ("open_app", "launch_app", "launch") or "open_app" in action or "launch" in action:
            try:
                from settings_manager import is_app_execution_allowed
                if not is_app_execution_allowed():
                    return {
                        "success": False,
                        "response": "Application launching is disabled by your Security -> Permissions settings.",
                        "tts": "App launching is disabled in security settings."
                    }
            except Exception:
                pass
            app_name = params.get("app_name") or params.get("target") or params.get("name") or "browser"
            try:
                from ai_assistant.core.intent_executor import get_intent_executor
                res = get_intent_executor().execute("open_app", {"app_name": app_name})
                r_val = res.get("result")
                msg = r_val.get("message") if isinstance(r_val, dict) else (str(r_val) if r_val else str(res.get("error") or ""))
                ok = bool(res.get("success", False)) and not ("❌" in msg and "✅" not in msg)
                if ok:
                    return {"success": True, "response": msg or f"Launched {app_name}.", "tts": f"Opening {app_name}."}
                return {"success": False, "response": msg or f"Could not open {app_name}.", "tts": f"Could not open {app_name}."}
            except Exception as e:
                return {"success": False, "response": f"Error opening {app_name}: {e}"}

        if action in ("close_app", "quit_app"):
            try:
                from settings_manager import is_app_execution_allowed
                if not is_app_execution_allowed():
                    return {
                        "success": False,
                        "response": "Application execution/closing is disabled by your Security -> Permissions settings.",
                        "tts": "App execution is disabled in security settings."
                    }
            except Exception:
                pass
            app_name = params.get("app_name") or params.get("target") or params.get("name") or ""
            try:
                from ai_assistant.core.intent_executor import get_intent_executor
                res = get_intent_executor().execute("close_app", {"app_name": app_name})
                msg = str(res.get("result") or res.get("error") or f"Closed {app_name}")
                return {"success": bool(res.get("success", False)), "response": msg, "tts": msg[:120]}
            except Exception as e:
                return {"success": False, "response": f"Error closing {app_name}: {e}"}

        executor_map = {
            "wifi_toggle": "wifi_toggle",
            "toggle_wifi": "wifi_toggle",
            "bluetooth_toggle": "bluetooth_toggle",
            "toggle_bluetooth": "bluetooth_toggle",
            "set_brightness": "set_brightness",
            "brightness_control": "set_brightness",
            "dark_mode_toggle": "dark_mode_toggle",
            "battery_status": "battery_status",
            "list_running_apps": "list_running_apps",
            "open_settings": "open_settings",
            "youtube_search": "youtube_search",
            "youtube_history": "youtube_history",
            "play_media": "play_media",
            "shutdown": "system_control",
            "restart": "system_control",
            "sleep": "system_control",
            "lock": "system_control",
        }
        if action in executor_map:
            if action in (
                "wifi_toggle", "toggle_wifi", "bluetooth_toggle", "toggle_bluetooth",
                "set_brightness", "brightness_control", "dark_mode_toggle",
                "open_settings", "shutdown", "restart", "sleep", "lock",
            ):
                try:
                    from settings_manager import is_system_control_allowed
                    if not is_system_control_allowed():
                        return {
                            "success": False,
                            "response": "System control commands are disabled by your Security -> Permissions settings.",
                            "tts": "System control is disabled in security settings."
                        }
                except Exception:
                    pass
            exec_intent = executor_map[action]
            exec_params = dict(params)
            if exec_intent == "system_control":
                exec_params.setdefault("action", action)
            try:
                from ai_assistant.core.intent_executor import get_intent_executor
                from ai_assistant.core.conversation_context import get_context_manager
                res = get_intent_executor().execute(exec_intent, exec_params, context_manager=get_context_manager())
                r_val = res.get("result")
                msg = r_val.get("message") if isinstance(r_val, dict) else str(r_val or res.get("error") or f"Executed {action}")
                return {"success": bool(res.get("success", False)), "response": msg, "tts": msg[:150]}
            except Exception as e:
                return {"success": False, "response": f"Error executing {action}: {e}"}

        return {
            "success": False,
            "response": f"Unsupported system control action: {action}",
            "tts": "I could not execute that system command.",
        }

    # -------------------------------------------------------------
    # 9. Background Tasks (Web Research while user works)
    # -------------------------------------------------------------
    def execute_background_task(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Runs web searches or research in the background without stealing focus"""
        query = params.get("query") or params.get("search_term") or action
        active_provider = self._get_active_provider_name()
        active_model = self._get_active_model_name()

        def _do_search():
            summary = None
            prompt_text = f"Research this query and summarize the most important facts in 3 crisp sentences: {query}"

            try:
                if active_provider == "gemini":
                    from settings_manager import get_api_key
                    gemini_key = get_api_key("gemini") or os.getenv("GEMINI_API_KEY")
                    if gemini_key:
                        import google.generativeai as genai
                        genai.configure(api_key=gemini_key)
                        model = genai.GenerativeModel(active_model if "gemini" in active_model else "gemini-2.5-flash")
                        resp = model.generate_content(prompt_text)
                        summary = resp.text.strip()
            except Exception as e:
                logger.warning(f"Background Gemini search failed: {e}")

            is_local_req = active_provider in ("gguf", "local", "offline")
            if not summary and (is_local_req or active_provider in ("gemini", "openai")):
                try:
                    from ai_assistant.ai.llm_provider import UnifiedChatInterface
                    target_prov = active_provider if active_provider in ("gguf", "openai", "local", "offline") else "gguf"
                    target_mod = active_model if target_prov == active_provider else "pulsar-final-q4_k_m"
                    chat_iface = UnifiedChatInterface(
                        provider=target_prov,
                        model=target_mod,
                        use_fallback=not is_local_req,
                    )
                    res_text = str(chat_iface.chat(prompt_text, stream=False)).strip()
                    if res_text and not res_text.startswith("Error:"):
                        summary = res_text
                except Exception as e2:
                    logger.warning(f"Background local/provider search failed: {e2}")

            if not summary:
                try:
                    from ai_assistant.core.core import search_google
                    summary = search_google(query)
                except Exception:
                    summary = f"Opened/completed background lookup for: {query}"

            try:
                from notification_monitor import get_notification_monitor
                monitor = get_notification_monitor()
                if monitor:
                    monitor.push_notification({
                        "type": "research",
                        "title": f"🔍 Research: {query[:25]}...",
                        "body": summary,
                        "priority": "normal",
                        "actions": ["Show", "Dismiss"]
                    })
            except Exception as e:
                logger.warning(f"Background notification push failed: {e}")

            try:
                from ai_assistant.core.jarvis_persona import get_lifecycle_coordinator
                get_lifecycle_coordinator().speak_proactive_report(
                    title=query,
                    summary=summary or "",
                    source="background_task",
                    speak=True,
                )
            except Exception as e:
                logger.debug(f"Background proactive report skipped: {e}")

        threading.Thread(target=_do_search, daemon=True).start()

        return {
            "success": True,
            "response": f"I'm searching for '{query}' in the background. I'll notify you as soon as I have the summary!",
            "tts": "I'm researching that in the background for you."
        }

    # -------------------------------------------------------------
    # 10. General Chat & Empathy
    # -------------------------------------------------------------
    def _execute_conversational_response(self, command: str, window_info: Dict[str, Any], include_screen: bool = False) -> Dict[str, Any]:
        """Generates friendly, helpful conversational AI responses with dynamic provider routing and GGUF fallback."""
        import time
        start_t = time.time()
        active_provider = self._get_active_provider_name()
        active_model = self._get_active_model_name()

        try:
            from ai_assistant.core.jarvis_persona import build_persona_system_prompt
            system_context = build_persona_system_prompt(
                provider=active_provider,
                model=active_model,
                active_window=window_info if include_screen else None,
                surface="companion",
            )
        except Exception:
            win_line = (
                f"Active application on screen: {window_info.get('title', 'Desktop')} ({window_info.get('app_name', 'System')}).\n"
                if include_screen
                else ""
            )
            system_context = (
                f"You are Pulsar, a brilliant, friendly, personal desktop AI companion.\n"
                f"You speak natural English or Hindi/Hinglish depending on the user.\n"
                f"{win_line}"
                f"Keep your direct response concise (1-3 sentences)."
            )

        reply = None
        actual_provider = active_provider
        actual_model = active_model
        fallback = False
        fallback_reason = None

        # --- ROUTE 1: OpenAI ---
        if active_provider == 'openai':
            try:
                from settings_manager import get_api_key
                openai_key = get_api_key('openai') or os.getenv('OPENAI_API_KEY')
                if not openai_key:
                    raise ValueError("OPENAI_API_KEY is not configured in Settings > Security.")
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                target_m = active_model if 'gpt' in active_model else 'gpt-4o-mini'
                actual_model = target_m
                completion = client.chat.completions.create(
                    model=target_m,
                    messages=[
                        {"role": "system", "content": system_context},
                        {"role": "user", "content": command}
                    ],
                    max_tokens=500
                )
                reply = completion.choices[0].message.content.strip()
            except Exception as e:
                logger.warning(f"OpenAI routing failed: {e}")
                fallback = True
                fallback_reason = str(e)

        # --- ROUTE 2: Local GGUF ---
        elif active_provider in ('gguf', 'local', 'offline'):
            try:
                from ai_assistant.ai.llm_provider import UnifiedChatInterface, LLMFactory
                target_m = LLMFactory.sanitize_model_for_provider('gguf', active_model)
                chat_iface = UnifiedChatInterface(provider='gguf', model=target_m, use_fallback=False)
                chat_iface.set_system_message(system_context)
                res_txt = str(chat_iface.chat(command, stream=False)).strip()
                if res_txt.startswith("Error:"):
                    raise RuntimeError(res_txt)
                reply = res_txt
                actual_provider = 'gguf'
                actual_model = getattr(chat_iface, 'model', target_m)
            except Exception as e:
                logger.warning(f"GGUF routing failed: {e}")
                fallback_reason = f"Local GGUF engine failed: {e}"

        # --- ROUTE 3: Google Gemini (when active) ---
        elif active_provider == 'gemini':
            try:
                import google.generativeai as genai
                from settings_manager import get_api_key
                gemini_key = get_api_key('gemini') or os.getenv('GEMINI_API_KEY')
                if not gemini_key:
                    raise ValueError("GEMINI_API_KEY not configured")
                genai.configure(api_key=gemini_key)
                target_m = active_model if 'gemini' in active_model else 'gemini-2.5-flash'
                actual_provider = 'gemini'
                actual_model = target_m
                model = genai.GenerativeModel(target_m)
                resp = model.generate_content(f"{system_context}\n\nUser: {command}")
                reply = (getattr(resp, 'text', '') or '').strip()
            except Exception as e:
                logger.warning(f"Gemini routing failed: {e}")
                fallback = True
                fallback_reason = str(e)

        # --- FALLBACK (Cloud -> Local GGUF ONLY; NEVER silently switch local -> cloud) ---
        is_local_req = active_provider in ('gguf', 'local', 'offline')
        if not reply and not is_local_req:
            try:
                from ai_assistant.ai.llm_provider import UnifiedChatInterface
                logger.info("Falling back to local GGUF model after cloud provider failure...")
                chat_iface = UnifiedChatInterface(provider='gguf', model='pulsar-final-q4_k_m', use_fallback=False)
                chat_iface.set_system_message(system_context)
                res_txt = str(chat_iface.chat(command, stream=False)).strip()
                if res_txt and not res_txt.startswith("Error:"):
                    reply = res_txt
                    actual_provider = 'gguf'
                    actual_model = getattr(chat_iface, 'model', 'pulsar-final-q4_k_m')
                    fallback = True
            except Exception as gguf_err:
                logger.warning(f"GGUF fallback also failed: {gguf_err}")

        succeeded = bool(reply)
        if not reply:
            detail = f" ({fallback_reason})" if fallback_reason else ""
            reply = f"Local/active AI model ({active_provider}) could not respond{detail}."

        latency_ms = round((time.time() - start_t) * 1000)
        result_payload = {
            "success": succeeded,
            "response": reply,
            "tts": reply[:180],
            "card": {"type": "chat", "title": f"🤖 Pulsar ({actual_provider})", "body": reply},
            "execution_meta": {
                "provider_requested": active_provider,
                "provider_used": actual_provider if succeeded else active_provider,
                "model_requested": active_model,
                "model_used": actual_model,
                "latency_ms": latency_ms,
                "fallback": fallback,
                "fallback_reason": fallback_reason
            }
        }
        if not succeeded:
            result_payload["error"] = fallback_reason or reply
        return result_payload

    # -------------------------------------------------------------
    # 11. Tier 3 Safety & Confirmation Store
    # -------------------------------------------------------------
    def _create_pending_confirmation(self, command: str, intent: str, action: str, params: Dict[str, Any], classification: Dict[str, Any]) -> Dict[str, Any]:
        """Stores action and returns a confirmation card for the user"""
        action_id = f"act_{int(time.time() * 1000)}"
        summary = classification.get("summary") or f"Execute {action}"

        self.pending_actions[action_id] = {
            "command": command,
            "intent": intent,
            "action": action,
            "params": params,
            "timestamp": time.time()
        }

        return {
            "success": True,
            "requires_confirmation": True,
            "action_id": action_id,
            "response": f"Are you sure you want me to: {summary}?",
            "tts": f"Please confirm: should I {summary}?",
            "card": {
                "type": "confirmation",
                "action_id": action_id,
                "title": "⚠️ Confirmation Required",
                "body": summary,
                "actions": ["Confirm", "Cancel"]
            }
        }

    def _check_pending_confirmation(self, command: str) -> Optional[Dict[str, Any]]:
        """Checks if user's speech is answering a pending confirmation"""
        if not self.pending_actions:
            return None

        c = command.lower()
        is_yes = any(w in c for w in ["yes", "haan", "ha", "sure", "confirm", "proceed", "kar do", "bhej do"])
        is_no = any(w in c for w in ["no", "nahi", "cancel", "mat karo", "abort", "stop"])

        if not (is_yes or is_no):
            return None

        # Grab latest pending action
        latest_id = list(self.pending_actions.keys())[-1]
        action_data = self.pending_actions.pop(latest_id)

        if is_no:
            return {
                "success": True,
                "response": "Action cancelled.",
                "tts": "Cancelled."
            }

        if is_yes:
            # Execute the stored gated action
            intent = action_data["intent"]
            action = action_data["action"]
            params = action_data["params"]
            window_info = self.get_active_window_info()

            if intent == "screen_action":
                return self.execute_screen_action(action, params, window_info)
            elif intent == "communication":
                return self.execute_communication(action, params)
            elif intent == "system_control":
                return self.execute_system_control(action, params)

        return None

    def confirm_action_by_id(self, action_id: str, confirmed: bool) -> Dict[str, Any]:
        """Called via API when user clicks 'Confirm' or 'Cancel' on a notification card"""
        if action_id not in self.pending_actions:
            return {"success": False, "response": "Action expired or already processed."}

        action_data = self.pending_actions.pop(action_id)
        if not confirmed:
            return {"success": True, "response": "Action cancelled.", "tts": "Action cancelled."}

        intent = action_data["intent"]
        action = action_data["action"]
        params = action_data["params"]
        window_info = self.get_active_window_info()

        if intent == "screen_action":
            return self.execute_screen_action(action, params, window_info)
        elif intent == "communication":
            return self.execute_communication(action, params)
        elif intent == "system_control":
            return self.execute_system_control(action, params)

        return {"success": True, "response": "Action completed."}


_global_brain = None

def get_agent_brain() -> AgentBrain:
    """Singleton getter for AgentBrain"""
    global _global_brain
    if _global_brain is None:
        _global_brain = AgentBrain()
    return _global_brain
