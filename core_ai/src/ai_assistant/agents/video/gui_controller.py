from typing import Dict, Any, Optional, List
from threading import Thread
import time
import abc

class AppControlInterface(abc.ABC):
    """Abstract interface for controlling external applications"""
    
    @abc.abstractmethod
    def focus_window(self, app_name: str) -> bool:
        pass
        
    @abc.abstractmethod
    def send_hotkey(self, keys: List[str]):
        pass
        
    @abc.abstractmethod
    def type_text(self, text: str):
        pass
        
    @abc.abstractmethod
    def click_at(self, x: int, y: int):
        pass

class BaseGUIController(AppControlInterface):
    """Generic GUI Controller using PyAutoGUI"""
    
    def __init__(self):
        self._pag = None
        self._pgw = None
        
    def _load_libs(self):
        if not self._pag:
            import pyautogui
            import pygetwindow
            self._pag = pyautogui
            self._pgw = pygetwindow
            # Safety features - Disable for bot operation to prevent random stops if mouse hits corner
            self._pag.FAILSAFE = False
            
    def focus_window(self, app_name: str) -> bool:
        self._load_libs()
        try:
            windows = self._pgw.getWindowsWithTitle(app_name)
            if windows:
                win = windows[0]
                if not win.isActive:
                    win.activate()
                return True
            return False
        except Exception as e:
            logger.error(f"Error focusing window: {e}")
            return False
            
    def send_hotkey(self, keys: List[str]):
        self._load_libs()
        self._pag.hotkey(*keys)
        
    def type_text(self, text: str):
        self._load_libs()
        self._pag.write(text)
        
    def click_at(self, x: int, y: int):
        self._load_libs()
        self._pag.click(x, y)

class PremiereProController(BaseGUIController):
    """
    Profile for Adobe Premiere Pro.
    Maps high-level actions to keyboard shortcuts.
    """
    
    KEYMAP = {
        "cut": ["ctrl", "k"],  # Add Edit
        "undo": ["ctrl", "z"],
        "redo": ["ctrl", "shift", "z"],
        "save": ["ctrl", "s"],
        "ripple_delete": ["shift", "delete"],
        "mark_in": ["i"],
        "mark_out": ["o"],
        "zoom_in": ["="],
        "zoom_out": ["-"]
    }
    
    def execute_action(self, action_name: str):
        """Execute a named action based on keymap"""
        keys = self.KEYMAP.get(action_name.lower())
        if keys:
            print(f"[Premiere] Executing {action_name}: {keys}")
            self.send_hotkey(keys)
        else:
            print(f"[Premiere] Unknown action: {action_name}")
            
    def perform_sequence(self, sequence_name: str):
        """Perform a common sequence of actions"""
        if sequence_name == "cut_and_delete":
             self.execute_action("cut")
             time.sleep(0.1)
             self.execute_action("ripple_delete")

import json
import os

class KnowledgeBaseController(BaseGUIController):
    """
    Controller that loads keymaps dynamically from the Knowledge Base.
    """
    def __init__(self, app_key: str):
        super().__init__()
        self.app_key = app_key
        self.kb_data = self._load_kb()
        self.keymap = self.kb_data.get("shortcuts", {})
        self.name = self.kb_data.get("name", app_key)
        
    def _load_kb(self) -> Dict:
        # Path relative to this file: agents/video/gui_controller.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up: video -> agents -> ai_assistant. Then down -> knowledge
        kb_path = os.path.abspath(os.path.join(current_dir, "..", "..", "knowledge", "video_tools_kb.json"))
        
        if not os.path.exists(kb_path):
            logger.warning(f"Warning: Knowledge Base not found at {kb_path}")
            return {}
            
        try:
            with open(kb_path, 'r') as f:
                data = json.load(f)
                return data.get("tools", {}).get(self.app_key, {})
        except Exception as e:
            logger.error(f"Error loading KB: {e}")
            return {}

    def execute_action(self, action_name: str):
        # Normalize action name
        keys = self.keymap.get(action_name.lower())
        
        # Mapping common aliases
        if not keys:
            if action_name == "cut": keys = self.keymap.get("split")
            if action_name == "split": keys = self.keymap.get("cut")
            
        if keys:
            print(f"[{self.name}] Executing {action_name}: {keys}")
            self.send_hotkey(keys)
        else:
            print(f"[{self.name}] Unknown action: {action_name}")

class AppControllerFactory:
    @staticmethod
    def get_controller(app_name: str) -> BaseGUIController:
        app_lower = app_name.lower()
        
        if "remiere" in app_lower:
            return KnowledgeBaseController("premiere_pro")
        elif "davinci" in app_lower or "resolve" in app_lower:
            return KnowledgeBaseController("davinci_resolve")
        elif "capcut" in app_lower:
            return KnowledgeBaseController("capcut_desktop")
        elif "filmora" in app_lower:
            return KnowledgeBaseController("filmora")
        elif "vn" in app_lower:
             return KnowledgeBaseController("vn_editor")
             
        # Fallback or specific manual classes
        return BaseGUIController()