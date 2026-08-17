
import sys
import os
import json
import logging
from flask import Flask

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.abspath(os.path.join(current_dir, '../src'))
sys.path.insert(0, src_path)

from ai_assistant.services.backend.blueprints.preferences import create_blueprint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_settings():
    app = Flask(__name__)
    bp = create_blueprint()
    app.register_blueprint(bp)
    
    client = app.test_client()
    
    print("--- Test 1: Get All Settings ---")
    response = client.get('/api/settings/all')
    print(f"Status Code: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: {response.json}")
        return
        
    data = response.json
    if not data['success']:
        print("Failed to get settings")
        return
    
    settings = data['settings']
    print("Settings keys:", list(settings.keys()))
    if 'security' not in settings:
        print("FAIL: 'security' key missing")
        return
    if 'modelPath' not in settings['ai']['localLlm']:
        print("FAIL: Nested key 'ai.localLlm.modelPath' missing")
        return
    print("PASS: Got settings with correct structure")

    print("\n--- Test 2: Update Settings ---")
    new_theme = "Light"
    
    # Update General settings
    payload = {
        "category": "general",
        "settings": {
            "language": "en-US",
            "secondaryLanguage": "hi-IN",
            "enableHinglish": True,
            "theme": new_theme,
            "animations": True,
            "startOnBoot": False
        }
    }
    response = client.post('/api/settings/update', json=payload, content_type='application/json')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Error: {response.json}")
        return
        
    # Verify update
    response = client.get('/api/settings/all')
    settings = response.json['settings']
    if settings['general']['theme'] == new_theme:
        print("PASS: General settings updated successfully")
    else:
        print(f"FAIL: Settings not updated. Got {settings['general']['theme']}")
        return

    print("\n--- Test 3: Reset Settings ---")
    # Reset general only
    payload = {"category": "general"}
    response = client.post('/api/settings/reset', json=payload, content_type='application/json')
    
    # Check if reset to default (Dark)
    response = client.get('/api/settings/all')
    settings = response.json['settings']
    if settings['general']['theme'] == "dark":
        print("PASS: Settings reset successfully")
    else:
        print(f"FAIL: Settings not reset. Got {settings['general']['theme']}")
        return

    print("\nAll tests passed!")

if __name__ == "__main__":
    verify_settings()
