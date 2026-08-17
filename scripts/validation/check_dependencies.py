#!/usr/bin/env python3
"""
Dependency Checker for YourDaddy Assistant
Checks for required and optional dependencies and provides installation guidance.
"""

import sys
import importlib
from pathlib import Path

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def check_dependency(module_name, package_name=None, optional=False):
    """Check if a dependency is available."""
    package_name = package_name or module_name
    try:
        importlib.import_module(module_name)
        status = f"{Colors.GREEN}✓{Colors.END}"
        message = f"{Colors.GREEN}Installed{Colors.END}"
        return True, f"{status} {package_name:30s} {message}"
    except ImportError:
        if optional:
            status = f"{Colors.YELLOW}○{Colors.END}"
            message = f"{Colors.YELLOW}Optional - Not installed{Colors.END}"
        else:
            status = f"{Colors.RED}✗{Colors.END}"
            message = f"{Colors.RED}Missing - Required{Colors.END}"
        return False, f"{status} {package_name:30s} {message}"

def main():
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}YourDaddy Assistant - Dependency Check{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    # Core dependencies
    print(f"{Colors.BOLD}{Colors.BLUE}Core Dependencies:{Colors.END}")
    core_deps = [
        ('flask', 'flask'),
        ('flask_socketio', 'flask-socketio'),
        ('flask_cors', 'flask-cors'),
        ('flask_jwt_extended', 'flask-jwt-extended'),
        ('flask_limiter', 'flask-limiter'),
        ('werkzeug', 'werkzeug'),
        ('dotenv', 'python-dotenv'),
        ('requests', 'requests'),
        ('psutil', 'psutil'),
    ]
    
    core_missing = []
    for module, package in core_deps:
        success, message = check_dependency(module, package, optional=False)
        print(f"  {message}")
        if not success:
            core_missing.append(package)
    
    # AI/LLM dependencies
    print(f"\n{Colors.BOLD}{Colors.BLUE}AI & LLM Dependencies:{Colors.END}")
    ai_deps = [
        ('openai', 'openai'),
        ('google.generativeai', 'google-generativeai'),
        ('anthropic', 'anthropic'),
    ]
    
    ai_missing = []
    for module, package in ai_deps:
        success, message = check_dependency(module, package, optional=True)
        print(f"  {message}")
        if not success:
            ai_missing.append(package)
    
    # Voice dependencies
    print(f"\n{Colors.BOLD}{Colors.BLUE}Voice & Audio Dependencies:{Colors.END}")
    voice_deps = [
        ('speech_recognition', 'SpeechRecognition'),
        ('pyttsx3', 'pyttsx3'),
        ('vosk', 'vosk'),
        ('pyaudio', 'PyAudio'),
        ('pvporcupine', 'pvporcupine'),
    ]
    
    voice_missing = []
    for module, package in voice_deps:
        success, message = check_dependency(module, package, optional=True)
        print(f"  {message}")
        if not success:
            voice_missing.append(package)
    
    # Data Science & ML dependencies
    print(f"\n{Colors.BOLD}{Colors.BLUE}Data Science & ML Dependencies:{Colors.END}")
    ds_deps = [
        ('numpy', 'numpy'),
        ('pandas', 'pandas'),
        ('sklearn', 'scikit-learn'),
        ('matplotlib', 'matplotlib'),
        ('networkx', 'networkx'),
    ]
    
    ds_missing = []
    for module, package in ds_deps:
        success, message = check_dependency(module, package, optional=True)
        print(f"  {message}")
        if not success:
            ds_missing.append(package)
    
    # Image & OCR dependencies
    print(f"\n{Colors.BOLD}{Colors.BLUE}Image & OCR Dependencies:{Colors.END}")
    image_deps = [
        ('PIL', 'Pillow'),
        ('pytesseract', 'pytesseract'),
        ('pdf2image', 'pdf2image'),
        ('cv2', 'opencv-python'),
    ]
    
    image_missing = []
    for module, package in image_deps:
        success, message = check_dependency(module, package, optional=True)
        print(f"  {message}")
        if not success:
            image_missing.append(package)
    
    # Google Services dependencies
    print(f"\n{Colors.BOLD}{Colors.BLUE}Google Services Dependencies:{Colors.END}")
    google_deps = [
        ('google.auth', 'google-auth'),
        ('google_auth_oauthlib', 'google-auth-oauthlib'),
        ('googleapiclient', 'google-api-python-client'),
    ]
    
    google_missing = []
    for module, package in google_deps:
        success, message = check_dependency(module, package, optional=True)
        print(f"  {message}")
        if not success:
            google_missing.append(package)
    
    # Other optional dependencies
    print(f"\n{Colors.BOLD}{Colors.BLUE}Other Optional Dependencies:{Colors.END}")
    other_deps = [
        ('schedule', 'schedule'),
        ('yt_dlp', 'yt-dlp'),
        ('googletrans', 'googletrans==4.0.0rc1'),
        ('spotipy', 'spotipy'),
        ('beautifulsoup4', 'beautifulsoup4'),
    ]
    
    other_missing = []
    for module, package in other_deps:
        success, message = check_dependency(module, package, optional=True)
        print(f"  {message}")
        if not success:
            other_missing.append(package)
    
    # Summary
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}Summary:{Colors.END}\n")
    
    if core_missing:
        print(f"{Colors.RED}❌ Missing core dependencies!{Colors.END}")
        print(f"{Colors.YELLOW}Install with:{Colors.END}")
        print(f"  pip install {' '.join(core_missing)}\n")
    else:
        print(f"{Colors.GREEN}✅ All core dependencies installed!{Colors.END}\n")
    
    total_optional_missing = len(ai_missing) + len(voice_missing) + len(ds_missing) + len(image_missing) + len(google_missing) + len(other_missing)
    
    if total_optional_missing > 0:
        print(f"{Colors.YELLOW}⚠️  {total_optional_missing} optional dependencies missing{Colors.END}")
        print(f"{Colors.BLUE}Optional features will be disabled{Colors.END}\n")
        
        if ai_missing:
            print(f"{Colors.YELLOW}For AI/LLM features:{Colors.END}")
            print(f"  pip install {' '.join(ai_missing)}")
        
        if voice_missing:
            print(f"\n{Colors.YELLOW}For voice features:{Colors.END}")
            print(f"  pip install {' '.join(voice_missing)}")
        
        if ds_missing:
            print(f"\n{Colors.YELLOW}For data science features:{Colors.END}")
            print(f"  pip install {' '.join(ds_missing)}")
        
        if image_missing:
            print(f"\n{Colors.YELLOW}For image/OCR features:{Colors.END}")
            print(f"  pip install {' '.join(image_missing)}")
        
        if google_missing:
            print(f"\n{Colors.YELLOW}For Google services:{Colors.END}")
            print(f"  pip install {' '.join(google_missing)}")
        
        if other_missing:
            print(f"\n{Colors.YELLOW}For other optional features:{Colors.END}")
            print(f"  pip install {' '.join(other_missing)}")
    else:
        print(f"{Colors.GREEN}✅ All optional dependencies installed!{Colors.END}")
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}\n")
    
    # Return exit code
    return 1 if core_missing else 0

if __name__ == '__main__':
    sys.exit(main())
