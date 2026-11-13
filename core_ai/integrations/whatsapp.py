import os
import time
import json
import logging
import subprocess
import urllib.parse
import re
import difflib
from typing import Optional, Dict, Any, List

# Attach to default interactive desktop station before importing GUI / COM modules
def ensure_default_desktop():
    """Ensure the calling thread is attached to the default interactive desktop station."""
    try:
        import win32service, win32con, ctypes
        h_default = win32service.OpenDesktop('Default', 0, False, win32con.GENERIC_ALL)
        ctypes.windll.user32.SetThreadDesktop(int(h_default))
    except Exception:
        pass

ensure_default_desktop()

try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Safety failsafe must ALWAYS be enabled
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import win32gui
    import win32con
    import win32process
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

try:
    import win32com.client
    COM_AVAILABLE = True
except ImportError:
    COM_AVAILABLE = False

try:
    import pywinauto
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

logger = logging.getLogger(__name__)

try:
    from core_ai.config.paths import CONFIG_DIR
    CONTACTS_FILE = str(CONFIG_DIR / 'contacts.json')
except Exception:
    CONTACTS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'contacts.json')
    if not os.path.exists(CONTACTS_FILE):
        CONTACTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'contacts.json')


def load_contacts() -> Dict[str, Any]:
    """Load contacts configuration from disk."""
    if not os.path.exists(CONTACTS_FILE):
        return {}
    try:
        with open(CONTACTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading contacts: {e}")
        return {}


def save_contacts(contacts_dict: Dict[str, Any]) -> bool:
    """Save contacts configuration back to disk."""
    try:
        os.makedirs(os.path.dirname(CONTACTS_FILE), exist_ok=True)
        with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(contacts_dict, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving contacts: {e}")
        return False


def add_or_update_contact(key: str, search_name: Optional[str] = None, aliases: Optional[List[str]] = None, phone: Optional[str] = None) -> bool:
    """
    Dynamically add or update a contact in contacts.json.
    Supports expanding alias lists and search names.
    """
    contacts = load_contacts()
    k = key.lower().strip()
    entry = contacts.get(k, {})
    if isinstance(entry, str):
        entry = {"search_name": entry, "aliases": []}
    elif not isinstance(entry, dict):
        entry = {}

    entry["search_name"] = search_name or entry.get("search_name") or key.strip().title()
    existing_aliases = set(a.lower().strip() for a in entry.get("aliases", []))
    existing_aliases.add(k)
    if aliases:
        for a in aliases:
            if a.strip():
                existing_aliases.add(a.lower().strip())
    entry["aliases"] = sorted(list(existing_aliases))
    if phone:
        entry["phone"] = phone

    contacts[k] = entry
    return save_contacts(contacts)


def add_contact_alias(contact_name: str, new_alias: str) -> bool:
    """Dynamically add an alias for an existing or new contact."""
    resolved = resolve_contact_search_name(contact_name)
    contacts = load_contacts()
    target_key = None
    for k, v in contacts.items():
        if isinstance(v, dict) and v.get("search_name", "").lower() == resolved.lower():
            target_key = k
            break
        elif k.lower() == contact_name.lower():
            target_key = k
            break

    if not target_key:
        target_key = contact_name.lower().strip()

    return add_or_update_contact(target_key, search_name=resolved, aliases=[new_alias])


def _soundex(name: str) -> str:
    """Compute American Soundex code for phonetic matching."""
    name = re.sub(r'[^A-Za-z]', '', name).upper()
    if not name:
        return ""
    mapping = {
        'B': '1', 'F': '1', 'P': '1', 'V': '1',
        'C': '2', 'G': '2', 'J': '2', 'K': '2', 'Q': '2', 'S': '2', 'X': '2', 'Z': '2',
        'D': '3', 'T': '3',
        'L': '4',
        'M': '5', 'N': '5',
        'R': '6'
    }
    first = name[0]
    codes = [first]
    prev = mapping.get(first, '0')
    for char in name[1:]:
        code = mapping.get(char, '0')
        if code != '0':
            if code != prev:
                codes.append(code)
            prev = code
        else:
            prev = '0'
    return (''.join(codes) + '0000')[:4]


def _normalize_name(name: str) -> str:
    """Normalize a name by lowering, collapsing repeated characters, and mapping homophones."""
    s = name.lower().strip()
    s = s.replace('ck', 'k').replace('ph', 'f').replace('ee', 'i').replace('oo', 'u')
    s = re.sub(r'(.)\1+', r'\1', s)
    return s


def resolve_contact_search_name(contact_name: str) -> str:
    """
    Resolve contact aliases to their actual display/search name in WhatsApp.
    Supports case-insensitive, normalized, phonetic Soundex, and fuzzy string matching.
    e.g. 'nikky' / 'nicky' / 'niki' -> 'Niky', 'mom' / 'maa' / 'ammi' -> 'Mom', 'diwakar' -> 'Myself'
    """
    if not contact_name:
        return ""

    raw = contact_name.lower().strip()

    # Strip common filler/preposition prefixes
    for prefix in ['send to ', 'message to ', 'msg to ', 'to ']:
        if raw.startswith(prefix):
            raw = raw[len(prefix):].strip()

    # Strip common filler/preposition suffixes
    for suffix in ['on whatsapp', 'via whatsapp', 'ko', 'pe', 'par', 'mein', 'please']:
        if raw.endswith(suffix):
            raw = raw[:-len(suffix)].strip()

    # Preserve explicit international phone numbers
    clean_digits = ''.join(c for c in raw if c.isdigit() or c == '+')
    if len(clean_digits) >= 10 and (raw.startswith('+') or raw.isdigit()):
        return raw

    contacts = load_contacts()

    # 1. Exact match on dictionary key, search_name, or configured aliases
    for key, val in contacts.items():
        if isinstance(val, dict):
            search_name = val.get('search_name', key.title())
            aliases = [a.lower().strip() for a in val.get('aliases', [])]
            aliases.extend([key.lower(), search_name.lower()])
            if raw in aliases:
                return search_name
        elif isinstance(val, str) and not val.startswith('+') and not val.isdigit():
            if raw == key.lower() or raw == val.lower():
                return val

    # 2. Normalized match (deduping repeating letters, ck -> k, ph -> f)
    norm_raw = _normalize_name(raw)
    for key, val in contacts.items():
        if isinstance(val, dict):
            search_name = val.get('search_name', key.title())
            aliases = [a.lower().strip() for a in val.get('aliases', [])]
            aliases.extend([key.lower(), search_name.lower()])
            for a in aliases:
                if norm_raw == _normalize_name(a):
                    return search_name

    # 3. Phonetic Soundex match (e.g. niky, nikky, nicky, niki all share soundex N200)
    raw_sx = _soundex(raw)
    if raw_sx:
        for key, val in contacts.items():
            if isinstance(val, dict):
                search_name = val.get('search_name', key.title())
                aliases = [a.lower().strip() for a in val.get('aliases', [])]
                aliases.extend([key.lower(), search_name.lower()])
                for a in aliases:
                    if _soundex(a) == raw_sx:
                        return search_name

    # 4. Fuzzy string similarity matching (difflib SequenceMatcher >= 0.70)
    best_match = None
    best_score = 0.0
    for key, val in contacts.items():
        if isinstance(val, dict):
            search_name = val.get('search_name', key.title())
            aliases = [a.lower().strip() for a in val.get('aliases', [])]
            aliases.extend([key.lower(), search_name.lower()])
            for a in aliases:
                score = difflib.SequenceMatcher(None, raw, a).ratio()
                if score > best_score:
                    best_score = score
                    best_match = search_name

    if best_score >= 0.70 and best_match:
        return best_match

    return contact_name.strip().title()


def find_whatsapp_window() -> Optional[int]:
    """Find top-level WhatsApp window HWND."""
    ensure_default_desktop()
    if not WIN32_AVAILABLE:
        return None

    candidates = []
    def enum_cb(hwnd, _):
        try:
            if win32gui.IsWindow(hwnd):
                title = win32gui.GetWindowText(hwnd)
                cls = win32gui.GetClassName(hwnd)
                if 'whatsapp' in title.lower() or 'whatsapp' in cls.lower():
                    candidates.append((hwnd, title, cls))
        except Exception:
            pass
        return True

    try:
        try:
            import win32service, win32con
            h_default = win32service.OpenDesktop('Default', 0, False, win32con.GENERIC_ALL)
            win32gui.EnumDesktopWindows(h_default, enum_cb, None)
        except Exception:
            win32gui.EnumWindows(enum_cb, None)
    except Exception as e:
        logger.debug(f"Enum windows error: {e}")

    for hwnd, title, cls in candidates:
        if 'winuidesktopwin32windowclass' in cls.lower() or title.strip() == 'WhatsApp':
            return hwnd
    if candidates:
        return candidates[0][0]
    return None


def is_whatsapp_focused(wa_hwnd: Optional[int] = None) -> bool:
    """Verify if WhatsApp is currently the foreground window."""
    ensure_default_desktop()
    if not WIN32_AVAILABLE:
        return False
    try:
        fg = win32gui.GetForegroundWindow()
        if not fg or not win32gui.IsWindow(fg):
            return False
        if wa_hwnd and fg == wa_hwnd:
            return True
        title = win32gui.GetWindowText(fg).lower()
        cls = win32gui.GetClassName(fg).lower()
        if 'whatsapp' in title or 'whatsapp' in cls:
            return True
        parent = win32gui.GetParent(fg)
        if parent and win32gui.IsWindow(parent):
            p_title = win32gui.GetWindowText(parent).lower()
            p_cls = win32gui.GetClassName(parent).lower()
            if 'whatsapp' in p_title or 'whatsapp' in p_cls:
                return True
    except Exception:
        pass
    return False


def focus_whatsapp_window(timeout: float = 3.0) -> bool:
    """
    Ensure WhatsApp Desktop is visible in the foreground.
    Uses win32com WScript.Shell and win32gui APIs before sending keyboard events.
    """
    ensure_default_desktop()

    # 1. Try WScript.Shell AppActivate
    if COM_AVAILABLE:
        try:
            shell = win32com.client.Dispatch("WScript.Shell")
            shell.AppActivate("WhatsApp")
        except Exception:
            pass

    # 2. Try win32gui restore and SetForegroundWindow
    wa_hwnd = find_whatsapp_window()
    if wa_hwnd and WIN32_AVAILABLE:
        try:
            if win32gui.IsIconic(wa_hwnd):
                win32gui.ShowWindow(wa_hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(wa_hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(wa_hwnd)
        except Exception:
            pass

    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_whatsapp_focused(wa_hwnd):
            return True
        time.sleep(0.15)

    # 3. Launch or restore via os.startfile if needed
    try:
        os.startfile('whatsapp:')
    except Exception:
        pass

    retry_start = time.time()
    while time.time() - retry_start < 2.0:
        if is_whatsapp_focused(wa_hwnd):
            return True
        time.sleep(0.2)

    return is_whatsapp_focused(wa_hwnd)


def check_and_dismiss_whatsapp_error_dialog(clean_digits: str = "", timeout: float = 2.5) -> Optional[str]:
    """
    Detect if WhatsApp displayed an invalid phone number or non-existent account popup dialog.
    Dismisses the dialog and returns a clean error message if found, or None if valid.
    """
    ensure_default_desktop()
    error_phrases = [
        "isn't on whatsapp", "is not on whatsapp",
        "doesn't exist on whatsapp", "does not exist on whatsapp",
        "doesn't exist", "does not exist",
        "phone number shared via url is invalid",
        "url is invalid", "invalid phone number"
    ]

    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check standard desktop modal dialogs
        if WIN32_AVAILABLE:
            try:
                found_titles = []
                def enum_dialog_cb(h, _):
                    if win32gui.IsWindow(h):
                        t = win32gui.GetWindowText(h).lower()
                        for ep in error_phrases:
                            if ep in t:
                                found_titles.append(win32gui.GetWindowText(h))
                    return True

                try:
                    import win32service, win32con
                    h_def = win32service.OpenDesktop('Default', 0, False, win32con.GENERIC_ALL)
                    win32gui.EnumDesktopWindows(h_def, enum_dialog_cb, None)
                except Exception:
                    win32gui.EnumWindows(enum_dialog_cb, None)

                if found_titles:
                    logger.warning(f"Detected WhatsApp error dialog via window title: {found_titles[0]}")
                    if PYAUTOGUI_AVAILABLE:
                        pyautogui.press('enter')
                        time.sleep(0.2)
                        pyautogui.press('esc')
                    return f"❌ Failed: Number {clean_digits} does not exist on WhatsApp"
            except Exception:
                pass

        # Check UIA tree elements inside WhatsApp
        if PYWINAUTO_AVAILABLE:
            wa_hwnd = find_whatsapp_window()
            if wa_hwnd:
                try:
                    app = pywinauto.Application(backend="uia").connect(handle=wa_hwnd)
                    w = app.window(handle=wa_hwnd)
                    for elem in w.descendants():
                        try:
                            name = elem.element_info.name
                            if not name:
                                continue
                            name_lower = name.lower()
                            if any(ep in name_lower for ep in error_phrases):
                                logger.warning(f"Detected WhatsApp error dialog in UI tree: '{name}'")
                                # Dismiss via OK / Dismiss button
                                dismissed = False
                                try:
                                    for btn in w.descendants(control_type="Button"):
                                        if btn.element_info.name in ["OK", "Ok", "Dismiss", "Close"]:
                                            btn.invoke()
                                            dismissed = True
                                            break
                                except Exception:
                                    pass

                                if not dismissed and PYAUTOGUI_AVAILABLE:
                                    pyautogui.press('enter')
                                    time.sleep(0.2)
                                    pyautogui.press('esc')

                                return f"❌ Failed: Number {clean_digits} does not exist on WhatsApp"
                        except Exception:
                            continue
                except Exception:
                    pass

        time.sleep(0.3)
    return None


def check_whatsapp_search_results(search_name: str) -> bool:
    """
    Verify if WhatsApp found matches for search_name.
    Returns False if 'No chats, contacts or messages found' is shown.
    """
    ensure_default_desktop()
    if not PYWINAUTO_AVAILABLE:
        return True

    wa_hwnd = find_whatsapp_window()
    if not wa_hwnd:
        return True

    try:
        app = pywinauto.Application(backend="uia").connect(handle=wa_hwnd)
        w = app.window(handle=wa_hwnd)
        for elem in w.descendants():
            try:
                name = elem.element_info.name
                if not name:
                    continue
                nl = name.lower()
                if "no chats, contacts or messages found" in nl or "no results found" in nl:
                    return False
            except Exception:
                continue
    except Exception:
        pass
    return True


def send_whatsapp_message(contact_name: str, message: str = "") -> str:
    """
    Sends a WhatsApp message visibly in the foreground:
    1. Resolves contact name via fuzzy and phonetic matching (e.g. Niky, Mom, Myself).
    2. Brings WhatsApp Desktop to foreground with active focus verification.
    3. Handles international phone numbers with error dialog detection.
    4. Searches for contact via Ctrl+F, validates results, and selects conversation.
    5. Types/pastes message via UTF-8 clipboard and sends with Enter.
    """
    search_name = resolve_contact_search_name(contact_name)
    logger.info(f"[WhatsApp UI Action] Contact='{search_name}', Message='{message}'")
    try:
        print(f"[WhatsApp] Contact='{search_name}', Message='{message}'")
    except Exception:
        pass

    if PYAUTOGUI_AVAILABLE:
        pyautogui.FAILSAFE = True

    # Check if contact is an international phone number with digits
    clean_digits = ''.join(c for c in contact_name if c.isdigit() or c == '+')
    if len(clean_digits) >= 11 and clean_digits.startswith('+'):
        try:
            encoded_msg = urllib.parse.quote(message) if message else ""
            url = f"whatsapp://send?phone={clean_digits}&text={encoded_msg}"
            os.startfile(url)

            # Wait for WhatsApp to open and validate number
            time.sleep(1.5)
            focus_whatsapp_window(timeout=2.5)

            # Detect if WhatsApp showed an invalid number dialog
            err_result = check_and_dismiss_whatsapp_error_dialog(clean_digits, timeout=2.5)
            if err_result:
                return err_result

            # If message was provided, press Enter to submit prefilled text
            if message and PYAUTOGUI_AVAILABLE:
                time.sleep(0.5)
                pyautogui.press('enter')
                return f"✅ Sent WhatsApp message to {clean_digits}: '{message}'"
            return f"✅ Opened WhatsApp chat for {clean_digits}"
        except Exception as e:
            logger.error(f"Failed to open phone URL: {e}")
            return f"❌ Failed to open WhatsApp phone URL: {e}"

    # Contact name search & UI automation in foreground
    try:
        # Step 1: Ensure WhatsApp is running and in foreground
        if not focus_whatsapp_window(timeout=3.5):
            logger.warning("WhatsApp window could not be confirmed in foreground, attempting anyway.")

        time.sleep(0.4)

        if PYAUTOGUI_AVAILABLE:
            pyautogui.FAILSAFE = True

            # Step 2: Clear active search or open modals
            pyautogui.press('esc')
            time.sleep(0.2)
            pyautogui.press('esc')
            time.sleep(0.2)

            # Step 3: Focus search bar (Ctrl + F) and clear previous text
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(0.4)
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            time.sleep(0.2)

            # Step 4: Type contact search name
            pyautogui.write(search_name, interval=0.05)

            # Step 5: Wait for UI to update search results
            time.sleep(1.0)

            # Check if contact was found
            if not check_whatsapp_search_results(search_name):
                pyautogui.press('esc')
                time.sleep(0.2)
                pyautogui.press('esc')
                return f"❌ Contact '{search_name}' not found on WhatsApp"

            # Step 6: Select top matched conversation
            pyautogui.press('down')
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(0.8)

            # Step 7: Send message or report chat opened
            if message:
                try:
                    # Use PowerShell Set-Clipboard for UTF-8 / emoji / Hindi handling
                    cmd = ["powershell", "-NoProfile", "-Command", "$val = @'\n" + message + "\n'@; Set-Clipboard -Value $val"]
                    subprocess.run(cmd, capture_output=True, timeout=3)
                    time.sleep(0.3)
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(0.4)
                except Exception as clip_err:
                    logger.warning(f"Clipboard paste fallback: {clip_err}")
                    pyautogui.write(message, interval=0.03)

                time.sleep(0.3)
                pyautogui.press('enter')
                return f"✅ Sent WhatsApp message to {search_name}: '{message}'"
            else:
                return f"✅ Opened WhatsApp chat for {search_name}"
        else:
            return f"⚠️ WhatsApp opened for {search_name}, but PyAutoGUI is not available to automate typing."

    except Exception as e:
        logger.error(f"WhatsApp UI automation error: {e}")
        return f"❌ Failed to send WhatsApp message: {e}"
