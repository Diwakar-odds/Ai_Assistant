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

# Ensure project paths are available
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))
sys.path.insert(0, str(project_root / "core_ai" / "src"))
sys.path.insert(0, str(project_root / "shared"))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

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

    def capture_screen(self, region=None):
        """High-speed screen capture via MultiModalAI / mss"""
        if self.multimodal_ai is None:
            from ai_assistant.vision.multimodal import MultiModalAI
            self.multimodal_ai = MultiModalAI()
        return self.multimodal_ai.capture_screen(region=region, use_cache=False)

    # -------------------------------------------------------------
    # 2. Main Processing & Intent Routing
    # -------------------------------------------------------------
    def process_command(self, command: str, include_screen: bool = False, source: str = "COMPANION_DESKTOP") -> Dict[str, Any]:
        """
        Receives user natural language command, perceives context,
        reasons on intent, and executes corresponding tool.
        """
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
        c = command.lower()

        # Media Control: Skip / Next
        if any(w in c for w in ["skip song", "next song", "gaana skip", "next track", "skip track", "skip karo"]):
            return self.execute_media_control("next", {})

        # Media Control: Pause / Play
        if any(w in c for w in ["pause video", "play video", "pause song", "play song", "gaana pause", "gaana roko", "pause karo"]):
            return self.execute_media_control("play_pause", {})

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
    def _classify_intent(self, command: str, window_info: Dict[str, Any], include_screen: bool = False) -> Dict[str, Any]:
        """Uses Gemini to classify user intent, parameters, and risk tier"""
        prompt = f"""You are the intent routing engine for Pulsar, an autonomous desktop AI assistant.
User command: "{command}"
Active Window: "{window_info.get('title', 'Unknown')}" (App: {window_info.get('app_name', 'Unknown')})

Classify the command into one of these intents:
1. "screen_action": Interacting with screen content (checking email grammar, reading/explaining code or PDF, clicking buttons like end video call, typing text).
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
            if self.multimodal_ai is None:
                from ai_assistant.vision.multimodal import MultiModalAI
                self.multimodal_ai = MultiModalAI()

            # We can use Gemini's fast text/vision interface
            import google.generativeai as genai
            model = genai.GenerativeModel("gemini-2.5-flash")
            resp = model.generate_content(prompt)
            raw = resp.text.strip()
            # Clean markdown codeblocks
            raw = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"^```\s*", "", raw, flags=re.MULTILINE)
            raw = raw.strip()
            parsed = json.loads(raw)
            parsed["_engine"] = "Google Gemini 2.5 Flash (Cloud)"
            return parsed
        except Exception as e:
            logger.warning(f"LLM classification fallback due to: {e}")
            # Heuristic fallback
            c = command.lower()
            engine_tag = "Local Heuristic Fallback"
            if any(k in c for k in ["grammar", "spelling", "check email", "screen", "pdf", "code", "call", "kaat"]):
                return {"intent": "screen_action", "action": "analyze_or_act", "params": {}, "risk_tier": 1, "_engine": engine_tag}
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
        analysis = self.multimodal_ai.analyze_image(
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

        analysis = self.multimodal_ai.analyze_image(screenshot, prompt=prompt)
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

        analysis = self.multimodal_ai.analyze_image(screenshot, prompt=prompt)
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
        analysis = self.multimodal_ai.analyze_image(screenshot, prompt=prompt)
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
        analysis = self.multimodal_ai.analyze_image(screenshot, prompt=prompt)
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
        action = action.lower()

        if "volume_up" in action:
            try:
                from ai_assistant.core.core import volume_up
                msg = volume_up()
                return {"success": True, "response": "Turned volume up.", "tts": "Volume up."}
            except Exception:
                pass

        if "volume_down" in action:
            try:
                from ai_assistant.core.core import volume_down
                msg = volume_down()
                return {"success": True, "response": "Turned volume down.", "tts": "Volume down."}
            except Exception:
                pass

        if "mute" in action:
            try:
                from ai_assistant.core.core import mute_volume
                msg = mute_volume()
                return {"success": True, "response": "Muted system audio.", "tts": "Muted."}
            except Exception:
                pass

        if "open_app" in action or "launch" in action:
            app_name = params.get("app_name") or params.get("name") or "browser"
            from ai_assistant.automation.app_discovery import smart_open_application
            msg = smart_open_application(app_name)
            return {"success": True, "response": f"Launched {app_name}.", "tts": f"Opening {app_name}."}

        return {"success": True, "response": f"Executed system control: {action}"}

    # -------------------------------------------------------------
    # 9. Background Tasks (Web Research while user works)
    # -------------------------------------------------------------
    def execute_background_task(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Runs web searches or research in the background without stealing focus"""
        query = params.get("query") or params.get("search_term") or action

        def _do_search():
            try:
                import google.generativeai as genai
                model = genai.GenerativeModel("gemini-2.5-flash")
                resp = model.generate_content(
                    f"Research this query and summarize the most important facts in 3 crisp sentences: {query}"
                )
                summary = resp.text.strip()
                # Post notification back to the system
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
                logger.warning(f"Background search failed: {e}")

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
        """Generates friendly, helpful conversational AI responses"""
        try:
            import google.generativeai as genai
            model = genai.GenerativeModel("gemini-2.5-flash")
            system_context = f"""You are Pulsar, a brilliant, friendly, personal desktop AI assistant.
You speak natural English or Hindi/Hinglish depending on the user.
Active application on screen: {window_info.get('title', 'Desktop')} ({window_info.get('app_name', 'System')}).
Keep your direct response concise (1-3 sentences) suitable for a desktop floating companion robot."""

            resp = model.generate_content(f"{system_context}\n\nUser: {command}")
            reply = resp.text.strip()
            return {
                "success": True,
                "response": reply,
                "tts": reply[:180],
                "card": {"type": "chat", "title": "🤖 Pulsar", "body": reply}
            }
        except Exception as e:
            return {
                "success": True,
                "response": f"I am online and ready to assist you. What would you like me to do?",
                "tts": "All systems online. How can I help?"
            }

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

        return {"success": True, "response": "Action completed."}


_global_brain = None

def get_agent_brain() -> AgentBrain:
    """Singleton getter for AgentBrain"""
    global _global_brain
    if _global_brain is None:
        _global_brain = AgentBrain()
    return _global_brain
