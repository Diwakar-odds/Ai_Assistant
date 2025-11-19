#!/usr/bin/env python3
"""
Enhanced wake word detection with fuzzy matching
"""

import difflib
from typing import List

def enhanced_wake_word_detection(text: str, wake_words: List[str], threshold: float = 0.6) -> tuple[bool, str]:
    """
    Enhanced wake word detection with fuzzy matching for better accuracy
    
    Args:
        text: The recognized speech text
        wake_words: List of wake words to detect
        threshold: Similarity threshold (0.0 to 1.0)
    
    Returns:
        (detected: bool, wake_word: str)
    """
    text_lower = text.lower().strip()
    
    # Direct match (highest priority)
    for wake_word in wake_words:
        if wake_word.lower() in text_lower:
            return True, wake_word
    
    # Fuzzy matching for similar sounds
    for wake_word in wake_words:
        # Check similarity ratio
        similarity = difflib.SequenceMatcher(None, wake_word.lower(), text_lower).ratio()
        if similarity >= threshold:
            return True, wake_word
        
        # Check if words are in text (partial matching)
        wake_word_parts = wake_word.lower().split()
        text_words = text_lower.split()
        
        matches = 0
        for part in wake_word_parts:
            for word in text_words:
                if difflib.SequenceMatcher(None, part, word).ratio() >= threshold:
                    matches += 1
                    break
        
        # If most parts match
        if matches >= len(wake_word_parts) * 0.7:
            return True, wake_word
    
    return False, ""

# Example usage:
if __name__ == "__main__":
    wake_words = ["hey daddy", "arre daddy", "sun daddy"]
    
    test_cases = [
        "hey daddy open chrome",
        "hey data open chrome",  # mishearing
        "are daddy tell time",   # mishearing
        "sun daddy volume up",
        "hey teddy",            # too different
        "daddy hey",            # reversed
    ]
    
    for test in test_cases:
        detected, word = enhanced_wake_word_detection(test, wake_words)
        print(f"'{test}' -> {detected} ({word})")