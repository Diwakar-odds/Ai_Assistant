#!/usr/bin/env python3
"""
YourDaddy Assistant - Unified Debug Tool
Debug and test various components of the assistant system
"""

import sys
import os
import json
import time
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class DebugManager:
    """Manages debugging operations for different components"""
    
    def __init__(self):
        self.modules = {}
        self.results = []
        self.load_modules()
    
    def load_modules(self):
        """Load available modules for debugging"""
        try:
            from modules.conversational_ai import AdvancedConversationalAI
            self.modules['conversational_ai'] = AdvancedConversationalAI
        except ImportError:
            self.modules['conversational_ai'] = None
        
        try:
            from modules.multimodal import MultiModalAI
            self.modules['multimodal'] = MultiModalAI
        except ImportError:
            self.modules['multimodal'] = None
        
        try:
            import automation_tools_new
            self.modules['automation'] = automation_tools_new
        except ImportError:
            self.modules['automation'] = None
        
        try:
            from modules.multilingual import MultilingualSupport
            self.modules['multilingual'] = MultilingualSupport
        except ImportError:
            self.modules['multilingual'] = None
    
    def show_main_menu(self):
        """Show main debug menu"""
        print("🐛 YourDaddy Assistant - Debug Tool")
        print("=" * 50)
        print()
        print("Available debug options:")
        print("1. Chat System Debug")
        print("2. Video/Image Analysis Debug")
        print("3. Automation Tools Debug")
        print("4. Voice & Audio Debug")
        print("5. Multilingual Debug")
        print("6. Backend API Debug")
        print("7. Full System Test")
        print("8. Module Health Check")
        print("9. Quick Chat Test")
        print("0. Exit")
        print()
        
        while True:
            choice = input("Select debug option (0-9): ").strip()
            
            if choice == "0":
                return False
            elif choice == "1":
                self.debug_chat_system()
            elif choice == "2":
                self.debug_video_analysis()
            elif choice == "3":
                self.debug_automation()
            elif choice == "4":
                self.debug_voice_audio()
            elif choice == "5":
                self.debug_multilingual()
            elif choice == "6":
                self.debug_backend_api()
            elif choice == "7":
                self.full_system_test()
            elif choice == "8":
                self.module_health_check()
            elif choice == "9":
                self.quick_chat_test()
            else:
                print("Invalid choice. Please try again.")
            
            input("\nPress Enter to continue...")
        
        return True
    
    def debug_chat_system(self):
        """Debug conversational AI system"""
        print("\n" + "=" * 50)
        print("🤖 CHAT SYSTEM DEBUG")
        print("=" * 50)
        
        if not self.modules['conversational_ai']:
            print("❌ Conversational AI module not available")
            return
        
        try:
            # Create test automation callback
            def test_automation_callback(action, param):
                return f"[DEBUG] {action}({param})"
            
            # Initialize AI
            ai = self.modules['conversational_ai'](automation_callback=test_automation_callback)
            print("✅ Conversational AI initialized successfully")
            
            # Test different message types
            test_messages = [
                "hello",
                "how are you",
                "what can you do",
                "open chrome",
                "play music",
                "search for python tutorial",
                "what is 10 plus 5",
                "help me",
                "i need assistance"
            ]
            
            print("\nTesting chat responses:")
            print("-" * 30)
            
            for i, message in enumerate(test_messages, 1):
                try:
                    print(f"\n{i}. User: {message}")
                    response = ai.process_message(message)
                    print(f"   AI: {response}")
                    
                    # Analyze response quality
                    quality = "Good" if len(response) > 20 else "Poor"
                    print(f"   Quality: {quality}")
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
        
        except Exception as e:
            print(f"❌ Chat system debug failed: {e}")
            traceback.print_exc()
    
    def debug_video_analysis(self):
        """Debug video and image analysis"""
        print("\n" + "=" * 50)
        print("🎥 VIDEO/IMAGE ANALYSIS DEBUG")
        print("=" * 50)
        
        if not self.modules['multimodal']:
            print("❌ Multimodal AI module not available")
            return
        
        try:
            # Initialize multimodal AI
            ai = self.modules['multimodal']()
            print("✅ Multimodal AI initialized successfully")
            
            # Test 1: Screenshot analysis
            print("\nTEST 1: Screenshot Analysis")
            print("-" * 30)
            
            try:
                import pyautogui
                screenshot = pyautogui.screenshot()
                screenshot.save("debug_screenshot.png")
                print("✅ Screenshot captured")
                
                # Analyze screenshot
                analysis = ai.analyze_screenshot()
                print(f"Analysis: {analysis[:200]}..." if len(analysis) > 200 else analysis)
                
            except Exception as e:
                print(f"❌ Screenshot test failed: {e}")
            
            # Test 2: Video file analysis (if available)
            print("\nTEST 2: Video File Analysis")
            print("-" * 30)
            
            # Look for sample video files
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
            sample_videos = []
            
            for ext in video_extensions:
                videos = list(Path(".").glob(f"*{ext}"))
                sample_videos.extend(videos)
            
            if sample_videos:
                video_path = sample_videos[0]
                print(f"Found video: {video_path}")
                print(f"File size: {video_path.stat().st_size / (1024*1024):.2f} MB")
                
                try:
                    import cv2
                    cap = cv2.VideoCapture(str(video_path))
                    ret, frame = cap.read()
                    if ret:
                        print("✅ Video frame extracted successfully")
                        cv2.imwrite("debug_frame.jpg", frame)
                    cap.release()
                except Exception as e:
                    print(f"❌ Video analysis failed: {e}")
            else:
                print("ℹ️ No video files found for testing")
        
        except Exception as e:
            print(f"❌ Video analysis debug failed: {e}")
            traceback.print_exc()
    
    def debug_automation(self):
        """Debug automation tools"""
        print("\n" + "=" * 50)
        print("🔧 AUTOMATION TOOLS DEBUG")
        print("=" * 50)
        
        if not self.modules['automation']:
            print("❌ Automation module not available")
            return
        
        try:
            automation = self.modules['automation']
            
            # Test basic functions
            tests = [
                ("get_system_status", "System Status"),
                ("list_installed_apps", "App List"),
                ("get_running_processes", "Running Processes"),
                ("get_network_info", "Network Info"),
                ("detect_taskbar_apps", "Taskbar Detection")
            ]
            
            for func_name, description in tests:
                try:
                    print(f"\nTesting {description}:")
                    if hasattr(automation, func_name):
                        func = getattr(automation, func_name)
                        result = func()
                        print(f"✅ {description}: {str(result)[:100]}...")
                    else:
                        print(f"❌ Function {func_name} not found")
                except Exception as e:
                    print(f"❌ {description} failed: {e}")
        
        except Exception as e:
            print(f"❌ Automation debug failed: {e}")
            traceback.print_exc()
    
    def debug_voice_audio(self):
        """Debug voice recognition and audio"""
        print("\n" + "=" * 50)
        print("🎤 VOICE & AUDIO DEBUG")
        print("=" * 50)
        
        # Test speech recognition
        try:
            import speech_recognition as sr
            print("✅ Speech Recognition module available")
            
            # Test microphone
            r = sr.Recognizer()
            with sr.Microphone() as source:
                print("🎤 Microphone test - speak something (5 seconds):")
                try:
                    audio = r.listen(source, timeout=5)
                    text = r.recognize_google(audio)
                    print(f"✅ Recognized: {text}")
                except sr.WaitTimeoutError:
                    print("⏰ Timeout - no speech detected")
                except Exception as e:
                    print(f"❌ Recognition failed: {e}")
        
        except ImportError:
            print("❌ Speech Recognition not available")
        
        # Test text-to-speech
        try:
            import pyttsx3
            print("✅ Text-to-Speech module available")
            
            engine = pyttsx3.init()
            engine.say("Testing text to speech functionality")
            engine.runAndWait()
            print("✅ TTS test completed")
        
        except ImportError:
            print("❌ Text-to-Speech not available")
        except Exception as e:
            print(f"❌ TTS test failed: {e}")
    
    def debug_multilingual(self):
        """Debug multilingual support"""
        print("\n" + "=" * 50)
        print("🌐 MULTILINGUAL DEBUG")
        print("=" * 50)
        
        if not self.modules['multilingual']:
            print("❌ Multilingual module not available")
            return
        
        try:
            # Initialize multilingual support
            ml = self.modules['multilingual']()
            print("✅ Multilingual support initialized")
            
            # Test translations
            test_phrases = [
                ("Hello, how are you?", "en", "hi"),
                ("Namaste, aap kaise hain?", "hi", "en"),
                ("Music bajao", "hi", "en")
            ]
            
            print("\nTesting translations:")
            print("-" * 30)
            
            for phrase, from_lang, to_lang in test_phrases:
                try:
                    translation = ml.translate_text(phrase, from_lang, to_lang)
                    print(f"'{phrase}' -> '{translation}'")
                except Exception as e:
                    print(f"❌ Translation failed: {e}")
        
        except Exception as e:
            print(f"❌ Multilingual debug failed: {e}")
            traceback.print_exc()
    
    def debug_backend_api(self):
        """Debug backend API endpoints"""
        print("\n" + "=" * 50)
        print("🌐 BACKEND API DEBUG")
        print("=" * 50)
        
        try:
            import requests
            
            base_url = "http://localhost:5000"
            
            # Test endpoints
            endpoints = [
                "/api/health",
                "/api/apps",
                "/api/system/status"
            ]
            
            print("Testing API endpoints:")
            print("-" * 30)
            
            for endpoint in endpoints:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=5)
                    print(f"✅ {endpoint}: {response.status_code}")
                except requests.exceptions.ConnectionError:
                    print(f"❌ {endpoint}: Connection refused (server not running?)")
                except Exception as e:
                    print(f"❌ {endpoint}: {e}")
            
            # Test command endpoint
            try:
                response = requests.post(
                    f"{base_url}/api/command",
                    json={"command": "hello"},
                    timeout=10
                )
                print(f"✅ /api/command: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    print(f"   Response: {data.get('response', '')[:50]}...")
            except Exception as e:
                print(f"❌ /api/command: {e}")
        
        except ImportError:
            print("❌ Requests module not available")
        except Exception as e:
            print(f"❌ API debug failed: {e}")
    
    def full_system_test(self):
        """Run comprehensive system test"""
        print("\n" + "=" * 50)
        print("🔬 FULL SYSTEM TEST")
        print("=" * 50)
        
        tests = [
            ("Module Health Check", self.module_health_check),
            ("Chat System", self.debug_chat_system),
            ("Automation Tools", self.debug_automation),
            ("Backend API", self.debug_backend_api)
        ]
        
        for test_name, test_func in tests:
            print(f"\n>>> Running {test_name}")
            try:
                test_func()
                print(f"✅ {test_name} completed")
            except Exception as e:
                print(f"❌ {test_name} failed: {e}")
    
    def module_health_check(self):
        """Check health of all modules"""
        print("\n" + "=" * 50)
        print("🏥 MODULE HEALTH CHECK")
        print("=" * 50)
        
        print("Core Python modules:")
        core_modules = ['os', 'sys', 'json', 'time', 'pathlib']
        for module in core_modules:
            try:
                __import__(module)
                print(f"✅ {module}")
            except ImportError:
                print(f"❌ {module}")
        
        print("\nOptional modules:")
        optional_modules = [
            ('requests', 'HTTP requests'),
            ('flask', 'Web framework'),
            ('cv2', 'OpenCV'),
            ('PIL', 'Pillow image processing'),
            ('speech_recognition', 'Speech recognition'),
            ('pyttsx3', 'Text-to-speech'),
            ('googletrans', 'Google Translate'),
            ('torch', 'PyTorch'),
            ('transformers', 'Transformers AI')
        ]
        
        for module, description in optional_modules:
            try:
                __import__(module)
                print(f"✅ {module} ({description})")
            except ImportError:
                print(f"❌ {module} ({description})")
        
        print("\nProject modules:")
        project_modules = self.modules
        for module_name, module in project_modules.items():
            status = "✅" if module else "❌"
            print(f"{status} {module_name}")
    
    def quick_chat_test(self):
        """Quick interactive chat test"""
        print("\n" + "=" * 50)
        print("💬 QUICK CHAT TEST")
        print("=" * 50)
        
        if not self.modules['conversational_ai']:
            print("❌ Conversational AI not available")
            return
        
        try:
            def test_callback(action, param):
                return f"[DEBUG] {action} -> {param}"
            
            ai = self.modules['conversational_ai'](automation_callback=test_callback)
            print("✅ Chat system initialized")
            print("Type 'quit' to exit\n")
            
            while True:
                user_input = input("You: ").strip()
                if user_input.lower() in ['quit', 'exit']:
                    break
                
                try:
                    response = ai.process_message(user_input)
                    print(f"AI: {response}\n")
                except Exception as e:
                    print(f"❌ Error: {e}\n")
        
        except Exception as e:
            print(f"❌ Quick chat test failed: {e}")

def main():
    """Main debug function"""
    print("🐛 YourDaddy Assistant Debug Tool")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        # Direct command mode
        command = sys.argv[1].lower()
        debug_manager = DebugManager()
        
        if command == "chat":
            debug_manager.debug_chat_system()
        elif command == "video":
            debug_manager.debug_video_analysis()
        elif command == "automation":
            debug_manager.debug_automation()
        elif command == "voice":
            debug_manager.debug_voice_audio()
        elif command == "multilingual":
            debug_manager.debug_multilingual()
        elif command == "api":
            debug_manager.debug_backend_api()
        elif command == "health":
            debug_manager.module_health_check()
        elif command == "full":
            debug_manager.full_system_test()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: chat, video, automation, voice, multilingual, api, health, full")
    else:
        # Interactive mode
        debug_manager = DebugManager()
        debug_manager.show_main_menu()

if __name__ == "__main__":
    main()