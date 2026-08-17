import cv2
import numpy as np
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(r"c:\users\hp\appdata\roaming\python\python39\site-packages")

from ai_assistant.agents.video.visual_verifier import VisualVerifier

def create_dummy_screen_and_template():
    """Create a synthetic screen image and a template to find within it"""
    # 1. Create a "Screen" (black background)
    screen = np.zeros((600, 800, 3), dtype=np.uint8)
    
    # 2. Draw a "Button" (green rectangle) at specific location
    button_loc = (200, 150)
    button_size = (100, 50)
    cv2.rectangle(screen, button_loc, (button_loc[0]+button_size[0], button_loc[1]+button_size[1]), (0, 255, 0), -1)
    
    # write text on button
    cv2.putText(screen, "EXPORT", (button_loc[0]+10, button_loc[1]+30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,0), 2)
    
    # 3. Save Screen
    screen_path = "test_screen.png"
    cv2.imwrite(screen_path, screen)
    
    # 4. Create "Template" (crop of the button)
    template = screen[button_loc[1]:button_loc[1]+button_size[1], button_loc[0]:button_loc[0]+button_size[0]]
    template_path = "test_template_button.png"
    cv2.imwrite(template_path, template)
    
    return screen_path, template_path, button_loc

def main():
    print("Testing Visual Verifier Logic...")
    
    # Setup data
    screen_path, template_path, expected_loc = create_dummy_screen_and_template()
    
    verifier = VisualVerifier()
    
    # Load screen manually to verify logic (skipping capture_screen so we don't rely on actual desktop)
    screen_img = cv2.imread(screen_path)
    
    print(f"Searching for template '{template_path}' in synthetic screen...")
    match = verifier.find_template(template_path, screen_image=screen_img)
    
    if match:
        x, y, w, h = match
        print(f"✅ Match Found at: ({x}, {y})")
        
        # Verify location matches expected
        if abs(x - expected_loc[0]) < 5 and abs(y - expected_loc[1]) < 5:
             print("✅ Location is correct!")
        else:
             print(f"❌ Location mismatch! Expected {expected_loc}, Got ({x},{y})")
    else:
        print("❌ No match found!")

    # Cleanup
    if os.path.exists(screen_path): os.remove(screen_path)
    if os.path.exists(template_path): os.remove(template_path)

if __name__ == "__main__":
    main()
