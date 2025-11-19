#!/usr/bin/env python3
"""
Example usage of YourDaddy Assistant Multilingual Features
Run this file to test the multilingual capabilities
"""

from modules.multilingual import MultilingualSupport, Language

def main():
    print("🚀 YourDaddy Assistant - Multilingual Demo")
    print("=" * 50)
    
    # Initialize multilingual support
    ml = MultilingualSupport()
    
    # Test language detection
    test_sentences = [
        "Hello, open Google Chrome please",
        "नमस्ते, कृपया क्रोम खोलिए",
        "Hi yaar, Chrome kholo please",
        "Phone kar Rahul ko",
        "Play some music बहुत बेकार lag रहा है",
        "Weather kya hai today?"
    ]
    
    print("\n📝 Language Detection Tests:")
    print("-" * 30)
    
    for sentence in test_sentences:
        context = ml.detect_language(sentence)
        print(f"Text: '{sentence}'")
        print(f"Language: {context.detected_language.value} (confidence: {context.confidence:.2f})")
        
        if context.is_mixed:
            print(f"Mixed language detected - Hindi: {context.hindi_percentage:.1f}%, English: {context.english_percentage:.1f}%")
        print()
    
    # Test Hinglish command processing
    print("\n🔄 Hinglish Command Processing:")
    print("-" * 35)
    
    hinglish_commands = [
        "Phone kar mom ko",
        "Music baja koi achha sa",
        "Google me search kar recipes",
        "Volume kam kar do",
        "Time kya hai abhi?"
    ]
    
    for command in hinglish_commands:
        result = ml.process_hinglish_command(command)
        print(f"Command: '{command}'")
        if result.get('command'):
            print(f"Detected: {result['command']}")
            if result.get('parameters'):
                print(f"Parameters: {result['parameters']}")
        else:
            print("No specific command detected")
        print()
    
    # Test translation
    print("\n🔤 Translation Tests:")
    print("-" * 20)
    
    try:
        translations = [
            ("Hello", Language.HINDI),
            ("Thank you", Language.HINDI),
            ("नमस्ते", Language.ENGLISH),
            ("धन्यवाद", Language.ENGLISH)
        ]
        
        for text, target_lang in translations:
            translated = ml.translate_text(text, target_lang)
            print(f"'{text}' -> '{translated}' ({target_lang.value})")
    
    except Exception as e:
        print(f"Translation requires internet connection: {e}")
    
    print("\n🎉 Multilingual demo completed!")
    print("\nTry these commands with your assistant:")
    print("- 'Phone kar dost ko'")
    print("- 'Music baja something romantic'") 
    print("- 'Google me search kar pizza places'")
    print("- 'Time batao please'")

if __name__ == "__main__":
    main()
