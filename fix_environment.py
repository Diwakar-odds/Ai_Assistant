"""
Environment Fix Script for YourDaddy Assistant
This script ensures all modules are installed in the correct virtual environment
and provides detailed diagnostics.
"""

import subprocess
import sys
import os
from pathlib import Path

# Setup centralized logging
from utils.logging_config import get_logger
logger = get_logger(__name__, log_category='system')

def print_header(title):
    """Print a formatted header"""
    logger.info("\n" + "="*70)
    logger.info(f"  {title}")
    logger.info("="*70)

def get_venv_python():
    """Get the path to the virtual environment Python executable."""
    venv_path = Path(__file__).parent / ".venv"
    
    if sys.platform == "win32":
        python_exe = venv_path / "Scripts" / "python.exe"
    else:
        python_exe = venv_path / "bin" / "python"
    
    return python_exe if python_exe.exists() else None

def check_current_environment():
    """Check which Python interpreter is currently being used."""
    print_section("Current Environment Check")
    
    print(f"Python Executable: {sys.executable}")
    print(f"Python Version: {sys.version}")
    print(f"Python Path: {sys.path[0]}")
    
    venv_python = get_venv_python()
    if venv_python:
        print(f"\n[OK] Virtual environment found at: {venv_python}")
        if str(venv_python) in sys.executable or str(venv_python.resolve()) == Path(sys.executable).resolve():
            print("[OK] Currently using virtual environment")
            return True
        else:
            print("[ERROR] NOT using virtual environment!")
            print(f"\nExpected: {venv_python}")
            print(f"Current:  {sys.executable}")
            return False
    else:
        print("[ERROR] Virtual environment not found!")
        return False

def install_requirements(python_exe):
    """Install all requirements using the specified Python executable."""
    print_section("Installing Requirements")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print(f"✗ requirements.txt not found at {requirements_file}")
        return False
    
    print(f"Installing packages from {requirements_file}")
    print("This may take several minutes...\n")
    
    try:
        # Upgrade pip first
        print("Upgrading pip...")
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            capture_output=False
        )
        
        # Install requirements
        print("\nInstalling requirements...")
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "install", "-r", str(requirements_file)],
            check=True,
            capture_output=False
        )
        
        print("\n[OK] All requirements installed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Installation failed with error: {e}")
        return False

def verify_critical_modules(python_exe):
    """Verify that critical modules can be imported."""
    print_section("Verifying Critical Modules")
    
    critical_modules = [
        "flask",
        "flask_socketio",
        "flask_cors",
        "flask_jwt_extended",
        "flask_limiter",
        "werkzeug",
        "dotenv",
        "google.generativeai",
        "vosk",
        "pyttsx3",
        "SpeechRecognition",
        "psutil",
        "PIL",
        "cv2",
        "numpy",
        "spotipy",
        "ytmusicapi",
    ]
    
    failed_imports = []
    
    for module in critical_modules:
        try:
            result = subprocess.run(
                [str(python_exe), "-c", f"import {module}"],
                check=True,
                capture_output=True,
                text=True
            )
            print(f"✓ {module}")
        except subprocess.CalledProcessError as e:
            print(f"✗ {module} - FAILED")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n[ERROR] {len(failed_imports)} modules failed to import:")
        for module in failed_imports:
            print(f"  - {module}")
        return False
    else:
        print(f"\n[OK] All {len(critical_modules)} critical modules verified successfully!")
        return True

def create_activation_scripts():
    """Create easy activation scripts for the virtual environment."""
    print_section("Creating Activation Helper Scripts")
    
    # Windows batch script
    activate_bat = Path(__file__).parent / "activate_venv.bat"
    activate_bat.write_text(
        "@echo off\n"
        "echo Activating virtual environment...\n"
        "call .venv\\Scripts\\activate.bat\n"
        "echo.\n"
        "echo Virtual environment activated!\n"
        "echo Python: %VIRTUAL_ENV%\\Scripts\\python.exe\n"
        "echo.\n"
        "echo To deactivate, type: deactivate\n"
    )
    print(f"[OK] Created {activate_bat}")
    
    # Bash script
    activate_sh = Path(__file__).parent / "activate_venv.sh"
    activate_sh.write_text(
        "#!/bin/bash\n"
        "echo 'Activating virtual environment...'\n"
        "source .venv/Scripts/activate\n"
        "echo ''\n"
        "echo 'Virtual environment activated!'\n"
        "echo \"Python: $VIRTUAL_ENV/Scripts/python\"\n"
        "echo ''\n"
        "echo 'To deactivate, type: deactivate'\n"
    )
    activate_sh.chmod(0o755)
    print(f"✓ Created {activate_sh}")
    
    print("\nTo activate the virtual environment:")
    print("  Windows: activate_venv.bat")
    print("  Linux/Mac: source activate_venv.sh")

def main():
    """Main function to fix environment issues."""
    print("\n" + "="*70)
    print("  YourDaddy Assistant - Environment Fix Tool")
    print("="*70)
    
    # Check if we're using the correct environment
    using_venv = check_current_environment()
    
    venv_python = get_venv_python()
    
    if not venv_python:
        print("\n" + "!"*70)
        print("ERROR: Virtual environment not found!")
        print("Please create a virtual environment first:")
        print("  python -m venv .venv")
        print("!"*70)
        return False
    
    # Install requirements
    if not install_requirements(venv_python):
        return False
    
    # Verify imports
    if not verify_critical_modules(venv_python):
        return False
    
    # Create activation scripts
    create_activation_scripts()
    
    # Final instructions
    print_section("Setup Complete!")
    
    if not using_venv:
        print("\n[WARNING] IMPORTANT: You are NOT using the virtual environment!")
        print("\nTo fix this, you must:")
        print("  1. Close this terminal")
        print("  2. Open a new terminal")
        print("  3. Navigate to the project directory")
        print("  4. Activate the virtual environment:")
        print("     Windows: .venv\\Scripts\\activate")
        print("     or simply run: activate_venv.bat")
        print("  5. Run your application")
        print("\nAlternatively, always run scripts with:")
        print(f"  {venv_python} your_script.py")
    else:
        print("\n[OK] You are using the correct virtual environment!")
        print("[OK] All modules are installed and verified!")
        print("\nYou can now run your application normally.")
    
    print("\n" + "="*70)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
