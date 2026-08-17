!/usr/bin/env python3
"""
YourDaddy Assistant - Unified Setup Script
Installs and configures all features including multimodal AI, multilingual support, and core dependencies.
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path

class SetupManager:
    """Manages the setup and installation process"""
    
    def __init__(self):
        self.installed_packages = []
        self.failed_packages = []
        self.features = {
            'core': True,
            'multimodal': False,
            'multilingual': False,
            'voice': False,
            'advanced_ai': False,
            'web_ui': False
        }
    
    def run_command(self, command, description, critical=True):
        """Run a command and handle errors"""
        print(f"📦 {description}...")
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
            print(f"✅ {description} completed successfully")
            return result.stdout
        except subprocess.CalledProcessError as e:
            if critical:
                print(f"❌ {description} failed: {e.stderr}")
            else:
                print(f"⚠️ {description} failed (optional): {e.stderr}")
            return None
    
    def check_package(self, package):
        """Check if a package is already installed"""
        try:
            __import__(package)
            return True
        except ImportError:
            return False
    
    def install_package(self, package, description=None, critical=True):
        """Install a Python package using pip"""
        if not description:
            description = f"Installing {package.split('==')[0] if '==' in package else package}"
        
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "install", package], 
                                  capture_output=True, text=True, check=True)
            self.installed_packages.append(package)
            print(f"✅ {description}")
            return True
        except subprocess.CalledProcessError as e:
            self.failed_packages.append(package)
            if critical:
                print(f"❌ {description} failed: {e.stderr}")
            else:
                print(f"⚠️ {description} failed (optional): {e.stderr}")
            return False
    
    def show_menu(self):
        """Show feature selection menu"""
        print("🎯 YourDaddy Assistant Setup - Feature Selection")
        print("=" * 60)
        print("Select which features you want to install:")
        print()
        print("1. Core Only        - Basic assistant functionality")
        print("2. Standard         - Core + Voice + Web UI")
        print("3. Enhanced         - Standard + Multilingual")
        print("4. Full Featured    - Everything including Multimodal AI")
        print("5. Custom           - Choose specific features")
        print("6. Web Frontend     - Install React frontend dependencies")
        print()
        
        while True:
            choice = input("Select setup type (1-6): ").strip()
            
            if choice == "1":
                self.features.update({'core': True})
                break
            elif choice == "2":
                self.features.update({'core': True, 'voice': True, 'web_ui': True})
                break
            elif choice == "3":
                self.features.update({'core': True, 'voice': True, 'web_ui': True, 'multilingual': True})
                break
            elif choice == "4":
                self.features.update({k: True for k in self.features})
                break
            elif choice == "5":
                self.custom_selection()
                break
            elif choice == "6":
                self.setup_web_frontend()
                return
            else:
                print("Invalid choice. Please try again.")
    
    def custom_selection(self):
        """Allow custom feature selection"""
        print("\n🔧 Custom Feature Selection")
        print("-" * 30)
        
        features_desc = {
            'multimodal': 'Multimodal AI (Image/Screen analysis)',
            'multilingual': 'Multilingual Support (Hindi/English/Hinglish)',
            'voice': 'Voice Recognition & TTS',
            'advanced_ai': 'Advanced AI Models (GPT, Transformers)',
            'web_ui': 'Web User Interface Dependencies'
        }
        
        for feature, desc in features_desc.items():
            while True:
                choice = input(f"Install {desc}? (y/n): ").strip().lower()
                if choice in ['y', 'yes']:
                    self.features[feature] = True
                    break
                elif choice in ['n', 'no']:
                    self.features[feature] = False
                    break
                else:
                    print("Please enter 'y' or 'n'")
    
    def install_core_dependencies(self):
        """Install core dependencies"""
        print("\n🔧 Installing Core Dependencies")
        print("=" * 40)
        
        core_packages = [
            "requests>=2.31.0",
            "beautifulsoup4>=4.12.0",
            "lxml>=4.9.0",
            "selenium>=4.15.0",
            "python-dotenv>=1.0.0",
            "psutil>=5.9.0",
            "pyautogui>=0.9.54",
            "pillow>=10.0.0",
            "flask>=3.0.0",
            "flask-socketio>=5.3.0",
            "flask-cors>=4.0.0",
            "flask-jwt-extended>=4.6.0",
            "flask-limiter>=3.5.0",
            "werkzeug>=3.0.0",
            "cryptography>=41.0.0",
            "pynacl>=1.5.0"
        ]
        
        for package in core_packages:
            self.install_package(package)
    
    def install_voice_dependencies(self):
        """Install voice recognition and TTS dependencies"""
        if not self.features['voice']:
            return
        
        print("\n🎤 Installing Voice Dependencies")
        print("=" * 40)
        
        voice_packages = [
            "SpeechRecognition>=3.10.0",
            "pyttsx3>=2.90",
            "gTTS>=2.5.0",
            "pyaudio>=0.2.14",
            "pydub>=0.25.0",
            "soundfile>=0.12.0",
            "whisper-openai>=20240930"  # OpenAI Whisper for better speech recognition
        ]
        
        for package in voice_packages:
            self.install_package(package, critical=False)
    
    def install_multilingual_dependencies(self):
        """Install multilingual support dependencies"""
        if not self.features['multilingual']:
            return
        
        print("\n🌐 Installing Multilingual Dependencies")
        print("=" * 40)
        
        multilingual_packages = [
            "googletrans==4.0.0rc1",
            "langdetect>=1.0.9",
            "transliterate>=1.10.2",
            "indic-transliteration>=2.3.37",
            "deep-translator>=1.11.4"
        ]
        
        for package in multilingual_packages:
            self.install_package(package, critical=False)
    
    def install_multimodal_dependencies(self):
        """Install multimodal AI dependencies"""
        if not self.features['multimodal']:
            return
        
        print("\n🖼️ Installing Multimodal AI Dependencies")
        print("=" * 40)
        
        # Check for GPU support
        gpu_available = self.check_gpu_support()
        
        multimodal_packages = [
            "opencv-python>=4.8.0",
            "numpy>=1.24.0",
            "matplotlib>=3.7.0",
            "scikit-image>=0.21.0",
            "transformers>=4.35.0",
            "sentence-transformers>=2.2.2",
            "huggingface-hub>=0.17.0"
        ]
        
        # Add AI framework packages
        if gpu_available:
            print("🔥 GPU detected - installing GPU-optimized packages")
            multimodal_packages.extend([
                "torch>=2.1.0",
                "torchvision>=0.16.0",
                "tensorflow-gpu>=2.13.0"
            ])
        else:
            print("💻 CPU-only mode - installing CPU packages")
            multimodal_packages.extend([
                "torch>=2.1.0 --index-url https://download.pytorch.org/whl/cpu",
                "torchvision>=0.16.0 --index-url https://download.pytorch.org/whl/cpu",
                "tensorflow-cpu>=2.13.0"
            ])
        
        for package in multimodal_packages:
            self.install_package(package, critical=False)
    
    def install_advanced_ai_dependencies(self):
        """Install advanced AI model dependencies"""
        if not self.features['advanced_ai']:
            return
        
        print("\n🧠 Installing Advanced AI Dependencies")
        print("=" * 40)
        
        advanced_packages = [
            "openai>=1.0.0",
            "anthropic>=0.7.0",
            "google-generativeai>=0.3.0",
            "langchain>=0.0.350",
            "chromadb>=0.4.0",
            "faiss-cpu>=1.7.4",
            "tiktoken>=0.5.0"
        ]
        
        for package in advanced_packages:
            self.install_package(package, critical=False)
    
    def install_web_dependencies(self):
        """Install web UI dependencies"""
        if not self.features['web_ui']:
            return
        
        print("\n🌐 Installing Web UI Dependencies")
        print("=" * 40)
        
        web_packages = [
            "jinja2>=3.1.0",
            "itsdangerous>=2.1.0",
            "click>=8.1.0",
            "gunicorn>=21.2.0",
            "eventlet>=0.33.0",
            "python-socketio>=5.9.0"
        ]
        
        for package in web_packages:
            self.install_package(package)
    
    def check_gpu_support(self):
        """Check if GPU is available for AI workloads"""
        try:
            import subprocess
            # Check for NVIDIA GPU
            result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
            if result.returncode == 0:
                return True
        except:
            pass
        return False
    
    def setup_web_frontend(self):
        """Setup React frontend dependencies"""
        print("\n🌐 Setting up Web Frontend")
        print("=" * 40)
        
        project_dir = Path("project")
        if not project_dir.exists():
            print("❌ Frontend project directory not found")
            return
        
        # Check if Node.js is installed
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            print(f"✅ Node.js version: {result.stdout.strip()}")
        except FileNotFoundError:
            print("❌ Node.js not found. Please install Node.js from https://nodejs.org")
            return
        
        # Install npm dependencies
        os.chdir(project_dir)
        if self.run_command("npm install", "Installing frontend dependencies"):
            print("✅ Frontend setup completed")
        os.chdir("..")
    
    def create_configuration_files(self):
        """Create necessary configuration files"""
        print("\n⚙️ Creating Configuration Files")
        print("=" * 40)
        
        # Create .env file if it doesn't exist
        if not Path(".env").exists():
            env_content = f"""# YourDaddy Assistant Configuration
# Backend Mode: simple, enhanced, full
BACKEND_MODE={'full' if self.features['multimodal'] else 'enhanced' if self.features['multilingual'] else 'simple'}

# Feature Flags
ENABLE_MULTIMODAL={'true' if self.features['multimodal'] else 'false'}
ENABLE_MULTILINGUAL={'true' if self.features['multilingual'] else 'false'}
ENABLE_VOICE={'true' if self.features['voice'] else 'false'}
ENABLE_AUTOMATION=true
ENABLE_LOGGING=true

# Security
JWT_SECRET_KEY=your-secret-key-here
ADMIN_PASSWORD=changeme123

# Optional API Keys (add your own)
# OPENAI_API_KEY=your-openai-key
# GOOGLE_API_KEY=your-google-key
"""
            with open(".env", "w") as f:
                f.write(env_content)
            print("✅ Created .env configuration file")
    
    def run_tests(self):
        """Run basic tests to verify installation"""
        print("\n🧪 Running Installation Tests")
        print("=" * 40)
        
        # Test core imports
        test_imports = [
            ("flask", "Flask web framework"),
            ("requests", "HTTP requests"),
            ("dotenv", "Environment variables")
        ]
        
        if self.features['voice']:
            test_imports.extend([
                ("speech_recognition", "Speech recognition"),
                ("pyttsx3", "Text-to-speech")
            ])
        
        if self.features['multilingual']:
            test_imports.append(("googletrans", "Google Translate"))
        
        if self.features['multimodal']:
            test_imports.extend([
                ("cv2", "OpenCV"),
                ("torch", "PyTorch")
            ])
        
        for module, description in test_imports:
            try:
                __import__(module)
                print(f"✅ {description}")
            except ImportError:
                print(f"❌ {description}")
    
    def show_summary(self):
        """Show installation summary"""
        print("\n" + "=" * 60)
        print("🎉 SETUP COMPLETE!")
        print("=" * 60)
        
        print("\n📊 Installation Summary:")
        print(f"✅ Successfully installed: {len(self.installed_packages)} packages")
        if self.failed_packages:
            print(f"❌ Failed to install: {len(self.failed_packages)} packages")
            print("Failed packages:", ", ".join(self.failed_packages))
        
        print("\n🎯 Enabled Features:")
        for feature, enabled in self.features.items():
            status = "✅" if enabled else "❌"
            print(f"{status} {feature.replace('_', ' ').title()}")
        
        print("\n🚀 Next Steps:")
        print("1. Review and update the .env configuration file")
        print("2. Add your API keys to .env if needed")
        print("3. Run the application:")
        print("   Windows: start.bat app")
        print("   Linux/macOS: ./start.sh app")
        print("\n4. Or start the web interface:")
        print("   Windows: start.bat web")
        print("   Linux/macOS: ./start.sh web")
        
        if self.failed_packages:
            print("\n⚠️ Some optional packages failed to install.")
            print("This is normal - try installing them manually if needed:")
            for package in self.failed_packages:
                print(f"   pip install {package}")

def main():
    """Main setup function"""
    print("🎯 YourDaddy Assistant - Unified Setup")
    print("=" * 60)
    print("Welcome to the YourDaddy Assistant setup wizard!")
    print("This will install all necessary dependencies for your chosen features.")
    print()
    
    setup = SetupManager()
    
    # Show feature selection menu
    setup.show_menu()
    
    print("\n🚀 Starting Installation Process")
    print("=" * 40)
    print("Selected features:", ", ".join([k for k, v in setup.features.items() if v]))
    print()
    
    # Install dependencies based on selected features
    setup.install_core_dependencies()
    setup.install_voice_dependencies()
    setup.install_multilingual_dependencies()
    setup.install_multimodal_dependencies()
    setup.install_advanced_ai_dependencies()
    setup.install_web_dependencies()
    
    # Create configuration files
    setup.create_configuration_files()
    
    # Run tests
    setup.run_tests()
    
    # Show summary
    setup.show_summary()

if __name__ == "__main__":
    main()