import sys
import ctypes
from ctypes import wintypes
from PIL import Image, ImageDraw

def test_layered():
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    # Create a simple 64x64 transparent RGBA image with an orange glowing circle
    w, h = 64, 64
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw robot
    draw.rounded_rectangle([8, 16, 56, 56], radius=12, fill=(20, 28, 43, 255), outline=(255, 165, 0, 255), width=3)
    draw.line([32, 16, 32, 6], fill=(0, 243, 255, 255), width=3)
    draw.ellipse([29, 3, 35, 9], fill=(0, 243, 255, 255))
    draw.ellipse([20, 30, 28, 42], fill=(255, 165, 0, 255))
    draw.ellipse([36, 30, 44, 42], fill=(255, 165, 0, 255))
    draw.ellipse([24, 57, 40, 61], fill=(0, 243, 255, 255))

    print("Image created successfully, testing Win32 layered window...")

if __name__ == '__main__':
    test_layered()

