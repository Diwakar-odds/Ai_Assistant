#!/usr/bin/env python3
"""
Pulsar Assistant - Unified Main Application
Entry point that includes system checks, configuration, and application startup
"""

import sys
import os
import traceback
import time
import argparse
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "modules"))
sys.path.insert(0, str(project_root / "utils"))

# Import utilities
try:
    from utils.logging_config import get_logger, setup_logging
    setup_logging()
    logger = get_logger(__name__)
except ImportError:
    # Fallback logging if advanced logging fails
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

def show_help():
    """Show help information"""
    print("ðŸ¤– Pulsar Assistant v3.1 - Usage Guide")
    print("=" * 50)
    print()
    print("Usage: python app.py [mode] [options]")
    print()
    print("Modes:")
    print("  gui        Launch with graphical interface (default)")
    print("  cli        Launch command-line interface")
    print("  web        Start web backend server only")
    print("  check      Run system check only")
    print("  setup      Run setup wizard")
    print("  test       Run test suite")
    print("  help       Show this help message")
    print()
    print("Options:")
    print("  --no-checks    Skip system compatibility checks")
    print("  --debug        Enable debug mode")
    print("  --port PORT    Set web server port (default: 5000)")
    print("  --host HOST    Set web server host (default: 0.0.0.0)")
    print()
    print("Examples:")
    print("  python app.py                # Start GUI mode")
    print("  python app.py web            # Start web server")
    print("  python app.py cli --debug    # CLI with debug mode")
    print("  python app.py check          # Check system only")

def run_system_check():
    """Run system compatibility check"""
    try:
        from launch_assistant import SystemChecker
        checker = SystemChecker()
        return checker.run_full_check()
    except ImportError:
        logger.warning("System checker not available")
        return True

def start_web_server(host='0.0.0.0', port=5000):
    """Start the web backend server"""
    try:
        logger.info(f"ðŸŒ Starting web server on {host}:{port}")
        
        # Set environment variables for backend configuration
        os.environ['HOST'] = str(host)
        os.environ['PORT'] = str(port)
        
        # Import and start backend
        from backend import main as start_backend
        start_backend()
        
    except ImportError:
        logger.error("âŒ Web backend not available")
        return False
    except Exception as e:
        logger.error(f"âŒ Web server failed: {e}")
        traceback.print_exc()
        return False

def start_gui_app():
    """Start the GUI application"""
    try:
        logger.info("ðŸ–¥ï¸ Starting GUI application")
        
        from pulsar_app import PulsarAssistant
        assistant = PulsarAssistant()
        assistant.run()
        
    except ImportError:
        logger.error("âŒ GUI application not available")
        return False
    except Exception as e:
        logger.error(f"âŒ GUI failed: {e}")
        traceback.print_exc()
        return False

def start_cli_app():
    """Start the command-line interface with learning integration"""
    try:
        logger.info("ðŸ’» Starting CLI application")
        
        # Initialize learning systems
        learning_active = False
        learning_assistant = None
        try:
            from ai_assistant.integrations.learning_integration import get_learning_assistant
            learning_assistant = get_learning_assistant()
            learning_active = learning_assistant.systems_active
            if learning_active:
                logger.info("âœ… Learning systems active")
        except ImportError:
            logger.warning("âš ï¸ Learning systems not available")
        
        # Simple CLI loop
        try:
            from ai_assistant.ai.conversational_ai import AdvancedConversationalAI
            ai = AdvancedConversationalAI()
            
            print("\nðŸ¤– Pulsar Assistant CLI")
            if learning_active:
                print("ðŸ§  Learning Mode: ACTIVE")
            print("Type 'quit', 'exit', or Ctrl+C to stop\n")
            
            command_history = []
            
            while True:
                # Show command suggestions if available
                if learning_active and command_history:
                    try:
                        suggestions = learning_assistant.get_command_suggestions("", {})
                        if suggestions:
                            print(f"ðŸ’¡ Suggestions: {', '.join(suggestions[:3])}")
                    except:
                        pass
                
                user_input = input("You: ").strip()
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    if learning_active:
                        stats = learning_assistant.get_session_stats()
                        print(f"\nðŸ“Š Session stats: {stats['commands_executed']} commands executed")
                    print("ðŸ‘‹ Goodbye!")
                    break
                
                if user_input:
                    start_time = time.time()
                    
                    # Generate intelligent response using learning
                    if learning_active:
                        user_input = learning_assistant.generate_intelligent_response(user_input)
                    
                    print("Assistant: ", end="", flush=True)
                    def stream_callback(token):
                        print(token, end="", flush=True)
                    response = ai.generate_model_response(user_input, stream_callback=stream_callback)
                    print("\n")
                    
                    # Log interaction for learning
                    if learning_active:
                        execution_time = time.time() - start_time
                        learning_assistant.log_command_execution(
                            user_input, response, True, execution_time
                        )
                        learning_assistant.log_conversation(user_input, response)
                        command_history.append(user_input)
                    
                    # Keep only recent history
                    if len(command_history) > 10:
                        command_history.pop(0)
        
        except ImportError:
            # Fallback simple CLI
            print("\nðŸ¤– Pulsar Assistant - Simple CLI")
            print("(Advanced AI not available)")
            print("Type 'quit' to exit\n")
            
            while True:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit']:
                    print("ðŸ‘‹ Goodbye!")
                    break
                
                if user_input:
                    print(f"Assistant: I received your message: {user_input}")
                    print("(Connect to web interface for full functionality)\n")
        
    except KeyboardInterrupt:
        print("\nðŸ‘‹ Goodbye!")
    except Exception as e:
        logger.error(f"âŒ CLI failed: {e}")
        traceback.print_exc()
        return False

def run_setup():
    """Run the setup wizard"""
    try:
        logger.info("âš™ï¸ Starting setup wizard")
        from setup import main as setup_main
        setup_main()
    except ImportError:
        logger.error("âŒ Setup wizard not available")
        return False
    except Exception as e:
        logger.error(f"âŒ Setup failed: {e}")
        traceback.print_exc()
        return False

def run_tests():
    """Run the test suite"""
    try:
        logger.info("ðŸ§ª Starting test suite")
        
        # Try different test options
        test_files = [
            ('test_chat.py', 'Chat functionality tests'),
            ('test_integration.py', 'Integration tests'),
            ('debug.py', 'Debug and diagnostics')
        ]
        
        print("\nAvailable test suites:")
        for i, (file, desc) in enumerate(test_files, 1):
            exists = os.path.exists(file)
            status = "âœ…" if exists else "âŒ"
            print(f"{i}. {desc} {status}")
        
        choice = input("\nSelect test suite (1-3, or Enter for all): ").strip()
        
        if choice == "1" and os.path.exists('test_chat.py'):
            os.system(f"{sys.executable} test_chat.py")
        elif choice == "2" and os.path.exists('test_integration.py'):
            os.system(f"{sys.executable} test_integration.py")
        elif choice == "3" and os.path.exists('debug.py'):
            os.system(f"{sys.executable} debug.py")
        else:
            # Run all available tests
            for file, desc in test_files:
                if os.path.exists(file):
                    print(f"\n{'='*50}")
                    print(f"Running: {desc}")
                    print(f"{'='*50}")
                    os.system(f"{sys.executable} {file}")
        
    except Exception as e:
        logger.error(f"âŒ Tests failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(description='Pulsar Assistant v3.1')
    parser.add_argument('mode', nargs='?', default='gui', 
                       choices=['gui', 'cli', 'web', 'check', 'setup', 'test', 'help'],
                       help='Application mode')
    parser.add_argument('--no-checks', action='store_true', 
                       help='Skip system compatibility checks')
    parser.add_argument('--debug', action='store_true', 
                       help='Enable debug mode')
    parser.add_argument('--port', type=int, default=5000, 
                       help='Web server port (default: 5000)')
    parser.add_argument('--host', default='0.0.0.0', 
                       help='Web server host (default: 0.0.0.0)')
    parser.add_argument('--skip-auth', action='store_true', 
                       help='Skip PIN authentication (development only)')
    
    args = parser.parse_args()
    
    # Show help
    if args.mode == 'help':
        show_help()
        return
    
    # PIN Authentication (unless skipped or in check mode)
    if not args.skip_auth and args.mode != 'check':
        print("ðŸ” PIN Authentication Required")
        print("-" * 30)
        try:
            import sys
            sys.path.insert(0, '../../')  # Add root directory to path
            from ai_assistant.auth import authenticate
            if not authenticate():
                print("âŒ Authentication failed. Exiting...")
                sys.exit(1)
            print("âœ… Authentication successful!\n")
        except ImportError as e:
            logger.error(f"Error importing PIN authentication: {e}")
            print("âŒ Authentication module not available. Please run from main.py or setup authentication.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            sys.exit(1)
    
    # Set debug mode
    if args.debug:
        logger.setLevel(logging.DEBUG)
        os.environ['DEBUG'] = 'true'
    
    print("ðŸ¤– Pulsar Assistant v3.1")
    print("=" * 40)
    
    # Run system checks (unless skipped)
    if not args.no_checks and args.mode != 'check':
        logger.info("ðŸ” Running system checks...")
        if not run_system_check():
            logger.warning("âš ï¸ System check failed, but continuing anyway...")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                logger.info("Exiting due to system check failure")
                return
    
    # Route to appropriate mode
    try:
        if args.mode == 'check':
            success = run_system_check()
            if success:
                print("âœ… All system checks passed!")
            else:
                print("âŒ Some system checks failed")
            return
        
        elif args.mode == 'web':
            start_web_server(args.host, args.port)
        
        elif args.mode == 'gui':
            start_gui_app()
        
        elif args.mode == 'cli':
            start_cli_app()
        
        elif args.mode == 'setup':
            run_setup()
        
        elif args.mode == 'test':
            run_tests()
        
        else:
            logger.error(f"Unknown mode: {args.mode}")
            show_help()
    
    except KeyboardInterrupt:
        logger.info("\nðŸ‘‹ Application stopped by user")
    except Exception as e:
        logger.error(f"âŒ Application failed: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
