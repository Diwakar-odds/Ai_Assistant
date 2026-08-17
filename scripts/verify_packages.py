#!/usr/bin/env python3
"""Verify all required packages can be imported"""

import sys

packages_to_test = {
    # Core Web & API
    'flask': 'Flask',
    'flask_socketio': 'Flask-SocketIO',
    'flask_cors': 'Flask-CORS',
    'flask_jwt_extended': 'Flask-JWT-Extended',
    'flask_limiter': 'Flask-Limiter',
    'werkzeug': 'Werkzeug',
    'websockets': 'websockets',
    'eventlet': 'eventlet',
    
    # AI & ML
    'google.generativeai': 'Google Generative AI',
    'openai': 'OpenAI',
    'autogen_agentchat': 'AutoGen',
    
    # ML Frameworks (heavy, may not be installed)
    # 'tensorflow': 'TensorFlow',
    # 'torch': 'PyTorch',
    # 'transformers': 'Transformers',
    
    # Voice & Audio
    'speech_recognition': 'SpeechRecognition',
    'pyttsx3': 'pyttsx3',
    'gtts': 'gTTS',
    
    # Computer Vision
    'cv2': 'OpenCV',
    'PIL': 'Pillow',
    'pytesseract': 'pytesseract',
    
    # Windows Automation
    'pywinauto': 'pywinauto',
    'pyautogui': 'PyAutoGUI',
    'comtypes': 'comtypes',
    
    # Web Scraping
    'selenium': 'Selenium',
    'bs4': 'BeautifulSoup4',
    'lxml': 'lxml',
    'feedparser': 'feedparser',
    
    # Networking
    'httpx': 'HTTPX',
    'requests': 'Requests',
    
    # Document Processing
    'PyPDF2': 'PyPDF2',
    'pdfplumber': 'pdfplumber',
    
    # System
    'psutil': 'psutil',
    'schedule': 'schedule',
    'watchdog': 'watchdog',
    
    # Data & Validation
    'pydantic': 'Pydantic',
    'numpy': 'NumPy',
    
    # Multilingual
    'deep_translator': 'deep-translator',
    'langdetect': 'langdetect',
    
    # Music
    'spotipy': 'spotipy',
    'ytmusicapi': 'ytmusicapi',
    
    # MCP
    'mcp': 'MCP',
    
    # Utilities
    'qrcode': 'qrcode',
    'colorama': 'colorama',
    'tqdm': 'tqdm',
}

print("=" * 60)
print("PACKAGE VERIFICATION")
print("=" * 60)
print()

success = []
failed = []

for module_name, display_name in packages_to_test.items():
    try:
        __import__(module_name)
        success.append(display_name)
        print(f"✅ {display_name:30} OK")
    except ImportError as e:
        failed.append((display_name, str(e)))
        print(f"❌ {display_name:30} MISSING")

print()
print("=" * 60)
print(f"Results: {len(success)} OK, {len(failed)} Missing")
print("=" * 60)

if failed:
    print()
    print("Missing packages:")
    for name, error in failed:
        print(f"  - {name}")
    print()
    print("Install missing packages with:")
    print("  pip install -r requirements.txt")
    sys.exit(1)
else:
    print()
    print("✅ All core packages are installed!")
    print()
    sys.exit(0)
