import sys
import os
# Force add user site packages
sys.path.append(r"c:\users\hp\appdata\roaming\python\python39\site-packages")

try:
    import moviepy as mp
    from moviepy import ColorClip, TextClip, CompositeVideoClip
except ImportError:
    # try old way just in case
    import moviepy.editor as mp
    from moviepy.editor import ColorClip, TextClip, CompositeVideoClip

def create_dummy_video(filename="dummy_test.mp4"):
    print(f"Creating dummy video: {filename}")
    
    # Create simple clip
    clip = ColorClip(size=(640, 480), color=(255, 0, 0), duration=5)
    
    # Add Text (Optional, requires ImageMagick usually, skipping to be safe)
    # just create a color clip
    
    output_path = os.path.abspath(filename)
    clip.write_videofile(output_path, fps=24, codec="libx264")
    print(f"Created: {output_path}")

if __name__ == "__main__":
    create_dummy_video()
