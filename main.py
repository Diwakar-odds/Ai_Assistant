#!/usr/bin/env python3
"""
AI Assistant - Main Entry Point

This is the main entry point for the AI Assistant application.
It provides a unified interface to start the assistant with different
configurations and interfaces.

Features PIN-based authentication for secure access.
"""

import sys
import os
import argparse
import signal
import logging
import traceback
from pathlib import Path

# Fix Windows console encoding for emojis using the new bootstrap
try:
    from core_ai.src.ai_assistant.utils.utf8_bootstrap import configure_utf8_stdout
    configure_utf8_stdout()
except Exception:
    pass

# Setup basic logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Add the project directories to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info("\n🛑 Shutdown signal received. Cleaning up...")
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, 'SIGTERM'):
    signal.signal(signal.SIGTERM, signal_handler)




def main():
    """Main entry point for the AI Assistant."""
    try:
        # Initialize config files from examples if needed
        try:
            from setup_config import setup_config_files
            setup_config_files()
        except Exception as e:
            logger.warning(f"Could not auto-initialize config files: {e}")
        
        # Show welcome banner
        print("\n" + "=" * 60)
        print("Pulsar AI Assistant")
        print("=" * 60)
    except Exception as e:
        logger.error(f"Initialization error: {e}")
    
    parser = argparse.ArgumentParser(description="AI Assistant - Your intelligent companion")
    parser.add_argument("--interface", choices=["cli", "web", "desktop", "desktop_modern"], default=None,
                       help="Interface to use (defaults to last used, or web)")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--port", type=int, default=8000, help="Port for web interface (default: 8000)")
    parser.add_argument("--setup-pin", action="store_true", help="Setup or change PIN")
    parser.add_argument("--skip-auth", action="store_true", default=False, help="Skip PIN authentication (development only)")
    
    args = parser.parse_args()
    
    # 1.5 Improve Startup Experience - Remember the last interface
    try:
        import json
        settings_path = project_root / 'config' / 'user_settings.json'
        
        # Load settings
        settings_data = {}
        if settings_path.exists():
            with open(settings_path, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
                
        # Determine interface
        if args.interface:
            interface_to_use = args.interface
        else:
            interface_to_use = settings_data.get("last_interface", "web")
            
        # Save last interface
        settings_data["last_interface"] = interface_to_use
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings_data, f, indent=2)
            
        args.interface = interface_to_use
    except Exception as e:
        logger.warning(f"Could not load/save last interface preference: {e}")
        if not args.interface:
            args.interface = "web"
    
    # Handle PIN setup
    if args.setup_pin:
        try:
            from ai_assistant.auth import setup_pin_cli
            setup_pin_cli()
            return
        except ImportError as e:
            print(f"❌ Error importing PIN authentication: {e}")
            print("Please ensure the authentication module is properly installed.")
            sys.exit(1)
    
    # Authenticate user (unless skipped for development)
    if not args.skip_auth:
        try:
            from ai_assistant.auth import authenticate
            if not authenticate():
                print("❌ Authentication failed. Exiting...")
                sys.exit(1)
        except ImportError as e:
            print(f"❌ Error importing PIN authentication: {e}")
            print("Setting up authentication system...")
            try:
                from ai_assistant.auth import setup_pin_cli
                if not setup_pin_cli():
                    print("❌ Failed to setup authentication. Exiting...")
                    sys.exit(1)
                print("✅ Authentication setup complete. Please restart the assistant.")
                return
            except ImportError:
                print("❌ Authentication module not available. Please check installation.")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            sys.exit(1)
    
    print("\n🚀 Starting AI Assistant...")
    
    try:
        if args.interface == "web":
            print(f"Starting web interface on port {args.port}...")
            # Start the web backend
            try:
                from ai_assistant.services.modern_web_backend import app, socketio
                print("🌐 Starting Pulsar Assistant Web Backend...")
                socketio.run(app, host='0.0.0.0', port=args.port, debug=args.verbose)
            except ImportError as e:
                print(f"❌ Web backend import failed: {e}")
                print("Please check your installation and dependencies.")
                sys.exit(1)
                    
        elif args.interface == "cli":
            # Try multiple possible locations for CLI
            try:
                from ai_assistant.apps.app import main as cli_main
                print("Starting CLI interface...")
                cli_main()  # Actually call the CLI main function
            except ImportError:
                try:
                    import app
                    print("Starting CLI interface...")
                    if hasattr(app, 'main'):
                        app.main()
                    else:
                        print("❌ CLI main function not found.")
                        sys.exit(1)
                except ImportError:
                    print("❌ CLI interface not found. Please check your installation.")
                    sys.exit(1)
                    
        elif args.interface == "desktop":
            # Try multiple possible locations for desktop GUI
            try:
                from ai_assistant.apps.pulsar_app import main as desktop_main
                print("Starting desktop interface...")
                desktop_main()  # Actually call the desktop main function
            except ImportError:
                try:
                    import pulsar_app
                    print("Starting desktop interface...")
                    if hasattr(pulsar_app, 'main'):
                        pulsar_app.main()
                    else:
                        print("❌ Desktop main function not found.")
                        sys.exit(1)
                except ImportError:
                    print("❌ Desktop interface not found. Please check your installation.")
                    sys.exit(1)
                    
        elif args.interface == "desktop_modern":
            try:
                from ai_assistant.apps.modern_desktop_app import main as modern_main
                print("Starting modern desktop interface (webview)...")
                modern_main()
            except ImportError as e:
                print(f"❌ Modern desktop interface not found. Error: {e}")
                print("Please ensure pywebview is installed: pip install pywebview")
                sys.exit(1)
            
    except ImportError as e:
        logger.error(f"Import error: {e}")
        print(f"❌ Error importing required modules: {e}")
        print("Please ensure all dependencies are installed:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Application stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.debug(traceback.format_exc())
        print(f"❌ Fatal error: {e}")
        print("\nFor detailed error information, check the logs.")
        sys.exit(1)

if __name__ == "__main__":
    main()
