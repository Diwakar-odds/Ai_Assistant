import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

from modules.multimodal import MultiModalAI
from PIL import Image
import cv2

video_path = r"c:\Users\hp\Videos\Captures\Cutting-Edge AI Assistant UI and 6 more pages - Personal - Microsoft Edge 2025-11-18 06-09-43.mp4"

print("="*70)
print("SIMPLE VIDEO TEST")
print("="*70)
print(f"\nVideo path: {video_path}")
print(f"File exists: {os.path.exists(video_path)}")

# List files in the directory to find the exact name
captures_dir = r"c:\Users\hp\Videos\Captures"
if os.path.exists(captures_dir):
    print(f"\nFiles in {captures_dir}:")
    for f in os.listdir(captures_dir):
        if '2025-11-18' in f and '.mp4' in f:
            print(f"  - {f}")
            video_path = os.path.join(captures_dir, f)

# Extract one frame
print("\n1. Extracting frame...")
cap = cv2.VideoCapture(video_path)
ret, frame = cap.read()
if not ret:
    print("Failed to read frame")
    exit(1)
    
frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
pil_image = Image.fromarray(frame_rgb)
cap.release()
print(f"   Frame size: {pil_image.size}")

# Initialize AI
print("\n2. Initializing AI...")
ai = MultiModalAI()
print(f"   Model: {ai.vision_model._model_name}")

# Test analysis
print("\n3. Analyzing frame...")
result = ai.analyze_image(pil_image, "Describe this screenshot")

print(f"\n4. Result:")
print(f"   Confidence: {result.get('confidence')}")

if result.get('confidence') == 'error':
    print(f"   ERROR: {result.get('analysis')}")
else:
    analysis = result.get('analysis', '')
    print(f"   SUCCESS!")
    print(f"   Analysis: {analysis[:300]}...")
    
print("\n"+"="*70)
