import io
import base64
import time
import logging
from typing import Optional
from collections import deque

logger = logging.getLogger(__name__)

try:
    import mediapipe as mp
    import numpy as np
    from PIL import Image
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    logger.warning("Mediapipe library not found. Gesture recognition disabled.")

class GestureRecognizer:
    def __init__(self):
        self.is_initialized = False
        if MEDIAPIPE_AVAILABLE:
            self.mp_hands = mp.solutions.hands
            self.mp_face = mp.solutions.face_detection
            
            self.hands = self.mp_hands.Hands(
                static_image_mode=False, # Set to False for tracking
                max_num_hands=1,
                min_detection_confidence=0.5
            )
            
            self.face_detection = self.mp_face.FaceDetection(
                min_detection_confidence=0.5
            )
            
            # Keep track of wrist position over time: (timestamp, x, y)
            self.wrist_history = deque(maxlen=5) 
            self.is_initialized = True

    def detect_gesture(self, b64_string: str) -> Optional[str]:
        """
        Takes a base64 image and returns a detected gesture string:
        'STOP', 'THUMBS_UP', 'THUMBS_DOWN', 'PEACE', 'MUTE_MIC', 'SWIPE_LEFT', 'SWIPE_RIGHT' or None.
        """
        if not self.is_initialized:
            return None
            
        try:
            if b64_string.startswith('data:image'):
                b64_string = b64_string.split(',')[1]
                
            image_data = base64.b64decode(b64_string)
            image = Image.open(io.BytesIO(image_data)).convert('RGB')
            frame_rgb = np.array(image)
            
            # 1. Process Hands
            results = self.hands.process(frame_rgb)
            
            if not results.multi_hand_landmarks:
                # If no hands, clear history to avoid stale swipe detection
                self.wrist_history.clear()
                return None
                
            hand_landmarks = results.multi_hand_landmarks[0]
            landmarks = hand_landmarks.landmark
            
            # --- SWIPE DETECTION ---
            current_time = time.time()
            wrist_x = landmarks[0].x
            
            # Clean old history (> 1 second)
            while self.wrist_history and current_time - self.wrist_history[0][0] > 1.0:
                self.wrist_history.popleft()
                
            self.wrist_history.append((current_time, wrist_x, landmarks[0].y))
            
            if len(self.wrist_history) >= 2:
                oldest_time, oldest_x, _ = self.wrist_history[0]
                newest_time, newest_x, _ = self.wrist_history[-1]
                
                # If we moved significantly within a short time (e.g. 0.2 across normalized width)
                # Note: Mirror image usually means moving hand right decreases X. 
                # Let's use simple logic: X goes from 0.8 to 0.2 (Diff = -0.6)
                x_diff = newest_x - oldest_x
                if abs(x_diff) > 0.25:
                    self.wrist_history.clear() # Reset to prevent double triggers
                    if x_diff < 0:
                        return 'SWIPE_LEFT'
                    else:
                        return 'SWIPE_RIGHT'

            # --- STATIC GESTURES ---
            def is_finger_extended(tip_idx, pip_idx):
                return landmarks[tip_idx].y < landmarks[pip_idx].y
                
            index_extended = is_finger_extended(8, 6)
            middle_extended = is_finger_extended(12, 10)
            ring_extended = is_finger_extended(16, 14)
            pinky_extended = is_finger_extended(20, 18)
            
            extended_fingers_count = sum([index_extended, middle_extended, ring_extended, pinky_extended])
            
            # Detect STOP
            if extended_fingers_count == 4:
                return 'STOP'
                
            # Detect PEACE
            if index_extended and middle_extended and not ring_extended and not pinky_extended:
                return 'PEACE'
                
            # Detect MUTE_MIC (Finger over lips)
            if index_extended and not middle_extended and not ring_extended and not pinky_extended:
                # Need to check face
                face_results = self.face_detection.process(frame_rgb)
                if face_results.detections:
                    # Get first face
                    detection = face_results.detections[0]
                    bbox = detection.location_data.relative_bounding_box
                    
                    # Approximate mouth region: Bottom 1/3rd of the face bounding box
                    mouth_y_min = bbox.ymin + (bbox.height * 0.6)
                    mouth_y_max = bbox.ymin + bbox.height
                    mouth_x_min = bbox.xmin + (bbox.width * 0.2)
                    mouth_x_max = bbox.xmin + (bbox.width * 0.8)
                    
                    index_tip = landmarks[8]
                    
                    if (mouth_x_min <= index_tip.x <= mouth_x_max) and \
                       (mouth_y_min <= index_tip.y <= mouth_y_max):
                        return 'MUTE_MIC'
                
            # Detect THUMBS UP / DOWN
            if extended_fingers_count <= 1:
                thumb_tip = landmarks[4]
                thumb_mcp = landmarks[2]
                index_mcp = landmarks[5]
                
                if thumb_tip.y < index_mcp.y - 0.05 and thumb_tip.y < thumb_mcp.y:
                    return 'THUMBS_UP'
                if thumb_tip.y > index_mcp.y + 0.05 and thumb_tip.y > thumb_mcp.y:
                    return 'THUMBS_DOWN'
                    
            return None
            
        except Exception as e:
            logger.error(f"Error in gesture detection: {e}")
            return None

gesture_recognition_sys = GestureRecognizer()
