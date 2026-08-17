#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Analysis Script
Analyzes a video file using the multimodal AI module
"""

import sys
import os

# Set UTF-8 encoding for console output
sys.stdout.reconfigure(encoding='utf-8')

from modules.multimodal import MultiModalAI

def main():
    """Analyze a video file."""
    
    # Video path - find the correct file
    captures_dir = r"c:\Users\hp\Videos\Captures"
    video_path = None
    
    if os.path.exists(captures_dir):
        for f in os.listdir(captures_dir):
            if '2025-11-18' in f and '.mp4' in f and 'Cutting-Edge' in f:
                video_path = os.path.join(captures_dir, f)
                break
    
    if not video_path or not os.path.exists(video_path):
        print(f"ERROR: Video file not found in {captures_dir}")
        return
    
    print("=" * 70)
    print("🎥 VIDEO ANALYSIS")
    print("=" * 70)
    print(f"📁 File: {os.path.basename(video_path)}")
    print(f"📍 Path: {video_path}")
    print()
    print("🔄 Initializing AI model...")
    
    try:
        # Initialize AI
        ai = MultiModalAI()
        
        print("✅ AI model ready")
        print()
        print("🎬 Analyzing video (this may take a minute)...")
        print()
        
        # Analyze video
        result = ai.analyze_video(
            video_path=video_path,
            prompt="Describe what's happening in this video. Focus on UI elements, text, and any activities shown.",
            max_frames=10
        )
        
        if result.get("success"):
            print()
            print("=" * 70)
            print("📊 ANALYSIS RESULTS")
            print("=" * 70)
            print()
            
            # Video properties
            props = result['video_properties']
            print(f"⏱️  Duration: {props['duration']:.1f} seconds")
            print(f"🎞️  FPS: {props['fps']:.1f}")
            print(f"📐 Resolution: {props['resolution']}")
            print(f"🔢 Total Frames: {props['frame_count']}")
            print(f"✅ Frames Analyzed: {result['frames_analyzed']}")
            print()
            
            # Summary
            print("=" * 70)
            print("📝 VIDEO SUMMARY")
            print("=" * 70)
            print()
            print(result['summary'])
            print()
            
            # Frame details
            print("=" * 70)
            print("🎞️ FRAME-BY-FRAME ANALYSIS")
            print("=" * 70)
            print()
            
            for frame in result['frame_descriptions']:
                print(f"⏰ Frame {frame['frame_number']} [{frame['timestamp']:.1f}s]:")
                print(f"   {frame['description']}")
                print()
            
            print("=" * 70)
            print("✅ Analysis complete!")
            print("=" * 70)
            
        else:
            print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
