import os
import io
import base64
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)

try:
    import face_recognition
    import numpy as np
    from PIL import Image
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    logger.warning("face_recognition library not found. Facial recognition features will be disabled.")

class FacialRecognitionSystem:
    def __init__(self, faces_dir: str = "user_data/faces"):
        self.faces_dir = Path(faces_dir)
        self.known_face_encodings = []
        self.known_face_names = []
        self.is_initialized = False
        
        if FACE_RECOGNITION_AVAILABLE:
            self.load_known_faces()
            self.is_initialized = True
            
    def load_known_faces(self):
        """Loads all images from the faces directory and generates encodings."""
        if not self.faces_dir.exists():
            self.faces_dir.mkdir(parents=True, exist_ok=True)
            return

        self.known_face_encodings = []
        self.known_face_names = []

        logger.info(f"Loading known faces from {self.faces_dir}...")
        
        # Iterate through person directories
        for person_dir in self.faces_dir.iterdir():
            if person_dir.is_dir():
                person_name = person_dir.name
                # Iterate through images for this person
                for image_path in person_dir.glob("*.*"):
                    if image_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                        try:
                            # Load image and get encoding
                            image = face_recognition.load_image_file(str(image_path))
                            # Get the face encodings (assume first face found is the person)
                            encodings = face_recognition.face_encodings(image)
                            
                            if encodings:
                                self.known_face_encodings.append(encodings[0])
                                self.known_face_names.append(person_name)
                                logger.debug(f"Loaded face encoding for {person_name} from {image_path.name}")
                            else:
                                logger.warning(f"No face found in {image_path}")
                        except Exception as e:
                            logger.error(f"Error loading face from {image_path}: {e}")
                            
        logger.info(f"Loaded {len(self.known_face_names)} face encodings.")

    def reload_faces(self):
        """Public method to reload faces if the directory changes."""
        if FACE_RECOGNITION_AVAILABLE:
            self.load_known_faces()

    def identify_person(self, b64_string: str) -> Optional[str]:
        """
        Takes a base64 image string and returns the name of the recognized person,
        or 'Unknown' if a face is found but not recognized,
        or None if no face is found or feature is unavailable.
        """
        if not self.is_initialized or not self.known_face_encodings:
            return None
            
        try:
            # Decode base64
            if b64_string.startswith('data:image'):
                b64_string = b64_string.split(',')[1]
                
            image_data = base64.b64decode(b64_string)
            image = Image.open(io.BytesIO(image_data)).convert('RGB')
            
            # Convert PIL image to numpy array format for face_recognition
            frame = np.array(image)
            
            # Find all face locations and encodings in the current frame
            face_locations = face_recognition.face_locations(frame)
            face_encodings = face_recognition.face_encodings(frame, face_locations)

            # If no faces found
            if not face_encodings:
                return None
                
            # For this feature, we usually only care about the most prominent face (the first one)
            # but we'll check the first detected face for simplicity in this implementation
            face_encoding = face_encodings[0]

            # See if the face is a match for the known face(s)
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.5)
            name = "Unknown"

            # Use the known face with the smallest distance to the new face
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = self.known_face_names[best_match_index]

            return name

        except Exception as e:
            logger.error(f"Error during face identification: {e}")
            return None

# Singleton instance for easy import
facial_recognition_sys = FacialRecognitionSystem()
