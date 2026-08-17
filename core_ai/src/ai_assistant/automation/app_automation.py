"""
Application Automation Module

Handles automation of Windows applications including:
- Sticky Notes (reading, creating, editing)
- WhatsApp (enhanced message sending)
- Generic window management

Uses combination of:
- pyautogui for GUI automation
- pywinauto for Windows app control
- OCR for text extraction
- TTS for reading content
"""

import os
import time
import logging
from typing import Optional, List, Dict, Any
import subprocess
import tempfile

# Windows automation (lazy-loaded to avoid import-time hangs on some systems)
pyautogui = None
WINDOWS_AUTO_AVAILABLE = False

# OCR for reading notes
try:
    import pytesseract
    from PIL import Image, ImageGrab
    OCR_AVAILABLE = True
except Exception as e:
    OCR_AVAILABLE = False
    print(f"âš ï¸ OCR not available: {e}")

# WhatsApp helpers are lazy-loaded to avoid heavy optional import chains.
send_whatsapp_message = None
WHATSAPP_MODULE_AVAILABLE = False

# TTS for reciting notes
try:
    import pyttsx3
    TTS_AVAILABLE = True
except Exception as e:
    TTS_AVAILABLE = False
    print(f"âš ï¸ TTS not available: {e}")

logger = logging.getLogger(__name__)


def _ensure_pyautogui() -> bool:
    """Lazy-load pyautogui only when an action requires it."""
    global pyautogui, WINDOWS_AUTO_AVAILABLE

    if pyautogui is not None:
        WINDOWS_AUTO_AVAILABLE = True
        return True

    try:
        import pyautogui as _pyautogui

        pyautogui = _pyautogui
        WINDOWS_AUTO_AVAILABLE = True
        return True
    except Exception as e:
        WINDOWS_AUTO_AVAILABLE = False
        logger.error(f"âŒ pyautogui unavailable: {e}")
        return False


def _get_desktop_class():
    """Lazy-load pywinauto Desktop class only when window focus is needed."""
    try:
        from pywinauto import Desktop

        return Desktop
    except Exception as e:
        logger.error(f"âŒ pywinauto unavailable: {e}")
        return None


def _ensure_whatsapp_module() -> bool:
    """Lazy-load WhatsApp helper module only when message features are used."""
    global send_whatsapp_message, WHATSAPP_MODULE_AVAILABLE

    if send_whatsapp_message is not None:
        WHATSAPP_MODULE_AVAILABLE = True
        return True

    try:
        from ai_assistant.integrations.whatsapp import send_whatsapp_message as _send_whatsapp_message

        send_whatsapp_message = _send_whatsapp_message
        WHATSAPP_MODULE_AVAILABLE = True
        return True
    except Exception as e:
        WHATSAPP_MODULE_AVAILABLE = False
        logger.error(f"âŒ WhatsApp module unavailable: {e}")
        return False


class AppAutomation:
    """
    Generic application automation handler
    """
    
    def __init__(self):
        """Initialize app automation"""
        self.active_windows = {}
        logger.info("✅ AppAutomation initialized")
    
    def open_app(self, app_name: str) -> bool:
        """
        Open an application natively (Windows or Web).
        """
        logger.info(f"📱 Opening app: {app_name}")
        
        try:
            from ai_assistant.automation.app_discovery import smart_open_application
            
            # Execute the smart launcher which handles both Web Apps and Native Windows Apps
            result_msg = smart_open_application(app_name)
            
            if "✅" in result_msg:
                logger.info(result_msg)
                return True
            else:
                logger.error(result_msg)
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to execute open_app: {e}")
            return False

    def search_web(self, query: str) -> bool:
        """Search the web for a query."""
        logger.info(f"🌐 Searching web for: {query}")
        try:
            import urllib.parse
            import webbrowser
            encoded_query = urllib.parse.quote_plus(query)
            url = f"https://www.google.com/search?q={encoded_query}"
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to search web: {e}")
            return False

    def play_media(self, query: str) -> bool:
        """Play media (music/video) by delegating to smart launcher."""
        logger.info(f"🎵 Playing media: {query}")
        try:
            from ai_assistant.automation.app_discovery import smart_open_application
            
            # Delegate to smart app launcher with action_type='play_music'
            # This allows it to check the user's preferred music player
            result_msg = smart_open_application(query, action_type='play_music')
            
            if "✅" in result_msg:
                logger.info(result_msg)
                return True
            else:
                logger.error(result_msg)
                return False
        except Exception as e:
            logger.error(f"❌ Failed to play media: {e}")
            return False
            
    def type_text(self, text: str, interval: float = 0.05) -> bool:
        """Type text using keyboard simulation"""
        if not _ensure_pyautogui():
            return False
        try:
            logger.info(f"âŒ¨ï¸ Typing: {text}")
            pyautogui.write(text, interval=interval)
            return True
        except Exception as e:
            logger.error(f"âŒ Failed to type text: {e}")
            return False
            
    def press_key(self, key_name: str) -> bool:
        """Press a keyboard key"""
        if not _ensure_pyautogui():
            return False
        try:
            logger.info(f"âŒ¨ï¸ Pressing key: {key_name}")
            pyautogui.press(key_name)
            return True
        except Exception as e:
            logger.error(f"âŒ Failed to press key: {e}")
            return False

    def click(self, x: int = None, y: int = None) -> bool:
        """Click mouse (at current position or specific coords)"""
        if not _ensure_pyautogui():
            return False
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y)
            else:
                pyautogui.click()
            return True
        except Exception as e:
            logger.error(f"âŒ Failed to click: {e}")
            return False
    
    def close_app(self, app_name: str) -> bool:
        """Close an application"""
        if not app_name:
            logger.error("âŒ close_app called without an app name")
            return False

        logger.info(f"ðŸ›‘ Closing app: {app_name}")

        def _run_taskkill(args: List[str]) -> subprocess.CompletedProcess:
            try:
                return subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    timeout=6,
                )
            except subprocess.TimeoutExpired:
                logger.warning(f"âš ï¸ taskkill timed out: {' '.join(args)}")
                return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="timeout")

        # Use taskkill first to avoid UI Automation hangs on some systems.
        try:
            token = app_name.strip().strip('"').split()[0]
            process_candidates = [token]
            if not token.lower().endswith('.exe'):
                process_candidates.append(f"{token}.exe")

            any_closed = False
            process_outputs = []
            for process_name in process_candidates:
                result = _run_taskkill(["taskkill", "/IM", process_name, "/F"])
                process_outputs.extend([result.stdout or "", result.stderr or ""])
                if result.returncode == 0:
                    logger.info(f"✅ Force-closed process: {process_name}")
                    any_closed = True

            # Try title filter as a secondary strategy.
            title_result = _run_taskkill(["taskkill", "/FI", f"WINDOWTITLE eq *{app_name}*", "/F"])
            if title_result.returncode == 0 and "No tasks running" not in title_result.stdout:
                logger.info(f"✅ Closed by window title filter: {app_name}")
                any_closed = True

            if any_closed:
                return True

            combined_output = " ".join(
                [*process_outputs, title_result.stdout or "", title_result.stderr or ""]
            ).lower()
            if (
                "no tasks" in combined_output
                or "no running" in combined_output
                or "not found" in combined_output
                or "no instances" in combined_output
            ):
                logger.info(f"â„¹ï¸ App already closed or not found: {app_name}")
                return True

            logger.warning(f"âš ï¸ Could not close app: {app_name}")
            return False
        except Exception as e:
            logger.error(f"âŒ Failed to close app '{app_name}': {e}")
            return False
    
    def focus_window(self, window_title: str) -> bool:
        """Focus a window by title"""
        desktop_class = _get_desktop_class()
        if desktop_class is None:
            return False
        
        try:
            # Find and focus window
            windows = desktop_class(backend="uia").windows()
            
            for window in windows:
                if window_title.lower() in window.window_text().lower():
                    window.set_focus()
                    logger.info(f"âœ… Focused window: {window.window_text()}")
                    return True
            
            logger.warning(f"âš ï¸ Window not found: {window_title}")
            return False
            
        except Exception as e:
            logger.error(f"âŒ Failed to focus window: {e}")
            return False


class StickyNotesAutomation(AppAutomation):
    """
    Windows Sticky Notes automation
    """
    
    APP_NAME = "Microsoft.MicrosoftStickyNotes"
    WINDOW_TITLE = "Sticky Notes"
    
    def __init__(self):
        super().__init__()
        self.tts_engine = None
        if TTS_AVAILABLE:
            self.tts_engine = pyttsx3.init()
    
    def open_sticky_notes(self) -> bool:
        """Open Sticky Notes app"""
        logger.info("ðŸ“ Opening Sticky Notes...")

        if not _ensure_pyautogui():
            logger.error("âŒ Windows automation not available for Sticky Notes")
            return False
        
        # Try to open via start menu search
        try:
            pyautogui.press('win')
            time.sleep(0.5)
            pyautogui.typewrite('sticky notes', interval=0.1)
            time.sleep(0.5)
            pyautogui.press('enter')
            time.sleep(2)
            
            logger.info("âœ… Sticky Notes opened")
            return True
            
        except Exception as e:
            logger.error(f"âŒ Failed to open Sticky Notes: {e}")
            return False
    
    def read_notes(self, speak: bool = False) -> List[str]:
        """
        Read all visible sticky notes using OCR
        
        Args:
            speak: Whether to speak the notes aloud
        
        Returns:
            List of note contents
        """
        if not OCR_AVAILABLE:
            logger.error("âŒ OCR not available")
            return []
        
        logger.info("ðŸ“– Reading sticky notes...")
        
        try:
            # Focus Sticky Notes window
            self.focus_window(self.WINDOW_TITLE)
            time.sleep(1)
            
            # Take screenshot of entire screen
            screenshot = ImageGrab.grab()
            
            # Use OCR to extract text
            text = pytesseract.image_to_string(screenshot)
            
            # Split into individual notes (basic heuristic)
            notes = [line.strip() for line in text.split('\n') if line.strip()]
            notes = [note for note in notes if len(note) > 3]  # Filter short false positives
            
            logger.info(f"âœ… Found {len(notes)} notes")
            
            # Speak notes if requested
            if speak and self.tts_engine and notes:
                for i, note in enumerate(notes, 1):
                    self.tts_engine.say(f"Note {i}: {note}")
                self.tts_engine.runAndWait()
            
            return notes
            
        except Exception as e:
            logger.error(f"âŒ Failed to read notes: {e}")
            return []
    
    def create_note(self, content: str) -> bool:
        """
        Create a new sticky note
        
        Args:
            content: Note content
        
        Returns:
            Success status
        """
        logger.info(f"ðŸ“ Creating note: {content[:50]}...")

        if not _ensure_pyautogui():
            logger.error("âŒ Windows automation not available for creating notes")
            return False
        
        try:
            # Open or focus Sticky Notes
            if not self.focus_window(self.WINDOW_TITLE):
                self.open_sticky_notes()
            
            time.sleep(1)
            
            # Create new note (Ctrl+N)
            pyautogui.hotkey('ctrl', 'n')
            time.sleep(0.5)
            
            # Type content
            pyautogui.typewrite(content, interval=0.05)
            
            logger.info("âœ… Note created")
            return True
            
        except Exception as e:
            logger.error(f"âŒ Failed to create note: {e}")
            return False


class WhatsAppAutomation(AppAutomation):
    """
    Enhanced WhatsApp automation
    """
    
    def send_message(self, contact: str, message: str) -> bool:
        """
        Send WhatsApp message
        
        Args:
            contact: Contact name
            message: Message text
        
        Returns:
            Success status
        """
        logger.info(f"ðŸ’¬ Sending WhatsApp to {contact}")
        
        # Use existing WhatsApp module
        if _ensure_whatsapp_module():
            try:
                result = send_whatsapp_message(contact, message)
                logger.info(f"âœ… WhatsApp result: {result}")
                return "âœ…" in result
            except Exception as e:
                logger.error(f"âŒ WhatsApp failed: {e}")
                return False
        else:
            logger.error("âŒ WhatsApp module not available")
            return False
    
    def send_with_attachment(self, contact: str, message: str, file_path: str) -> bool:
        """
        Send message with attachment
        
        Args:
            contact: Contact name/number
            message: Message text
            file_path: Absolute path to file
            
        Returns:
            Success status
        """
        logger.info(f"ðŸ“Ž Sending WhatsApp to {contact} with attachment: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"âŒ Attachment not found: {file_path}")
            return False

        if not _ensure_pyautogui():
            logger.error("âŒ Windows automation (pyautogui/pywinauto) not available")
            return False
            
        try:
            # 1. Open WhatsApp & Chat (using standard send_message logic to get to chat)
            # We use the whatsapp:// protocol to open the chat window
            import webbrowser
            from urllib.parse import quote
            
            # Need a phone number or exact contact match for deep link.
            # If we don't have a phone number, we rely on the user having the chat open 
            # OR we try to finding it in the UI (harder).
            # For now, let's assume we can use the protocol if possible, or just focus window.
            
            # Try to get number if possible (imports inside method to avoid cycles)
            from ai_assistant.integrations.whatsapp import get_contact_number
            phone = get_contact_number(contact)
            
            if phone:
                url = f"whatsapp://send?phone={phone}&text={quote(message)}"
                webbrowser.open(url)
                time.sleep(3) # Wait for app to open/focus
            else:
                # If no phone number, we assume the contact name is searchable or recently used
                # This is a bit risky. Fallback: Request manual open or implement UI search.
                logger.warning(f"âš ï¸ No phone number for {contact}. Attempting to focus WhatsApp.")
                
                # Focus WhatsApp
                if not self.focus_window("WhatsApp"):
                    self.open_app("WhatsApp")
                    time.sleep(5)
                
                # Search for contact (Ctrl + F)
                pyautogui.hotkey('ctrl', 'f')
                time.sleep(0.5)
                pyautogui.write(contact)
                time.sleep(1)
                pyautogui.press('enter')
                time.sleep(1)
                
                # Type message
                if message:
                    pyautogui.write(message)
            
            time.sleep(2)
            
            # 2. Attach File
            # Standard shortcut for "Attach" in WhatsApp Desktop is not universal, 
            # usually we click the paperclip icon or copy-paste the file.
            
            # METHOD A: Copy-Paste File (Most robust)
            # This requires 'pyperclip' or similar to put file struct on clipboard, which is hard in pure python without win32api
            # OR using powershell to set clipboard.
            
            # METHOD B: UI Interaction (Click Clip -> Click Document -> Type Path)
            
            # Let's try the Clip Button approach if visual navigation works, 
            # BUT generic keyboard shortcuts are safer. 
            # WhatsApp Desktop: Shift+Tab to focus clip? No standard hotkey.
            
            # METHOD C: Drag and Drop (Simulated)? Hard.
            
            # METHOD D:  "Select File" Dialog
            # Click 'Attach' (Clip icon) -> assume it's near the text box? 
            # Or use Image recognition to find the clip icon.
            
            # Let's try finding the clip icon visually if possible (requires template matching)
            # IF NOT, fallback to:
            #   Focus text box -> Tab backwards?
            
            # SIMPLIFIED APPROACH for now:
            # We will use the 'Copy File' method if possible, otherwise we report limitation.
            # Actually, we can use the 'pywinauto' to find the button if we had the control ID.
            
            # Let's try the Visual approach since we have `pyautogui`
            # But we don't have the icon image. 
            #
            # ALTERNATIVE: Ctrl+V (Paste) the file path? No, that pastes text.
            
            # LET'S IMPLEMENT: "Document" attachment via Paperclip click (Blind coordinate guess relative to corners? No.)
            
            # BEST BET WITHOUT VISION: 
            # 1. Type message
            # 2. DON'T send yet.
            # 3. Use the 'Attach' button if we can find it.
            
            # Wait, there IS a shortcut to attach document in some versions: Ctrl+Shift+U (Upload)? No.
            
            # Let's use the `pywhatkit` style approach or just `pyperclip` to copy the file object?
            # It's complex. 
            
            # Let's try a simple visual search for the paperclip if we can. 
            # Since we don't have the asset, let's assume the user has to confirm or we implement a standard "Task" for the user.
            
            # REVISION: Implementing the "File Copy to Clipboard" using PowerShell is reliable.
            # Then Ctrl+V in WhatsApp.
            
            clipboard_result = subprocess.run(
                ["powershell", "-Command", "Set-Clipboard", "-Path", file_path],
                capture_output=True,
                text=True,
            )
            if clipboard_result.returncode != 0:
                logger.error(f"âŒ Failed to place attachment on clipboard: {clipboard_result.stderr}")
                return False
            
            time.sleep(1)
            
            # Paste in WhatsApp
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(2) # Wait for preview
            
            # Press Enter to send
            pyautogui.press('enter')
            
            logger.info("âœ… File pasted and sent")
            return True
            
        except Exception as e:
            logger.error(f"âŒ Failed to attach/send: {e}")
            return False


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test Sticky Notes
    sticky = StickyNotesAutomation()
    
    # Read existing notes
    notes = sticky.read_notes(speak=True)
    print(f"\nFound {len(notes)} notes:")
    for i, note in enumerate(notes, 1):
        print(f"{i}. {note}")
    
    # Create a new note
    # sticky.create_note("Test note from automation")

