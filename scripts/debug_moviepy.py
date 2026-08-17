import sys
sys.path.append(r"c:\users\hp\appdata\roaming\python\python39\site-packages")

try:
    import moviepy as mp
    print(f"MoviePy Version: {mp.__version__}")
    
    if hasattr(mp, 'VideoFileClip'):
        print("VideoFileClip found in mp")
        clip = mp.VideoFileClip("dummy_test.mp4")
        print(f"Clip methods: {[m for m in dir(clip) if 'sub' in m or 'clip' in m or 'trim' in m]}")
        print(f"Clip audio: {clip.audio}")
        clip.close()
    else:
        print("VideoFileClip NOT found in mp")

except Exception as e:
    print(f"Error: {e}")
