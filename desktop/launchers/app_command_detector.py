# -*- coding: utf-8 -*-
"""
App Command Detector
Detects and parses app-related commands in multiple languages.
"""

import re
from typing import Optional, Dict, Any
from enum import Enum


class AppAction(Enum):
    """Types of app actions"""
    OPEN = "open"
    CLOSE = "close"
    LAUNCH = "launch"
    START = "start"


class AppCommand:
    """Structured app command object"""
    
    def __init__(self, action: AppAction, app_name: str, original_command: str, language: str = "english"):
        self.action = action
        self.app_name = app_name
        self.original_command = original_command
        self.language = language
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'action': self.action.value,
            'app_name': self.app_name,
            'original_command': self.original_command,
            'language': self.language
        }
    
    def __repr__(self):
        return f"AppCommand(action={self.action.value}, app_name={self.app_name}, language={self.language})"


class AppCommandDetector:
    """
    Detects app-related commands in multiple languages.
    
    Supports:
    - English: "open X", "launch X", "start X", "close X"
    - Hindi: "X खोलो", "X बंद करो", "X चालू करो"
    - Hinglish: "X open karo", "X close karo"
    """
    
    def __init__(self):
        # English patterns
        self.english_patterns = [
            # "open chrome", "launch notepad", "start calculator"
            (r'^(?:please\s+)?(?:open|launch|start)\s+(.+?)(?:\s+please)?$', AppAction.OPEN),
            (r'^(?:please\s+)?(?:close|quit|exit)\s+(.+?)(?:\s+please)?$', AppAction.CLOSE),
            (r'^(?:can you|could you|will you)\s+(?:open|launch|start)\s+(.+?)(?:\s+please)?(?:\?)?$', AppAction.OPEN),
            # "i want to open X", "i need to use X"
            (r'^(?:i\s+(?:want|need)\s+to\s+(?:open|use|start))\s+(.+?)$', AppAction.OPEN),
        ]
        
        # Hindi patterns
        self.hindi_patterns = [
            # "chrome खोलो", "notepad खोल दो"
            (r'^(.+?)\s+(?:खोलो|खोल\s+दो|चालू\s+करो|चालू\s+कर\s+दो)$', AppAction.OPEN),
            (r'^(.+?)\s+(?:बंद\s+करो|बंद\s+कर\s+दो|close\s+करो)$', AppAction.CLOSE),
            # "खोलो chrome", "चालू करो calculator"
            (r'^(?:खोलो|खोल\s+दो|चालू\s+करो)\s+(.+?)$', AppAction.OPEN),
            (r'^(?:बंद\s+करो|बंद\s+कर\s+दो)\s+(.+?)$', AppAction.CLOSE),
        ]
        
        # Hinglish patterns
        self.hinglish_patterns = [
            # "chrome open karo", "notepad band karo"
            (r'^(.+?)\s+(?:open|launch|start)\s+(?:karo|kar\s+do|karna)$', AppAction.OPEN),
            (r'^(.+?)\s+(?:close|band|quit)\s+(?:karo|kar\s+do|karna)$', AppAction.CLOSE),
            # "open karo chrome", "band karo notepad"
            (r'^(?:open|launch|start)\s+(?:karo|kar\s+do)\s+(.+?)$', AppAction.OPEN),
            (r'^(?:close|band|quit)\s+(?:karo|kar\s+do)\s+(.+?)$', AppAction.CLOSE),
        ]
    
    def detect(self, command_text: str) -> Optional[AppCommand]:
        """
        Detect if command is app-related and extract details.
        
        Args:
            command_text: User's command text
            
        Returns:
            AppCommand object if detected, None otherwise
        """
        if not command_text or not isinstance(command_text, str):
            return None
        
        # Normalize command
        command = command_text.strip().lower()
        
        if not command:
            return None
        
        # Try English patterns first
        result = self._try_patterns(command, self.english_patterns, "english")
        if result:
            return result
        
        # Try Hinglish patterns
        result = self._try_patterns(command, self.hinglish_patterns, "hinglish")
        if result:
            return result
        
        # Try Hindi patterns
        result = self._try_patterns(command, self.hindi_patterns, "hindi")
        if result:
            return result
        
        return None
    
    def _try_patterns(self, command: str, patterns: list, language: str) -> Optional[AppCommand]:
        """Try matching command against a list of patterns"""
        for pattern, action in patterns:
            match = re.search(pattern, command, re.IGNORECASE)
            if match:
                app_name = match.group(1).strip()
                
                # Clean up app name
                app_name = self._clean_app_name(app_name)
                
                if app_name:
                    return AppCommand(
                        action=action,
                        app_name=app_name,
                        original_command=command,
                        language=language
                    )
        
        return None
    
    def _clean_app_name(self, app_name: str) -> str:
        """Clean and normalize app name"""
        # Remove common filler words
        filler_words = ['the', 'application', 'app', 'program', 'software', 'for', 'me']
        
        words = app_name.split()
        cleaned_words = [w for w in words if w.lower() not in filler_words]
        
        if cleaned_words:
            return ' '.join(cleaned_words)
        
        # If all words were filler, return original
        return app_name
    
    def is_app_command(self, command_text: str) -> bool:
        """Quick check if command is app-related"""
        return self.detect(command_text) is not None


# Singleton instance
_detector_instance = None


def get_app_command_detector() -> AppCommandDetector:
    """Get singleton instance of AppCommandDetector"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = AppCommandDetector()
    return _detector_instance


# Convenience function
def detect_app_command(command_text: str) -> Optional[AppCommand]:
    """
    Detect app command from text.
    
    Examples:
        >>> detect_app_command("open chrome")
        AppCommand(action=open, app_name=chrome, language=english)
        
        >>> detect_app_command("calculator खोलो")
        AppCommand(action=open, app_name=calculator, language=hindi)
        
        >>> detect_app_command("notepad band karo")
        AppCommand(action=close, app_name=notepad, language=hinglish)
    """
    detector = get_app_command_detector()
    return detector.detect(command_text)


if __name__ == "__main__":
    # Test the detector
    test_commands = [
        "open chrome",
        "launch calculator",
        "please start notepad",
        "can you open brave",
        "calculator खोलो",
        "chrome चालू करो",
        "notepad open karo",
        "discord band karo",
        "i want to open spotify",
        "close discord",
        "random text that is not an app command"
    ]
    
    detector = get_app_command_detector()
    
    print("Testing App Command Detector:\n")
    for cmd in test_commands:
        result = detector.detect(cmd)
        if result:
            print(f"[DETECTED] '{cmd}'")
            print(f"  -> {result}")
        else:
            print(f"[NOT APP CMD] '{cmd}'")
        print()
