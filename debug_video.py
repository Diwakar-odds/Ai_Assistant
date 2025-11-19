#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug Video Analysis Script
"""

import sys
import os
from modules.multimodal import MultiModalAI
import cv2
from PIL import Image

def main():
    """Debug video analysis."""
    
    video_path = r"c:\Users\hp\Videos\Captures\Cutting-Edge AI Assistant UI and 6 more pages - Personal - Microsoft​ Edge 2025-11-18 06-09-43.mp4"
    
    print("=" * 70)
    print("🐛 DEBUG VIDEO ANALYSIS")
    print("=" * 70)
    print()
    
    # Test 1: Check video file
    print("TEST 1: Video File Check")
    print(f"  File exists: {os.path.exists(video_path)}")
    print(f"  File size: {os.path.getsize(video_path) / (1024*1024):.2f} MB")
    print()
    
    # Test 2: Extract a single frame
    print("TEST 2: Frame Extraction")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("  ❌ Failed to open video")
        return
    
    ret, frame = cap.read()
    if ret:
        print("  ✅ Frame extracted successfully")
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        print(f"  Frame size: {pil_image.size}")
        print(f"  Frame mode: {pil_image.mode}")
    else:
        print("  ❌ Failed to read frame")
        cap.release()
        return
    cap.release()
    print()
    
    # Test 3: Initialize AI
    print("TEST 3: AI Initialization")
    try:
        ai = MultiModalAI()
        print("  ✅ AI initialized")
        print(f"  Vision model: {ai.vision_model._model_name if hasattr(ai.vision_model, '_model_name') else 'Unknown'}")
    except Exception as e:
        print(f"  ❌ AI initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return
    print()
    
    # Test 4: Analyze single frame
    print("TEST 4: Single Frame Analysis")
    try:
        result = ai.analyze_image(pil_image, "Describe this image briefly")
        print(f"  Timestamp: {result.get('timestamp')}")
        print(f"  Confidence: {result.get('confidence')}")
        print(f"  Has analysis: {'analysis' in result}")
        
        if result.get('confidence') == 'error':
            print(f"  ❌ ERROR: {result.get('analysis')}")
        else:
            print(f"  ✅ Analysis: {result.get('analysis', '')[:100]}...")
    except Exception as e:
        print(f"  ❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    # Test 5: Check API key
    print("TEST 5: API Key Check")
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        print(f"  ✅ API key found: {api_key[:10]}...{api_key[-5:]}")
        print(f"  Key length: {len(api_key)}")
    else:
        print("  ❌ No API key found in environment")
    print()
    
    print("=" * 70)
    print("Debug complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
