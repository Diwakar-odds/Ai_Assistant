#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate placeholder PWA icons using PIL
Run this script to create basic icons
"""

# Fix Windows console encoding for emojis
import sys
import os

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from PIL import Image, ImageDraw, ImageFont

def create_icon(size, output_path):
    """Create a simple gradient icon with AI symbol"""
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
    
    # Draw simple "AI" text if size is large enough
    if size >= 128:
        try:
            font_size = size // 4
            # Try to use a nice font, fallback to default
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
    os.makedirs("static/icons", exist_ok=True)
    os.makedirs("static/splash", exist_ok=True)
    os.makedirs("static/screenshots", exist_ok=True)
    
    # Icon sizes for PWA
    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    
    print("🎨 Generating PWA icons...\n")
    
    for size in sizes:
        create_icon(size, f"static/icons/icon-{size}x{size}.png")
    
    # Create additional icons
    print("\n🖼️ Creating additional assets...\n")
    
    # Badge icon (for notifications)
    create_icon(72, "static/icons/badge-72x72.png")
    
    # Voice icon
    create_icon(192, "static/icons/voice.png")
    
    # Chat icon
    create_icon(192, "static/icons/chat.png")
    
    # Automation icon  
    create_icon(192, "static/icons/automation.png")
    
    # Splash screen (for iOS)
    create_icon(2048, "static/splash/splash-2048x2732.png")
    
    # Screenshot placeholders
    img_desktop = Image.new('RGB', (1280, 720), color='#4a90e2')
    draw = ImageDraw.Draw(img_desktop)
    draw.text((640, 360), "Desktop Screenshot", fill='white', anchor="mm")
    img_desktop.save("static/screenshots/desktop.png")
    print("✅ Created static/screenshots/desktop.png")
    
    img_mobile = Image.new('RGB', (750, 1334), color='#667eea')
    draw = ImageDraw.Draw(img_mobile)
    draw.text((375, 667), "Mobile Screenshot", fill='white', anchor="mm")
    img_mobile.save("static/screenshots/mobile.png")
    print("✅ Created static/screenshots/mobile.png")
    
    print("\n" + "="*60)
    print("✨ All icons generated successfully!")
    print("="*60)
    print("\n📝 Next steps:")
    print("  1. Replace these placeholder icons with custom designs")
    print("  2. Use tools like Canva, Figma, or Adobe Express")
    print("  3. Or hire a designer on Fiverr ($5-20)")
    print("\n💡 Recommended: Use https://realfavicongenerator.net/")
    print("   for professional-looking icons\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure Pillow is installed:")
        print("  pip install pillow")
