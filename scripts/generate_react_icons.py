#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate PWA icons for the React frontend
Creates icons in project/public/icons/
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.system('chcp 65001 > nul 2>&1')

from PIL import Image, ImageDraw, ImageFont

def create_icon(size, output_path):
    """Create a gradient icon with AI symbol"""
    # Create gradient background
    img = Image.new('RGB', (size, size))
    draw = ImageDraw.Draw(img)
    
    # Gradient from blue to purple
    for y in range(size):
        r = int(74 + (102 - 74) * y / size)
        g = int(144 + (117 - 144) * y / size)
        b = int(226 + (234 - 226) * y / size)
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    
    # Draw white circle (AI brain)
    padding = size // 4
    draw.ellipse(
        [padding, padding, size - padding, size - padding],
        fill='#ffffff',
        outline='#333333',
        width=max(2, size // 50)
    )
    
    # Draw "AI" text if large enough
    if size >= 128:
        try:
            font_size = size // 4
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            text = "AI"
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (size - text_width) // 2
            y = (size - text_height) // 2
            
            draw.text((x, y), text, fill='#4a90e2', font=font)
        except:
            pass
    
    # Save
    img.save(output_path, 'PNG')
    print(f"✅ Created {output_path}")

def main():
    # Create directories
    icons_dir = "project/public/icons"
    os.makedirs(icons_dir, exist_ok=True)
    
    print("🎨 Generating PWA icons for React app...\n")
    
    # Icon sizes for PWA
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    for size in sizes:
        create_icon(size, f"{icons_dir}/icon-{size}x{size}.png")
    
    print("\n✨ All icons generated successfully!")
    print(f"\n📁 Icons saved to: {icons_dir}/")
    print("\n💡 You can replace these with custom icons from:")
    print("   - Canva: https://www.canva.com")
    print("   - Figma: https://www.figma.com")
    print("   - Icon Generator: https://realfavicongenerator.net/")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure Pillow is installed:")
        print("  pip install pillow")
