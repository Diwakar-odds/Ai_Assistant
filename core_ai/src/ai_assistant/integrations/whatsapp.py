import webbrowser
import time
import json
import os
import logging
from typing import Optional

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

logger = logging.getLogger(__name__)

CONTACTS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'contacts.json')

def load_contacts():
    if not os.path.exists(CONTACTS_FILE):
        return {}
    try:
        with open(CONTACTS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading contacts: {e}")
        return {}

def get_contact_number(name: str) -> Optional[str]:
    contacts = load_contacts()
    return contacts.get(name.lower())

def send_whatsapp_message(contact_name: str, message: str) -> str:
    """
    Sends a WhatsApp message to a contact.
    1. Looks up contact number.
    2. Opens WhatsApp (Web or App) with pre-filled message.
    3. Simulates 'Enter' to send.
    """
    print(f"📱 Sending WhatsApp to {contact_name}: {message}")
    
    phone_number = get_contact_number(contact_name)
    
    if not phone_number:
        return f"❌ I couldn't find a contact named '{contact_name}'. Please add them to your contacts list."
    
    # Clean phone number (remove spaces, ensure it has country code if needed)
    # This is a basic implementation.
    
    try:
        # Construct URL
        # UPDATED: Prefer Desktop App (whatsapp://) protocol first
        # fallback to web URL if strictly needed, but user requested desktop priority.
        
        # 1. Try Desktop Protocol
        url = f"whatsapp://send?phone={phone_number}&text={message}"
        
        print(f"  🔗 Opening protocol: {url}")
        # webbrowser.open handles protocols correctly on Windows if app is installed
        webbrowser.open(url)
        
        if PYAUTOGUI_AVAILABLE:
            # Wait for WhatsApp to load
            time.sleep(15) # Wait time depends on internet speed
            
            # Press Enter to send
            pyautogui.press('enter')
            return f"✅ Message sent to {contact_name} (simulated)"
        else:
            return f"✅ Opened WhatsApp chat for {contact_name}. Please press Enter to send."
            
    except Exception as e:
        return f"❌ Failed to send WhatsApp message: {e}"