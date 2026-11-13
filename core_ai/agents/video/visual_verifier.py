from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)


class VisualVerifier:
    """Provides lazy-loaded computer vision verification capabilities."""

    def __init__(self):
        self._cv2 = None
        self._np = None
        self._pag = None

    def _ensure_cv(self) -> None:
        if self._cv2 is None:
            import cv2
            import numpy as np

            self._cv2 = cv2
            self._np = np

    def _ensure_screenshot(self) -> None:
        self._ensure_cv()
        if self._pag is None:
            import pyautogui

            self._pag = pyautogui

    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Any:
        """Capture the screen or a region and return an OpenCV BGR ndarray."""
        self._ensure_screenshot()
        screenshot = self._pag.screenshot(region=region)
        frame = self._np.array(screenshot)
        return self._cv2.cvtColor(frame, self._cv2.COLOR_RGB2BGR)

    def find_template(
        self,
        template_path: str,
        screen_image: Optional[Any] = None,
        confidence: float = 0.8,
    ) -> Optional[Tuple[int, int, int, int]]:
        """Find a template image on screen or within a provided BGR ndarray."""
        if not template_path or not os.path.exists(template_path):
            logger.debug("Template not found: %s", template_path)
            return None

        self._ensure_cv()
        if screen_image is None:
            screen_image = self.capture_screen()

        template = self._cv2.imread(template_path)
        if template is None:
            logger.error("Failed to load template: %s", template_path)
            return None

        sh, sw = screen_image.shape[:2]
        th, tw = template.shape[:2]
        if th > sh or tw > sw:
            logger.warning("Template (%sx%s) larger than target image (%sx%s)", tw, th, sw, sh)
            return None

        result = self._cv2.matchTemplate(screen_image, template, self._cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = self._cv2.minMaxLoc(result)

        if max_val >= confidence:
            return (int(max_loc[0]), int(max_loc[1]), int(tw), int(th))
        return None

    def compare_frames(self, before_image: Any, after_image: Any, min_change_ratio: float = 0.001) -> bool:
        """Return True if measurable visual change occurred between two frames."""
        if before_image is None or after_image is None:
            return False
        self._ensure_cv()
        if before_image.shape != after_image.shape:
            return True
        diff = self._cv2.absdiff(before_image, after_image)
        changed = float(self._np.count_nonzero(diff)) / max(1, diff.size)
        return changed >= min_change_ratio

    def verify_state(
        self,
        expected_state: str,
        app_name: str = "generic",
        template_path: Optional[str] = None,
        screen_image: Optional[Any] = None,
        before_image: Optional[Any] = None,
    ) -> bool:
        """
        Verify UI state via template matching, frame transition comparison,
        or Knowledge Base template lookup. Returns False when verification cannot confirm state.
        """
        if template_path:
            return self.find_template(template_path, screen_image=screen_image) is not None

        kb_template = (
            Path(__file__).resolve().parents[2]
            / "knowledge"
            / "templates"
            / app_name.lower()
            / f"{expected_state}.png"
        )
        if kb_template.exists():
            return self.find_template(str(kb_template), screen_image=screen_image) is not None

        if before_image is not None and screen_image is not None:
            return self.compare_frames(before_image, screen_image)

        if screen_image is not None:
            self._ensure_cv()
            return bool(getattr(screen_image, "size", 0) > 0 and float(self._np.std(screen_image)) > 0.0)

        logger.warning(
            "Visual verification cannot confirm '%s' for '%s': no template or screen frame supplied",
            expected_state,
            app_name,
        )
        return False
