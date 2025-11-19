#!/usr/bin/env python3
"""
YourDaddy Assistant - Main Application
A sophisticated AI-powered personal assistant with voice recognition,
smart automation, multilingual support, and modern interface capabilities.
"""

import sys
import os
import time
import threading
import json
from pathlib import Path
from datetime import datetime
from utils.user_data_logger import log_query, log_reply, log_action, log_module_usage

# Add project modules to path
sys.path.append(str(Path(__file__).parent / "modules"))

# Validate configuration before loading modules
try:
    from config_validator import validate_config
    print("🔍 Validating configuration...")
    config_validator = validate_config(exit_on_failure=False)
    if not config_validator.validate():
        print("\n⚠️ Warning: Some required configurations are missing.")
        print("The application may not work correctly.")
        response = input("\nDo you want to continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
except Exception as e:
    print(f"⚠️ Configuration validation failed: {e}")
    print("Continuing anyway, but some features may not work...")

# Core imports
try:
    from automation_tools_new import *
    print("✅ Automation tools loaded successfully")
except ImportError as e:
    print(f"❌ Failed to load automation tools: {e}")
    sys.exit(1)

# Multilingual support import
try:
    from multilingual import MultilingualSupport, Language, LanguageContext, voice_listen_loop
    print("✅ Multilingual support loaded successfully")
except ImportError as e:
    print(f"⚠️ Multilingual support not available: {e}")
    MultilingualSupport = None
    voice_listen_loop = None

# GUI imports
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    print("✅ GUI framework loaded")
except ImportError:
    print("❌ GUI framework not available")

class YourDaddyAssistant:
    """Main YourDaddy Assistant Application"""
    
    def __init__(self):
        self.version = "3.1.0"  # Updated version for multilingual support
        self.running = False
        self.voice_listening = False
        self.talkback_enabled = True  # Auto-speak responses
        self.config = self.load_config()
        
        # Initialize components
        self.setup_logging()
        self.setup_memory()
        self.setup_multilingual()
        self.setup_voice_recognition()
        self.setup_gui()
        
        print(f"🚀 YourDaddy Assistant {self.version} initialized with multilingual support")
    
    def load_config(self):
        """Load configuration from multimodal_config.json"""
        config_path = Path("multimodal_config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            return self.default_config()
    
    def default_config(self):
        """Default configuration"""
        return {
            "ui": {"theme": "dark", "animations": True},
            "voice": {"enabled": True, "wake_word": "hey daddy"},
            "features": {
                "multimodal_ai": True,
                "voice_commands": True,
                "smart_automation": True
            }
        }
    
    def setup_logging(self):
        """Setup logging system"""
        from utils.logging_config import get_logger
        self.logger = get_logger('yourdaddy_app', log_category='app')
        self.logger.info("Logging system initialized")
    
    def setup_memory(self):
        """Initialize memory system"""
        try:
            setup_memory()
            self.logger.info("Memory system initialized")
        except Exception as e:
            self.logger.error(f"Memory setup failed: {e}")
    
    def setup_multilingual(self):
        """Initialize multilingual support"""
        try:
            if MultilingualSupport:
                # Get language configuration from main config
                lang_config = self.config.get('languages', {})
                
                # Initialize multilingual support
                self.multilingual = MultilingualSupport(lang_config)
                
                # Set default language preference
                user_id = "default_user"
                primary_lang = lang_config.get('primary', 'hinglish')
                self.multilingual.set_language_preference(
                    user_id, 
                    Language(primary_lang)
                )
                
                self.logger.info("✅ Multilingual support initialized")
                self.multilingual_enabled = True
            else:
                self.logger.warning("⚠️ Multilingual support not available")
                self.multilingual = None
                self.multilingual_enabled = False
                
        except Exception as e:
            self.logger.error(f"Multilingual setup failed: {e}")
            self.multilingual = None
            self.multilingual_enabled = False
    
    def setup_voice_recognition(self):
        """Initialize voice recognition with multilingual support"""
        try:
            # Check if voice recognition is available
            if voice_listen_loop is None:
                self.voice_enabled = False
                self.logger.warning("Voice recognition module not available")
                return
            
            # Initialize voice control attributes
            self.voice_enabled = True
            self.voice_stop_event = threading.Event()
            self.voice_thread = None
            self.wake_words = self.config.get('voice', {}).get('wake_word', {}).get('hindi_keywords', ['hey daddy', 'arre daddy', 'sun daddy'])
            
            # Enable multilingual voice recognition if available
            if self.multilingual_enabled:
                self.voice_languages = self.config.get('voice', {}).get('recognition', {}).get('supported_languages', ['en-US', 'hi-IN', 'en-IN'])
                self.use_vosk = self.config.get('voice', {}).get('recognition', {}).get('engine', 'vosk') == 'vosk'
                self.logger.info(f"Voice recognition ready with languages: {self.voice_languages}")
                self.logger.info(f"Using {'Vosk (offline)' if self.use_vosk else 'Google (online)'}")
            else:
                self.voice_languages = ['en-US']
                self.use_vosk = True
                self.logger.info("Voice recognition ready (English only)")
                
        except Exception as e:
            self.voice_enabled = False
            self.logger.error(f"Voice recognition setup failed: {e}")
    
    def setup_gui(self):
        """Setup graphical user interface"""
        try:
            self.root = tk.Tk()
            self.root.title(f"YourDaddy Assistant {self.version}")
            self.root.geometry("800x600")
            self.root.configure(bg='#1e1e1e')
            
            # Main frame
            main_frame = ttk.Frame(self.root)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # Title
            title = ttk.Label(
                main_frame,
                text="YourDaddy Assistant",
                font=("Arial", 24, "bold")
            )
            title.pack(pady=(0, 20))
            
            # Status frame
            status_frame = ttk.Frame(main_frame)
            status_frame.pack(fill=tk.X, pady=(0, 20))
            
            self.status_label = ttk.Label(
                status_frame,
                text="Ready",
                font=("Arial", 12)
            )
            self.status_label.pack(side=tk.LEFT)
            
            # Language selection
            if self.multilingual_enabled:
                lang_frame = ttk.Frame(status_frame)
                lang_frame.pack(side=tk.LEFT, padx=(20, 0))
                
                ttk.Label(lang_frame, text="Language:").pack(side=tk.LEFT)
                
                self.language_var = tk.StringVar()
                self.language_var.set("hinglish")
                
                language_menu = ttk.Combobox(
                    lang_frame,
                    textvariable=self.language_var,
                    values=["english", "hindi", "hinglish"],
                    state="readonly",
                    width=10
                )
                language_menu.pack(side=tk.LEFT, padx=(5, 0))
                language_menu.bind('<<ComboboxSelected>>', self.on_language_change)
                
                # Translation button
                self.translate_button = ttk.Button(
                    lang_frame,
                    text="🔄 Translate",
                    command=self.toggle_translation_mode
                )
                self.translate_button.pack(side=tk.LEFT, padx=(5, 0))
            
            # Voice button
            self.voice_button = ttk.Button(
                status_frame,
                text="🎤 Voice",
                command=self.toggle_voice_listening
            )
            self.voice_button.pack(side=tk.RIGHT)
            
            # Talkback toggle button
            self.talkback_button = ttk.Button(
                status_frame,
                text="🔊 Talkback: ON" if self.talkback_enabled else "🔇 Talkback: OFF",
                command=self.toggle_talkback
            )
            self.talkback_button.pack(side=tk.RIGHT, padx=(0, 5))
            
            # Voice Settings button
            self.voice_settings_button = ttk.Button(
                status_frame,
                text="⚙️ Voice Settings",
                command=self.show_voice_settings
            )
            self.voice_settings_button.pack(side=tk.RIGHT, padx=(0, 5))
            
            # Command entry
            command_frame = ttk.Frame(main_frame)
            command_frame.pack(fill=tk.X, pady=(0, 20))
            
            ttk.Label(command_frame, text="Command:", font=("Arial", 12)).pack(anchor=tk.W)
            
            self.command_entry = ttk.Entry(command_frame, font=("Arial", 11))
            self.command_entry.pack(fill=tk.X, pady=(5, 0))
            self.command_entry.bind('<Return>', self.process_text_command)
            
            # Output text area
            output_frame = ttk.Frame(main_frame)
            output_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(output_frame, text="Output:", font=("Arial", 12)).pack(anchor=tk.W)
            
            # Text widget with scrollbar
            text_frame = ttk.Frame(output_frame)
            text_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
            
            self.output_text = tk.Text(
                text_frame,
                wrap=tk.WORD,
                font=("Consolas", 10),
                bg='#2d2d2d',
                fg='#ffffff',
                insertbackground='#ffffff'
            )
            
            scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.output_text.yview)
            self.output_text.configure(yscrollcommand=scrollbar.set)
            
            self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Control buttons
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(20, 0))
            
            ttk.Button(
                button_frame,
                text="Discover Apps",
                command=self.discover_applications
            ).pack(side=tk.LEFT, padx=(0, 10))
            
            ttk.Button(
                button_frame,
                text="System Status",
                command=self.show_system_status
            ).pack(side=tk.LEFT, padx=(0, 10))
            
            ttk.Button(
                button_frame,
                text="Clear",
                command=self.clear_output
            ).pack(side=tk.RIGHT)
            
            self.gui_ready = True
            self.log_output("YourDaddy Assistant GUI initialized")
            
        except Exception as e:
            self.gui_ready = False
            self.logger.error(f"GUI setup failed: {e}")
    
    def log_output(self, message, level="INFO", speak=False):
        """Log message to output area with optional voice feedback"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}\n"
        
        if hasattr(self, 'output_text'):
            self.output_text.insert(tk.END, formatted_message)
            self.output_text.see(tk.END)
        
        self.logger.info(message)
        
        # Auto-speak if enabled
        if speak and self.talkback_enabled and self.multilingual_enabled and hasattr(self, 'multilingual'):
            try:
                # Clean message for speaking (remove emojis and timestamps)
                clean_msg = message.split(':', 1)[-1].strip() if ':' in message else message
                self.multilingual.speak_multilingual(clean_msg)
            except Exception as e:
                self.logger.error(f"TTS error: {e}")
    
    def toggle_voice_listening(self):
        """Toggle voice listening mode"""
        if not self.voice_enabled:
            self.log_output("Voice recognition not available", "WARNING")
            messagebox.showwarning(
                "Voice Recognition",
                "Voice recognition is not available.\n\nPlease ensure:\n" +
                "1. PyAudio is installed (pip install pyaudio)\n" +
                "2. Vosk models are downloaded\n" +
                "3. Microphone is connected"
            )
            return
        
        self.voice_listening = not self.voice_listening
        
        if self.voice_listening:
            # Start voice listening
            self.voice_button.configure(text="🔴 Stop")
            self.status_label.configure(text="Listening for wake word...")
            self.log_output(f"Voice listening started. Say: {', '.join(self.wake_words)}")
            
            # Clear stop event
            self.voice_stop_event.clear()
            
            # Start voice listening in separate thread
            self.voice_thread = threading.Thread(target=self.voice_listen_loop, daemon=True)
            self.voice_thread.start()
            
        else:
            # Stop voice listening
            self.log_output("Stopping voice listening...")
            self.voice_button.configure(text="⏳ Stopping...")
            
            # Signal thread to stop
            if hasattr(self, 'voice_stop_event'):
                self.voice_stop_event.set()
            
            # Reset button after a delay
            self.root.after(1000, self._reset_voice_button)
    
    def toggle_talkback(self):
        """Toggle automatic voice response (talkback) feature"""
        self.talkback_enabled = not self.talkback_enabled
        
        if hasattr(self, 'talkback_button'):
            button_text = "🔊 Talkback: ON" if self.talkback_enabled else "🔇 Talkback: OFF"
            self.talkback_button.configure(text=button_text)
        
        status = "enabled" if self.talkback_enabled else "disabled"
        self.log_output(f"Talkback {status}", speak=self.talkback_enabled)
    
    def show_voice_settings(self):
        """Show voice settings dialog"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("🎤 Voice Settings")
        settings_window.geometry("400x300")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Settings frame
        main_frame = ttk.Frame(settings_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Wake words setting
        ttk.Label(main_frame, text="Wake Words:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        wake_words_text = ", ".join(self.wake_words)
        self.wake_words_var = tk.StringVar(value=wake_words_text)
        wake_entry = ttk.Entry(main_frame, textvariable=self.wake_words_var, width=50)
        wake_entry.pack(fill=tk.X, pady=(2, 10))
        
        # Voice engine setting
        ttk.Label(main_frame, text="Voice Engine:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.voice_engine_var = tk.StringVar(value="Vosk (Offline)" if self.use_vosk else "Google (Online)")
        engine_combo = ttk.Combobox(main_frame, textvariable=self.voice_engine_var, 
                                   values=["Vosk (Offline)", "Google (Online)"], state="readonly")
        engine_combo.pack(fill=tk.X, pady=(2, 10))
        
        # Language setting
        ttk.Label(main_frame, text="Voice Language:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.voice_lang_var = tk.StringVar(value="Auto-detect")
        lang_combo = ttk.Combobox(main_frame, textvariable=self.voice_lang_var,
                                 values=["Auto-detect", "English", "Hindi", "Hinglish"], state="readonly")
        lang_combo.pack(fill=tk.X, pady=(2, 10))
        
        # TTS Settings
        ttk.Label(main_frame, text="Text-to-Speech:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 0))
        
        # TTS Speed
        speed_frame = ttk.Frame(main_frame)
        speed_frame.pack(fill=tk.X, pady=(2, 5))
        ttk.Label(speed_frame, text="Speed:").pack(side=tk.LEFT)
        self.tts_speed_var = tk.DoubleVar(value=1.0)
        speed_scale = ttk.Scale(speed_frame, from_=0.5, to=2.0, variable=self.tts_speed_var, orient=tk.HORIZONTAL)
        speed_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="Test Voice", command=lambda: self.test_voice_settings()).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Save", command=lambda: self.save_voice_settings(settings_window)).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.RIGHT, padx=(0, 5))
    
    def test_voice_settings(self):
        """Test current voice settings"""
        if self.talkback_enabled and self.multilingual_enabled:
            self.multilingual.speak_multilingual("Voice settings test. This is how I will sound.")
    
    def save_voice_settings(self, window):
        """Save voice settings"""
        try:
            # Update wake words
            new_wake_words = [w.strip() for w in self.wake_words_var.get().split(',') if w.strip()]
            if new_wake_words:
                self.wake_words = new_wake_words
                
            # Update voice engine
            self.use_vosk = "Vosk" in self.voice_engine_var.get()
            
            self.log_output("Voice settings saved!", speak=True)
            window.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    def voice_listen_loop(self):
        """Voice listening loop with callback"""
        try:
            # Determine language setting
            if self.multilingual_enabled:
                primary_lang = self.config.get('languages', {}).get('primary', 'hinglish')
                if primary_lang == 'hinglish' or primary_lang == 'auto':
                    lang_code = 'auto'
                elif primary_lang == 'hindi' or primary_lang == 'hi':
                    lang_code = 'hi'
                else:
                    lang_code = 'en'
            else:
                lang_code = 'en'
            
            self.logger.info(f"Starting voice recognition with language: {lang_code}")
            
            # Start voice listening loop from multilingual module
            voice_listen_loop(
                callback_function=self.handle_voice_command,
                wake_words=self.wake_words,
                use_vosk=self.use_vosk,
                language=lang_code,
                stop_event=self.voice_stop_event
            )
            
        except Exception as e:
            self.log_output(f"Voice recognition error: {e}", "ERROR")
            self.logger.error(f"Voice loop failed: {e}")
        finally:
            # Reset voice listening state
            self.voice_listening = False
            if hasattr(self, 'root'):
                self.root.after(0, self._reset_voice_button)
    
    def handle_voice_command(self, text: str):
        """Handle recognized voice command"""
        try:
            # Check if this is a wake word notification
            if text.startswith('[WAKE_WORD_DETECTED:'):
                wake_word = text.split(':')[1].rstrip(']').strip()
                if hasattr(self, 'root'):
                    self.root.after(0, lambda: self.log_output(f"🎤 Wake word detected: {wake_word}", "INFO"))
                    self.root.after(0, lambda: self.status_label.configure(text="Listening for command..."))
                return
            
            # Log recognized text
            if hasattr(self, 'root'):
                self.root.after(0, lambda: self.log_output(f"🎤 Heard: {text}", "INFO"))
                self.root.after(0, lambda: self.status_label.configure(text="Processing..."))
            
            # Process the command
            self.process_command_multilingual(text)
            
            # Reset status
            if hasattr(self, 'root'):
                self.root.after(0, lambda: self.status_label.configure(text="Listening..."))
                
        except Exception as e:
            self.logger.error(f"Voice command handling error: {e}")
            if hasattr(self, 'root'):
                self.root.after(0, lambda: self.log_output(f"Voice command error: {e}", "ERROR"))
    
    def _reset_voice_button(self):
        """Reset voice button state (GUI thread safe)"""
        if hasattr(self, 'voice_button'):
            self.voice_button.configure(text="🎤 Voice")
        if hasattr(self, 'status_label'):
            self.status_label.configure(text="Ready")
    
    def process_text_command(self, event=None):
        """Process text command from entry field with multilingual support"""
        command = self.command_entry.get().strip()
        if not command:
            return
        
        self.log_output(f"Command: {command}")
        self.command_entry.delete(0, tk.END)
        
        # Process command with language detection and translation
        self.process_command_multilingual(command)
    
    def process_command_multilingual(self, command):
        """Process command with multilingual support"""
        log_query(command)
        try:
            if self.multilingual_enabled:
                # Detect language and process accordingly
                language_context = self.multilingual.detect_language(command)
                
                self.log_output(f"Detected language: {language_context.detected_language.value} "
                              f"(confidence: {language_context.confidence:.2f})")
                
                # Handle Hinglish commands specially
                if language_context.detected_language == Language.HINGLISH:
                    hinglish_result = self.multilingual.process_hinglish_command(command)
                    if hinglish_result.get('command'):
                        self.log_output(f"Hinglish command detected: {hinglish_result['command']}")
                        # Execute the detected command
                        self.execute_hinglish_command(hinglish_result)
                        return
                
                # Translate to English if needed for processing
                if language_context.detected_language == Language.HINDI:
                    english_command = self.multilingual.translate_text(command, Language.ENGLISH)
                    self.log_output(f"Translated to English: {english_command}")
                    command = english_command
            
            # Process the command (now in English or original English)
            self.process_command(command)
            
        except Exception as e:
            self.log_output(f"Multilingual processing error: {e}", "ERROR")
            # Fallback to original processing
            self.process_command(command)
    
    def execute_hinglish_command(self, hinglish_result):
        """Execute commands detected from Hinglish input"""
        try:
            command = hinglish_result.get('command')
            parameters = hinglish_result.get('parameters', {})
            
            if command == 'make_call':
                if 'phone' in parameters:
                    result = f"Calling {parameters['phone']}..."
                elif 'contact' in parameters:
                    result = f"Calling {parameters['contact']}..."
                else:
                    result = "Phone number या contact name नहीं मिला"
                self.log_output(result)
                
            elif command == 'play_music':
                if 'song' in parameters:
                    result = f"Playing song: {parameters['song']}"
                    # You could integrate with music players here
                else:
                    result = "कौन सा song play करना है?"
                self.log_output(result)
                
            elif command == 'web_search':
                if 'query' in parameters:
                    result = search_google(parameters['query'])
                    self.log_output(f"Google search for '{parameters['query']}': {result}")
                else:
                    result = "Search query नहीं मिला"
                    self.log_output(result)
                    
            elif command == 'adjust_volume':
                direction = parameters.get('direction', 'up')
                level = parameters.get('level')
                if level:
                    result = set_volume(level)
                elif direction == 'up':
                    result = increase_volume()
                else:
                    result = decrease_volume()
                self.log_output(f"Volume adjustment: {result}")
                
            elif command == 'tell_time':
                current_time = datetime.now().strftime("%H:%M:%S")
                result = f"Current time is {current_time}"
                self.log_output(result, speak=True)
                
                # Speak in the detected language
                if self.multilingual_enabled:
                    language_context = hinglish_result.get('language_context')
                    if language_context and language_context.detected_language == Language.HINGLISH:
                        hindi_time = f"अभी समय है {current_time}"
                        # Already spoken via log_output, skip duplicate
                    
            else:
                self.log_output(f"Hinglish command '{command}' recognized but not implemented yet")
                
        except Exception as e:
            self.log_output(f"Error executing Hinglish command: {e}", "ERROR")
    
    def on_language_change(self, event=None):
        """Handle language selection change"""
        if hasattr(self, 'language_var') and self.multilingual_enabled:
            selected_lang = self.language_var.get()
            
            try:
                # Map GUI selection to Language enum
                lang_map = {
                    'english': Language.ENGLISH,
                    'hindi': Language.HINDI,
                    'hinglish': Language.HINGLISH
                }
                
                new_language = lang_map.get(selected_lang, Language.HINGLISH)
                self.multilingual.set_language_preference("default_user", new_language)
                
                self.log_output(f"Language changed to: {selected_lang}")
                
                # Update status based on language
                if selected_lang == 'hindi':
                    self.status_label.configure(text="तैयार है")
                elif selected_lang == 'hinglish':
                    self.status_label.configure(text="Ready / तैयार है")
                else:
                    self.status_label.configure(text="Ready")
                    
            except Exception as e:
                self.log_output(f"Error changing language: {e}", "ERROR")
    
    def toggle_translation_mode(self):
        """Toggle translation mode for real-time translation"""
        try:
            if not hasattr(self, 'translation_mode'):
                self.translation_mode = False
            
            self.translation_mode = not self.translation_mode
            
            if self.translation_mode:
                self.translate_button.configure(text="🔄 ON")
                self.log_output("Translation mode enabled - commands will be translated")
            else:
                self.translate_button.configure(text="🔄 Translate")
                self.log_output("Translation mode disabled")
                
        except Exception as e:
            self.log_output(f"Error toggling translation mode: {e}", "ERROR")
    
    def process_command(self, command):
        """Process natural language command"""
        log_query(command)
        command_lower = command.lower()
        
        try:
            if "open" in command_lower:
                app_name = command_lower.replace("open", "").strip()
                log_action('open_application', {'app_name': app_name})
                log_module_usage('core', 'open_application')
                result = open_application(app_name)
                self.log_output(f"Opening {app_name}: {result}")
                log_reply(f"Opening {app_name}: {result}")
            
            elif "search" in command_lower and "google" in command_lower:
                query = command_lower.replace("search", "").replace("google", "").strip()
                log_action('search_google', {'query': query})
                log_module_usage('core', 'search_google')
                result = search_google(query)
                self.log_output(f"Google search for '{query}': {result}")
                log_reply(f"Google search for '{query}': {result}")
            
            elif "note" in command_lower or "write" in command_lower:
                note_text = command.replace("note", "").replace("write", "").strip()
                log_action('write_a_note', {'note_text': note_text})
                log_module_usage('core', 'write_a_note')
                result = write_a_note(note_text)
                self.log_output(f"Note saved: {result}")
                log_reply(f"Note saved: {result}")
            
            elif "volume" in command_lower:
                # Extract volume level
                words = command_lower.split()
                for i, word in enumerate(words):
                    if word.isdigit():
                        level = int(word)
                        log_action('set_system_volume', {'level': level})
                        log_module_usage('core', 'set_system_volume')
                        result = set_system_volume(level)
                        self.log_output(f"Volume set to {level}%: {result}", speak=True)
                        log_reply(f"Volume set to {level}%: {result}")
                        break
                else:
                    self.log_output("Please specify volume level (0-100)", speak=True)
                    log_reply("Please specify volume level (0-100)")
            
            elif "status" in command_lower or "system" in command_lower:
                log_action('show_system_status', {})
                log_module_usage('system', 'get_system_status')
                self.show_system_status()
            
            else:
                self.log_output(f"Command not recognized: {command}")
                log_reply(f"Command not recognized: {command}")
                self.log_output("Available commands: open [app], search google [query], write note [text], volume [level], status")
        
        except Exception as e:
            self.log_output(f"Command processing error: {e}", "ERROR")
            log_reply(f"Command processing error: {e}")
    
    def discover_applications(self):
        """Discover installed applications"""
        try:
            self.log_output("Discovering applications...")
            from modules.app_discovery import discover_applications
            result = discover_applications()
            self.log_output(f"Application discovery completed: {result}")
        except Exception as e:
            self.log_output(f"Application discovery failed: {e}", "ERROR")
    
    def show_system_status(self):
        """Show system status"""
        try:
            self.log_output("Getting system status...")
            status = get_system_status()
            self.log_output(f"System Status: {status}")
        except Exception as e:
            self.log_output(f"System status error: {e}", "ERROR")
    
    def clear_output(self):
        """Clear output text area"""
        if hasattr(self, 'output_text'):
            self.output_text.delete(1.0, tk.END)
    
    def run(self):
        """Run the assistant"""
        self.running = True
        self.log_output("YourDaddy Assistant started")
        
        if self.gui_ready:
            try:
                self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
                self.root.mainloop()
            except KeyboardInterrupt:
                self.log_output("Interrupted by user")
            except Exception as e:
                self.log_output(f"GUI error: {e}", "ERROR")
        else:
            # Fallback to console mode
            self.console_mode()
    
    def console_mode(self):
        """Run in console mode"""
        self.log_output("Running in console mode")
        print("\nYourDaddy Assistant - Console Mode")
        print("Type 'quit' or 'exit' to stop\n")
        
        while self.running:
            try:
                command = input("Command: ").strip()
                if command.lower() in ['quit', 'exit']:
                    break
                elif command:
                    self.process_command(command)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def on_closing(self):
        """Handle application closing"""
        self.running = False
        self.voice_listening = False
        
        # Stop voice recognition thread
        if hasattr(self, 'voice_stop_event'):
            self.voice_stop_event.set()
        
        # Wait for voice thread to finish (with timeout)
        if hasattr(self, 'voice_thread') and self.voice_thread and self.voice_thread.is_alive():
            self.log_output("Stopping voice recognition...")
            self.voice_thread.join(timeout=2.0)
        
        self.log_output("Shutting down...")
        if hasattr(self, 'root'):
            self.root.destroy()

def main():
    """Main entry point"""
    print("=" * 60)
    print("🤖 YourDaddy Assistant - Starting...")
    print("=" * 60)
    
    try:
        assistant = YourDaddyAssistant()
        assistant.run()
    except Exception as e:
        print(f"❌ Failed to start assistant: {e}")
        sys.exit(1)
    
    print("\n👋 YourDaddy Assistant - Goodbye!")

if __name__ == "__main__":
    main()
