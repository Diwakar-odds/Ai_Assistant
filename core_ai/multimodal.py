"""
Bridge module for backward compatibility.
Exposes MultiModalAI and visual utilities from ai_assistant.vision.multimodal.
"""

from ai_assistant.vision.multimodal import (
    MultiModalAI,
    analyze_current_screen,
    answer_visual_question_quick,
    extract_screen_text,
    describe_current_screen,
    analyze_video_file
)

__all__ = [
    'MultiModalAI',
    'analyze_current_screen',
    'answer_visual_question_quick',
    'extract_screen_text',
    'describe_current_screen',
    'analyze_video_file'
]
