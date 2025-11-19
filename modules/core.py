# Core Windows Automation Module
"""
Basic Windows automation, file operations, and system control functions.
This module handles the fundamental "hands" operations of the assistant.
"""

from pywinauto.application import Application
import time
import os 
import pyttsx3
import json 
import re
import subprocess
import shlex
from typing import Optional

# Import the intelligent app discovery system
from .app_discovery import smart_open_application, discover_applications, refresh_app_database, list_installed_apps

# --- Imports for Volume Control ---
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

# --- Imports for PDF Generation ---
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    REPORTLAB_INSTALLED = True
except ImportError:
    REPORTLAB_INSTALLED = False


# --- Helper Functions ---
def extract_number(text: str) -> Optional[int]:
    """
    Extract a number from text (supports both digits and words).
    
    :param text: Text containing a number
    :return: Extracted number or None
    """
    # Try to find digits first
    digit_match = re.search(r'\b(\d+)\b', text)
    if digit_match:
        return int(digit_match.group(1))
    
    # Word to number mapping for Hindi/English
    word_to_num = {
        'zero': 0, 'ek': 1, 'one': 1, 'do': 2, 'two': 2, 'teen': 3, 'three': 3,
        'char': 4, 'four': 4, 'paanch': 5, 'five': 5, 'chhe': 6, 'six': 6,
        'saat': 7, 'seven': 7, 'aath': 8, 'eight': 8, 'nau': 9, 'nine': 9,
        'das': 10, 'ten': 10, 'pandrah': 15, 'fifteen': 15, 'bees': 20, 'twenty': 20,
        'pachees': 25, 'twenty-five': 25, 'tees': 30, 'thirty': 30,
        'paintees': 35, 'thirty-five': 35, 'chalis': 40, 'forty': 40,
        'paintalis': 45, 'forty-five': 45, 'pachaas': 50, 'fifty': 50,
        'pachpan': 55, 'fifty-five': 55, 'saath': 60, 'sixty': 60,
        'paisath': 65, 'sixty-five': 65, 'sattar': 70, 'seventy': 70,
        'pachattar': 75, 'seventy-five': 75, 'assi': 80, 'eighty': 80,
        'pachasi': 85, 'eighty-five': 85, 'nabbe': 90, 'ninety': 90,
        'panchanan': 95, 'ninety-five': 95, 'sau': 100, 'hundred': 100
    }
    
    text_lower = text.lower()
    for word, num in word_to_num.items():
        if word in text_lower:
            return num
    
    return None


def write_a_note(message: str) -> str:
    """Opens Notepad, types a message, and closes it without saving."""
    print(f"\\n--- 'Hands' (write_a_note) activated. Message: {message} ---")
    try:
        app = Application(backend="uia").start("notepad.exe")
        main_window = app.window(title="Untitled - Notepad")
        main_window.wait("ready", timeout=5)
        main_window.child_window(title="Text Editor", control_type="Edit").type_keys(message, with_spaces=True)
        time.sleep(1) 
        main_window.close()
        app.window(title="Notepad", control_type="Window").wait("ready", timeout=2)
        app.window(title="Notepad").child_window(title="Don't Save", control_type="Button").click()
        print("--- 'Hands' (write_a_note) finished. ---")
        return f"Successfully wrote '{message}' to Notepad and closed it."
    except Exception as e:
        return f"Error controlling Notepad: {e}"

def open_application(app_name: str) -> str:
    """Opens any application on the computer using intelligent discovery."""
    print(f"--- 'Hands' (open_application) activated. App: {app_name} ---")
    
    # Use the smart application discovery system
    return smart_open_application(app_name)

def open_settings_page(page_name: str) -> str:
    """Opens a specific Windows settings page using ms-settings URI."""
    print(f"--- 'Hands' (open_settings_page) activated. Page: {page_name} ---")
    try:
        # Validate page_name to prevent command injection
        # Only allow alphanumeric characters, hyphens, and underscores
        if not re.match(r'^[a-zA-Z0-9\-_]+$', page_name):
            return f"Error: Invalid settings page name. Only alphanumeric characters, hyphens, and underscores are allowed."
        
        # Use subprocess with list arguments (no shell) for security
        subprocess.Popen(['start', '', f'ms-settings:{page_name}'], shell=True)
        return f"Opened settings page: {page_name}"
    except Exception as e:
        return f"Error opening settings page {page_name}: {e}"

def search_google(query: str) -> str:
    """Searches for a query on Google in the default web browser."""
    print(f"--- 'Hands' (search_google) activated. Query: {query} ---")
    try:
        import urllib.parse
        import webbrowser
        
        # Sanitize and validate query
        if len(query) > 500:
            return "Error: Query is too long"
        
        # URL encode the query to prevent injection
        quoted_query = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={quoted_query}"
        
        # Use webbrowser module instead of os.system for security
        webbrowser.open(url)
        return f"Successfully searched Google for: {query}"
    except Exception as e:
        return f"Error searching Google: {e}"

def search_youtube(query: str) -> str:
    """Searches for a query on YouTube in the default web browser."""
    print(f"--- 'Hands' (search_youtube) activated. Query: {query} ---")
    try:
        import urllib.parse
        import webbrowser
        
        # Sanitize and validate query
        if len(query) > 500:
            return "Error: Query is too long"
        
        # URL encode the query to prevent injection
        quoted_query = urllib.parse.quote_plus(query)
        url = f"https://www.youtube.com/results?search_query={quoted_query}"
        
        # Use webbrowser module instead of os.system for security
        webbrowser.open(url)
        return f"Successfully searched YouTube for: {query}"
    except Exception as e:
        return f"Error searching YouTube: {e}"

def close_application(app_name: str) -> str:
    """Closes an open application by its window name."""
    print(f"--- 'Hands' (close_application) activated. App: {app_name} ---")
    try:
        app = Application(backend="uia").connect(title_re=f".*{app_name}.*", timeout=5)
        app.window(title_re=f".*{app_name}.*").close()
        return f"Successfully closed {app_name}."
    except Exception as e:
        return f"Error closing {app_name}: {e}. (Is it already closed?)"

def speak(text_to_speak: str) -> str:
    """Speaks a given text string out loud."""
    print(f"--- 'Hands' (speak) activated. Text: {text_to_speak} ---")
    try:
        engine = pyttsx3.init()
        engine.say(text_to_speak)
        engine.runAndWait()
        engine.stop()
        del engine
        return "Successfully spoke the text."
    except Exception as e:
        return f"Error speaking text: {e}"

def set_system_volume(level: int) -> str:
    """Sets the system's master volume to a specific level (0-100)."""
    print(f"--- 'Hands' (set_system_volume) activated. Level: {level} ---")
    try:
        if not (0 <= level <= 100):
            return "Error: Volume must be between 0 and 100."
        
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        scalar_level = level / 100.0
        volume.SetMasterVolumeLevelScalar(scalar_level, None)
        return f"Successfully set volume to {level}%."
    except Exception as e:
        return f"Error setting volume: {e}"


def get_system_volume() -> str:
    """Gets the current system volume level (0-100)."""
    print("--- 'Hands' (get_system_volume) activated ---")
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        current_volume = volume.GetMasterVolumeLevelScalar()
        volume_percent = int(current_volume * 100)
        
        is_muted = volume.GetMute()
        status = "🔇 Muted" if is_muted else f"🔊 {volume_percent}%"
        
        return f"System Volume: {status}"
    except Exception as e:
        return f"Error getting volume: {e}"


def volume_up(increment: int = 10) -> str:
    """Increases system volume by specified increment."""
    print(f"--- 'Hands' (volume_up) activated. Increment: {increment} ---")
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        current_volume = volume.GetMasterVolumeLevelScalar()
        new_volume = min(1.0, current_volume + (increment / 100.0))
        volume.SetMasterVolumeLevelScalar(new_volume, None)
        
        new_percent = int(new_volume * 100)
        return f"🔊 Volume increased to {new_percent}%"
    except Exception as e:
        return f"Error increasing volume: {e}"


def volume_down(decrement: int = 10) -> str:
    """Decreases system volume by specified decrement."""
    print(f"--- 'Hands' (volume_down) activated. Decrement: {decrement} ---")
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        current_volume = volume.GetMasterVolumeLevelScalar()
        new_volume = max(0.0, current_volume - (decrement / 100.0))
        volume.SetMasterVolumeLevelScalar(new_volume, None)
        
        new_percent = int(new_volume * 100)
        return f"🔉 Volume decreased to {new_percent}%"
    except Exception as e:
        return f"Error decreasing volume: {e}"


def mute_volume() -> str:
    """Mutes system volume."""
    print("--- 'Hands' (mute_volume) activated ---")
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        volume.SetMute(1, None)
        return "🔇 Volume muted"
    except Exception as e:
        return f"Error muting volume: {e}"


def unmute_volume() -> str:
    """Unmutes system volume."""
    print("--- 'Hands' (unmute_volume) activated ---")
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(
            IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        
        volume.SetMute(0, None)
        return "🔊 Volume unmuted"
    except Exception as e:
        return f"Error unmuting volume: {e}"


def make_phone_call(contact_name: str = "", phone_number: str = "") -> str:
    """
    Initiates a phone call (stub function for future implementation).
    This is a placeholder for phone calling functionality.
    
    :param contact_name: Name of the contact to call
    :param phone_number: Phone number to call
    """
    print(f"--- 'Hands' (make_phone_call) activated. Contact: {contact_name}, Number: {phone_number} ---")
    
    # This is a stub function - actual implementation would require:
    # 1. Integration with phone hardware/software (e.g., via Bluetooth, USB modem, or VoIP)
    # 2. Contact database integration
    # 3. Phone number validation
    # 4. Calling API (Twilio, etc.)
    
    if not contact_name and not phone_number:
        return "❌ Please provide either a contact name or phone number"
    
    if phone_number:
        # Validate phone number format (basic validation)
        phone_clean = re.sub(r'\D', '', phone_number)
        if len(phone_clean) < 10:
            return f"❌ Invalid phone number format: {phone_number}"
        
        message = f"📞 Phone calling stub: Would call {phone_number}"
    else:
        message = f"📞 Phone calling stub: Would call contact '{contact_name}'"
    
    message += "\n\n⚠️ Note: Phone calling functionality is not yet implemented."
    message += "\nTo enable this feature, you would need to:"
    message += "\n  • Connect a phone via Bluetooth or USB"
    message += "\n  • Set up VoIP integration (e.g., Twilio, Skype)"
    message += "\n  • Configure contact database access"
    
    return message


def process_hinglish_command(text: str) -> dict:
    """
    Processes Hinglish commands and maps them to appropriate functions.
    
    :param text: Hinglish command text
    :return: Dictionary with command info and execution result
    """
    print(f"--- 'Hands' (process_hinglish_command) activated. Text: {text} ---")
    
    text_lower = text.lower()
    result = {
        'detected_command': None,
        'parameters': {},
        'execution_result': None,
        'original_text': text
    }
    
    try:
        # Volume control patterns
        if any(word in text_lower for word in ['volume', 'awaaz', 'awaz', 'sound']):
            if any(word in text_lower for word in ['up', 'badha', 'badhao', 'zyada', 'jyada', 'increase']):
                result['detected_command'] = 'volume_up'
                result['execution_result'] = volume_up(10)
            elif any(word in text_lower for word in ['down', 'kam', 'kum', 'ghata', 'decrease']):
                result['detected_command'] = 'volume_down'
                result['execution_result'] = volume_down(10)
            elif any(word in text_lower for word in ['mute', 'band', 'chup']):
                result['detected_command'] = 'mute'
                result['execution_result'] = mute_volume()
            elif any(word in text_lower for word in ['unmute', 'chalu', 'on']):
                result['detected_command'] = 'unmute'
                result['execution_result'] = unmute_volume()
            else:
                # Check for specific volume level
                num = extract_number(text)
                if num is not None:
                    result['detected_command'] = 'set_volume'
                    result['parameters']['level'] = num
                    result['execution_result'] = set_system_volume(num)
                else:
                    result['detected_command'] = 'get_volume'
                    result['execution_result'] = get_system_volume()
        
        # Phone call patterns
        elif any(word in text_lower for word in ['call', 'phone', 'dial', 'ring']):
            # Extract phone number
            phone_match = re.search(r'\b\d{10}\b|\b\d{3}-\d{3}-\d{4}\b', text)
            
            # Extract contact name (word before 'ko')
            contact_match = re.search(r'(\w+)\s+ko\s+(?:call|phone)', text_lower)
            
            result['detected_command'] = 'make_call'
            
            if phone_match:
                result['parameters']['phone_number'] = phone_match.group()
                result['execution_result'] = make_phone_call(phone_number=phone_match.group())
            elif contact_match:
                contact_name = contact_match.group(1)
                result['parameters']['contact_name'] = contact_name
                result['execution_result'] = make_phone_call(contact_name=contact_name)
            else:
                result['execution_result'] = make_phone_call()
        
        # App opening patterns
        elif any(word in text_lower for word in ['open', 'kholo', 'start', 'chalu', 'launch']):
            # Extract app name - get the word(s) immediately before the action word
            app_name = None
            for word in ['kholo', 'open', 'chalu', 'start', 'launch']:
                # Try to find word before action
                pattern = r'(\w+(?:\s+\w+)?)\s+' + word
                match = re.search(pattern, text_lower)
                if match:
                    app_name = match.group(1).strip()
                    # Remove 'karo' if present
                    app_name = re.sub(r'\s+karo$', '', app_name)
                    break
            
            if app_name:
                result['detected_command'] = 'open_app'
                result['parameters']['app_name'] = app_name
                result['execution_result'] = open_application(app_name)

        
        # Search patterns
        elif any(word in text_lower for word in ['search', 'google', 'youtube', 'dhundo', 'khojo']):
            if 'youtube' in text_lower:
                query_match = re.search(r'youtube\s+(?:pe|me|par|search|kar|karo)\s+(.+)', text_lower)
                if query_match:
                    query = query_match.group(1)
                    result['detected_command'] = 'search_youtube'
                    result['parameters']['query'] = query
                    result['execution_result'] = search_youtube(query)
            else:
                query_match = re.search(r'(?:google|search|dhundo|khojo)\s+(?:kar|karo|me|pe)?\s*(.+)', text_lower)
                if query_match:
                    query = query_match.group(1)
                    result['detected_command'] = 'search_google'
                    result['parameters']['query'] = query
                    result['execution_result'] = search_google(query)
        
        # If no command detected
        if result['detected_command'] is None:
            result['execution_result'] = "❌ Could not understand Hinglish command. Please try again."
        
    except Exception as e:
        result['execution_result'] = f"❌ Error processing Hinglish command: {e}"
    
    return result

def scan_and_save_apps() -> str:
    """Scans the Windows Start Menu for.lnk shortcuts and saves them to apps.json."""
    print("--- 'Hands' (scan_and_save_apps) activated ---")
    apps = {}
    
    path1 = os.path.join(os.environ.get('APPDATA', ''), r'Microsoft\\Windows\\Start Menu\\Programs')
    path2 = os.path.join(os.environ.get('PROGRAMDATA', ''), r'Microsoft\\Windows\\Start Menu\\Programs')
    
    paths = [path1, path2] 

    for path in paths:
        if os.path.exists(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith('.lnk'):
                        name = file[:-4].lower()
                        full_path = os.path.join(root, file)
                        apps[name] = full_path
    
    try:
        with open('apps.json', 'w') as f:
            json.dump(apps, f, indent=4)
        
        if not apps:
            return "Scan complete, but I couldn't find many apps. Try running as administrator?"
            
        return f"Scan complete. Found {len(apps)} applications."
    except Exception as e:
        return f"Error saving app list: {e}"

def get_app_path_from_name(app_name: str) -> Optional[str]:
    """Loads the apps.json file and finds the path for a given app name."""
    try:
        with open('apps.json', 'r') as f:
            apps = json.load(f)
        
        app_name_lower = app_name.lower()
        if app_name_lower in apps:
            return apps[app_name_lower]
        
        for name, path in apps.items():
            if app_name_lower in name:
                return path
                
        return None 
    except FileNotFoundError:
        return "not_scanned"
    except Exception as e:
        print(f"Error loading app list: {e}")
        return None

def write_to_file(filename: str, content: str) -> str:
    """
    Creates a new text file (like.txt or.md) or a simple PDF and writes the given content to it.
    :param filename: The name of the file to create (e.g., "my_note.txt", "report.pdf").
    :param content: The text content to write into the file.
    """
    print(f"--- 'Hands' (write_to_file) activated. Filename: {filename} ---")
    try:
        # PDF Generation
        if filename.lower().endswith('.pdf'):
            if not REPORTLAB_INSTALLED:
                return "Error: To save PDFs, I need the 'reportlab' library. Please run 'pip install reportlab'."
            
            c = canvas.Canvas(filename, pagesize=letter)
            width, height = letter
            text_object = c.beginText(72, height - 72)
            text_object.setFont("Helvetica", 10)
            
            for line in content.split('\\n'):
                text_object.textLine(line)
                
            c.drawText(text_object)
            c.showPage()
            c.save()
            return f"Successfully generated and saved {filename}."

        # For all other files (.txt,.md, etc.)
        else:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully saved content to {filename}."
            
    except Exception as e:
        return f"Error writing file: {e}"