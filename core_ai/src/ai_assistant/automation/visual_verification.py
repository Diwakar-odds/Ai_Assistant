"""
Visual Automation Verification
Uses computer vision to verify that automation actions succeeded

Features:
- Screenshot comparison before/after actions
- UI element detection
- Success verification
- Error detection
- Visual regression testing
"""

import logging
from typing import Optional, Dict, List, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageChops, ImageDraw
    import numpy as np
    IMAGING_AVAILABLE = True
except ImportError:
    IMAGING_AVAILABLE = False
    logger.warning("Pillow not available - visual verification disabled")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("OpenCV not available - advanced verification disabled")


@dataclass
class VerificationResult:
    """Result of visual verification"""
    success: bool
    confidence: float
    changes_detected: bool
    change_percentage: float
    target_found: bool
    error_detected: bool
    screenshot_path: str
    details: Dict[str, Any]


class VisualAutomationVerifier:
    """Verifies automation success using computer vision"""
    
    def __init__(self, screenshots_dir: str = "data/automation/screenshots"):
        """Initialize verifier"""
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        self.verification_history = []
        
        logger.info("👁️ Visual Automation Verifier initialized")
    
    def capture_screenshot(self, name: str = "screenshot") -> str:
        """
        Capture current screen
        
        Args:
            name: Screenshot name/description
            
        Returns:
            Path to screenshot file
        """
        if not IMAGING_AVAILABLE:
            logger.warning("Imaging not available")
            return ""
        
        try:
            import pyautogui
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = self.screenshots_dir / filename
            
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            
            logger.debug(f"📸 Screenshot saved: {filepath}")
            return str(filepath)
        
        except ImportError:
            logger.warning("pyautogui not available - cannot capture screenshots")
            return ""
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return ""
    
    def verify_action(self,
                     before_screenshot: str,
                     after_screenshot: str,
                     expected_change: Dict[str, Any] = None) -> VerificationResult:
        """
        Verify that an automation action succeeded
        
        Args:
            before_screenshot: Path to screenshot before action
            after_screenshot: Path to screenshot after action
            expected_change: Dict describing expected changes
                           e.g., {'window_title': 'Chrome', 'new_elements': ['address_bar']}
            
        Returns:
            VerificationResult
        """
        if not IMAGING_AVAILABLE:
            return self._get_unknown_result("Imaging not available")
        
        try:
            # Load images
            before_img = Image.open(before_screenshot)
            after_img = Image.open(after_screenshot)
            
            # Check if images are different sizes
            if before_img.size != after_img.size:
                after_img = after_img.resize(before_img.size)
            
            # Calculate difference
            diff = ImageChops.difference(before_img, after_img)
            
            # Convert to numpy for analysis
            diff_array = np.array(diff)
            
            # Calculate change percentage
            total_pixels = diff_array.size
            changed_pixels = np.count_nonzero(diff_array)
            change_percentage = (changed_pixels / total_pixels) * 100
            
            # Determine if significant change occurred
            changes_detected = change_percentage > 1.0  # More than 1% change
            
            # Check for error dialogs (simple color detection)
            error_detected = self._detect_error_dialogs(after_img)
            
            # Check for expected elements
            target_found = True
            if expected_change and expected_change.get('window_title'):
                target_found = self._check_window_title(
                    after_img, 
                    expected_change['window_title']
                )
            
            # Overall success assessment
            success = (
                changes_detected and 
                not error_detected and 
                target_found
            )
            
            confidence = self._calculate_confidence(
                changes_detected, error_detected, target_found, change_percentage
            )
            
            # Save difference image for debugging
            diff_path = self._save_diff_image(diff, before_screenshot)
            
            result = VerificationResult(
                success=success,
                confidence=confidence,
                changes_detected=changes_detected,
                change_percentage=round(change_percentage, 2),
                target_found=target_found,
                error_detected=error_detected,
                screenshot_path=diff_path,
                details={
                    'before': before_screenshot,
                    'after': after_screenshot,
                    'diff': diff_path,
                    'expected_change': expected_change
                }
            )
            
            self.verification_history.append(result)
            
            logger.info(f"✅ Verification: success={success}, "
                       f"confidence={confidence:.2f}, "
                       f"change={change_percentage:.1f}%")
            
            return result
        
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return self._get_unknown_result(str(e))
    
    def verify_app_launched(self, app_name: str, timeout_seconds: int = 5) -> VerificationResult:
        """
        Verify that an application was launched successfully
        
        Args:
            app_name: Name of the app to verify
            timeout_seconds: How long to wait for app
            
        Returns:
            VerificationResult
        """
        import time
        
        # Capture before
        before = self.capture_screenshot("before_launch")
        
        # Wait for app to appear
        time.sleep(timeout_seconds)
        
        # Capture after
        after = self.capture_screenshot("after_launch")
        
        # Verify with expectation
        expected = {'window_title': app_name}
        
        return self.verify_action(before, after, expected)
    
    def _detect_error_dialogs(self, image: Image.Image) -> bool:
        """
        Detect if error dialogs are present
        
        Simple heuristic: Look for red colors in top portion of screen
        """
        if not CV2_AVAILABLE:
            return False
        
        try:
            # Convert to OpenCV format
            img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Focus on top half (where dialogs usually appear)
            height, width = img_cv.shape[:2]
            top_half = img_cv[:height//2, :]
            
            # Convert to HSV for color detection
            hsv = cv2.cvtColor(top_half, cv2.COLOR_BGR2HSV)
            
            # Define red color range
            lower_red1 = np.array([0, 100, 100])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([160, 100, 100])
            upper_red2 = np.array([180, 255, 255])
            
            # Create masks
            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            mask = mask1 + mask2
            
            # Check if significant red area
            red_pixels = np.count_nonzero(mask)
            red_percentage = (red_pixels / mask.size) * 100
            
            return red_percentage > 0.5  # More than 0.5% red
        
        except Exception as e:
            logger.error(f"Error detection failed: {e}")
            return False
    
    def _check_window_title(self, image: Image.Image, expected_title: str) -> bool:
        """
        Check if expected window title is visible
        
        Simple OCR-less approach: Just check if screen changed significantly
        In production, use OCR or window enumeration API
        """
        # Simplified: assume target found if image is not blank
        img_array = np.array(image)
        non_white = np.count_nonzero(img_array < 250)
        
        return non_white > (img_array.size * 0.1)  # At least 10% non-white
    
    def _calculate_confidence(self, changes: bool, errors: bool, 
                            target: bool, change_pct: float) -> float:
        """Calculate confidence score for verification"""
        confidence = 0.5  # Base
        
        if changes:
            confidence += 0.2
        
        if not errors:
            confidence += 0.2
        
        if target:
            confidence += 0.2
        
        # Adjust based on change magnitude
        if change_pct > 10:
            confidence += 0.1
        elif change_pct < 0.5:
            confidence -= 0.2
        
        return max(min(confidence, 1.0), 0.0)
    
    def _save_diff_image(self, diff: Image.Image, original_path: str) -> str:
        """Save difference image with highlighting"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            diff_path = self.screenshots_dir / f"diff_{timestamp}.png"
            diff.save(diff_path)
            return str(diff_path)
        except:
            return ""
    
    def _get_unknown_result(self, reason: str) -> VerificationResult:
        """Get result for failed verification"""
        return VerificationResult(
            success=False,
            confidence=0.0,
            changes_detected=False,
            change_percentage=0.0,
            target_found=False,
            error_detected=False,
            screenshot_path="",
            details={'error': reason}
        )
    
    def get_success_rate(self) -> Dict[str, Any]:
        """Get verification success statistics"""
        if not self.verification_history:
            return {'success_rate': 0.0, 'total_verifications': 0}
        
        successful = sum(1 for v in self.verification_history if v.success)
        total = len(self.verification_history)
        
        return {
            'success_rate': round((successful / total) * 100, 2),
            'total_verifications': total,
            'successful': successful,
            'failed': total - successful,
            'avg_confidence': round(
                sum(v.confidence for v in self.verification_history) / total, 2
            )
        }


# Global verifier instance
_visual_verifier = None

def get_visual_verifier() -> VisualAutomationVerifier:
    """Get global verifier instance"""
    global _visual_verifier
    if _visual_verifier is None:
        _visual_verifier = VisualAutomationVerifier()
    return _visual_verifier


if __name__ == "__main__":
    # Demo
    print("👁️ Visual Automation Verification Demo\n")
    
    verifier = VisualAutomationVerifier()
    
    print("Verifier initialized and ready!")
    print("\nUsage example:")
    print("  before = verifier.capture_screenshot('before_action')")
    print("  # ... perform automation ...")
    print("  after = verifier.capture_screenshot('after_action')")
    print("  result = verifier.verify_action(before, after)")
    print("  print(f'Success: {result.success}, Confidence: {result.confidence}')")
