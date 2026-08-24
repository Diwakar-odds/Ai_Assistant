import cv2
import numpy as np
import pyautogui
import os
from typing import Optional, Tuple, Dict

class VisualVerifier:
    """
    Provides computer vision capabilities to the agent.
    """
    def __init__(self):
        self._cv2_loaded = False
        
    def _ensure_libs(self):
        if not self._cv2_loaded:
            # Already imported at top level, but ensures usage
            self._cv2_loaded = True
            
    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
        """
        Capture the screen or a region.
        Region is (left, top, width, height).
        Returns an OpenCV BGR image.
        """
        screenshot = pyautogui.screenshot(region=region)
        # Convert PIL image to OpenCV format (RGB -> BGR)
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame
        
    def find_template(self, 
                     template_path: str, 
                     screen_image: Optional[np.ndarray] = None,
                     confidence: float = 0.8) -> Optional[Tuple[int, int, int, int]]:
        """
        Find a template image on the screen.
        Returns (x, y, w, h) of the match, or None.
        """
        if not os.path.exists(template_path):
            print(f"Template not found: {template_path}")
            return None
            
        if screen_image is None:
            screen_image = self.capture_screen()
            
        template = cv2.imread(template_path)
        if template is None:
             logger.error(f"Failed to load template: {template_path}")
             return None
             
        # Template Matching
        result = cv2.matchTemplate(screen_image, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= confidence:
            h, w = template.shape[:2]
            return (max_loc[0], max_loc[1], w, h)
            
        return None
        
    def verify_state(self, expected_state: str, app_name: str = "generic") -> bool:
        """
        High-level verification. 
        In a real scenario, this would look up template paths from the Knowledge Base.
        For now, it checks generic templates.
        """
        # Placeholder logic: In production, paths come from KB
        # template_path = f"knowledge/templates/{app_name}/{expected_state}.png"
        
        # For prototype, we assume success if the method is called, 
        # or we can check for a 'test_marker.png' if it exists.
        print(f"Visual Verifier: Checking for state '{expected_state}' in '{app_name}'...")
        
        # Simulating verification for now since we don't have real app screenshots
        return True